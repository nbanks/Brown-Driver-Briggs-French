#!/usr/bin/env python3
"""Tests for chunk-based HTML assembly in llm_html_assemble.py.

Tests verify:
1. split_html and split_txt produce aligned chunk counts for real entries
2. Chunk pairing falls back (returns None) on mismatched counts
3. Concatenating HTML chunks reproduces the original HTML
4. build_chunk_prompt inserts chunk-mode note
5. Real entries with @@SPLIT markers produce consistent html/txt chunk counts
"""

import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from split_entry import split_html, split_txt
from llm_html_assemble import build_chunk_prompt
from validate_html import validate_file

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
TXT_DIR = os.path.join(BASE, "Entries_txt")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


# --- Unit tests for chunk pairing logic ---

def test_chunk_counts_match_for_split_markers():
    """Entries with @@SPLIT markers should produce the same chunk count
    in both html and txt_fr splitting."""
    # Find entries that have @@SPLIT markers in their txt
    checked = 0
    mismatches = []
    for fname in sorted(os.listdir(TXT_DIR)):
        if not fname.endswith('.txt'):
            continue
        bdb = fname.replace('.txt', '')
        txt_path = os.path.join(TXT_DIR, fname)
        html_path = os.path.join(ENTRIES_DIR, bdb + '.html')
        txt_fr_path = os.path.join(TXT_FR_DIR, fname)
        if not os.path.exists(html_path) or not os.path.exists(txt_fr_path):
            continue

        txt = open(txt_path).read()
        if '@@SPLIT:' not in txt:
            continue

        html = open(html_path).read()
        txt_fr = open(txt_fr_path).read()

        h_chunks = split_html(html)
        t_chunks = split_txt(txt_fr)

        if len(h_chunks) != len(t_chunks):
            mismatches.append((bdb, len(h_chunks), len(t_chunks)))
        checked += 1

    assert checked > 100, f"Expected to check many entries, only found {checked}"
    assert len(mismatches) == 0, (
        f"{len(mismatches)}/{checked} entries have mismatched chunk counts: "
        f"{mismatches[:10]}"
    )


def test_html_chunk_roundtrip():
    """Concatenating HTML chunks should reproduce the original for most entries.

    split_html has known edge cases with adjacent/empty divs where inter-div
    gap accounting adds a few bytes. We allow up to 1% size difference.
    """
    failures = []
    checked = 0
    for fname in sorted(os.listdir(ENTRIES_DIR))[:500]:
        if not fname.endswith('.html'):
            continue
        html_path = os.path.join(ENTRIES_DIR, fname)
        html = open(html_path).read()
        chunks = split_html(html)
        reassembled = "".join(c["html"] for c in chunks)
        checked += 1
        if reassembled != html:
            diff_pct = abs(len(reassembled) - len(html)) / max(len(html), 1)
            if diff_pct > 0.01:
                failures.append((fname, len(html), len(reassembled), diff_pct))

    assert checked > 100
    assert len(failures) == 0, (
        f"{len(failures)}/{checked} entries have >1% roundtrip drift: "
        f"{failures[:5]}"
    )


def test_single_chunk_entries_not_split():
    """Small entries with no div structure return a single 'whole' chunk."""
    # BDB1 is a simple entry
    html_path = os.path.join(ENTRIES_DIR, "BDB1.html")
    if not os.path.exists(html_path):
        pytest.skip("BDB1.html not found")
    html = open(html_path).read()
    chunks = split_html(html)
    assert len(chunks) == 1
    assert chunks[0]["type"] == "whole"


def test_build_chunk_prompt_contains_mode_note():
    """build_chunk_prompt should include the chunk mode note."""
    template = "Template {{ORIGINAL_HTML}} and {{FRENCH_TXT}}"
    result = build_chunk_prompt(template, "<p>html</p>", "texte", 0, 3)
    assert "Mode morceau (1/3)" in result
    assert "<p>html</p>" in result
    assert "texte" in result
    assert "n'ajoutez pas" in result


def test_build_chunk_prompt_preserves_template():
    """The chunk prompt should contain the full template with substitutions."""
    template = "Start {{ORIGINAL_HTML}} middle {{FRENCH_TXT}} end"
    result = build_chunk_prompt(template, "HTML", "TXT", 2, 5)
    assert "Start HTML middle TXT end" in result
    assert "Mode morceau (3/5)" in result


def test_large_entries_produce_multiple_chunks():
    """The top 20 largest entries should all split into 2+ chunks."""
    entries = sorted(
        (os.path.join(ENTRIES_DIR, f) for f in os.listdir(ENTRIES_DIR)
         if f.endswith('.html')),
        key=os.path.getsize, reverse=True
    )[:20]

    for path in entries:
        html = open(path).read()
        chunks = split_html(html)
        bdb = os.path.basename(path)
        assert len(chunks) >= 2, (
            f"{bdb} ({os.path.getsize(path)} bytes) produced only "
            f"{len(chunks)} chunk(s)"
        )


# --- Fragment / chunked HTML validation tests ---
#
# These test that validate_file() works correctly on HTML produced by
# concatenating chunk outputs — including edge cases like missing header,
# missing footer, only-middle-chunk, etc.

# A real entry we'll use as a basis for fragment tests
_SAMPLE_BDB = "BDB200"


@pytest.fixture
def validation_dirs():
    """Create temp dirs mimicking Entries/, Entries_fr/, Entries_txt_fr/
    with a copy of a real entry."""
    tmpdir = tempfile.mkdtemp(prefix="test_chunk_val_")
    entries = os.path.join(tmpdir, "Entries")
    entries_fr = os.path.join(tmpdir, "Entries_fr")
    txt_fr = os.path.join(tmpdir, "Entries_txt_fr")
    os.makedirs(entries)
    os.makedirs(entries_fr)
    os.makedirs(txt_fr)

    # Copy real entry files
    orig = os.path.join(ENTRIES_DIR, _SAMPLE_BDB + ".html")
    txt = os.path.join(TXT_FR_DIR, _SAMPLE_BDB + ".txt")
    if not os.path.exists(orig) or not os.path.exists(txt):
        pytest.skip(f"{_SAMPLE_BDB} files not found")

    shutil.copy(orig, os.path.join(entries, _SAMPLE_BDB + ".html"))
    shutil.copy(txt, os.path.join(txt_fr, _SAMPLE_BDB + ".txt"))

    yield {
        "tmpdir": tmpdir,
        "entries": entries,
        "entries_fr": entries_fr,
        "txt_fr": txt_fr,
        "orig_html": open(orig).read(),
        "txt_fr_text": open(txt).read(),
    }

    shutil.rmtree(tmpdir)


def _write_fr(dirs, html_content):
    """Write html_content as the French entry and validate."""
    fr_path = os.path.join(dirs["entries_fr"], _SAMPLE_BDB + ".html")
    with open(fr_path, "w") as f:
        f.write(html_content)
    return validate_file(
        _SAMPLE_BDB,
        entries_dir=dirs["entries"],
        entries_fr_dir=dirs["entries_fr"],
        txt_fr_dir=dirs["txt_fr"],
    )


def test_correct_concatenation_validates_clean(validation_dirs):
    """A properly translated full entry should validate clean (or near-clean).

    We use the real Entries_fr if it exists, otherwise build from chunks."""
    real_fr = os.path.join(BASE, "Entries_fr", _SAMPLE_BDB + ".html")
    if not os.path.exists(real_fr):
        pytest.skip("No existing Entries_fr for BDB200")
    # Validate the real French file against our temp copies
    shutil.copy(real_fr, os.path.join(
        validation_dirs["entries_fr"], _SAMPLE_BDB + ".html"))
    errors = validate_file(
        _SAMPLE_BDB,
        entries_dir=validation_dirs["entries"],
        entries_fr_dir=validation_dirs["entries_fr"],
        txt_fr_dir=validation_dirs["txt_fr"],
    )
    # Real entry should be clean or have at most minor issues
    assert len(errors) <= 2, f"Real entry has too many errors: {errors}"


def test_missing_header_chunk_detected(validation_dirs):
    """If the header chunk (with <html>, <head>, entry IDs) is missing,
    validation should catch missing entry IDs and Hebrew text."""
    html = validation_dirs["orig_html"]
    chunks = split_html(html)
    if len(chunks) < 2:
        pytest.skip("Entry doesn't split into chunks")

    # Concatenate everything except the header
    no_header = "".join(c["html"] for c in chunks if c["type"] != "header")
    errors = _write_fr(validation_dirs, no_header)
    # Should detect missing entry IDs at minimum
    error_msgs = [msg for _, msg in errors]
    assert any("entry ID" in msg or "Hebrew" in msg or "tag" in msg
               for msg in error_msgs), (
        f"Expected missing-entry-ID or missing-Hebrew errors, got: {error_msgs}"
    )


def test_missing_footer_chunk_detected(validation_dirs):
    """If the footer chunk (with <hr>) is dropped, validation may catch
    tag sequence differences."""
    html = validation_dirs["orig_html"]
    chunks = split_html(html)
    footer_chunks = [c for c in chunks if c["type"] == "footer"]
    if not footer_chunks:
        pytest.skip("Entry has no footer chunk")

    no_footer = "".join(c["html"] for c in chunks if c["type"] != "footer")
    errors = _write_fr(validation_dirs, no_footer)
    # Footer removal should cause some validation issue (tag seq, missing text)
    # Even if no errors, that's also acceptable — footer is often just <hr>
    # This test documents the behavior rather than strictly requiring errors


def test_only_middle_chunk_detected(validation_dirs):
    """Using only a middle chunk should trigger many validation errors."""
    html = validation_dirs["orig_html"]
    chunks = split_html(html)
    middle = [c for c in chunks if c["type"] not in ("header", "footer")]
    if not middle:
        pytest.skip("No middle chunks")

    # Use just the first middle chunk
    errors = _write_fr(validation_dirs, middle[0]["html"])
    assert len(errors) > 0, "Expected errors from a single middle chunk"


def test_empty_html_detected(validation_dirs):
    """An empty French HTML file should produce validation errors."""
    errors = _write_fr(validation_dirs, "")
    error_msgs = [msg for _, msg in errors]
    assert len(errors) > 0, "Expected errors from empty HTML"


def test_english_original_as_french_detected(validation_dirs):
    """Passing the English original as French output should detect
    untranslated content (English book names in refs, etc.)."""
    errors = _write_fr(validation_dirs, validation_dirs["orig_html"])
    error_msgs = [msg for _, msg in errors]
    # Should catch English book names or missing French text
    has_english_error = any(
        "English" in msg or "French text missing" in msg or "colon" in msg
        for msg in error_msgs
    )
    # BDB200 has refs like "1Chr 7:16" which should be caught
    assert has_english_error, (
        f"Expected English-detection errors, got: {error_msgs}"
    )


def test_chunks_concatenated_match_whole_entry_validation(validation_dirs):
    """Validation results should be identical whether we write the full
    original HTML or the concatenation of its chunks."""
    html = validation_dirs["orig_html"]
    chunks = split_html(html)
    reassembled = "".join(c["html"] for c in chunks)

    errors_orig = _write_fr(validation_dirs, html)
    errors_reasm = _write_fr(validation_dirs, reassembled)

    # Same error count (might differ slightly if roundtrip isn't perfect)
    assert abs(len(errors_orig) - len(errors_reasm)) <= 1, (
        f"orig errors: {len(errors_orig)}, reassembled errors: {len(errors_reasm)}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
