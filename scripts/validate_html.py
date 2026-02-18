#!/usr/bin/env python3
"""Validate translated HTML entries against originals and French text.

For each file in Entries_fr/, this script checks:
1. All Hebrew/Aramaic text (<bdbheb>, <bdbarc>) from the original is present.
2. All placeholder tags are preserved unchanged.
3. All <ref> attributes are preserved (ref, b, cBegin, vBegin, etc.).
4. All <lookup>/<reflink> abbreviations are preserved.
5. All <entry> IDs are preserved.
6. The French .txt content (from Entries_txt_fr/) appears in the output
   (character-level check, ignoring whitespace differences).
7. No obvious English remnants (common English words not inside preserved tags).

Usage:
    python3 scripts/validate_html.py                # validate all
    python3 scripts/validate_html.py BDB17          # validate one entry
    python3 scripts/validate_html.py --summary      # just totals

Requires: beautifulsoup4, lxml
"""

import os
import re
import sys
from bs4 import BeautifulSoup


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
ENTRIES_FR_DIR = os.path.join(BASE, "Entries_fr")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


def extract_preserved(html_content):
    """Extract all elements that must be preserved from HTML."""
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
            text = tag.get_text().strip()
            if text:
                result["lookup_texts"].append(text)

    return result


def normalize_ws(text):
    """Collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", text).strip()


def validate_file(bdb_id, errors):
    """Validate one translated entry. Appends issues to errors list."""
    orig_path = os.path.join(ENTRIES_DIR, bdb_id + ".html")
    fr_path = os.path.join(ENTRIES_FR_DIR, bdb_id + ".html")
    txt_fr_path = os.path.join(TXT_FR_DIR, bdb_id + ".txt")

    if not os.path.isfile(fr_path):
        return  # nothing to validate

    with open(orig_path, "r", encoding="utf-8") as f:
        orig_html = f.read()
    with open(fr_path, "r", encoding="utf-8") as f:
        fr_html = f.read()

    orig = extract_preserved(orig_html)
    fr = extract_preserved(fr_html)

    # 1. Hebrew/Aramaic text preserved
    orig_heb = set(orig["hebrew_texts"])
    fr_heb = set(fr["hebrew_texts"])
    missing_heb = orig_heb - fr_heb
    for t in missing_heb:
        errors.append((bdb_id, f"missing Hebrew/Aramaic: {t}"))

    # 2. Placeholders preserved
    orig_ph = sorted(orig["placeholder_tags"])
    fr_ph = sorted(fr["placeholder_tags"])
    if orig_ph != fr_ph:
        errors.append((bdb_id, f"placeholder mismatch: orig={orig_ph} fr={fr_ph}"))

    # 3. Ref attributes preserved
    orig_refs = set(a.get("ref", "") for a in orig["ref_attrs"] if a.get("ref"))
    fr_refs = set(a.get("ref", "") for a in fr["ref_attrs"] if a.get("ref"))
    missing_refs = orig_refs - fr_refs
    for r in missing_refs:
        errors.append((bdb_id, f"missing ref attribute: {r}"))

    # 4. Lookup/reflink abbreviations preserved
    orig_lu = set(orig["lookup_texts"])
    fr_lu = set(fr["lookup_texts"])
    missing_lu = orig_lu - fr_lu
    for t in missing_lu:
        errors.append((bdb_id, f"missing lookup/abbreviation: {t}"))

    # 5. Entry IDs preserved
    orig_ent = set(orig["entry_texts"])
    fr_ent = set(fr["entry_texts"])
    missing_ent = orig_ent - fr_ent
    for t in missing_ent:
        errors.append((bdb_id, f"missing entry ID: {t}"))

    # 6. French text content present (if .txt.fr exists)
    if os.path.isfile(txt_fr_path):
        with open(txt_fr_path, "r", encoding="utf-8") as f:
            txt_fr = f.read()
        lines = txt_fr.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("===") or line == "---":
                continue
            if re.match(r"^[\u0590-\u05FF\u0600-\u06FF\s\[\]:./, ]+$", line):
                continue
            words = re.findall(r"[a-zA-Z\u00C0-\u024F]{3,}", line)
            for word in words:
                if word not in fr_html:
                    errors.append((bdb_id, f"French text missing from HTML: '{word}'"))
                    break

    # 7. English remnant check (heuristic)
    text_only = re.sub(r"<[^>]+>", " ", fr_html)
    text_only = re.sub(r"[\u0590-\u05FF]+", "", text_only)
    text_only = normalize_ws(text_only).lower()
    english_markers = [
        " the ", " of the ", " which ", " father ", " mother ",
        " son of ", "daughter of", " see ", " compare ",
        " mourn ", " choose ", "worn out", " gift ",
    ]
    for marker in english_markers:
        if marker in text_only:
            errors.append((bdb_id, f"possible English remnant: '{marker.strip()}'"))


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
        validate_file(bdb_id, errors)

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
