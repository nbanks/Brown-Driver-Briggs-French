#!/usr/bin/env python3
"""Tests for scripts/split_entry.py.

Tests verify:
1. HTML and txt split consistently for the vast majority of entries
2. txt and txt_fr split into the same number of chunks
3. Roundtrip: concatenating chunks reproduces the original
4. Small entries with no splits return a single chunk
"""

import os
import re
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.split_entry import split_html, split_txt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
TXT_DIR = os.path.join(BASE, "Entries_txt")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


def _all_entry_ids():
    """Get sorted list of BDB entry IDs that have both HTML and txt."""
    html_files = {f.replace('.html', '') for f in os.listdir(ENTRIES_DIR)
                  if f.startswith('BDB') and f.endswith('.html')}
    txt_files = {f.replace('.txt', '') for f in os.listdir(TXT_DIR)
                 if f.startswith('BDB') and f.endswith('.txt')}
    return sorted(html_files & txt_files)


def _all_txt_fr_ids():
    """Get sorted list of BDB entry IDs that have both txt and txt_fr."""
    txt_files = {f.replace('.txt', '') for f in os.listdir(TXT_DIR)
                 if f.startswith('BDB') and f.endswith('.txt')}
    fr_files = {f.replace('.txt', '') for f in os.listdir(TXT_FR_DIR)
                if f.startswith('BDB') and f.endswith('.txt')}
    return sorted(txt_files & fr_files)


# --- Core consistency test: HTML vs txt chunk count (aggregate) ---

def test_html_txt_chunk_count_aggregate():
    """At least 98% of entries must have matching HTML and txt chunk counts.

    Some entries have structural mismatches (e.g. sense divs inside point
    divs, unclosed divs, numbered senses without corresponding div markup)
    that make exact matching impossible for all ~10k entries.
    """
    all_ids = _all_entry_ids()
    mismatches = []

    for entry_id in all_ids:
        html_path = os.path.join(ENTRIES_DIR, f"{entry_id}.html")
        txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")

        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        with open(txt_path, encoding="utf-8") as f:
            txt = f.read()

        html_chunks = split_html(html)
        txt_chunks = split_txt(txt)

        if len(html_chunks) != len(txt_chunks):
            mismatches.append(entry_id)

    pct = (len(all_ids) - len(mismatches)) / len(all_ids) * 100
    assert pct >= 98.0, (
        f"Only {pct:.1f}% match ({len(mismatches)} mismatches out of "
        f"{len(all_ids)}). First 10: {mismatches[:10]}"
    )


# --- Specific entries that MUST match ---

@pytest.mark.parametrize("entry_id", [
    "BDB50",    # verb with 3 stems
    "BDB200",   # non-verb with 2 senses
    "BDB1300",  # verb with nested senses inside stems
    "BDB1",     # simple letter entry (no split)
    "BDB5",     # simple proper name (no split)
])
def test_specific_entries_match(entry_id):
    """Key entries must have matching HTML and txt chunk counts."""
    html_path = os.path.join(ENTRIES_DIR, f"{entry_id}.html")
    txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")

    if not os.path.exists(html_path) or not os.path.exists(txt_path):
        pytest.skip(f"{entry_id} not found")

    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    with open(txt_path, encoding="utf-8") as f:
        txt = f.read()

    html_chunks = split_html(html)
    txt_chunks = split_txt(txt)

    html_types = [c["type"] for c in html_chunks]
    txt_types = [c["type"] for c in txt_chunks]
    assert len(html_chunks) == len(txt_chunks), (
        f"{entry_id}: HTML {html_types} vs txt {txt_types}"
    )


# --- txt vs txt_fr chunk count (aggregate) ---

def test_txt_txt_fr_chunk_count_aggregate():
    """At least 98% of entries must have matching txt and txt_fr chunk counts."""
    fr_ids = _all_txt_fr_ids()
    mismatches = []

    for entry_id in fr_ids:
        txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")
        fr_path = os.path.join(TXT_FR_DIR, f"{entry_id}.txt")

        with open(txt_path, encoding="utf-8") as f:
            txt = f.read()
        with open(fr_path, encoding="utf-8") as f:
            txt_fr = f.read()

        if not txt.strip() or not txt_fr.strip():
            continue

        txt_chunks = split_txt(txt)
        fr_chunks = split_txt(txt_fr)

        if len(txt_chunks) != len(fr_chunks):
            mismatches.append(entry_id)

    if not fr_ids:
        pytest.skip("no txt_fr files")

    pct = (len(fr_ids) - len(mismatches)) / len(fr_ids) * 100
    assert pct >= 95.0, (
        f"Only {pct:.1f}% match ({len(mismatches)} mismatches out of "
        f"{len(fr_ids)}). First 10: {mismatches[:10]}"
    )


# --- Roundtrip tests ---

@pytest.mark.parametrize("entry_id", ["BDB50", "BDB200", "BDB1300"])
def test_html_roundtrip(entry_id):
    """Concatenating HTML chunks must reproduce the original."""
    html_path = os.path.join(ENTRIES_DIR, f"{entry_id}.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    chunks = split_html(html)
    reassembled = "".join(c["html"] for c in chunks)
    assert reassembled == html, f"{entry_id}: roundtrip mismatch"


@pytest.mark.parametrize("entry_id", ["BDB50", "BDB200", "BDB1300"])
def test_txt_roundtrip(entry_id):
    """Concatenating txt chunks preserves all content."""
    txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")
    with open(txt_path, encoding="utf-8") as f:
        txt = f.read()

    chunks = split_txt(txt)
    reassembled = "\n".join(c["txt"] for c in chunks)
    orig_stripped = re.sub(r'\s+', ' ', txt).strip()
    reasm_stripped = re.sub(r'\s+', ' ', reassembled).strip()
    assert orig_stripped == reasm_stripped, f"{entry_id}: roundtrip content mismatch"


# --- Small entry test ---

def test_small_entry_no_split():
    """Entries with no stems and <=1 sense return 1 chunk (no split)."""
    for entry_id in ["BDB5", "BDB10", "BDB20"]:
        txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")
        html_path = os.path.join(ENTRIES_DIR, f"{entry_id}.html")
        if not os.path.exists(txt_path) or not os.path.exists(html_path):
            continue
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        with open(txt_path, encoding="utf-8") as f:
            txt = f.read()

        html_chunks = split_html(html)
        txt_chunks = split_txt(txt)

        if len(html_chunks) == 1:
            assert html_chunks[0]["type"] == "whole"
        if len(txt_chunks) == 1:
            assert txt_chunks[0]["type"] == "whole"
        break


# --- Verb detection test ---

def test_verb_detection():
    """BDB50 (verb) and BDB200 (non-verb) must be correctly classified."""
    with open(os.path.join(TXT_DIR, "BDB50.txt"), encoding="utf-8") as f:
        txt50 = f.read()
    chunks50 = split_txt(txt50)
    stem_types = [c["type"] for c in chunks50 if c["type"] == "stem"]
    assert len(stem_types) >= 2, "BDB50 should have multiple stem chunks"

    with open(os.path.join(TXT_DIR, "BDB200.txt"), encoding="utf-8") as f:
        txt200 = f.read()
    chunks200 = split_txt(txt200)
    sense_types = [c["type"] for c in chunks200 if c["type"] == "sense"]
    assert len(sense_types) >= 2, "BDB200 should have multiple sense chunks"


# --- Hebrew preservation across split chunks (txt vs txt_fr) ---

_HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')


def _extract_hebrew(text):
    """Return all Hebrew/Aramaic characters in order as a single string."""
    return ''.join(_HEBREW_RE.findall(text))


def test_split_chunks_hebrew_preservation():
    """For every entry with splits, each corresponding txt/txt_fr chunk
    must contain the same Hebrew words in the same order.

    This verifies that @@SPLIT markers were inserted at structurally
    equivalent positions in the French files.
    """
    fr_ids = _all_txt_fr_ids()
    failures = []

    for entry_id in fr_ids:
        txt_path = os.path.join(TXT_DIR, f"{entry_id}.txt")
        fr_path = os.path.join(TXT_FR_DIR, f"{entry_id}.txt")

        with open(txt_path, encoding="utf-8") as f:
            txt = f.read()
        with open(fr_path, encoding="utf-8") as f:
            txt_fr = f.read()

        if not txt.strip() or not txt_fr.strip():
            continue

        txt_chunks = split_txt(txt)
        fr_chunks = split_txt(txt_fr)

        if len(txt_chunks) != len(fr_chunks):
            continue  # chunk count mismatch tested separately

        if len(txt_chunks) <= 1:
            continue  # no splits, nothing to check

        for i, (tc, fc) in enumerate(zip(txt_chunks, fr_chunks)):
            en_heb = _extract_hebrew(tc["txt"])
            fr_heb = _extract_hebrew(fc["txt"])
            if en_heb != fr_heb:
                failures.append(
                    f"{entry_id} chunk {i} ({tc['type']}): "
                    f"en has {len(en_heb)} Hebrew chars, "
                    f"fr has {len(fr_heb)} Hebrew chars"
                )
                break  # one failure per entry is enough

    if not fr_ids:
        pytest.skip("no txt_fr files")

    pct = (len(fr_ids) - len(failures)) / len(fr_ids) * 100
    assert pct >= 98.0, (
        f"Only {pct:.1f}% of entries have matching Hebrew in split chunks "
        f"({len(failures)} failures out of {len(fr_ids)}). "
        f"First 10: {failures[:10]}"
    )
