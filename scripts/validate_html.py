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
        # Strip <sub>...</sub> entirely (txt_fr uses _N_ which gets stripped)
        fr_visible = re.sub(r"<sub>[^<]*</sub>", " ", fr_html)
        # Strip remaining tags
        fr_visible = re.sub(r"<[^>]+>", " ", fr_visible)
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

    # 9a. &amp; in French that wasn't in original should be "et"
    _orig_visible = re.sub(r"<[^>]+>", " ", orig_html)
    _fr_visible = re.sub(r"<[^>]+>", " ", fr_html)
    orig_amp_count = len(re.findall(r"&amp;", _orig_visible))
    fr_amp_count = len(re.findall(r"&amp;", _fr_visible))
    extra_amp = fr_amp_count - orig_amp_count
    if extra_amp > 0:
        found.append(
            f"&amp; in HTML should be \"et\" ({extra_amp} occurrence"
            f"{'s' if extra_amp > 1 else ''})")

    # 9b. Bare & (not &amp;) in French HTML — bad encoding
    bare_amp = len(re.findall(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", fr_html))
    if bare_amp:
        found.append(
            f"bare & in HTML (should be &amp; or \"et\") ({bare_amp} "
            f"occurrence{'s' if bare_amp > 1 else ''})")

    # 10. Tag sequence check
    orig_seq = _tag_seq(orig_soup)
    fr_seq = _tag_seq(fr_soup)

    orig_seq_cmp = _dedup_highlights(orig_seq)
    fr_seq_cmp = _dedup_highlights(fr_seq)

    if orig_seq_cmp != fr_seq_cmp:
        # Check if the difference is only highlights moving position.
        # French word order (e.g. possessive reversal) can legitimately
        # shift <highlight> tags relative to <bdbheb> and other tags.
        # Adjacent highlights may also merge/split after dedup, so we
        # only require that non-highlight subsequences are identical.
        _orig_no_hl = [t for t in orig_seq_cmp if t != "highlight"]
        _fr_no_hl = [t for t in fr_seq_cmp if t != "highlight"]
        _highlight_reorder_only = (_orig_no_hl == _fr_no_hl)

        if _highlight_reorder_only:
            # Tolerate reordering/combining, but flag if ALL highlights
            # were stripped (likely an LLM that ignored them entirely).
            orig_hl_count = fr_seq.count("highlight")
            if orig_seq.count("highlight") > 0 and orig_hl_count == 0:
                found.append(
                    "all <highlight> tags dropped in French "
                    f"(original had {orig_seq.count('highlight')})")

        if not _highlight_reorder_only:
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


def _status_line(bdb_id, use_color=True, verbose=False):
    """Print a compact one-line status with per-chunk ✓/✗ markers.

    If verbose=True, also prints error details for failing chunks.
    Returns True if the entry has failures.
    """
    from split_entry import split_html, split_txt

    G = "\033[32m" if use_color else ""  # green
    R = "\033[31m" if use_color else ""  # red
    Y = "\033[33m" if use_color else ""  # yellow
    D = "\033[2m" if use_color else ""   # dim
    Z = "\033[0m" if use_color else ""   # reset

    orig_path = os.path.join(ENTRIES_DIR, bdb_id + ".html")
    fr_path = os.path.join(ENTRIES_FR_DIR, bdb_id + ".html")
    txt_fr_path = os.path.join(TXT_FR_DIR, bdb_id + ".txt")
    filename = bdb_id + ".html"

    if not os.path.isfile(fr_path):
        print(f"{filename:<20s} {R}MISSING{Z}")
        return True

    orig_html = open(orig_path, encoding="utf-8").read()
    fr_html = open(fr_path, encoding="utf-8").read()
    txt_fr = None
    if os.path.isfile(txt_fr_path):
        txt_fr = open(txt_fr_path, encoding="utf-8").read()

    orig_chunks = split_html(orig_html)
    n = len(orig_chunks)

    if n < 2:
        # Non-chunked: single validation
        fr_kb = len(fr_html) // 1024
        errs = validate_html(orig_html, fr_html, txt_fr)
        if errs:
            print(f"{filename:<20s} {fr_kb}KB {R}✗{Z}  {R}FAILED{Z}")
            if verbose:
                for msg in errs:
                    print(f"  {D}{msg}{Z}")
        else:
            print(f"{filename:<20s} {fr_kb}KB {G}✓{Z}  {G}CLEAN{Z}")
        return bool(errs)

    fr_chunks = split_html(fr_html)
    txt_chunks = split_txt(txt_fr) if txt_fr else []
    n_fr = len(fr_chunks)

    # Per-chunk validation (works even when chunk counts differ)
    chunks_str = []
    chunk_errors = []  # [(idx, tag, [errors])]
    any_fail = n_fr != n  # mismatch is always a failure
    for idx in range(n):
        tag = f"{idx+1}/{n}"
        if idx >= n_fr:
            chunks_str.append(f"{tag} {R}—{Z}")
            continue
        txt_c = txt_chunks[idx]["txt"] if txt_chunks and idx < len(txt_chunks) else None
        chunk_kb = len(fr_chunks[idx]["html"]) // 1024
        errs = validate_html(
            orig_chunks[idx]["html"], fr_chunks[idx]["html"], txt_c)
        if errs:
            any_fail = True
            chunks_str.append(f"{tag} {chunk_kb}KB {R}✗{Z}")
            chunk_errors.append((idx, tag, errs))
        else:
            chunks_str.append(f"{tag} {chunk_kb}KB {G}✓{Z}")

    mismatch = f"  {Y}mismatch orig={n} fr={n_fr}{Z}" if n_fr != n else ""
    status = f"{R}FAILED{Z}" if any_fail else f"{G}CLEAN{Z}"
    print(f"{filename:<20s} {' '.join(chunks_str)}{mismatch}  {status}")
    if verbose and chunk_errors:
        for idx, tag, errs in chunk_errors:
            print(f"  {R}[{tag}]{Z}")
            for msg in errs:
                print(f"    {D}{msg}{Z}")
    return any_fail


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Validate translated HTML entries against originals.",
        epilog="Examples:\n"
               "  %(prog)s                        # validate all\n"
               "  %(prog)s BDB17                   # validate one entry\n"
               "  %(prog)s --summary               # just totals\n"
               "  %(prog)s --status BDB1045         # per-chunk status\n"
               "  %(prog)s --chunk 1 5 BDB1045      # validate chunks 1 and 5\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("entries", nargs="*", metavar="BDB_ID",
                        help="Entry IDs to validate (default: all).")
    parser.add_argument("--summary", action="store_true",
                        help="Print only summary totals.")
    parser.add_argument("--status", action="store_true",
                        help="Show per-chunk validation status.")
    parser.add_argument("--chunk", nargs="+", type=int, metavar="N",
                        help="Validate specific chunk indices only.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show error details for failing chunks (with --status).")
    parser.add_argument("--colour", "--color", action="store_true",
                        help="Force colour output (even when piped).")
    args = parser.parse_args()

    use_color = args.colour or sys.stdout.isatty()

    def _normalize(bdb_id):
        return bdb_id if bdb_id.startswith("BDB") else "BDB" + bdb_id

    # --chunk mode
    if args.chunk is not None:
        if not args.entries:
            print("Error: --chunk requires a BDB entry ID", file=sys.stderr)
            return 1
        bdb_id = _normalize(args.entries[0])
        results = validate_chunks(bdb_id, args.chunk)
        ok = True
        for label, msg in results:
            print(f"  {label}: {msg}")
            if msg != "OK":
                ok = False
        return 0 if ok else 1

    # Resolve entry list
    if args.entries:
        bdb_ids = [_normalize(e) for e in args.entries]
    else:
        if not os.path.isdir(ENTRIES_FR_DIR):
            print(f"No {ENTRIES_FR_DIR}/ directory found. Nothing to validate.")
            return 0
        bdb_ids = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(ENTRIES_FR_DIR)
            if f.endswith(".html")
        )

    # --status mode: compact one-line-per-file with chunk markers
    # verbose (show errors) when specific entries are named
    if args.status:
        verbose = args.verbose
        any_fail = False
        for bdb_id in bdb_ids:
            if _status_line(bdb_id, use_color=use_color, verbose=verbose):
                any_fail = True
        return 1 if any_fail else 0

    # Validate with progress indicator, using clean cache to skip
    from pathlib import Path
    from split_entry import split_html, split_txt
    from llm_common import (load_clean_cache, check_clean_cache,
                             update_clean_cache)

    cache_path = Path(BASE) / "llm_html_clean.txt"
    clean_cache = load_clean_cache(cache_path)
    n_files = len(bdb_ids)
    dot_interval = max(1, n_files // 40)
    show_progress = n_files > 50

    errors = []
    n_cached = 0
    # Chunk-level counters
    n_chunked_files = 0
    total_chunks = 0
    clean_chunks = 0
    failed_chunks = 0
    mismatched_files = 0

    if show_progress:
        sys.stdout.write(f"Validating {n_files} files ")
        sys.stdout.flush()

    for i, bdb_id in enumerate(bdb_ids):
        if show_progress and i % dot_interval == 0:
            sys.stdout.write(".")
            sys.stdout.flush()

        orig_path = Path(ENTRIES_DIR) / (bdb_id + ".html")
        fr_path = Path(ENTRIES_FR_DIR) / (bdb_id + ".html")
        txt_fr_path = Path(TXT_FR_DIR) / (bdb_id + ".txt")

        # Report missing files when specific entries were requested
        if not fr_path.exists():
            if args.entries:
                errors.append((bdb_id, "no Entries_fr file found"))
            continue
        if not orig_path.exists():
            if args.entries:
                errors.append((bdb_id, "no Entries/ original file found"))
            continue

        # Skip if clean cache says this entry is unchanged
        if (txt_fr_path.exists()
                and check_clean_cache(clean_cache, bdb_id,
                                      orig_path, txt_fr_path, fr_path)):
            n_cached += 1
            continue
        orig_html = orig_path.read_text()
        fr_html = fr_path.read_text()
        txt_fr = txt_fr_path.read_text() if txt_fr_path.exists() else None

        orig_chunks = split_html(orig_html)
        n_orig = len(orig_chunks)

        if n_orig < 2:
            # Non-chunked: validate as a whole
            msgs = validate_html(orig_html, fr_html, txt_fr)
            file_errs = [(bdb_id, msg) for msg in msgs]
        else:
            # Chunked: validate per-chunk with labeled errors
            fr_chunks = split_html(fr_html)
            n_fr = len(fr_chunks)
            n_chunked_files += 1
            total_chunks += n_orig
            txt_chunks = split_txt(txt_fr) if txt_fr else []
            file_errs = []
            if n_fr != n_orig:
                mismatched_files += 1
                file_errs.append((bdb_id,
                    f"chunk mismatch: orig={n_orig} fr={n_fr}"))
            for idx in range(n_orig):
                label = f"{bdb_id}[{idx+1}]"
                if idx >= n_fr:
                    failed_chunks += 1
                    file_errs.append((label, "missing chunk"))
                    continue
                txt_c = (txt_chunks[idx]["txt"]
                         if txt_chunks and idx < len(txt_chunks) else None)
                errs = validate_html(
                    orig_chunks[idx]["html"],
                    fr_chunks[idx]["html"], txt_c)
                if errs:
                    failed_chunks += 1
                    file_errs.extend((label, msg) for msg in errs)
                else:
                    clean_chunks += 1

        errors.extend(file_errs)

        # Update cache if clean
        if not file_errs and txt_fr_path.exists() and fr_path.exists():
            update_clean_cache(cache_path, bdb_id,
                               orig_path, txt_fr_path, fr_path)

    if show_progress:
        print(" done")

    n_errors = len(errors)
    n_validated = n_files - n_cached
    n_clean = n_cached + n_validated - len(set(e[0] for e in errors))
    n_fail = n_files - n_clean
    cached_s = f" ({n_cached} cached)" if n_cached else ""

    if args.summary:
        print(f"Validated {n_files} files: {n_clean} clean{cached_s}, "
              f"{n_fail} with issues ({n_errors} total issues)")
        if n_chunked_files:
            print(f"  Chunked: {n_chunked_files} files, "
                  f"{total_chunks} chunks: "
                  f"{clean_chunks} clean, {failed_chunks} failed"
                  f"{f', {mismatched_files} mismatched' if mismatched_files else ''}")
    else:
        if errors:
            for bdb_id, msg in errors:
                print(f"  {bdb_id}: {msg}")
            print(f"\n{n_errors} issues in {n_fail} files")
            if n_chunked_files:
                print(f"  Chunked: {n_chunked_files} files, "
                      f"{total_chunks} chunks: "
                      f"{clean_chunks} clean, {failed_chunks} failed"
                      f"{f', {mismatched_files} mismatched' if mismatched_files else ''}")
        else:
            print(f"All {n_files} files validated OK{cached_s}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
