#!/usr/bin/env python3
"""Validate translated HTML entries against originals and French text.

For each file in Entries_fr/, this script checks:
1. All Hebrew/Aramaic text (<bdbheb>, <bdbarc>) from the original is present.
2. All placeholder tags are preserved unchanged.
3. All <ref> attributes are preserved (ref, b, cBegin, vBegin, etc.).
4. All <lookup>/<reflink> abbreviations are preserved.
5. All <entry> IDs are preserved.
6. The French .txt content (from Entries_txt_fr/) appears verbatim in the
   HTML's visible text (whitespace-normalized comparison of each text
   fragment).
7. No obvious English remnants (common English words not inside preserved tags).

Usage:
    python3 scripts/validate_html.py                # validate all
    python3 scripts/validate_html.py BDB17          # validate one entry
    python3 scripts/validate_html.py --summary      # just totals

Requires: beautifulsoup4, lxml
"""

import html
import os
import re
import sys
import warnings
from collections import Counter
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
ENTRIES_FR_DIR = os.path.join(BASE, "Entries_fr")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")

# Regex to strip placeholder notation from txt_fr lines
_PLACEHOLDER_RE = re.compile(r"\[placeholder\d+:\s*Placeholders/\d+\.gif\]")


def extract_preserved(html_content, soup=None):
    """Extract all elements that must be preserved from HTML."""
    if soup is None:
        soup = BeautifulSoup(html_content, "lxml")
    result = {
        "hebrew_texts": [],
        "placeholder_tags": [],
        "ref_attrs": [],
        "lookup_texts": [],
        "entry_texts": [],
    }

    for tag in soup.find_all(True):
        name = tag.name

        # Placeholders
        m = re.match(r"placeholder(\d+)", name)
        if m:
            result["placeholder_tags"].append(name)
            continue

        if name in ("bdbheb", "bdbarc"):
            text = tag.get_text().strip()
            if text:
                result["hebrew_texts"].append(text)
        elif name == "entry":
            text = tag.get_text().strip()
            if text:
                result["entry_texts"].append(text)
        elif name == "ref":
            result["ref_attrs"].append(dict(tag.attrs))
        elif name in ("lookup", "reflink"):
            # Only compare the abbreviation code, not <sup>/<sub> prose
            # (which may be translated). Extract direct text + non-sup children.
            parts = []
            for child in tag.children:
                if getattr(child, "name", None) in ("sup", "sub"):
                    continue
                parts.append(child.get_text() if hasattr(child, "get_text") else str(child))
            text = "".join(parts).strip()
            if text:
                result["lookup_texts"].append(text)

    return result


def normalize_ws(text):
    """Collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_compare(text):
    """Strip all whitespace for content comparison.

    Tag-stripping and superscript handling introduce unpredictable spaces
    (e.g. <lookup>Dl<sup>W</sup></lookup> -> "Dl W" vs txt "DlW").
    Removing all whitespace avoids these false positives while still
    catching genuinely missing content.
    """
    return re.sub(r"\s+", "", text)


def validate_file(bdb_id, errors=None, *, entries_dir=None,
                   entries_fr_dir=None, txt_fr_dir=None):
    """Validate one translated entry. Returns list of (bdb_id, message) tuples.

    If *errors* is provided (a list), issues are also appended to it for
    backwards compatibility. The returned list is the canonical result.

    Optional keyword arguments override the module-level directory paths,
    allowing callers (tests, other scripts) to point at custom locations.
    """
    _entries = entries_dir or ENTRIES_DIR
    _fr = entries_fr_dir or ENTRIES_FR_DIR
    _txt_fr = txt_fr_dir or TXT_FR_DIR

    orig_path = os.path.join(_entries, bdb_id + ".html")
    fr_path = os.path.join(_fr, bdb_id + ".html")
    txt_fr_path = os.path.join(_txt_fr, bdb_id + ".txt")

    found = []

    if not os.path.isfile(fr_path):
        if errors is not None:
            errors.extend(found)
        return found

    with open(orig_path, "r", encoding="utf-8") as f:
        orig_html = f.read()
    with open(fr_path, "r", encoding="utf-8") as f:
        fr_html = f.read()

    orig_soup = BeautifulSoup(orig_html, "lxml")
    fr_soup = BeautifulSoup(fr_html, "lxml")
    orig = extract_preserved(orig_html, orig_soup)
    fr = extract_preserved(fr_html, fr_soup)

    # 1. Hebrew/Aramaic text preserved
    orig_heb = set(orig["hebrew_texts"])
    fr_heb = set(fr["hebrew_texts"])
    missing_heb = orig_heb - fr_heb
    for t in missing_heb:
        found.append((bdb_id, f"missing Hebrew/Aramaic: {t}"))

    # 2. Placeholders preserved
    orig_ph = sorted(orig["placeholder_tags"])
    fr_ph = sorted(fr["placeholder_tags"])
    if orig_ph != fr_ph:
        found.append((bdb_id, f"placeholder mismatch: orig={orig_ph} fr={fr_ph}"))

    # 3. Ref attributes preserved (counted — catches duplicates changed)
    orig_refs = Counter(a.get("ref", "") for a in orig["ref_attrs"] if a.get("ref"))
    fr_refs = Counter(a.get("ref", "") for a in fr["ref_attrs"] if a.get("ref"))
    missing_refs = orig_refs - fr_refs
    for r, count in sorted(missing_refs.items()):
        found.append((bdb_id, f"missing ref attribute: {r} (×{count})"))

    # 4. Lookup/reflink abbreviations preserved
    orig_lu = set(orig["lookup_texts"])
    fr_lu = set(fr["lookup_texts"])
    missing_lu = orig_lu - fr_lu
    for t in missing_lu:
        found.append((bdb_id, f"missing lookup/abbreviation: {t}"))

    # 5. Entry IDs preserved
    orig_ent = set(orig["entry_texts"])
    fr_ent = set(fr["entry_texts"])
    missing_ent = orig_ent - fr_ent
    for t in missing_ent:
        found.append((bdb_id, f"missing entry ID: {t}"))

    # 6. French text content present verbatim (if txt_fr exists)
    if os.path.isfile(txt_fr_path):
        with open(txt_fr_path, "r", encoding="utf-8") as f:
            txt_fr = f.read()

        # Extract visible text from the French HTML (strip all tags, decode entities)
        fr_visible = re.sub(r"<[^>]+>", " ", fr_html)
        fr_visible = html.unescape(fr_visible)
        # Normalize & to "et" so that HTML &amp; matches txt_fr "et"
        fr_visible = fr_visible.replace("&", " et ")
        fr_visible_cmp = normalize_for_compare(fr_visible)

        for line in txt_fr.strip().split("\n"):
            line = line.strip()
            # Skip headers, separators, blank lines
            if not line or line.startswith("===") or line == "---":
                continue
            # Strip placeholder notation, keep surrounding text
            line = _PLACEHOLDER_RE.sub("", line).strip()
            # Strip caret superscript markers (from extract_txt.py)
            line = line.replace("^", "")
            # Strip _N_ subscript markers (from extract_txt.py)
            line = re.sub(r"_(\d+)_", "", line)
            if not line:
                continue
            # Skip lines that are purely Hebrew/Aramaic + punctuation/spaces
            if re.match(
                r"^[\u0590-\u05FF\u0600-\u06FF\s\[\]:.,;/\-—–()+|=^'\"]+$",
                line,
            ):
                continue
            # Normalize and check if this fragment appears in the HTML text
            frag = normalize_for_compare(line)
            if not frag:
                continue
            if frag not in fr_visible_cmp:
                # Show the readable (whitespace-normalized) version
                display = normalize_ws(line)
                if len(display) > 80:
                    display = display[:77] + "..."
                found.append(
                    (bdb_id, f"French text missing from HTML: \"{display}\"")
                )

    # 7. Extra refs in French not in original (fabricated/duplicated)
    extra_refs = fr_refs - orig_refs
    for r, count in sorted(extra_refs.items()):
        found.append((bdb_id, f"extra ref attribute not in original: {r} (×{count})"))

    # 8. Translated tag content check
    #    Tags that should be translated: if the original had Latin-script
    #    content and the French tag is empty, that's a reassembly error
    #    (content likely floated outside the tag).
    _TRANSLATED_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                        "language", "gloss"}
    _HAS_LATIN = re.compile(r"[a-zA-Z\u00C0-\u024F]")
    orig_ttags = [t for t in orig_soup.find_all(_TRANSLATED_TAGS)]
    fr_ttags = [t for t in fr_soup.find_all(_TRANSLATED_TAGS)]
    for ot, ft in zip(orig_ttags, fr_ttags):
        if ot.name != ft.name:
            continue
        orig_text = ot.get_text().strip()
        fr_text = ft.get_text().strip()
        if orig_text and _HAS_LATIN.search(orig_text) and not fr_text:
            found.append(
                (bdb_id, f"empty <{ft.name}> tag (original had: "
                 f"\"{orig_text[:50]}\")")
            )

    # 9. English remnant check (heuristic)
    text_only = re.sub(r"<[^>]+>", " ", fr_html)
    text_only = re.sub(r"[\u0590-\u05FF]+", "", text_only)
    text_only = normalize_ws(text_only).lower()
    english_markers = [
        " the ", " of the ", " which ", " father ", " mother ",
        " son of ", "daughter of", " see ",
        " mourn ", " choose ", "worn out", " gift ",
    ]
    for marker in english_markers:
        if marker in text_only:
            found.append((bdb_id, f"possible English remnant: '{marker.strip()}'"))

    if errors is not None:
        errors.extend(found)
    return found


def main():
    summary_only = "--summary" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if args:
        bdb_ids = args
    else:
        if not os.path.isdir(ENTRIES_FR_DIR):
            print(f"No {ENTRIES_FR_DIR}/ directory found. Nothing to validate.")
            return 0
        bdb_ids = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(ENTRIES_FR_DIR)
            if f.endswith(".html")
        )

    errors = []
    for bdb_id in bdb_ids:
        errors.extend(validate_file(bdb_id))

    if summary_only:
        n_files = len(bdb_ids)
        n_errors = len(errors)
        n_clean = n_files - len(set(e[0] for e in errors))
        print(f"Validated {n_files} files: {n_clean} clean, "
              f"{n_files - n_clean} with issues ({n_errors} total issues)")
    else:
        if errors:
            for bdb_id, msg in errors:
                print(f"  {bdb_id}: {msg}")
            print(f"\n{len(errors)} issues in {len(set(e[0] for e in errors))} files")
        else:
            print(f"All {len(bdb_ids)} files validated OK")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
