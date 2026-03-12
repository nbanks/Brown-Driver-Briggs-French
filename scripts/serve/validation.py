"""HTML validation, staleness checking, and txt/html consistency."""

import difflib
import os
import re

import split_entry


def get_html_chunks(project_root, stem):
    """Split both EN and FR HTML files into aligned chunks.

    Returns list of {label, type, en_html, fr_html} dicts.
    """
    en_path = os.path.join(project_root, 'Entries', stem + '.html')
    fr_path = os.path.join(project_root, 'Entries_fr', stem + '.html')
    en_html = _read_file(en_path)
    fr_html = _read_file(fr_path)

    en_chunks = split_entry.split_html(en_html) if en_html else []
    fr_chunks = split_entry.split_html(fr_html) if fr_html else []

    max_len = max(len(en_chunks), len(fr_chunks), 1)
    result = []
    for i in range(max_len):
        en_c = en_chunks[i] if i < len(en_chunks) else {'type': 'missing', 'html': '', 'label': '?'}
        fr_c = fr_chunks[i] if i < len(fr_chunks) else {'type': 'missing', 'html': '', 'label': '?'}
        label = en_c.get('label', '') or fr_c.get('label', '') or str(i)
        result.append({
            'type': en_c.get('type', 'whole'),
            'label': label,
            'en_html': en_c.get('html', ''),
            'fr_html': fr_c.get('html', ''),
        })
    return result


def check_html_staleness(project_root, stem):
    """Check if Entries_fr HTML is older than Entries_txt_fr txt.

    Returns True if HTML is stale (txt_fr newer than fr html).
    """
    txt_fr_path = os.path.join(project_root, 'Entries_txt_fr', stem + '.txt')
    html_fr_path = os.path.join(project_root, 'Entries_fr', stem + '.html')
    if not os.path.exists(txt_fr_path) or not os.path.exists(html_fr_path):
        return False
    return os.path.getmtime(txt_fr_path) > os.path.getmtime(html_fr_path)


def check_txt_html_consistency(project_root, stem):
    """Compare txt content against HTML-extracted text for both EN and FR.

    Returns whole-entry result: {
        'en': {'match': bool, 'diff_count': int},
        'fr': {'match': bool, 'diff_count': int},
    }
    """
    return _compare_txt_html(project_root, stem)


def check_txt_html_consistency_per_chunk(project_root, stem):
    """Compare txt vs HTML per chunk for both EN and FR.

    Returns list of per-chunk results aligned with split_txt/split_html output:
    [{en: {match, diff_count}, fr: {match, diff_count}}, ...]
    """
    results = []

    # Split txt and html for both languages
    en_txt_chunks = _split_file(project_root, 'Entries_txt', stem, 'txt')
    fr_txt_chunks = _split_file(project_root, 'Entries_txt_fr', stem, 'txt')
    en_html_chunks = _split_file(project_root, 'Entries', stem, 'html')
    fr_html_chunks = _split_file(project_root, 'Entries_fr', stem, 'html')

    max_len = max(len(en_txt_chunks), len(fr_txt_chunks),
                  len(en_html_chunks), len(fr_html_chunks), 1)

    for i in range(max_len):
        chunk_result = {'en': None, 'fr': None}

        for lang, txt_chunks, html_chunks in [
            ('en', en_txt_chunks, en_html_chunks),
            ('fr', fr_txt_chunks, fr_html_chunks),
        ]:
            if i >= len(txt_chunks) or i >= len(html_chunks):
                continue
            txt_text = txt_chunks[i]
            html_text = html_chunks[i]
            if not txt_text.strip() or not html_text.strip():
                continue
            chunk_result[lang] = _compare_texts(txt_text, html_text)

        results.append(chunk_result)

    return results


def _split_file(project_root, directory, stem, fmt):
    """Split a file into chunks, returning list of text strings."""
    ext = '.txt' if fmt == 'txt' else '.html'
    path = os.path.join(project_root, directory, stem + ext)
    content = _read_file(path)
    if not content.strip():
        return []
    if fmt == 'txt':
        chunks = split_entry.split_txt(content)
        return [c.get('txt', '') for c in chunks]
    else:
        chunks = split_entry.split_html(content)
        texts = []
        for c in chunks:
            try:
                texts.append(split_entry.extract_text_from_html_chunk(c.get('html', '')))
            except Exception:
                texts.append('')
        return texts


def _compare_texts(txt_text, html_text):
    """Compare normalized txt vs html-extracted text.

    Returns {match, diff_count, diffs} where diffs is a list of
    human-readable difference descriptions.
    """
    txt_norm = _normalize_for_compare(txt_text)
    html_norm = _normalize_for_compare(html_text)
    if txt_norm == html_norm:
        return {'match': True, 'diff_count': 0, 'diffs': []}
    txt_words = txt_norm.split()
    html_words = html_norm.split()
    sm = difflib.SequenceMatcher(None, txt_words, html_words, autojunk=False)
    diffs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        tw = ' '.join(txt_words[i1:i2])
        hw = ' '.join(html_words[j1:j2])
        if op == 'replace':
            diffs.append(f'txt «{tw}» → html «{hw}»')
        elif op == 'delete':
            diffs.append(f'txt has «{tw}» (missing in html)')
        elif op == 'insert':
            diffs.append(f'html has «{hw}» (missing in txt)')
    return {'match': False, 'diff_count': len(diffs), 'diffs': diffs}


def _compare_txt_html(project_root, stem):
    """Whole-file txt vs HTML comparison."""
    result = {'en': None, 'fr': None}
    for lang, txt_dir, html_dir in [
        ('en', 'Entries_txt', 'Entries'),
        ('fr', 'Entries_txt_fr', 'Entries_fr'),
    ]:
        txt_path = os.path.join(project_root, txt_dir, stem + '.txt')
        html_path = os.path.join(project_root, html_dir, stem + '.html')
        if not os.path.exists(txt_path) or not os.path.exists(html_path):
            continue
        txt_content = _read_file(txt_path)
        html_content = _read_file(html_path)
        if not txt_content.strip() or not html_content.strip():
            continue
        try:
            html_text = split_entry.extract_text_from_html_chunk(html_content)
        except Exception:
            result[lang] = {'match': False, 'diff_count': -1}
            continue
        result[lang] = _compare_texts(txt_content, html_text)
    return result


def _normalize_for_compare(text):
    """Normalize text for txt-vs-HTML comparison."""
    lines = text.split('\n')
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('## SPLIT ') or s.startswith('==='):
            continue
        out.append(s)
    return re.sub(r'\s+', ' ', ' '.join(out)).strip()


def _read_file(path):
    """Read a file, return '' if not found."""
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
