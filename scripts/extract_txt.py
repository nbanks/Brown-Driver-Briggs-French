#!/usr/bin/env python3
"""Extract readable plain text from BDB HTML entries.

Reads each .html file from Entries/ and writes a .txt file to Entries_txt/
with all HTML tags stripped, except:
- Placeholder references become [placeholder8: Placeholders/8.gif]
  so translators (human or LLM) can view the cognate script image.
- Hebrew/Aramaic text from <bdbheb> and <bdbarc> tags is preserved inline.
- Scholarly abbreviations from <lookup>/<reflink> are preserved inline.
- Transliterations from <transliteration> are preserved inline.
- Biblical references show their display text (e.g. "Gen 44:19").
- BDB entry IDs and Strong numbers are shown on a header line.

The output is easy to read and translate into French.  A separate step will
reinsert the HTML structure using both the English HTML and the French .txt.

Usage:
    python3 scripts/extract_txt.py                # extract all
    python3 scripts/extract_txt.py BDB17          # extract one entry
    python3 scripts/extract_txt.py BDB17 BDB998   # extract several

Requires: beautifulsoup4, lxml
"""

import os
import re
import sys
from bs4 import BeautifulSoup, NavigableString
from split_entry import subsplit_html, determine_split_divs


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
TXT_DIR = os.path.join(BASE, "Entries_txt")

# Tags whose content is opaque (not translatable) -- emit text as-is
OPAQUE_TAGS = {"bdbheb", "bdbarc", "transliteration", "grk"}

# ---------------------------------------------------------------------------
# Split-marker injection (v4 approach)
#
# Before BS4 parsing, use regex to find top-level split div positions in
# the raw HTML (same logic as split_entry.split_html), then inject
# ## SPLIT N type text right after each opening <div> tag.  BS4 preserves
# these as text nodes, and extract_text passes them through.  The marker
# lines let split_entry split txt files without heuristics.
# ---------------------------------------------------------------------------

_ANY_DIV_OPEN_RE = re.compile(r'<div\b[^>]*>')

DEFAULT_MAX_BYTES = 10000


def inject_split_markers(html_text, max_bytes=DEFAULT_MAX_BYTES):
    """Inject ## SPLIT markers after each split div's opening tag.

    Top-level markers use position-based div detection (reliable even
    for entries with nested/overlapping divs):
        ## SPLIT 1 stem
        ## SPLIT 2 stem

    Sub-split markers use subsplit_html from split_entry to guarantee
    exact alignment with the assembly pipeline:
        ## SPLIT 1.1 stem
        ## SPLIT 1.2 stem
    """
    splits = determine_split_divs(html_text)
    if not splits:
        return html_text

    # Collect all marker injection points: (insert_pos, marker_text)
    markers = []

    # Sub-split the header (content before first div) if oversized
    header_html = html_text[:splits[0][0]]
    if header_html.strip():
        header_chunk = {"type": "header", "html": header_html}
        header_subs = subsplit_html(header_chunk, max_bytes=max_bytes)
        if len(header_subs) > 1:
            sub_offset = 0
            for i, sc in enumerate(header_subs):
                sub_end = sub_offset + len(sc["html"])
                suffix = sc["type"][len("header"):]  # e.g. ".1"
                sub_num = f"0{suffix}"
                m2 = _ANY_DIV_OPEN_RE.search(html_text, sub_offset)
                if m2 and m2.start() < sub_end:
                    markers.append((m2.end(),
                                    f'## SPLIT {sub_num} header'))
                sub_offset = sub_end

    for num, (start, end, stype) in enumerate(splits, 1):
        # Top-level marker
        m = _ANY_DIV_OPEN_RE.match(html_text, start)
        if m:
            markers.append((m.end(), f'## SPLIT {num} {stype}'))

        # Sub-split markers: build the chunk the same way _build_chunks
        # does (including gap text from previous div end) so subsplit_html
        # sees the same content as the assembly pipeline.
        if num == 1:
            chunk_start = start
        else:
            chunk_start = splits[num - 2][1]  # end of previous div
        chunk_html = html_text[chunk_start:end]
        if num == len(splits):
            chunk_html += html_text[end:]  # footer for last chunk
        chunk = {"type": stype, "html": chunk_html}
        # Get depth-1 sub-chunks first (to emit intermediate markers),
        # then the fully-recursive sub-chunks for leaf markers.
        depth1_subs = subsplit_html(chunk, max_bytes=max_bytes,
                                    max_depth=1)
        all_subs = subsplit_html(chunk, max_bytes=max_bytes)

        if len(all_subs) > 1:
            # Emit depth-1 markers (e.g. ## SPLIT 1.1, 1.2, ...)
            # These serve as intermediate grouping markers.
            if len(depth1_subs) > 1:
                d1_offset = start
                d1_gap = start - chunk_start
                for i, sc in enumerate(depth1_subs):
                    if i == 0:
                        d1_end = d1_offset + len(sc["html"]) - d1_gap
                    else:
                        d1_end = d1_offset + len(sc["html"])
                    suffix = sc["type"][len(stype):]
                    sub_num = f"{num}{suffix}"
                    m2 = _ANY_DIV_OPEN_RE.search(html_text, d1_offset)
                    if m2 and m2.start() < d1_end:
                        markers.append((m2.end(),
                                        f'## SPLIT {sub_num} {stype}'))
                    d1_offset = d1_end

            # Emit leaf markers (e.g. ## SPLIT 1.1.1, 1.1.2, ...)
            # Skip any that duplicate depth-1 markers (same suffix).
            d1_suffixes = set()
            for sc in depth1_subs:
                d1_suffixes.add(sc["type"][len(stype):])

            sub_offset = start
            gap_len = start - chunk_start
            for i, sc in enumerate(all_subs):
                if i == 0:
                    sub_end = sub_offset + len(sc["html"]) - gap_len
                else:
                    sub_end = sub_offset + len(sc["html"])
                suffix = sc["type"][len(stype):]
                # Skip if this is already covered by a depth-1 marker
                if suffix not in d1_suffixes:
                    sub_num = f"{num}{suffix}"
                    m2 = _ANY_DIV_OPEN_RE.search(html_text, sub_offset)
                    if m2 and m2.start() < sub_end:
                        markers.append((m2.end(),
                                        f'## SPLIT {sub_num} {stype}'))
                sub_offset = sub_end

    # Insert in reverse position order to preserve offsets.
    # Secondary sort: longer markers first (deeper sub-splits), so that
    # when parent and child share a position, the parent is inserted last
    # and thus appears first in the output.
    markers.sort(key=lambda x: (-x[0], -len(x[1])))
    result = html_text
    for pos, marker_text in markers:
        result = result[:pos] + f'\n{marker_text}\n' + result[pos:]
    return result


def extract_text(element, entry_ids, in_h1=False):
    """Recursively extract readable text from a BeautifulSoup element."""
    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            # Suppress bracket noise around Strong numbers in <h1>
            if in_h1:
                text = re.sub(r"[\[\]\n]", "", text)
                if text.strip():
                    parts.append(text)
                continue
            parts.append(text)
            continue

        name = child.name
        if not name:
            continue

        # Skip <head>
        if name == "head":
            continue

        # <h1> -- extract entry IDs, suppress bracket text
        if name == "h1":
            extract_text(child, entry_ids, in_h1=True)
            continue

        # Entry IDs -> collect separately
        if name == "entry":
            entry_ids.append(child.get_text().strip())
            continue

        # Placeholder -> image reference
        if name.startswith("placeholder"):
            m = re.match(r"placeholder(\d+)", name)
            if m:
                num = m.group(1)
                parts.append(f"[placeholder{num}: Placeholders/{num}.gif]")
            continue

        # Self-closing markers -- skip silently
        if name in ("checkingneeded", "wrongreferenceremoved"):
            continue

        # <hr> -> separator
        if name == "hr":
            parts.append("\n---\n")
            continue

        # <sub>/<sup> -- add bracketed superscript/subscript marker
        if name == "sub":
            parts.append(f"_{child.get_text()}_")
            continue
        if name == "sup":
            parts.append(f"^{child.get_text()}^")
            continue

        # Opaque tags -- emit their text without recursion into sub-tags
        if name in OPAQUE_TAGS:
            parts.append(child.get_text())
            continue

        # Block elements -> add newlines
        if name in ("div", "p"):
            cls = child.get("class", [])
            if isinstance(cls, list):
                cls = " ".join(cls)
            if cls in ("sense", "subsense", "stem"):
                parts.append("\n")
            elif name == "p":
                parts.append("\n")
            parts.append(extract_text(child, entry_ids))
            continue

        # Everything else: recurse
        parts.append(extract_text(child, entry_ids))

    return "".join(parts)


def extract_file(html_path):
    """Parse one HTML file and return plain text."""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Inject split markers into raw HTML before BS4 parsing
    marked_content = inject_split_markers(content)

    soup = BeautifulSoup(marked_content, "lxml")
    entry_ids = []
    body = extract_text(soup, entry_ids)

    # Clean up whitespace, preserving ## SPLIT markers
    lines = body.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## SPLIT "):
            cleaned.append(stripped)
        else:
            cleaned.append(re.sub(r"[ \t]+", " ", line).strip())
    body = "\n".join(cleaned)
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = body.strip()

    header = " ".join(entry_ids)
    if header:
        return f"=== {header} ===\n{body}\n"
    return body + "\n"


def main():
    if not os.path.isdir(ENTRIES_DIR):
        print(f"error: {ENTRIES_DIR} not found", file=sys.stderr)
        return 1

    os.makedirs(TXT_DIR, exist_ok=True)

    # Determine which files to process
    if len(sys.argv) > 1:
        targets = []
        for arg in sys.argv[1:]:
            name = arg if arg.endswith(".html") else arg + ".html"
            path = os.path.join(ENTRIES_DIR, name)
            if os.path.isfile(path):
                targets.append(name)
            else:
                print(f"warning: {path} not found, skipping", file=sys.stderr)
        if not targets:
            print("error: no valid files to process", file=sys.stderr)
            return 1
    else:
        targets = sorted(
            f for f in os.listdir(ENTRIES_DIR)
            if f.endswith(".html") and f != "style.css"
        )

    count = 0
    for filename in targets:
        html_path = os.path.join(ENTRIES_DIR, filename)
        txt_name = filename.replace(".html", ".txt")
        txt_path = os.path.join(TXT_DIR, txt_name)

        text = extract_file(html_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        count += 1

    print(f"Extracted {count} files to {TXT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
