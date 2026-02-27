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
7. (removed — redundant with other checks)

Usage:
    python3 scripts/validate_html.py                # validate all
    python3 scripts/validate_html.py BDB17          # validate one entry
    python3 scripts/validate_html.py --summary      # just totals
    python3 scripts/validate_html.py BDB1045 --chunk 1   # validate chunk 1 only
    python3 scripts/validate_html.py BDB1045 --chunk 1 5 # validate chunks 1 and 5

Requires: beautifulsoup4, lxml
"""

import difflib
import html
import os
import re
import sys
import warnings
from collections import Counter
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def _stripped_to_orig_map(stripped, original):
    """Build a mapping from each index in *stripped* to the corresponding
    index in *original*, where *stripped* = re.sub(r'\\s+', '', original).
    Returns a list where map[i] is the index into *original* for stripped[i].
    """
    mapping = []
    j = 0
    for i in range(len(original)):
        if j >= len(stripped):
            break
        if not original[i].isspace() and original[i] == stripped[j]:
            mapping.append(i)
            j += 1
    return mapping


def _readable_ctx(stripped, orig, smap, start, end, ctx=20):
    """Extract a readable (with spaces) context snippet from *orig* around
    the region [start, end) in *stripped*.  Falls back to *stripped* slice
    if no mapping is available.
    """
    if smap and orig:
        # Map stripped indices to original indices
        o_start = smap[max(0, start - ctx)] if start - ctx >= 0 else 0
        o_end_idx = min(end + ctx, len(smap) - 1) if end + ctx < len(smap) else len(orig)
        o_end = smap[o_end_idx] + 1 if end + ctx < len(smap) else len(orig)
        return orig[o_start:o_end].strip()
    return stripped[max(0, start - ctx):end + ctx]


def _find_mismatch(frag, haystack, ctx=15,
                   frag_orig=None, haystack_orig=None):
    """Find the longest prefix of *frag* that appears in *haystack* and
    return a message showing where they diverge.

    Both frag and haystack are whitespace-stripped strings (from
    normalize_for_compare).  If frag_orig / haystack_orig are provided
    (the pre-stripped versions), the error message will show readable
    context with spaces preserved.

    Returns None if no partial match is found (less than 40% of frag
    matches).
    """
    # Build index mappings for readable output
    frag_map = _stripped_to_orig_map(frag, frag_orig) if frag_orig else None
    hay_map = _stripped_to_orig_map(haystack, haystack_orig) if haystack_orig else None

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
                txt_exp = _readable_ctx(frag, frag_orig, frag_map,
                                        0, suffix_start + ctx, ctx=0)
                txt_got = _readable_ctx(haystack, haystack_orig, hay_map,
                                        max(0, spos - suffix_start),
                                        spos + ctx, ctx=0)
                return (f"French text nearly matches HTML (diverges near "
                        f"start). txt_fr has ...{txt_exp}... "
                        f"but HTML has ...{txt_got}...")
        return None  # too little overlap — not a near-miss

    # Show context around the divergence point
    txt_exp = _readable_ctx(frag, frag_orig, frag_map,
                            match_len, match_len, ctx)
    txt_got = _readable_ctx(haystack, haystack_orig, hay_map,
                            best_pos + match_len, best_pos + match_len, ctx)
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

_STRUCTURAL_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                    "language", "gloss", "sense", "ref", "bdbheb",
                    "bdbarc", "entry", "lookup", "reflink",
                    "transliteration"}
_HAS_LATIN = re.compile(r"[a-zA-Z\u00C0-\u024F]")

_RAW_TAG_RE = re.compile(r"<[^>]+>")
_RAW_TAG_COVERED = re.compile(
    r"^</?(highlight|pos|primary|descrip|meta|language|gloss|sense"
    r"|ref|bdbheb|bdbarc|entry|lookup|reflink|transliteration"
    r"|grk|sup|sub|placeholder\d+|checkingNeeded|wrongReferenceRemoved)\b",
    re.IGNORECASE,
)

_TRANSLATED_TAGS = {"pos", "primary", "highlight", "descrip", "meta",
                    "language", "gloss"}


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


def _dedup_highlights(seq):
    out = []
    for tag in seq:
        if tag == "highlight" and out and out[-1] == "highlight":
            continue
        out.append(tag)
    return out


def _normalize_tag(t):
    """Normalize whitespace inside a tag for comparison."""
    return re.sub(r"\s+", " ", t.strip())


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
    for t in fr_heb - orig_heb:
        found.append(f"extra Hebrew/Aramaic not in original: {t}")

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
                diff_msg = _find_mismatch(frag, fr_visible_cmp,
                                          frag_orig=line,
                                          haystack_orig=fr_visible)
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
    amp_count = len(re.findall(r"&amp;", _visible_text, re.IGNORECASE))
    if amp_count:
        found.append(
            f"&amp; in HTML should be \"et\" ({amp_count} occurrence"
            f"{'s' if amp_count > 1 else ''})")

    # 10. Tag sequence check
    orig_seq = _tag_seq(orig_soup)
    fr_seq = _tag_seq(fr_soup)

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

    # 10b. Raw tag sequence check (catches extra/missing tags that
    # BeautifulSoup auto-completes, e.g. </p></html> added by LLM in chunks)
    orig_raw_tags = [_normalize_tag(m.group()) for m in _RAW_TAG_RE.finditer(orig_html)
                     if not _RAW_TAG_COVERED.match(m.group())]
    fr_raw_tags = [_normalize_tag(m.group()) for m in _RAW_TAG_RE.finditer(fr_html)
                   if not _RAW_TAG_COVERED.match(m.group())]

    if orig_raw_tags != fr_raw_tags:
        sm = difflib.SequenceMatcher(None, orig_raw_tags, fr_raw_tags)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            orig_part = orig_raw_tags[i1:i2]
            fr_part = fr_raw_tags[j1:j2]
            if op == "delete":
                for t in orig_part:
                    found.append(f"raw tag missing in French: {t!r}")
            elif op == "insert":
                for t in fr_part:
                    found.append(f"raw tag extra in French: {t!r}")
            elif op == "replace":
                for t in orig_part:
                    found.append(f"raw tag missing in French: {t!r}")
                for t in fr_part:
                    found.append(f"raw tag extra in French: {t!r}")

    # 10c. Empty translated tag content check
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


def validate_chunks(bdb_id, chunk_indices):
    """Validate specific chunks of an entry. Returns list of (label, msg)."""
    from split_entry import split_html, split_txt

    orig_path = os.path.join(ENTRIES_DIR, bdb_id + ".html")
    fr_path = os.path.join(ENTRIES_FR_DIR, bdb_id + ".html")
    txt_fr_path = os.path.join(TXT_FR_DIR, bdb_id + ".txt")

    if not os.path.isfile(fr_path):
        return [(bdb_id, "no Entries_fr file found")]

    orig_html = open(orig_path, encoding="utf-8").read()
    fr_html = open(fr_path, encoding="utf-8").read()
    txt_fr_content = None
    if os.path.isfile(txt_fr_path):
        txt_fr_content = open(txt_fr_path, encoding="utf-8").read()

    html_chunks = split_html(orig_html)
    fr_chunks = split_html(fr_html)
    txt_chunks = split_txt(txt_fr_content) if txt_fr_content else []

    found = []
    for idx in chunk_indices:
        label = f"{bdb_id}[{idx}]"
        if idx >= len(html_chunks):
            found.append((label, f"chunk {idx} out of range "
                          f"(orig has {len(html_chunks)} chunks)"))
            continue
        if idx >= len(fr_chunks):
            found.append((label, f"chunk {idx} out of range "
                          f"(fr has {len(fr_chunks)} chunks)"))
            continue

        orig_chunk = html_chunks[idx]["html"]
        fr_chunk = fr_chunks[idx]["html"]
        txt_chunk = None
        if txt_chunks and idx < len(txt_chunks):
            txt_chunk = txt_chunks[idx]["txt"]

        msgs = validate_html(orig_chunk, fr_chunk, txt_chunk)
        if msgs:
            for msg in msgs:
                found.append((label, msg))
        else:
            found.append((label, "OK"))

    return found


def main():
    summary_only = "--summary" in sys.argv
    chunk_mode = "--chunk" in sys.argv

    # Parse --chunk indices
    chunk_indices = []
    if chunk_mode:
        ci = sys.argv.index("--chunk")
        for a in sys.argv[ci + 1:]:
            if a.startswith("-"):
                break
            try:
                chunk_indices.append(int(a))
            except ValueError:
                break

    args = [a for a in sys.argv[1:]
            if not a.startswith("-") and a not in map(str, chunk_indices)]

    if chunk_mode:
        if not args:
            print("Error: --chunk requires a BDB entry ID", file=sys.stderr)
            return 1
        bdb_id = args[0]
        if not bdb_id.startswith("BDB"):
            bdb_id = "BDB" + bdb_id
        results = validate_chunks(bdb_id, chunk_indices)
        ok = True
        for label, msg in results:
            print(f"  {label}: {msg}")
            if msg != "OK":
                ok = False
        return 0 if ok else 1

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
