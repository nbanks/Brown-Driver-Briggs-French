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
# @@SPLIT:type@@ text right after each opening <div> tag.  BS4 preserves
# these as text nodes, and extract_text passes them through.  The marker
# lines let split_entry split txt files without heuristics.
# ---------------------------------------------------------------------------

_STEM_DIV_RE = re.compile(r'<div\s+class="stem"[^>]*>')
_SENSE_DIV_RE = re.compile(r'<div\s+class="sense"[^>]*>')
_SECTION_DIV_RE = re.compile(r'<div\s+class="section"[^>]*>')
_POINT_DIV_RE = re.compile(r'<div\s+class="point"[^>]*>')
_ANY_DIV_OPEN_RE = re.compile(r'<div\b[^>]*>')
_DIV_CLOSE_RE = re.compile(r'</div>')


def _find_div_spans(html_text, div_re):
    """Find (start, end) of each div matching div_re, handling nesting."""
    results = []
    for m in div_re.finditer(html_text):
        start = m.start()
        depth = 1
        pos = m.end()
        while depth > 0 and pos < len(html_text):
            next_open = _ANY_DIV_OPEN_RE.search(html_text, pos)
            next_close = _DIV_CLOSE_RE.search(html_text, pos)
            if next_close is None:
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


def _determine_split_divs(html_text):
    """Find top-level split div start positions (same logic as split_html).
    Returns list of (start_pos, type_str)."""
    stem_spans = _find_div_spans(html_text, _STEM_DIV_RE)
    if stem_spans:
        return [(s, 'stem') for s, e in stem_spans]

    sense_spans = _find_div_spans(html_text, _SENSE_DIV_RE)
    point_spans = _find_div_spans(html_text, _POINT_DIV_RE)
    all_senses = sorted(sense_spans + point_spans)
    if all_senses:
        top = []
        for i, (s, e) in enumerate(all_senses):
            nested = any(s2 < s and e <= e2
                         for j, (s2, e2) in enumerate(all_senses) if i != j)
            if not nested:
                top.append((s, 'sense'))
        if top:
            return top

    section_spans = _find_div_spans(html_text, _SECTION_DIV_RE)
    if section_spans:
        return [(s, 'section') for s, e in section_spans]
    return []


def inject_split_markers(html_text):
    """Inject @@SPLIT:type@@ text after each top-level split div's
    opening tag.  Returns modified HTML string."""
    splits = _determine_split_divs(html_text)
    if not splits:
        return html_text
    # Insert in reverse order to preserve positions
    splits.sort(key=lambda x: x[0], reverse=True)
    result = html_text
    for pos, stype in splits:
        m = _ANY_DIV_OPEN_RE.match(result, pos)
        if m:
            insert_pos = m.end()
            result = (result[:insert_pos]
                      + f'\n@@SPLIT:{stype}@@\n'
                      + result[insert_pos:])
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

    # Clean up whitespace, preserving @@SPLIT markers
    lines = body.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("@@SPLIT:") and stripped.endswith("@@"):
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
