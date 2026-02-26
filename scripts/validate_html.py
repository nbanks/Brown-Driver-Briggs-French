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


def _find_mismatch(frag, haystack, ctx=15):
    """Find the longest prefix of *frag* that appears in *haystack* and
    return a message showing where they diverge.

    Both frag and haystack are whitespace-stripped strings (from
    normalize_for_compare).  Returns None if no partial match is found
    (less than 40% of frag matches).
    """
    # Binary-search for the longest matching prefix
    lo, hi = 0, len(frag)
    best_pos = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        prefix = frag[:mid]
        pos = haystack.find(prefix)
        if pos != -1:
            best_pos = pos
            lo = mid + 1
        else:
            hi = mid - 1
    match_len = lo - 1  # length of the longest matching prefix
    if match_len < len(frag) * 0.4:
        return None  # too little overlap — not a near-miss

    # Show context around the divergence point
    div = best_pos + match_len
    txt_got = haystack[max(0, div - ctx):div + ctx]
    txt_exp = frag[max(0, match_len - ctx):match_len + ctx]
    pct = match_len * 100 // len(frag)
    return (f"French text nearly matches HTML ({pct}% prefix match). "
            f"Diverges at: txt_fr has ...{txt_exp}... "
            f"but HTML has ...{txt_got}...")


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

    # 6. Ref display text: check for untranslated English book abbreviations
    _ENG_BOOK_ABBREVS = {
        "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth",
        "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh",
        "Esth", "Job", "Prov", "Eccl", "Song", "Isa", "Jer", "Lam",
        "Ezek", "Dan", "Hos", "Joel", "Amos", "Obad", "Jonah",
        "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
    }
    _ENG_BOOK_RE = re.compile(
        r"\b(" + "|".join(re.escape(b) for b in sorted(_ENG_BOOK_ABBREVS, key=lambda x: -len(x))) + r")\b"
    )
    for tag in fr_soup.find_all("ref"):
        display = tag.get_text()
        display_stripped = normalize_ws(display)
        ref_attr = tag.get("ref", "")
        m = _ENG_BOOK_RE.search(display_stripped)
        if m:
            found.append(
                (bdb_id, f"English book name in <ref> display text: "
                 f"\"{display_stripped}\" (in <ref ref=\"{ref_attr}\">)")
            )
        elif ":" in display_stripped and re.search(r"\d+:\d+", display_stripped):
            found.append(
                (bdb_id, f"colon in <ref> display text (use comma): "
                 f"\"{display_stripped}\" (in <ref ref=\"{ref_attr}\">)")
            )

    # 7. French text content present verbatim (if txt_fr exists)
    if os.path.isfile(txt_fr_path):
        with open(txt_fr_path, "r", encoding="utf-8") as f:
            txt_fr = f.read()

        # Extract visible text from the French HTML (strip all tags, decode entities)
        fr_visible = re.sub(r"<[^>]+>", " ", fr_html)
        fr_visible = html.unescape(fr_visible)
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
                # Try to pinpoint where the mismatch occurs by finding
                # the longest prefix of frag that appears in fr_visible_cmp
                diff_msg = _find_mismatch(frag, fr_visible_cmp)
                if diff_msg:
                    found.append((bdb_id, diff_msg))
                else:
                    # No partial match at all — show the full line
                    display = normalize_ws(line)
                    if len(display) > 80:
                        display = display[:77] + "..."
                    found.append(
                        (bdb_id,
                         f"French text missing from HTML: \"{display}\"")
                    )

    # 8. Extra refs in French not in original (fabricated/duplicated)
    extra_refs = fr_refs - orig_refs
    for r, count in sorted(extra_refs.items()):
        found.append((bdb_id, f"extra ref attribute not in original: {r} (×{count})"))

    # 9. &amp; should be "et" in French text
    #    The original BDB uses & as shorthand; French output must spell out "et".
    #    Only flag & that appears in visible text (not inside tag attributes).
    _AMP_RE = re.compile(r"&amp;", re.IGNORECASE)
    amp_count = len(_AMP_RE.findall(fr_html))
    if amp_count:
        found.append(
            (bdb_id, f"&amp; in HTML should be \"et\" ({amp_count} occurrence"
             f"{'s' if amp_count > 1 else ''})"))

    # 10. Tag sequence check
    #    All structural tags must appear in the same order and count in
    #    the French HTML as in the original.  This catches dropped,
    #    duplicated, and reordered tags.
    _STRUCTURAL_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                        "language", "gloss", "sense", "ref", "bdbheb",
                        "bdbarc", "entry", "lookup", "reflink",
                        "transliteration"}
    _HAS_LATIN = re.compile(r"[a-zA-Z\u00C0-\u024F]")

    def _tag_seq(soup):
        """Extract ordered list of (tag_name,) for structural tags.

        For tags with identifying attributes (ref, entry, sense), include
        enough info to tell them apart.
        """
        seq = []
        for tag in soup.find_all(True):
            name = tag.name
            # Include placeholder tags
            if re.match(r"placeholder\d+", name):
                seq.append(name)
                continue
            if name not in _STRUCTURAL_TAGS:
                continue
            if name == "ref":
                seq.append(f"ref[{tag.get('ref', '')}]")
            elif name == "entry":
                seq.append(f"entry[{tag.get_text().strip()}]")
            elif name == "sense":
                seq.append(f"sense[{tag.get_text().strip()}]")
            else:
                seq.append(name)
        return seq

    orig_seq = _tag_seq(orig_soup)
    fr_seq = _tag_seq(fr_soup)

    if orig_seq != fr_seq:
        # Use SequenceMatcher to produce a clear diff
        import difflib
        sm = difflib.SequenceMatcher(None, orig_seq, fr_seq)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            orig_part = orig_seq[i1:i2]
            fr_part = fr_seq[j1:j2]
            if op == "delete":
                for t in orig_part:
                    found.append(
                        (bdb_id, f"missing tag in French: <{t}>"))
            elif op == "insert":
                for t in fr_part:
                    found.append(
                        (bdb_id, f"extra tag in French: <{t}>"))
            elif op == "replace":
                found.append(
                    (bdb_id,
                     f"tag sequence mismatch: original has "
                     f"{orig_part} but French has {fr_part}"))

    # 10b. Empty translated tag content check
    _TRANSLATED_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                        "language", "gloss"}
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

    # 11. English remnant check (heuristic)
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
