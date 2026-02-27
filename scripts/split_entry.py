#!/usr/bin/env python3
"""Split BDB entries into chunks at natural boundaries.

For verb entries: split at <div class="stem"> (HTML) or stem names on their
own line (txt).
For non-verb entries: split at top-level <div class="sense"> or
<div class="section"> (HTML), or numbered senses (txt).

Each function returns a list of chunk dicts with 'type' and content keys.
"""

import re
from bs4 import BeautifulSoup, NavigableString


# All stem names found in BDB entries (used for txt splitting)
STEM_NAMES = {
    "Qal", "Qal Passive",
    "Niph`al", "Nithp.",
    "Pi`el", "Piel", "Piel.", "Pi`lel", "Pil`el.", "Pilpel", "Pil.",
    "Pu`al", "Pual", "Pu`lal",
    "Hiph`il", "Hilph.", "Hoph`al",
    "Hithpa`el", "Hithpa`al", "Hithpa`lel", "Hithpalpel",
    "Hithpe`el", "Hithpo`el", "Hithpo`lel", "Hithpolel",
    "Hithp.", "Hitph.",
    "Hothpa`al",
    "Po`el", "Po`el.", "Poe`l", "Po`êl", "Pô`el",
    "Po`al", "Po`lel", "Po`lel.", "Pol`el", "Polel", "Pô`lel", "Polpal",
    "Po`lal", "Po`lal.",
    "Po", "Po.", "Po`", "Po`.",
    "Po`l.", "Pa`el", "Pa`lel", "Palpel", "Pa.",
    "Pe`al", "Pe`al`al", "Pe`il", "Pe`îl", "Peîl", "Pe",
    "Ethpo`lel",
    "Haph`el", "Hephal",
    "Ishtaph.",
    "Ithpa`al", "Ithpe`el",
    "Shaph`el", "Tiph`el",
}

_sorted_stems = sorted(STEM_NAMES, key=len, reverse=True)
_escaped = [re.escape(s) for s in _sorted_stems]
STEM_LINE_RE = re.compile(
    r'^(' + '|'.join(_escaped) + r')\.?(?:_\d+_)?(?:\s|$)', re.MULTILINE
)

# Regex patterns for HTML div detection
_STEM_DIV_RE = re.compile(r'<div\s+class="stem"[^>]*>')
_SENSE_DIV_RE = re.compile(r'<div\s+class="sense"[^>]*>')
_SECTION_DIV_RE = re.compile(r'<div\s+class="section"[^>]*>')
_POINT_DIV_RE = re.compile(r'<div\s+class="point"[^>]*>')
_ANY_DIV_OPEN_RE = re.compile(r'<div\b[^>]*>')
_DIV_CLOSE_RE = re.compile(r'</div>')


def _find_div_spans(html_text, div_re):
    """Find the start position and end position of each div matching div_re,
    properly handling nested divs. Returns list of (start, end, type_str)."""
    results = []

    for m in div_re.finditer(html_text):
        start = m.start()
        # Now find the matching </div> by counting nesting
        depth = 1
        pos = m.end()
        while depth > 0 and pos < len(html_text):
            next_open = _ANY_DIV_OPEN_RE.search(html_text, pos)
            next_close = _DIV_CLOSE_RE.search(html_text, pos)
            if next_close is None:
                # Unclosed div — extend to end of file
                pos = len(html_text)
                break
            if next_open and next_open.start() < next_close.start():
                depth += 1
                pos = next_open.end()
            else:
                depth -= 1
                pos = next_close.end()
                if depth == 0:
                    break

        results.append((start, pos))

    return results


def split_html(html_text):
    """Split an HTML entry into chunks at stem/sense/section divs.

    Strategy: if there are stem divs, split at stems (senses are nested
    inside stems). If there are section divs, split at sections. Otherwise,
    split at top-level sense divs. If nothing, return whole entry.

    Returns list of dicts: {"type": str, "html": str}
    Types: "header", "stem", "sense", "section", "footer", "whole"
    """
    # Priority: stems > top-level senses > sections
    stem_spans = _find_div_spans(html_text, _STEM_DIV_RE)
    if stem_spans:
        return _build_chunks(html_text, stem_spans, "stem")

    # For senses, include "point" divs (variant of "sense" in ~13 entries)
    sense_spans = _find_div_spans(html_text, _SENSE_DIV_RE)
    point_spans = _find_div_spans(html_text, _POINT_DIV_RE)
    sense_spans = sorted(sense_spans + point_spans)
    if sense_spans:
        # Filter to top-level: a sense is top-level if its start position
        # is not inside another sense span
        top_senses = []
        for i, (s, e) in enumerate(sense_spans):
            nested = False
            for j, (s2, e2) in enumerate(sense_spans):
                if i != j and s2 < s and e <= e2:
                    nested = True
                    break
            if not nested:
                top_senses.append((s, e))
        if top_senses:
            return _build_chunks(html_text, top_senses, "sense")

    section_spans = _find_div_spans(html_text, _SECTION_DIV_RE)
    if section_spans:
        return _build_chunks(html_text, section_spans, "section")

    return [{"type": "whole", "html": html_text}]


def _build_chunks(html_text, spans, div_type):
    """Build chunk list from div spans.

    Ensures full coverage of html_text — every character is in exactly
    one chunk, so concatenating all chunks reproduces the original.
    """
    chunks = []

    # Header: everything before first div
    header = html_text[:spans[0][0]]
    if header.strip():
        chunks.append({"type": "header", "html": header})

    # Each div, including any gap before it (inter-div whitespace)
    prev_end = spans[0][0]
    for start, end in spans:
        # Include gap between previous chunk end and this div start
        chunk_html = html_text[prev_end:end]
        chunks.append({"type": div_type, "html": chunk_html})
        prev_end = end

    # Footer: everything after last div — fold into last chunk
    # so chunk counts match txt splits (which also trim trailing ---)
    footer = html_text[prev_end:]
    if footer:
        chunks[-1]["html"] += footer

    return chunks



def _is_verb_entry_txt(txt_text):
    """Detect if a txt entry is a verb entry by looking for stem headings
    preceded by blank lines."""
    lines = txt_text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if STEM_LINE_RE.match(stripped):
            if i > 0 and lines[i - 1].strip() == '':
                return True
    return False


def split_txt(txt_text):
    """Split a txt entry into chunks at @@SPLIT:type@@ markers (if present)
    or fall back to heuristic stem/sense detection for unmarked files.

    Returns list of dicts: {"type": str, "txt": str}
    """
    # Primary: use @@SPLIT markers injected by extract_txt.py v4
    marker_re = re.compile(r'^@@SPLIT:(\w+)@@$')
    lines = txt_text.split('\n')
    marker_indices = []
    for i, line in enumerate(lines):
        m = marker_re.match(line.strip())
        if m:
            marker_indices.append((i, m.group(1)))

    if marker_indices:
        return _split_txt_by_markers(lines, marker_indices)

    # Fallback: heuristic splitting (for txt_fr or legacy files)
    if _is_verb_entry_txt(txt_text):
        return _split_txt_by_stems(lines)
    else:
        return _split_txt_by_senses(lines, txt_text)


def _split_txt_by_markers(lines, marker_indices):
    """Split txt at @@SPLIT:type@@ marker lines."""
    chunks = []

    # Header: everything before first marker
    header_lines = lines[:marker_indices[0][0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header})

    for i, (idx, stype) in enumerate(marker_indices):
        if i + 1 < len(marker_indices):
            chunk_lines = lines[idx:marker_indices[i + 1][0]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        chunks.append({"type": stype, "txt": chunk_txt})

    _split_footer(chunks)
    return chunks


def _split_txt_by_stems(lines):
    """Split txt at real stem name boundaries.

    Uses Hebrew-anchored heuristic to skip inline stem references."""
    split_indices = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if STEM_LINE_RE.match(stripped):
            if i > 0 and lines[i - 1].strip() == '':
                split_indices.append(i)

    if not split_indices:
        return [{"type": "whole", "txt": '\n'.join(lines)}]

    chunks = []

    header_lines = lines[:split_indices[0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header})

    for i, idx in enumerate(split_indices):
        if i + 1 < len(split_indices):
            chunk_lines = lines[idx:split_indices[i + 1]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        stem_match = STEM_LINE_RE.match(lines[idx].strip())
        stem_name = stem_match.group(1) if stem_match else "stem"
        chunks.append({"type": "stem", "txt": chunk_txt, "name": stem_name})

    _split_footer(chunks)
    return chunks


def _split_txt_by_senses(lines, txt_text):
    """Split txt at top-level numbered sense boundaries."""
    sense_re = re.compile(r'^(\d+)\.(\s|$)')

    # Find all candidate sense lines preceded by blank lines
    candidates_with_blank = []
    sense_1_no_blank = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = sense_re.match(stripped)
        if m:
            num = int(m.group(1))
            preceded_by_blank = i > 0 and lines[i - 1].strip() == ''
            if preceded_by_blank:
                candidates_with_blank.append((i, num))
            elif num == 1 and sense_1_no_blank is None:
                sense_1_no_blank = i

    # If we found sense 2+ with blank lines, and sense 1 without,
    # include sense 1 as well (handles BDB entries where pos is inside
    # the first sense div and extract_txt doesn't produce a blank line)
    split_indices = [idx for idx, _ in candidates_with_blank]
    if (sense_1_no_blank is not None
            and any(n >= 2 for _, n in candidates_with_blank)
            and not any(n == 1 for _, n in candidates_with_blank)):
        split_indices.insert(0, sense_1_no_blank)

    if not split_indices:
        return [{"type": "whole", "txt": txt_text}]

    chunks = []

    header_lines = lines[:split_indices[0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header})

    for i, idx in enumerate(split_indices):
        if i + 1 < len(split_indices):
            chunk_lines = lines[idx:split_indices[i + 1]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        chunks.append({"type": "sense", "txt": chunk_txt})

    _split_footer(chunks)
    return chunks


def _split_footer(chunks):
    """No-op — the trailing --- stays in the last chunk.

    Previously this split the --- into a separate footer chunk, but that
    created a useless extra chunk every time. Now it's kept attached to
    the last real chunk so roundtrip concatenation is preserved."""
    pass


def extract_text_from_html_chunk(chunk_html):
    """Strip tags from an HTML chunk to get plain text, using similar logic
    to extract_txt.py. For comparison purposes only."""
    OPAQUE_TAGS = {"bdbheb", "bdbarc", "transliteration", "grk"}

    def _extract(element):
        parts = []
        for child in element.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
                continue
            name = child.name
            if not name:
                continue
            if name == "head":
                continue
            if name.startswith("placeholder"):
                m = re.match(r"placeholder(\d+)", name)
                if m:
                    num = m.group(1)
                    parts.append(f"[placeholder{num}: Placeholders/{num}.gif]")
                continue
            if name in ("checkingneeded", "wrongreferenceremoved"):
                continue
            if name == "hr":
                parts.append("\n---\n")
                continue
            if name == "sub":
                parts.append(f"_{child.get_text()}_")
                continue
            if name == "sup":
                parts.append(f"^{child.get_text()}^")
                continue
            if name in OPAQUE_TAGS:
                parts.append(child.get_text())
                continue
            if name in ("div", "p"):
                cls = child.get("class", [])
                if isinstance(cls, list):
                    cls = " ".join(cls)
                if cls in ("sense", "subsense", "stem", "section"):
                    parts.append("\n")
                elif name == "p":
                    parts.append("\n")
                parts.append(_extract(child))
                continue
            if name == "entry":
                continue
            if name == "h1":
                continue
            parts.append(_extract(child))
        return "".join(parts)

    soup = BeautifulSoup(chunk_html, "lxml")
    body = soup.find("body") or soup
    raw = _extract(body)

    lines = raw.split("\n")
    cleaned = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
