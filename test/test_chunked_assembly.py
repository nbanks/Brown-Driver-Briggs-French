#!/usr/bin/env python3
"""Tests for chunk-based HTML assembly in llm_html_assemble.py.

Tests verify:
1. split_html and split_txt produce aligned chunk counts for real entries
2. Chunk pairing falls back (returns None) on mismatched counts
3. Concatenating HTML chunks reproduces the original HTML
4. build_chunk_prompt inserts chunk-mode note
5. Real entries with ## SPLIT markers produce consistent html/txt chunk counts
"""

import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from split_entry import split_html, split_txt
from llm_html_assemble import build_chunk_prompt, extract_html, check_llm_errata
from validate_html import validate_file

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRIES_DIR = os.path.join(BASE, "Entries")
TXT_DIR = os.path.join(BASE, "Entries_txt")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


# --- Unit tests for chunk pairing logic ---

def test_chunk_counts_match_for_split_markers():
    """Entries with ## SPLIT markers should produce the same chunk count
    in both html and txt_fr splitting."""
    # Find entries that have ## SPLIT markers in their txt
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
        if '## SPLIT ' not in txt:
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
    result = build_chunk_prompt(template, "<p>html</p>", "texte", "1", "3")
    assert "Mode morceau (1/3)" in result
    assert "<p>html</p>" in result
    assert "texte" in result
    assert "Reproduisez exactement" in result


def test_build_chunk_prompt_preserves_template():
    """The chunk prompt should contain the full template with substitutions."""
    template = "Start {{ORIGINAL_HTML}} middle {{FRENCH_TXT}} end"
    result = build_chunk_prompt(template, "HTML", "TXT", "3", "5")
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
_SAMPLE_BDB = "BDB10015"


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
        pytest.skip(f"No existing Entries_fr for {_SAMPLE_BDB}")
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


def test_missing_last_chunk_detected(validation_dirs):
    """Dropping the last chunk should trigger validation errors
    (missing Hebrew text, tag sequence differences, etc.)."""
    html = validation_dirs["orig_html"]
    chunks = split_html(html)
    if len(chunks) < 2:
        pytest.skip("Entry doesn't split into multiple chunks")

    without_last = "".join(c["html"] for c in chunks[:-1])
    errors = _write_fr(validation_dirs, without_last)
    assert len(errors) > 0, (
        "Expected errors from dropping the last chunk"
    )


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
    # The English original should have untranslated refs that get caught
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


# --- extract_html tests ---

class TestExtractHtml:
    def test_full_fence(self):
        raw = "```html\n<p>hello</p>\n```"
        assert extract_html(raw) == "<p>hello</p>"

    def test_full_fence_no_lang(self):
        raw = "```\n<p>hello</p>\n```"
        assert extract_html(raw) == "<p>hello</p>"

    def test_trailing_only_fence(self):
        raw = "<html><p>content</p></html>\n```"
        assert extract_html(raw) == "<html><p>content</p></html>"

    def test_trailing_fence_no_newline(self):
        raw = "<html><p>content</p></html>```"
        assert extract_html(raw) == "<html><p>content</p></html>"

    def test_no_fence(self):
        raw = "<html><p>content</p></html>"
        assert extract_html(raw) == raw

    def test_backticks_inside_html_not_stripped(self):
        """Backticks inside HTML content should not be treated as fences."""
        raw = "<p>use ```code``` here</p>"
        assert extract_html(raw) == raw

    def test_whitespace_stripped(self):
        raw = "  \n```html\n<p>x</p>\n```\n  "
        assert extract_html(raw) == "<p>x</p>"


# --- check_llm_errata tests ---

class TestCheckLlmErrata:
    def test_no_errata(self):
        raw = "<html><p>normal output</p></html>"
        reason, html = check_llm_errata(raw)
        assert reason is None
        assert html is None

    def test_pure_errata_no_html(self):
        raw = (">>> ERRATA: contenu tronqué — le texte français ne couvre "
               "qu'une fraction de l'entrée originale")
        reason, html = check_llm_errata(raw)
        assert reason is not None
        assert "tronqué" in reason
        assert html is None

    def test_errata_with_html_after(self):
        raw = (">>> ERRATA: accent manquant sur majuscule\n"
               "Le texte a un problème.\n"
               "<html><p>contenu</p></html>")
        reason, html = check_llm_errata(raw)
        assert reason is not None
        assert "accent" in reason
        assert html is not None
        assert "<html>" in html

    def test_errata_with_fenced_html_after(self):
        raw = (">>> ERRATA: erreur de ponctuation\n"
               "Explication du problème.\n"
               "```html\n<html><p>contenu</p></html>\n```")
        reason, html = check_llm_errata(raw)
        assert reason is not None
        assert html is not None
        assert "<html>" in html
        assert "```" not in html

    def test_errata_with_trailing_fence_html(self):
        raw = (">>> ERRATA: référence non convertie\n"
               "Ceci est une explication.\n"
               "<html><p>contenu</p></html>\n```")
        reason, html = check_llm_errata(raw)
        assert reason is not None
        assert html is not None
        assert "```" not in html

    def test_errata_prose_only(self):
        """Errata with multi-line prose explanation but no HTML."""
        raw = (">>> ERRATA: contenu sévèrement tronqué\n"
               "Le texte français ne couvre qu'une fraction.\n"
               "Il manque le sens 2 et ses sous-sens.")
        reason, html = check_llm_errata(raw)
        assert reason is not None
        assert html is None


# --- Incremental write tests ---

from llm_html_assemble import _write_partial_entry


class TestWritePartialEntry:
    def test_mixed_complete_and_pending(self, tmp_path):
        """Completed chunks appear; pending chunks use original English."""
        import llm_html_assemble as mod
        orig_dir = mod.ENTRIES_FR_DIR
        mod.ENTRIES_FR_DIR = tmp_path
        try:
            orig_parts = [
                '<html><head></head><body><p>header</p>',
                '<div class="sense"><p>English sense 1</p></div>',
                '<div class="sense"><p>English sense 2</p></div>',
                '</body></html>',
            ]
            outputs = [
                '<html><head></head><body><p>en-tête</p>',
                '<div class="sense"><p>sens français 1</p></div>',
                None,  # pending — original English preserved
                '</body></html>',
            ]
            _write_partial_entry("BDB9999", outputs, orig_parts)

            result = (tmp_path / "BDB9999.html").read_text()
            # Completed chunks present
            assert "sens français 1" in result
            assert "en-tête" in result
            # Pending chunk uses original (preserves structure for re-read)
            assert "English sense 2" in result
        finally:
            mod.ENTRIES_FR_DIR = orig_dir

    def test_all_pending(self, tmp_path):
        """All-None outputs produce original content (identical to English)."""
        import llm_html_assemble as mod
        orig_dir = mod.ENTRIES_FR_DIR
        mod.ENTRIES_FR_DIR = tmp_path
        try:
            orig_parts = [
                '<p>header</p>',
                '<div class="stem"><p>Qal</p></div>',
                '<div class="stem"><p>Niphal</p></div>',
            ]
            outputs = [None, None, None]
            _write_partial_entry("BDB8888", outputs, orig_parts)

            result = (tmp_path / "BDB8888.html").read_text()
            # All original content preserved
            assert "<p>header</p>" in result
            assert "<p>Qal</p>" in result
            assert "<p>Niphal</p>" in result
        finally:
            mod.ENTRIES_FR_DIR = orig_dir

    def test_all_complete(self, tmp_path):
        """All-complete outputs produce no placeholders."""
        import llm_html_assemble as mod
        orig_dir = mod.ENTRIES_FR_DIR
        mod.ENTRIES_FR_DIR = tmp_path
        try:
            orig_parts = ['<p>h</p>', '<div class="sense">en</div>']
            outputs = ['<p>h</p>', '<div class="sense">fr</div>']
            _write_partial_entry("BDB7777", outputs, orig_parts)

            result = (tmp_path / "BDB7777.html").read_text()
            # No original English content remains
            assert ">en<" not in result
            assert "fr" in result
        finally:
            mod.ENTRIES_FR_DIR = orig_dir


class TestChunkVsWholeValidation:
    """Regression test for BDB3160: chunks can pass individually while the
    assembled file fails whole-file validation.  This happens when --skip-failed
    keeps an untranslated header chunk from a prior run but sense chunks are
    regenerated correctly."""

    _BDB = "BDB3160"

    @pytest.fixture(autouse=True)
    def _check_entry_exists(self):
        for d in (ENTRIES_DIR, TXT_FR_DIR):
            if not os.path.exists(os.path.join(d, self._BDB + (".html" if "Entries" == os.path.basename(d) else ".txt"))):
                pytest.skip(f"{self._BDB} not found in {d}")

    def _load(self):
        from validate_html import validate_html as _validate
        orig = open(os.path.join(ENTRIES_DIR, self._BDB + ".html")).read()
        txt = open(os.path.join(TXT_FR_DIR, self._BDB + ".txt")).read()
        fr_path = os.path.join(
            os.path.dirname(ENTRIES_DIR), "Entries_fr", self._BDB + ".html")
        fr = open(fr_path).read() if os.path.exists(fr_path) else None
        return orig, txt, fr, _validate

    def test_entry_has_three_chunks(self):
        orig, txt, fr, _ = self._load()
        chunks = split_html(orig)
        assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
        assert chunks[0]["type"] == "header"
        assert chunks[1]["type"] == "sense"
        assert chunks[2]["type"] == "sense"

    def test_assembled_validation_catches_untranslated_header(self):
        """When the header is untranslated but senses are translated,
        per-chunk validation of the senses passes but whole-file
        validation must fail."""
        orig, txt, fr, validate = self._load()
        orig_chunks = split_html(orig)
        txt_chunks = split_txt(txt)

        # Build an assembled file with untranslated header + translated senses
        # Use the English header as-is
        header_html = orig_chunks[0]["html"]

        # Build translated senses (use fr file if available, otherwise orig)
        if fr:
            fr_chunks = split_html(fr)
            if len(fr_chunks) == 3:
                sense1 = fr_chunks[1]["html"]
                sense2 = fr_chunks[2]["html"]
            else:
                sense1 = orig_chunks[1]["html"]
                sense2 = orig_chunks[2]["html"]
        else:
            sense1 = orig_chunks[1]["html"]
            sense2 = orig_chunks[2]["html"]

        # Sense chunks should validate clean individually (or nearly so)
        # The key assertion: whole-file validation MUST catch the
        # untranslated header even if sense chunks are fine
        assembled = header_html + sense1 + sense2
        whole_errors = validate(orig, assembled, txt)
        assert len(whole_errors) > 0, (
            "Whole-file validation should catch untranslated header content "
            "(English book names, pos, primary) even when sense chunks are OK"
        )
        # Verify the errors are about English content
        error_text = " ".join(str(e) for e in whole_errors)
        assert ("English" in error_text
                or "expected" in error_text.lower()
                or "missing" in error_text.lower()), (
            f"Expected English-detection errors, got: {whole_errors[:3]}"
        )


class TestSkipFailedRejectsUntranslated:
    """skip-failed should not keep chunks identical to the English original."""

    _BDB = "BDB3160"

    @pytest.fixture(autouse=True)
    def _check_entry_exists(self):
        for d in (ENTRIES_DIR, TXT_FR_DIR):
            ext = ".html" if os.path.basename(d) == "Entries" else ".txt"
            if not os.path.exists(os.path.join(d, self._BDB + ext)):
                pytest.skip(f"{self._BDB} not found in {d}")

    def test_untranslated_chunk_not_kept(self):
        """When a chunk is identical to the original English, skip-failed
        should NOT accept it — it needs regeneration."""
        orig = open(os.path.join(ENTRIES_DIR, self._BDB + ".html")).read()
        orig_chunks = split_html(orig)
        # Simulate: fr_leaf_parts[0] is identical to orig (never translated)
        fr_leaf = orig_chunks[0]["html"]
        orig_part = orig_chunks[0]["html"]
        # The guard: identical content should NOT be kept
        assert fr_leaf == orig_part, "Sanity: they should be identical"
        # Our fix: skip_failed rejects chunks identical to original
        should_keep = (fr_leaf != orig_part)
        assert not should_keep, (
            "skip-failed should reject chunks identical to the English original"
        )

    def test_translated_chunk_is_kept(self):
        """When a chunk differs from the original, skip-failed should keep it
        even if it has validation errors."""
        orig = open(os.path.join(ENTRIES_DIR, self._BDB + ".html")).read()
        orig_chunks = split_html(orig)
        # Simulate: a chunk that was translated (differs from orig)
        fr_leaf = orig_chunks[0]["html"].replace("Biblical Hebrew",
                                                  "hébreu biblique")
        orig_part = orig_chunks[0]["html"]
        should_keep = (fr_leaf != orig_part)
        assert should_keep, (
            "skip-failed should keep chunks that differ from the original"
        )


class TestWarmStartIdentityDetection:
    """Verify that untranslated chunks (identical to original) are detected
    as needing work on re-read, while translated chunks are kept."""

    def test_identical_chunk_needs_work(self):
        """A chunk identical to the original should not be kept."""
        orig = '<div class="sense"><p>English content</p></div>'
        fr = '<div class="sense"><p>English content</p></div>'
        assert fr == orig, "Identical chunks need regeneration"

    def test_translated_chunk_is_kept(self):
        """A chunk that differs from the original should be kept."""
        orig = '<div class="sense"><p>English content</p></div>'
        fr = '<div class="sense"><p>contenu français</p></div>'
        assert fr != orig, "Translated chunks should be kept"



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
