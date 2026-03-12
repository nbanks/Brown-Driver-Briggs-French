"""Data access layer: notes, results, translations, chunking.

Caches parsed data in memory; detects filesystem changes via mtime checks.
"""

import csv
import io
import json
import os
import re
import time
from collections import OrderedDict

import split_entry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    'CORRECT': '#1a7d1a',
    'ERROR':   '#b91c1c',
    'WARN':    '#a16207',
    'SKIPPED': '#4a8a8a',
}

STATUS_BG = {
    'CORRECT': '#dcfce7',
    'ERROR':   '#fee2e2',
    'WARN':    '#fef9c3',
    'SKIPPED': '#e0f2fe',
}

STATUS_RANK = {'ERROR': 0, 'WARN': 1, 'SKIPPED': 2, 'CORRECT': 3}

MODE_CONFIG = {
    'txt': {
        'results_file': 'llm_verify_txt_results.txt',
        'notes_dir': 'Entries_notes',
        'en_dir': 'Entries_txt',
        'fr_dir': 'Entries_txt_fr',
        'html_en_dir': 'Entries',
        'html_fr_dir': 'Entries_fr',
        'ext': '.txt',
    },
    'json': {
        'results_file': 'llm_verify_json_results.txt',
        'notes_dir': 'json_output_notes',
        'en_dir': 'json_output',
        'fr_dir': 'json_output_fr',
        'html_en_dir': None,
        'html_fr_dir': None,
        'ext': '.json',
    },
}

# Hebrew letter names keyed by first Unicode codepoint
HEBREW_LETTERS = {
    '\u05D0': 'Aleph', '\u05D1': 'Bet', '\u05D2': 'Gimel', '\u05D3': 'Dalet',
    '\u05D4': 'He', '\u05D5': 'Vav', '\u05D6': 'Zayin', '\u05D7': 'Chet',
    '\u05D8': 'Tet', '\u05D9': 'Yod', '\u05DA': 'Kaf', '\u05DB': 'Kaf',
    '\u05DC': 'Lamed', '\u05DD': 'Mem', '\u05DE': 'Mem', '\u05DF': 'Nun',
    '\u05E0': 'Nun', '\u05E1': 'Samekh', '\u05E2': 'Ayin', '\u05E3': 'Pe',
    '\u05E4': 'Pe', '\u05E5': 'Tsade', '\u05E6': 'Tsade', '\u05E7': 'Qof',
    '\u05E8': 'Resh', '\u05E9': 'Shin', '\u05EA': 'Tav',
}


def _stem_from_filename(filename):
    """Extract BDB stem from filename like 'BDB1234.txt' or 'BDB1234.json'."""
    return re.sub(r'\.(txt|json)$', '', filename)


def _bdb_number(stem):
    """Extract numeric part from stem like 'BDB1234'."""
    m = re.search(r'(\d+)', stem)
    return int(m.group(1)) if m else 0


def _head_word_letter(hw):
    """Extract the Hebrew letter name from a head_word string."""
    for ch in hw:
        # Strip cantillation/vowel marks (U+0590-U+05CF), get base letter
        if '\u05D0' <= ch <= '\u05EA':
            return HEBREW_LETTERS.get(ch, '')
    return ''


# ---------------------------------------------------------------------------
# In-memory cache with mtime-based invalidation
# ---------------------------------------------------------------------------

class _Cache:
    """Simple mtime-based cache for expensive data."""

    def __init__(self):
        self._results = {}      # mode -> (mtime, data)
        self._notes = {}        # mode -> (scan_time, data)
        self._head_words = {}   # stem -> head_word
        self._hw_loaded = False

    def get_results(self, project_root, mode):
        cfg = MODE_CONFIG[mode]
        path = os.path.join(project_root, cfg['results_file'])
        if not os.path.exists(path):
            return OrderedDict()
        mtime = os.path.getmtime(path)
        cached = self._results.get(mode)
        if cached and cached[0] == mtime:
            return cached[1]
        data = _parse_results_raw(path)
        self._results[mode] = (mtime, data)
        return data

    def get_notes(self, project_root, mode):
        """Scan notes dir. Re-scans if >5 seconds since last scan."""
        cached = self._notes.get(mode)
        now = time.time()
        if cached and (now - cached[0]) < 5:
            return cached[1]
        data = _scan_notes_raw(project_root, mode)
        self._notes[mode] = (now, data)
        return data

    def invalidate_notes(self, mode):
        """Force re-scan on next access."""
        self._notes.pop(mode, None)

    def get_head_words(self, project_root):
        """Load all head_words once (they don't change)."""
        if self._hw_loaded:
            return self._head_words
        json_dir = os.path.join(project_root, 'json_output')
        if not os.path.isdir(json_dir):
            return self._head_words
        for fname in os.listdir(json_dir):
            if not fname.endswith('.json'):
                continue
            stem = fname[:-5]
            path = os.path.join(json_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._head_words[stem] = data.get('head_word', '') or ''
            except Exception:
                self._head_words[stem] = ''
        self._hw_loaded = True
        return self._head_words


CACHE = _Cache()


# ---------------------------------------------------------------------------
# Results parsing (from llm_verify output)
# ---------------------------------------------------------------------------

def _parse_results_raw(path):
    """Parse llm_verify results file into grouped structure."""
    raw = OrderedDict()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            reader = csv.reader(io.StringIO(line))
            try:
                row = next(reader)
            except StopIteration:
                continue
            if len(row) < 6:
                continue
            filename = row[0].strip()
            status = row[1].strip()
            sev_str = row[2].strip()
            severity = int(sev_str) if sev_str.lstrip('-').isdigit() else 0
            reason = row[5].strip().strip('"')
            raw[filename] = {
                'status': status,
                'severity': severity,
                'reason': reason,
            }

    # Group by base filename
    grouped = OrderedDict()
    for filename, data in raw.items():
        base = filename.split(':')[0]
        if base not in grouped:
            grouped[base] = {
                'chunks': OrderedDict(),
                'worst_status': 'CORRECT',
                'worst_severity': 0,
            }
        grouped[base]['chunks'][filename] = data
        if STATUS_RANK.get(data['status'], 3) < STATUS_RANK.get(grouped[base]['worst_status'], 3):
            grouped[base]['worst_status'] = data['status']
        if data['severity'] > grouped[base]['worst_severity']:
            grouped[base]['worst_severity'] = data['severity']

    return grouped


def parse_results(project_root, mode='txt'):
    return CACHE.get_results(project_root, mode)


# ---------------------------------------------------------------------------
# Note parsing / writing
# ---------------------------------------------------------------------------

def parse_note(project_root, stem, mode='txt'):
    """Parse a note file. Returns {reviewer, text, raw, chunk_verdicts}."""
    cfg = MODE_CONFIG[mode]
    path = os.path.join(project_root, cfg['notes_dir'], stem + cfg['ext'])
    empty = {'reviewer': '', 'text': '', 'raw': '', 'chunk_verdicts': {}}
    if not os.path.exists(path):
        return empty

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return empty

    reviewer = ''
    text = content

    reviewer_match = re.search(r'^# REVIEWER:\s*(.+)$', content, re.MULTILINE)

    # Parse per-chunk verdict overrides: # VERDICT:chunk_num STATUS severity
    chunk_verdicts = {}
    for m in re.finditer(r'^# VERDICT:(\S+)\s+(\S+)\s+(\d+)', content, re.MULTILINE):
        chunk_verdicts[m.group(1)] = {
            'status': m.group(2),
            'severity': int(m.group(3)),
        }

    if reviewer_match:
        reviewer = reviewer_match.group(1).strip()

    # Text is everything after the header block
    lines = content.split('\n')
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('# '):
            body_start = i + 1
        elif line.strip() == '' and body_start > 0:
            body_start = i + 1
            break
    text = '\n'.join(lines[body_start:]).strip()

    return {'reviewer': reviewer, 'text': text, 'raw': content,
            'chunk_verdicts': chunk_verdicts}


def _scan_notes_raw(project_root, mode):
    """Scan notes directory, return dict[stem] = {reviewer, has_note}."""
    cfg = MODE_CONFIG[mode]
    notes_dir = os.path.join(project_root, cfg['notes_dir'])
    if not os.path.isdir(notes_dir):
        return {}
    result = {}
    for fname in os.listdir(notes_dir):
        stem = _stem_from_filename(fname)
        # Check if note was human-reviewed (has REVIEWER header from web UI)
        path = os.path.join(notes_dir, fname)
        human = False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if first_line.startswith('# REVIEWER:'):
                    human = True
        except OSError:
            pass
        result[stem] = {'has_note': True, 'human_note': human}
    return result


def scan_notes(project_root, mode='txt'):
    return CACHE.get_notes(project_root, mode)


def save_note(project_root, stem, mode, note_text, reviewer,
              chunk_verdicts=None):
    """Save a note with structured header and verdict overrides."""
    cfg = MODE_CONFIG[mode]
    notes_dir = os.path.join(project_root, cfg['notes_dir'])
    os.makedirs(notes_dir, exist_ok=True)
    path = os.path.join(notes_dir, stem + cfg['ext'])

    from datetime import date
    header = f'# REVIEWER: {reviewer}\n# DATE: {date.today().isoformat()}\n'
    if chunk_verdicts:
        for cnum, vdata in sorted(chunk_verdicts.items()):
            vs = vdata.get('status', '')
            sev = vdata.get('severity', 0)
            if vs:
                header += f'# VERDICT:{cnum} {vs} {sev}\n'
    header += '\n'
    content = header + note_text.rstrip() + '\n'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    CACHE.invalidate_notes(mode)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def get_chunks(project_root, stem, mode='txt'):
    """Get aligned English/French chunks for an entry.

    Returns list of dicts: [{type, label, en_text, fr_text}, ...]
    """
    cfg = MODE_CONFIG[mode]

    if mode == 'json':
        en_path = os.path.join(project_root, cfg['en_dir'], stem + cfg['ext'])
        fr_path = os.path.join(project_root, cfg['fr_dir'], stem + cfg['ext'])
        en_text = _read_file(en_path)
        fr_text = _read_file(fr_path)
        return [{'type': 'whole', 'label': 'JSON', 'en_text': en_text, 'fr_text': fr_text}]

    # txt mode: use split_txt
    en_path = os.path.join(project_root, cfg['en_dir'], stem + cfg['ext'])
    fr_path = os.path.join(project_root, cfg['fr_dir'], stem + cfg['ext'])
    en_text = _read_file(en_path)
    fr_text = _read_file(fr_path)

    if not en_text:
        return [{'type': 'whole', 'label': 'Entry', 'en_text': '', 'fr_text': fr_text}]

    en_chunks = split_entry.split_txt(en_text)
    fr_chunks = split_entry.split_txt(fr_text) if fr_text else []

    result = []
    max_len = max(len(en_chunks), len(fr_chunks))
    for i in range(max_len):
        en_c = en_chunks[i] if i < len(en_chunks) else {'type': 'missing', 'txt': '', 'label': f'chunk {i+1}'}
        fr_c = fr_chunks[i] if i < len(fr_chunks) else {'type': 'missing', 'txt': '', 'label': f'chunk {i+1}'}
        label = en_c.get('label', '') or fr_c.get('label', '') or f'chunk {i+1}'
        result.append({
            'type': en_c.get('type', 'whole'),
            'label': label,
            'en_text': en_c.get('txt', ''),
            'fr_text': fr_c.get('txt', ''),
        })

    return result


def get_html_content(project_root, stem):
    """Load rendered HTML for Entries_fr/ and Entries/, if they exist."""
    en_path = os.path.join(project_root, 'Entries', stem + '.html')
    fr_path = os.path.join(project_root, 'Entries_fr', stem + '.html')
    return {
        'en_html': _read_file(en_path),
        'fr_html': _read_file(fr_path),
    }



# Validation functions are in serve.validation — re-export for convenience
from serve.validation import (get_html_chunks, check_html_staleness,
                              check_txt_html_consistency,
                              check_txt_html_consistency_per_chunk)


def reconstruct_from_chunks(chunks_text_list, original_text):
    """Reconstruct a full file from edited chunk texts.

    split_txt() produces chunks that already include their ## SPLIT marker
    lines, but drops the blank line that separates the previous chunk's
    content from the ## SPLIT marker. We restore it by inserting a blank
    line before any chunk that starts with '## SPLIT'.
    """
    parts = []
    for i, chunk_text in enumerate(chunks_text_list):
        if i > 0 and chunk_text.startswith('## SPLIT'):
            # Ensure blank line separator before split marker
            if parts and not parts[-1].endswith('\n\n'):
                parts.append('\n')
        parts.append(chunk_text)
    result = ''.join(parts)
    if result and not result.endswith('\n'):
        result += '\n'
    return result


# ---------------------------------------------------------------------------
# Save edited translations
# ---------------------------------------------------------------------------

def save_translations(project_root, stem, mode, chunks_en=None, chunks_fr=None):
    """Save edited chunk content back to translation files."""
    cfg = MODE_CONFIG[mode]
    modified = []

    if chunks_en is not None:
        en_path = os.path.join(project_root, cfg['en_dir'], stem + cfg['ext'])
        orig_en = _read_file(en_path)
        if mode == 'json' or len(chunks_en) == 1:
            new_text = chunks_en[0]
        else:
            new_text = reconstruct_from_chunks(chunks_en, orig_en)
        with open(en_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        modified.append(cfg['en_dir'])

    if chunks_fr is not None:
        fr_path = os.path.join(project_root, cfg['fr_dir'], stem + cfg['ext'])
        orig_fr = _read_file(fr_path)
        if mode == 'json' or len(chunks_fr) == 1:
            new_text = chunks_fr[0]
        else:
            new_text = reconstruct_from_chunks(chunks_fr, orig_fr)
        with open(fr_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        modified.append(cfg['fr_dir'])

    return modified


# ---------------------------------------------------------------------------
# Head word lookup
# ---------------------------------------------------------------------------

def load_head_word(project_root, stem):
    """Load Hebrew head_word from cached data."""
    hw_map = CACHE.get_head_words(project_root)
    return hw_map.get(stem, '')


# ---------------------------------------------------------------------------
# Chunk content preview (for dropdown in dashboard)
# ---------------------------------------------------------------------------

def load_chunk_previews(project_root, stem, max_chars=60):
    """Get short previews for each chunk, both EN and FR."""
    cfg = MODE_CONFIG['txt']
    en_path = os.path.join(project_root, cfg['en_dir'], stem + '.txt')
    fr_path = os.path.join(project_root, cfg['fr_dir'], stem + '.txt')

    def _previews(path):
        text = _read_file(path)
        if not text:
            return {}
        chunks = split_entry.split_txt(text)
        result = {}
        for i, c in enumerate(chunks):
            txt = c.get('txt', '')
            lines = [l.strip() for l in txt.splitlines()
                     if l.strip() and not l.strip().startswith('## SPLIT')]
            preview = ' '.join(lines)[:max_chars]
            if len(' '.join(lines)) > max_chars:
                preview += '...'
            result[i + 1] = preview
        return result

    return {'en': _previews(en_path), 'fr': _previews(fr_path)}


# ---------------------------------------------------------------------------
# Dashboard data
# ---------------------------------------------------------------------------

# Available sort modes
# (name, Unicode character) for dropdown display
ALL_HEBREW_LETTERS = [
    ('Aleph', '\u05D0'), ('Bet', '\u05D1'), ('Gimel', '\u05D2'),
    ('Dalet', '\u05D3'), ('He', '\u05D4'), ('Vav', '\u05D5'),
    ('Zayin', '\u05D6'), ('Chet', '\u05D7'), ('Tet', '\u05D8'),
    ('Yod', '\u05D9'), ('Kaf', '\u05DB'), ('Lamed', '\u05DC'),
    ('Mem', '\u05DE'), ('Nun', '\u05E0'), ('Samekh', '\u05E1'),
    ('Ayin', '\u05E2'), ('Pe', '\u05E4'), ('Tsade', '\u05E6'),
    ('Qof', '\u05E7'), ('Resh', '\u05E8'), ('Shin', '\u05E9'),
    ('Tav', '\u05EA'),
]

SORT_MODES = {
    'severity': 'Severity (worst first)',
    'bdb': 'BDB number',
}


def get_dashboard_data(project_root, mode='txt', verdict_filter=None,
                       digit_filter=None, letter_filter=None, sort='severity',
                       page=1, per_page=100):
    """Build dashboard data.

    Returns (entries, total_count, verdict_counts, letters_available).
    """
    results = parse_results(project_root, mode)
    notes = scan_notes(project_root, mode)
    hw_map = CACHE.get_head_words(project_root)

    entries = []
    letters_seen = set()

    for filename, data in results.items():
        stem = _stem_from_filename(filename)
        bdb_num = _bdb_number(stem)
        last_digit = bdb_num % 10

        # Digit filter
        if digit_filter is not None and last_digit not in digit_filter:
            continue

        # Verdict filter
        if verdict_filter and data['worst_status'] not in verdict_filter:
            continue

        head_word = hw_map.get(stem, '')
        letter = _head_word_letter(head_word)
        letters_seen.add(letter)

        # Letter filter
        if letter_filter and letter not in letter_filter:
            continue

        note_info = notes.get(stem)
        has_note = note_info is not None
        human_note = note_info.get('human_note', False) if note_info else False

        entries.append({
            'stem': stem,
            'bdb_num': bdb_num,
            'head_word': head_word,
            'letter': letter,
            'worst_status': data['worst_status'],
            'worst_severity': data['worst_severity'],
            'chunks': data['chunks'],
            'has_note': has_note,
            'human_note': human_note,
        })

    # Sort
    if sort == 'bdb':
        entries.sort(key=lambda e: e['bdb_num'])
    else:  # severity (default)
        entries.sort(key=lambda e: (STATUS_RANK.get(e['worst_status'], 3),
                                    -e['worst_severity'], e['bdb_num']))

    # Counts summary
    verdict_counts = {}
    for e in entries:
        verdict_counts[e['worst_status']] = verdict_counts.get(e['worst_status'], 0) + 1

    total = len(entries)

    # Paginate
    start = (page - 1) * per_page
    page_entries = entries[start:start + per_page]

    return page_entries, total, verdict_counts, sorted(letters_seen)


# ---------------------------------------------------------------------------
# Navigation: find next unreviewed
# ---------------------------------------------------------------------------

def next_unreviewed(project_root, stem, mode='txt', sort='severity'):
    """Find the next entry needing review after the given stem."""
    results = parse_results(project_root, mode)
    notes = scan_notes(project_root, mode)

    current_num = _bdb_number(stem)
    candidates = []
    for filename, data in results.items():
        s = _stem_from_filename(filename)
        n = _bdb_number(s)
        if s not in notes and data['worst_status'] in ('ERROR', 'WARN'):
            candidates.append((STATUS_RANK.get(data['worst_status'], 3),
                                -data['worst_severity'], n, s))

    candidates.sort()
    # Find first after current (by BDB number)
    for _, _, n, s in candidates:
        if n > current_num:
            return s
    if candidates:
        return candidates[0][3]
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read a file, return '' if not found."""
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
