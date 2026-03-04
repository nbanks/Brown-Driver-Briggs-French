#!/usr/bin/env python3
"""Unit tests for sub-split integration in llm_html_assemble.py.

Tests the flatten/reassemble helpers, chunk labeling, and errata
parsing without requiring a running LLM server.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from llm_html_assemble import (
    _flatten_to_leaf_chunks, _parse_errata_line,
    _reassemble_leaf_outputs,
)
from split_entry import split_html, split_txt

ENTRIES_DIR = ROOT / "Entries"
TXT_FR_DIR = ROOT / "Entries_txt_fr"


# ---------------------------------------------------------------------------
# _parse_errata_line — backward compatibility
# ---------------------------------------------------------------------------

def test_parse_old_format():
    bdb, idx, reason = _parse_errata_line("BDB1234:2/3 html  some error")
    assert bdb == "BDB1234"
    assert idx == 1  # 2 - 1
    assert reason == "some error"


def test_parse_new_dot_format():
    bdb, idx, reason = _parse_errata_line("BDB5678:2.1/5.3 html  dot error")
    assert bdb == "BDB5678"
    assert idx == "2.1"  # stored as string
    assert reason == "dot error"


def test_parse_whole_file():
    bdb, idx, reason = _parse_errata_line("BDB9999 html  whole file error")
    assert bdb == "BDB9999"
    assert idx is None
    assert reason == "whole file error"


def test_parse_no_html_tag():
    bdb, idx, reason = _parse_errata_line("something unrelated")
    assert bdb == ""
    assert idx is None


# ---------------------------------------------------------------------------
# _flatten_to_leaf_chunks + _reassemble_leaf_outputs — round-trip
# ---------------------------------------------------------------------------

def _round_trip_entry(bdb_id):
    """Verify flatten + reassemble reproduces original for a real entry."""
    html_path = ENTRIES_DIR / f"{bdb_id}.html"
    txt_path = TXT_FR_DIR / f"{bdb_id}.txt"
    if not html_path.exists() or not txt_path.exists():
        return None  # skip if files missing

    html = html_path.read_text()
    txt = txt_path.read_text()
    hc = split_html(html)
    tc = split_txt(txt)

    if len(hc) != len(tc) or len(hc) < 2:
        return None  # not a chunked entry

    leaf_html, leaf_txt, labels, parent_indices = _flatten_to_leaf_chunks(hc, tc)

    # Every leaf must have a valid label and parent index
    assert len(leaf_html) == len(leaf_txt) == len(labels) == len(parent_indices)
    # At least as many leaves as top-level chunks
    assert len(leaf_html) >= len(hc)
    # All labels should be non-empty strings
    assert all(isinstance(l, str) and l for l in labels)

    # Round-trip: reassemble leaves back to top-level
    top = _reassemble_leaf_outputs(leaf_html, parent_indices, len(hc))
    orig_parts = [c["html"] for c in hc]
    for i in range(len(hc)):
        assert top[i] == orig_parts[i], \
            f"{bdb_id}: top chunk {i} mismatch after round-trip"

    return len(leaf_html), labels


def test_round_trip_oversized_entry():
    """Test with BDB2162 (242KB, known to have sub-splits)."""
    result = _round_trip_entry("BDB2162")
    if result is None:
        print("SKIP: BDB2162 not available")
        return
    n_leaves, labels = result
    # BDB2162 has 6 top-level chunks, should expand to 20+ leaves
    assert n_leaves > 6, f"Expected >6 leaves, got {n_leaves}"
    # Labels should contain dot notation for sub-splits
    assert any("." in l for l in labels), \
        f"Expected dot-notation labels, got {labels}"


def test_round_trip_small_entry():
    """Test with a small entry that has no sub-splits — should pass through."""
    html_path = ROOT / "test/html_assemble/Entries/BDB200.html"
    txt_path = ROOT / "test/html_assemble/Entries_txt_fr/BDB200.txt"
    if not html_path.exists() or not txt_path.exists():
        print("SKIP: BDB200 test fixture not available")
        return

    html = html_path.read_text()
    txt = txt_path.read_text()
    hc = split_html(html)
    tc = split_txt(txt)

    if len(hc) != len(tc) or len(hc) < 2:
        print("SKIP: BDB200 not chunked")
        return

    leaf_html, leaf_txt, labels, parent_indices = _flatten_to_leaf_chunks(hc, tc)
    # Small entry: no sub-splitting, leaf count == top-level count
    assert len(leaf_html) == len(hc)
    # All parent indices should just be sequential
    assert parent_indices == list(range(len(hc)))


def test_flatten_mismatch_fallback():
    """When subsplit counts differ between HTML and txt, fall back to no-split."""
    # Create synthetic chunks where subsplit would mismatch
    hc = [{"type": "stem", "html": "<div>small</div>", "label": "1"}]
    tc = [{"type": "stem", "txt": "## SPLIT 1.1 stem\nfoo\n## SPLIT 1.2 stem\nbar",
           "label": "1"}]

    leaf_html, leaf_txt, labels, parent_indices = _flatten_to_leaf_chunks(hc, tc)
    # Should fall back: 1 leaf per top-level chunk
    assert len(leaf_html) == 1
    assert parent_indices[0] == 0
    assert labels[0] == "1"


def test_reassemble_with_none():
    """Test _reassemble_leaf_outputs when some leaves are None."""
    outputs = ["<a>", None, "<c>"]
    parent_indices = [0, 0, 1]
    top = _reassemble_leaf_outputs(outputs, parent_indices, 2)
    assert top[0] == "<a>"  # only first leaf contributed
    assert top[1] == "<c>"


# ---------------------------------------------------------------------------
# Label propagation through split + subsplit
# ---------------------------------------------------------------------------

def test_split_html_labels():
    """Labels on split_html chunks should be sequential strings."""
    # Need a real entry to test, fall back to synthetic
    from split_entry import split_html
    hc = split_html("<html><body>header</body></html>")
    assert len(hc) == 1
    assert hc[0].get("label") == "0"  # whole entry


def test_split_txt_labels():
    """Labels on split_txt chunks from markers."""
    from split_entry import split_txt
    txt = ("=== BDB50 ===\nheader\n"
           "## SPLIT 1 stem\nQal stuff\n"
           "## SPLIT 2 stem\nNiphal stuff\n")
    chunks = split_txt(txt)
    assert chunks[0]["label"] == "0"  # header
    assert chunks[1]["label"] == "1"
    assert chunks[2]["label"] == "2"


def test_subsplit_txt_labels():
    """Labels on subsplit_txt should come from ## SPLIT markers."""
    from split_entry import split_txt, subsplit_txt
    txt = ("## SPLIT 1 stem\n"
           "## SPLIT 1.1 stem\nfoo\n"
           "## SPLIT 1.2 stem\nbar\n")
    # Create a chunk as if it came from split_txt
    chunk = {"type": "stem", "txt": txt.strip(), "label": "1"}
    subs = subsplit_txt(chunk)
    assert len(subs) == 2
    assert subs[0]["label"] == "1.1"
    assert subs[1]["label"] == "1.2"


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            passed += 1
            print(f"  PASS  {name}")
        except Exception:
            failed += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
