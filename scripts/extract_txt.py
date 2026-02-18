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

    soup = BeautifulSoup(content, "lxml")
    entry_ids = []
    body = extract_text(soup, entry_ids)

    # Clean up whitespace
    lines = body.split("\n")
    cleaned = []
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned.append(line)
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
