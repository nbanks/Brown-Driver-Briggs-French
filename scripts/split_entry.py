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


def determine_split_divs(html_text):
    """Find top-level split div spans in an HTML entry.

    Priority: stem divs > top-level sense/point divs > section divs.
    Returns list of (start, end, type_str) tuples, or [] if no splits.

    This is the canonical split-point finder used by both split_html()
    and extract_txt.inject_split_markers() to ensure consistency.
    """
    stem_spans = _find_div_spans(html_text, _STEM_DIV_RE)
    if stem_spans:
        return [(s, e, 'stem') for s, e in stem_spans]

    sense_spans = _find_div_spans(html_text, _SENSE_DIV_RE)
    point_spans = _find_div_spans(html_text, _POINT_DIV_RE)
    all_senses = sorted(sense_spans + point_spans)
    if all_senses:
        top = []
        for i, (s, e) in enumerate(all_senses):
            nested = any(s2 < s and e <= e2
                         for j, (s2, e2) in enumerate(all_senses) if i != j)
            if not nested:
                top.append((s, e, 'sense'))
        if top:
            return top

    section_spans = _find_div_spans(html_text, _SECTION_DIV_RE)
    if section_spans:
        return [(s, e, 'section') for s, e in section_spans]
    return []


def split_html(html_text):
    """Split an HTML entry into chunks at stem/sense/section divs.

    Strategy: if there are stem divs, split at stems (senses are nested
    inside stems). If there are section divs, split at sections. Otherwise,
    split at top-level sense divs. If nothing, return whole entry.

    Returns list of dicts: {"type": str, "html": str}
    Types: "header", "stem", "sense", "section", "footer", "whole"
    """
    splits = determine_split_divs(html_text)
    if not splits:
        return [{"type": "whole", "html": html_text, "label": "0"}]
    spans = [(s, e) for s, e, _ in splits]
    div_type = splits[0][2]
    return _build_chunks(html_text, spans, div_type)


def _build_chunks(html_text, spans, div_type):
    """Build chunk list from div spans.

    Ensures full coverage of html_text — every character is in exactly
    one chunk, so concatenating all chunks reproduces the original.

    Gap text between consecutive divs is appended to the PREVIOUS chunk
    (not prepended to the next), matching how extract_txt.py places
    ## SPLIT markers right after each div's opening tag.
    """
    chunks = []

    # Header: everything before first div
    header = html_text[:spans[0][0]]
    if header.strip():
        chunks.append({"type": "header", "html": header, "label": "0"})

    # Each div as its own chunk (start to end only)
    for div_num, (start, end) in enumerate(spans, 1):
        # Gap between previous div end and this div start goes to
        # the previous chunk (header or prior div)
        if div_num > 1:
            gap = html_text[spans[div_num - 2][1]:start]
        else:
            gap = html_text[spans[0][0]:start] if chunks else ""
            # If no header chunk, the first div starts at spans[0][0]
            # so gap is empty
        if gap and chunks:
            chunks[-1]["html"] += gap
        elif gap:
            # No previous chunk — create header from gap
            chunks.append({"type": "header", "html": header + gap,
                           "label": "0"})

        chunk_html = html_text[start:end]
        chunks.append({"type": div_type, "html": chunk_html,
                       "label": str(div_num)})

    # Footer: everything after last div — fold into last chunk
    # so chunk counts match txt splits (which also trim trailing ---)
    footer = html_text[spans[-1][1]:]
    if footer:
        chunks[-1]["html"] += footer

    return chunks


_SUBSENSE_DIV_RE = re.compile(r'<div\s+class="subsense"[^>]*>')


def _top_level_spans(html_text, div_re):
    """Find top-level div spans (not nested inside another of the same type)."""
    all_spans = _find_div_spans(html_text, div_re)
    top = []
    for i, (s, e) in enumerate(all_spans):
        nested = False
        for j, (s2, e2) in enumerate(all_spans):
            if i != j and s2 < s and e <= e2:
                nested = True
                break
        if not nested:
            top.append((s, e))
    return top


def _group_spans_by_size(html_text, spans, max_bytes):
    """Group consecutive div spans into sub-chunks that fit under max_bytes.

    Returns list of (start_offset, end_offset) covering all of html_text
    from spans[0] start through spans[-1] end, with inter-div gaps included.
    Each group's byte size is kept under max_bytes when possible (a single
    div exceeding the limit is kept as its own group).
    """
    groups = []
    group_start = spans[0][0]
    group_end = spans[0][1]

    for i in range(1, len(spans)):
        s, e = spans[i]
        # Prospective group: from group_start to e (includes inter-div gap)
        candidate = html_text[group_start:e].encode('utf-8')
        if len(candidate) <= max_bytes:
            group_end = e
        else:
            groups.append((group_start, group_end))
            group_start = group_end  # start from end of prev group (gap text)
            group_end = e

    groups.append((group_start, group_end))
    return groups


def subsplit_html(chunk, max_bytes=10000, max_depth=None):
    """Sub-split an oversized HTML chunk at div.sense/div.subsense boundaries.

    Recursively splits chunks that exceed max_bytes by finding nested div
    boundaries (sense, then subsense). Uses dot notation for sub-chunk
    numbering: chunk type "stem" becomes "stem.1", "stem.2", and if
    stem.1 needs further splitting it becomes "stem.1.1", "stem.1.2", etc.

    Args:
        chunk: dict with 'type' and 'html' keys
        max_bytes: target maximum size in bytes per sub-chunk
        max_depth: maximum nesting depth (None = unlimited, 1 = one level only)

    Returns list of dicts. Concatenating all 'html' values reproduces the
    original exactly.
    """
    parent_label = chunk.get("label", "")
    return _subsplit_recursive(chunk, max_bytes, max_depth, depth=0,
                               parent_label=parent_label)


def _subsplit_recursive(chunk, max_bytes, max_depth, depth,
                        parent_label=""):
    """Recursive implementation of subsplit_html."""
    chunk_html = chunk["html"]
    chunk_type = chunk["type"]

    if len(chunk_html.encode('utf-8')) <= max_bytes:
        return [chunk]

    if max_depth is not None and depth >= max_depth:
        return [chunk]

    # Find div boundaries to split on. Try sense/point first, then subsense.
    spans = _find_inner_div_spans(chunk_html)

    if not spans:
        return [chunk]

    # Group spans into sub-chunks under max_bytes
    groups = _group_spans_by_size(chunk_html, spans, max_bytes)

    # If grouping didn't actually split anything, stop recursion
    if len(groups) < 2:
        return [chunk]

    # Build sub-chunks with full coverage (header + groups + footer)
    sub_chunks = _build_sub_chunks(chunk_html, chunk_type, groups,
                                   parent_label=parent_label)

    # Verify round-trip at this level
    assert "".join(sc["html"] for sc in sub_chunks) == chunk_html, \
        f"subsplit round-trip failed at depth {depth}"

    # Recurse into any sub-chunk still over max_bytes
    final = []
    for sc in sub_chunks:
        if len(sc["html"].encode('utf-8')) > max_bytes:
            inner = _subsplit_recursive(sc, max_bytes, max_depth, depth + 1,
                                        parent_label=sc.get("label", ""))
            final.extend(inner)
        else:
            final.append(sc)

    return final


def _find_inner_div_spans(html_text):
    """Find the best set of inner div spans to split on.

    Tries sense/point divs first, then subsense divs. Filters out any
    wrapper div that spans nearly the entire text.
    """
    chunk_len = len(html_text)

    def _filter_wrapper(spans):
        """Remove spans that wrap (nearly) the whole chunk."""
        return [
            (s, e) for s, e in spans
            if not (s < 10 and e > chunk_len - 50)
        ]

    # Try sense + point divs
    spans = _top_level_spans(html_text, _SENSE_DIV_RE)
    spans += _top_level_spans(html_text, _POINT_DIV_RE)
    spans = _filter_wrapper(sorted(spans))
    if len(spans) >= 2:
        return spans

    # Try subsense divs
    spans = _top_level_spans(html_text, _SUBSENSE_DIV_RE)
    spans = _filter_wrapper(spans)
    if len(spans) >= 2:
        return spans

    return []


def _build_sub_chunks(html_text, base_type, groups, parent_label=""):
    """Build numbered sub-chunk dicts from grouped spans.

    Ensures full coverage: concat of all sub-chunk html == html_text.
    Uses dot notation: base_type.1, base_type.2, etc. (1-indexed).
    parent_label is prepended to the sub-chunk label with a dot separator.
    """
    sub_chunks = []
    header_text = html_text[:groups[0][0]]

    for i, (gs, ge) in enumerate(groups):
        if i == 0:
            html = header_text + html_text[gs:ge]
        else:
            html = html_text[groups[i - 1][1]:ge]
        sub_label = (f"{parent_label}.{i + 1}" if parent_label
                     else str(i + 1))
        sub_chunks.append({
            "type": f"{base_type}.{i + 1}",
            "html": html,
            "label": sub_label,
        })

    # Footer: append to last sub-chunk
    footer = html_text[groups[-1][1]:]
    if footer:
        sub_chunks[-1]["html"] += footer

    return sub_chunks


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
    """Split a txt entry into chunks at ## SPLIT markers (if present)
    or fall back to heuristic stem/sense detection for unmarked files.

    Returns list of dicts: {"type": str, "txt": str}
    """
    lines = txt_text.split('\n')
    marker_indices = []

    # Top-level format: ## SPLIT 1 stem (integer only, not 1.1)
    new_re = re.compile(r'^## SPLIT (\d+) (\w+)$')
    for i, line in enumerate(lines):
        m = new_re.match(line.strip())
        if m:
            marker_indices.append((i, int(m.group(1)), m.group(2)))

    if marker_indices:
        return _split_txt_by_markers(lines, marker_indices)

    # Fallback: heuristic splitting (for txt_fr or legacy files)
    if _is_verb_entry_txt(txt_text):
        return _split_txt_by_stems(lines)
    else:
        return _split_txt_by_senses(lines, txt_text)


def _split_txt_by_markers(lines, marker_indices):
    """Split txt at ## SPLIT marker lines.

    marker_indices is a list of (line_idx, marker_num_str, type_str).
    """
    chunks = []

    # Header: everything before first marker
    header_lines = lines[:marker_indices[0][0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header, "label": "0"})

    for i, (idx, marker_num, stype) in enumerate(marker_indices):
        if i + 1 < len(marker_indices):
            chunk_lines = lines[idx:marker_indices[i + 1][0]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        chunks.append({"type": stype, "txt": chunk_txt,
                       "label": str(marker_num)})

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
        return [{"type": "whole", "txt": '\n'.join(lines), "label": "0"}]

    chunks = []

    header_lines = lines[:split_indices[0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header, "label": "0"})

    for i, idx in enumerate(split_indices):
        if i + 1 < len(split_indices):
            chunk_lines = lines[idx:split_indices[i + 1]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        stem_match = STEM_LINE_RE.match(lines[idx].strip())
        stem_name = stem_match.group(1) if stem_match else "stem"
        chunks.append({"type": "stem", "txt": chunk_txt, "name": stem_name,
                       "label": str(i + 1)})

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
        return [{"type": "whole", "txt": txt_text, "label": "0"}]

    chunks = []

    header_lines = lines[:split_indices[0]]
    header = '\n'.join(header_lines)
    if header.strip():
        chunks.append({"type": "header", "txt": header, "label": "0"})

    for i, idx in enumerate(split_indices):
        if i + 1 < len(split_indices):
            chunk_lines = lines[idx:split_indices[i + 1]]
        else:
            chunk_lines = lines[idx:]
        chunk_txt = '\n'.join(chunk_lines)
        chunks.append({"type": "sense", "txt": chunk_txt,
                       "label": str(i + 1)})

    _split_footer(chunks)
    return chunks


def _split_footer(chunks):
    """No-op — the trailing --- stays in the last chunk.

    Previously this split the --- into a separate footer chunk, but that
    created a useless extra chunk every time. Now it's kept attached to
    the last real chunk so roundtrip concatenation is preserved."""
    pass


def subsplit_txt(chunk, max_bytes=10000, max_depth=None):
    """Sub-split a txt chunk at ## SPLIT N.M markers (dot-numbered).

    Parallel to subsplit_html(): takes a txt chunk that may contain
    sub-split markers like ## SPLIT 1.1 stem, ## SPLIT 1.2 stem inside it,
    and splits at those markers.

    Args:
        chunk: dict with 'type' and 'txt' keys
        max_bytes: not used directly (markers are pre-placed by extract_txt)
        max_depth: not used (markers are pre-placed)

    Returns list of dicts with 'type' and 'txt' keys. Concatenating all
    'txt' values (joined by newlines at marker boundaries) reproduces the
    original chunk content.
    """
    txt = chunk["txt"]
    base_type = chunk["type"]
    lines = txt.split('\n')

    # Find sub-split markers whose prefix matches this chunk's number.
    # e.g. if base_type came from "## SPLIT 1 stem", look for "## SPLIT 1.N stem"
    sub_re = re.compile(r'^## SPLIT (\d+(?:\.\d+)+) (\w+)$')
    sub_indices = []
    for i, line in enumerate(lines):
        m = sub_re.match(line.strip())
        if m:
            sub_indices.append((i, m.group(1), m.group(2)))

    if not sub_indices:
        return [chunk]

    # Filter to leaf markers only: a marker is a leaf if no other marker
    # has it as a prefix (e.g., 1.1 is NOT a leaf if 1.1.1 exists).
    all_nums = {num for _, num, _ in sub_indices}
    leaf_indices = [(idx, num, stype) for idx, num, stype in sub_indices
                    if not any(other.startswith(num + '.') for other in all_nums)]

    if not leaf_indices:
        return [chunk]

    # Split at leaf markers
    sub_chunks = []
    for i, (idx, num, stype) in enumerate(leaf_indices):
        if i + 1 < len(leaf_indices):
            chunk_lines = lines[idx:leaf_indices[i + 1][0]]
        else:
            chunk_lines = lines[idx:]
        sub_chunks.append({
            "type": f"{base_type}.{i + 1}",
            "txt": '\n'.join(chunk_lines),
            "label": num,  # e.g. "1.1", "5.3" — directly from ## SPLIT marker
        })

    # Header: text before first leaf marker belongs to first sub-chunk
    header_lines = lines[:leaf_indices[0][0]]
    header = '\n'.join(header_lines)
    if header.strip():
        sub_chunks[0]["txt"] = header + '\n' + sub_chunks[0]["txt"]

    return sub_chunks


def get_chunk_labels(chunks):
    """Get the list of leaf labels from a list of chunk dicts.

    Handles both top-level chunks and subsplit chunks. For each top-level
    chunk, if subsplitting produces multiple sub-chunks, their labels are
    used; otherwise the top-level chunk's label is used.
    """
    labels = []
    for c in chunks:
        if "txt" in c:
            subs = subsplit_txt(c)
        else:
            subs = subsplit_html(c)
        if len(subs) == 1:
            labels.append(c.get("label", "?"))
        else:
            for sc in subs:
                labels.append(sc.get("label", "?"))
    return labels


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
