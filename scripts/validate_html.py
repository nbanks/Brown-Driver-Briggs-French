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
            # Compare by onclick attribute (the scholarly code identifier),
            # not by visible text (which may be translated, e.g. Isa → Es).
            onclick = tag.get("onclick", "")
            if onclick:
                result["lookup_texts"].append(onclick)
            else:
                # Fallback for reflink or lookup without onclick
                text = tag.get_text().strip()
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
        # Prefix match too short — try suffix match to catch cases where
        # a single punctuation change near the start breaks the prefix.
        for suffix_start in range(1, min(10, len(frag))):
            suffix = frag[suffix_start:]
            spos = haystack.find(suffix)
            if spos != -1:
                # Found a suffix match — the divergence is in the first
                # few characters
                txt_exp = frag[:suffix_start + ctx]
                txt_got = haystack[max(0, spos - suffix_start):spos + ctx]
                return (f"French text nearly matches HTML (diverges near "
                        f"start). txt_fr has ...{txt_exp}... "
                        f"but HTML has ...{txt_got}...")
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


def validate_html(orig_html, fr_html, txt_fr_content=None):
    """Core validation: compare French HTML against original, return error messages.

    All inputs are in-memory strings. Returns a list of plain error message
    strings (no bdb_id prefix). The caller is responsible for tagging errors
    with an identifier if needed.

    Args:
        orig_html: Original English HTML content.
        fr_html: French translated HTML content.
        txt_fr_content: Optional French plain-text content. When provided,
            checks that every line appears verbatim in fr_html.
    """
    found = []

    orig_soup = BeautifulSoup(orig_html, "lxml")
    fr_soup = BeautifulSoup(fr_html, "lxml")
    orig = extract_preserved(orig_html, orig_soup)
    fr = extract_preserved(fr_html, fr_soup)

    # 1. Hebrew/Aramaic text preserved
    orig_heb = set(orig["hebrew_texts"])
    fr_heb = set(fr["hebrew_texts"])
    for t in orig_heb - fr_heb:
        found.append(f"missing Hebrew/Aramaic: {t}")

    # 2. Placeholders preserved
    orig_ph = sorted(orig["placeholder_tags"])
    fr_ph = sorted(fr["placeholder_tags"])
    if orig_ph != fr_ph:
        found.append(f"placeholder mismatch: orig={orig_ph} fr={fr_ph}")

    # 3. Ref attributes preserved (counted — catches duplicates changed)
    orig_refs = Counter(a.get("ref", "") for a in orig["ref_attrs"] if a.get("ref"))
    fr_refs = Counter(a.get("ref", "") for a in fr["ref_attrs"] if a.get("ref"))
    for r, count in sorted((orig_refs - fr_refs).items()):
        found.append(f"missing ref attribute: {r} (×{count})")

    # 4. Lookup/reflink abbreviations preserved (by onclick attribute)
    orig_lu = set(orig["lookup_texts"])
    fr_lu = set(fr["lookup_texts"])
    missing_lu = orig_lu - fr_lu
    extra_lu = fr_lu - orig_lu
    for t in missing_lu:
        hint = ""
        if extra_lu:
            hint = (f" (French HTML has {extra_lu} instead — "
                    f"attributes must be copied exactly from the "
                    f"original, only the visible display text between "
                    f"the tags should be translated)")
        found.append(f"missing lookup attribute: \"{t}\"{hint}")

    # 5. Entry IDs preserved
    orig_ent = set(orig["entry_texts"])
    fr_ent = set(fr["entry_texts"])
    for t in orig_ent - fr_ent:
        found.append(f"missing entry ID: {t}")

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
                f"English book name in <ref> display text: "
                f"\"{display_stripped}\" (in <ref ref=\"{ref_attr}\">)")
        elif ":" in display_stripped and re.search(r"\d+:\d+", display_stripped):
            found.append(
                f"colon in <ref> display text (use comma): "
                f"\"{display_stripped}\" (in <ref ref=\"{ref_attr}\">)")

    # 6b. Lookup display text: check for untranslated English book abbreviations
    for tag in fr_soup.find_all("lookup"):
        parts = []
        for child in tag.children:
            child_name = getattr(child, "name", None)
            if child_name in ("sup", "sub", "bdbheb", "bdbarc", "reflink"):
                continue
            parts.append(child.get_text() if hasattr(child, "get_text") else str(child))
        base_text = normalize_ws("".join(parts))
        if base_text:
            m = _ENG_BOOK_RE.search(base_text)
            if m:
                onclick = tag.get("onclick", "")
                found.append(
                    f"English book name in <lookup> display text: "
                    f"\"{base_text}\" (in <lookup onclick=\"{onclick}\">)")

    # 7. French text content present verbatim (if txt_fr provided)
    if txt_fr_content is not None:
        fr_visible = re.sub(r"<[^>]+>", " ", fr_html)
        fr_visible = html.unescape(fr_visible)
        fr_visible = re.sub(r"&", "et", fr_visible)
        fr_visible = fr_visible.replace("`", "")
        fr_visible_cmp = normalize_for_compare(fr_visible)

        for line in txt_fr_content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("===") or line == "---":
                continue
            if line.startswith("@@SPLIT:") and line.endswith("@@"):
                continue
            line = _PLACEHOLDER_RE.sub("", line).strip()
            line = line.replace("^", "")
            line = line.replace("`", "")
            line = re.sub(r"_(\d+)_", "", line)
            if not line:
                continue
            if re.match(
                r"^[\u0590-\u05FF\u0600-\u06FF\s\[\]:.,;/\-—–()+|=^'\"]+$",
                line,
            ):
                continue
            line = line.replace("&", "et")
            frag = normalize_for_compare(line)
            if not frag:
                continue
            if frag not in fr_visible_cmp:
                diff_msg = _find_mismatch(frag, fr_visible_cmp)
                if diff_msg:
                    found.append(diff_msg)
                else:
                    display = normalize_ws(line)
                    if len(display) > 80:
                        display = display[:77] + "..."
                    found.append(f"French text missing from HTML: \"{display}\"")

    # 8. Extra refs in French not in original (fabricated/duplicated)
    extra_refs = fr_refs - orig_refs
    for r, count in sorted(extra_refs.items()):
        found.append(f"extra ref attribute not in original: {r} (×{count})")

    # 9. &amp; should be "et" in French text
    _visible_text = re.sub(r"<[^>]+>", " ", fr_html)
    _AMP_RE = re.compile(r"&amp;", re.IGNORECASE)
    amp_count = len(_AMP_RE.findall(_visible_text))
    if amp_count:
        found.append(
            f"&amp; in HTML should be \"et\" ({amp_count} occurrence"
            f"{'s' if amp_count > 1 else ''})")

    # 10. Tag sequence check
    _STRUCTURAL_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                        "language", "gloss", "sense", "ref", "bdbheb",
                        "bdbarc", "entry", "lookup", "reflink",
                        "transliteration"}
    _HAS_LATIN = re.compile(r"[a-zA-Z\u00C0-\u024F]")

    def _tag_seq(soup):
        seq = []
        for tag in soup.find_all(True):
            name = tag.name
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
            elif name == "highlight":
                seq.append("highlight")
            else:
                seq.append(name)
        return seq

    orig_seq = _tag_seq(orig_soup)
    fr_seq = _tag_seq(fr_soup)

    # Collapse consecutive highlights — merging adjacent highlights is
    # acceptable because French word order often differs from English,
    # making 1:1 highlight splits unnatural.
    def _dedup_highlights(seq):
        out = []
        for tag in seq:
            if tag == "highlight" and out and out[-1] == "highlight":
                continue
            out.append(tag)
        return out

    orig_seq_cmp = _dedup_highlights(orig_seq)
    fr_seq_cmp = _dedup_highlights(fr_seq)

    if orig_seq_cmp != fr_seq_cmp:
        # Build a map from (deduped) sequence index to original
        # highlight content for error messages.
        _orig_highlights = [
            tag.get_text().strip()
            for tag in orig_soup.find_all("highlight")
        ]
        _highlight_idx = 0
        _orig_highlight_at = {}  # deduped seq index -> highlight text
        prev_was_hl = False
        for si, key in enumerate(orig_seq):
            if key == "highlight":
                if not prev_was_hl and _highlight_idx < len(_orig_highlights):
                    # Find the deduped index for this highlight
                    deduped_idx = len(_dedup_highlights(orig_seq[:si + 1])) - 1
                    _orig_highlight_at[deduped_idx] = (
                        _orig_highlights[_highlight_idx])
                prev_was_hl = True
                _highlight_idx += 1
            else:
                prev_was_hl = False

        import difflib
        sm = difflib.SequenceMatcher(None, orig_seq_cmp, fr_seq_cmp)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            orig_part = orig_seq_cmp[i1:i2]
            fr_part = fr_seq_cmp[j1:j2]
            if op == "delete":
                for k, t in enumerate(orig_part):
                    hint = ""
                    if t == "highlight":
                        content = _orig_highlight_at.get(i1 + k, "")
                        if content:
                            hint = (f" (original: \"{content[:60]}\" "
                                    f"— wrap the French equivalent "
                                    f"in <highlight>)")
                    found.append(
                        f"missing tag in French: <{t}>{hint}")
            elif op == "insert":
                for t in fr_part:
                    found.append(f"extra tag in French: <{t}>")
            elif op == "replace":
                found.append(
                    f"tag sequence mismatch: original has "
                    f"{orig_part} but French has {fr_part}")

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
                f"empty <{ft.name}> tag (original had: "
                f"\"{orig_text[:50]}\")")

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
            found.append(f"possible English remnant: '{marker.strip()}'")

    return found


def validate_file(bdb_id, errors=None, *, entries_dir=None,
                   entries_fr_dir=None, txt_fr_dir=None):
    """Validate one translated entry from disk. Returns list of (bdb_id, message) tuples.

    Thin wrapper around validate_html that reads files from disk and
    prepends bdb_id to each error message.
    """
    _entries = entries_dir or ENTRIES_DIR
    _fr = entries_fr_dir or ENTRIES_FR_DIR
    _txt_fr = txt_fr_dir or TXT_FR_DIR

    fr_path = os.path.join(_fr, bdb_id + ".html")
    if not os.path.isfile(fr_path):
        return []

    orig_path = os.path.join(_entries, bdb_id + ".html")
    txt_fr_path = os.path.join(_txt_fr, bdb_id + ".txt")

    with open(orig_path, "r", encoding="utf-8") as f:
        orig_html = f.read()
    with open(fr_path, "r", encoding="utf-8") as f:
        fr_html = f.read()

    txt_fr_content = None
    if os.path.isfile(txt_fr_path):
        with open(txt_fr_path, "r", encoding="utf-8") as f:
            txt_fr_content = f.read()

    msgs = validate_html(orig_html, fr_html, txt_fr_content)
    found = [(bdb_id, msg) for msg in msgs]

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
