#!/usr/bin/env python3
"""Tests for scripts/check_splits.py."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.check_splits import hebrew_split_sequence, compare_entry


# --- hebrew_split_sequence ---

def test_only_hebrew():
    text = "some english אָבַל more text תֶּאֱבַל end"
    seq = hebrew_split_sequence(text)
    assert seq == ['אָבַל', 'תֶּאֱבַל']


def test_only_splits():
    text = "header\n@@SPLIT:stem@@\nbody\n@@SPLIT:sense@@\nfooter"
    seq = hebrew_split_sequence(text)
    assert seq == ['@@SPLIT:stem@@', '@@SPLIT:sense@@']


def test_mixed():
    text = (
        "=== BDB50 ===\n"
        "I. אָבַל verb\n"
        "@@SPLIT:stem@@\n"
        "Qal Perfect אָבַל Isa 24:7\n"
        "@@SPLIT:stem@@\n"
        "Hithpael הִתְאַבֵּל\n"
    )
    seq = hebrew_split_sequence(text)
    assert seq == [
        'אָבַל',
        '@@SPLIT:stem@@',
        'אָבַל',
        '@@SPLIT:stem@@',
        'הִתְאַבֵּל',
    ]


def test_no_hebrew_no_splits():
    text = "just english text\nno hebrew here"
    seq = hebrew_split_sequence(text)
    assert seq == []


def test_split_marker_not_on_own_line():
    """@@SPLIT must be on its own line to count as a marker."""
    text = "text @@SPLIT:stem@@ more text"
    seq = hebrew_split_sequence(text)
    assert seq == []  # no Hebrew, and the SPLIT isn't on its own line


def test_hebrew_presentation_forms():
    """Characters in U+FB1D-FB4F range should be captured."""
    text = "word \uFB2A\uFB2B end"  # shin dot, sin dot
    seq = hebrew_split_sequence(text)
    assert seq == ['\uFB2A\uFB2B']


# --- compare_entry ---

def test_identical():
    en = "I. אָבַל verb\n@@SPLIT:stem@@\nQal אָבַל\n@@SPLIT:stem@@\nHiph הֶאֱבַלְתִּי\n"
    fr = "I. אָבַל verbe\n@@SPLIT:stem@@\nQal אָבַל\n@@SPLIT:stem@@\nHiph הֶאֱבַלְתִּי\n"
    ok, detail = compare_entry(en, fr)
    assert ok is True
    assert detail is None


def test_different_latin_same_hebrew():
    """Different Latin text but same Hebrew = match."""
    en = "English text אוּלָם proper name\n@@SPLIT:sense@@\n1. אוּלָם ref\n"
    fr = "Texte français אוּלָם nom propre\n@@SPLIT:sense@@\n1. אוּלָם réf\n"
    ok, detail = compare_entry(en, fr)
    assert ok is True


def test_missing_split_in_french():
    en = "אוּלָם\n@@SPLIT:sense@@\n1.\n@@SPLIT:sense@@\n2.\n"
    fr = "אוּלָם\n@@SPLIT:sense@@\n1.\n2.\n"  # missing second split
    ok, detail = compare_entry(en, fr)
    assert ok is False
    assert 'extra' in detail or 'diverge' in detail


def test_split_in_wrong_position():
    """Split placed before different Hebrew word."""
    en = "אוּלָם\n@@SPLIT:sense@@\nאָבַל\nתֶּאֱבַל\n"
    fr = "אוּלָם\nאָבַל\n@@SPLIT:sense@@\nתֶּאֱבַל\n"
    ok, detail = compare_entry(en, fr)
    assert ok is False
    assert 'diverge' in detail


def test_extra_split_in_french():
    en = "אוּלָם\n@@SPLIT:sense@@\nאָבַל\n"
    fr = "אוּלָם\n@@SPLIT:sense@@\n@@SPLIT:sense@@\nאָבַל\n"
    ok, detail = compare_entry(en, fr)
    assert ok is False


def test_no_splits_both_sides():
    """No splits at all — Hebrew still compared."""
    en = "English אוּלָם text אָבַל"
    fr = "Français אוּלָם texte אָבַל"
    ok, detail = compare_entry(en, fr)
    assert ok is True


def test_hebrew_mismatch():
    """Different Hebrew = mismatch even with matching splits."""
    en = "אוּלָם\n@@SPLIT:sense@@\nאָבַל\n"
    fr = "אוּלָם\n@@SPLIT:sense@@\nתֶּאֱבַל\n"
    ok, detail = compare_entry(en, fr)
    assert ok is False
    assert 'diverge' in detail


def test_wrong_split_type():
    """@@SPLIT:stem@@ vs @@SPLIT:sense@@ = mismatch."""
    en = "אוּלָם\n@@SPLIT:stem@@\nאָבַל\n"
    fr = "אוּלָם\n@@SPLIT:sense@@\nאָבַל\n"
    ok, detail = compare_entry(en, fr)
    assert ok is False
    assert 'diverge' in detail


# --- Integration: real BDB entries ---

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT_DIR = os.path.join(BASE, "Entries_txt")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


@pytest.mark.parametrize("entry_id", ["BDB200", "BDB1300"])
def test_real_entry_with_splits(entry_id):
    """Known entries with splits should have matching Hebrew+SPLIT sequences
    if their French files have markers."""
    en_path = os.path.join(TXT_DIR, f"{entry_id}.txt")
    fr_path = os.path.join(TXT_FR_DIR, f"{entry_id}.txt")
    if not os.path.exists(en_path) or not os.path.exists(fr_path):
        pytest.skip(f"{entry_id} not found")

    en = open(en_path, encoding='utf-8').read()
    fr = open(fr_path, encoding='utf-8').read()

    # Only test if French has splits
    import re
    split_re = re.compile(r'^@@SPLIT:\w+@@$', re.MULTILINE)
    if not split_re.search(fr):
        pytest.skip(f"{entry_id} French has no splits yet")

    ok, detail = compare_entry(en, fr)
    assert ok, f"{entry_id}: {detail}"


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
