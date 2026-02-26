#!/usr/bin/env python3
"""Tests for scripts/validate_html.py, focused on &amp; vs 'et' handling."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_html import validate_file


class TestAmpersandEt(unittest.TestCase):
    """The original HTML uses &amp; but the French txt uses 'et'.

    validate_html should treat these as equivalent so that a correct
    translation like '&amp;' -> 'et' doesn't get flagged as missing text.
    """

    def _run(self, orig_html, fr_html, txt_fr):
        """Write temp files and run validate_file, return issue list."""
        with tempfile.TemporaryDirectory() as d:
            entries = os.path.join(d, "Entries")
            entries_fr = os.path.join(d, "Entries_fr")
            txt_fr_dir = os.path.join(d, "Entries_txt_fr")
            os.makedirs(entries)
            os.makedirs(entries_fr)
            os.makedirs(txt_fr_dir)

            for path, content in [
                (os.path.join(entries, "BDB10.html"), orig_html),
                (os.path.join(entries_fr, "BDB10.html"), fr_html),
                (os.path.join(txt_fr_dir, "BDB10.txt"), txt_fr),
            ]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

            return validate_file(
                "BDB10",
                entries_dir=entries,
                entries_fr_dir=entries_fr,
                txt_fr_dir=txt_fr_dir,
            )

    def test_ampersand_kept_in_html_matches_et_in_txt(self):
        """HTML keeps &amp; from original, txt_fr has 'et' -- should pass."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb>, &amp; <bdbheb>\u05D1</bdbheb>'
            ' (construct) <pos>noun [masculine]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb>, &amp; <bdbheb>\u05D1</bdbheb>'
            ' (construit) <pos>nom [masculin]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        txt = (
            "\u05D0, et \u05D1 (construit) nom [masculin]\n"
            "destruction\n"
        )
        issues = self._run(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i[1]]
        self.assertEqual(missing, [], f"False positive: {missing}")

    def test_ampersand_replaced_by_et_in_html(self):
        """HTML has 'et' instead of &amp; -- should also pass."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb>, &amp; <bdbheb>\u05D1</bdbheb>'
            ' (construct) <pos>noun [masculine]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb>, et <bdbheb>\u05D1</bdbheb>'
            ' (construit) <pos>nom [masculin]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        txt = (
            "\u05D0, et \u05D1 (construit) nom [masculin]\n"
            "destruction\n"
        )
        issues = self._run(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i[1]]
        self.assertEqual(missing, [], f"False positive: {missing}")

    def test_genuinely_missing_text_still_caught(self):
        """If real French text is missing, it should still be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>noun [masculine]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>nom [masculin]</pos>'
            ' <primary>destruction</primary></p>'
            '</body></html>'
        )
        txt = (
            "nom [masculin]\n"
            "destruction\n"
            "cette phrase n'est pas dans le HTML\n"
        )
        issues = self._run(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i[1]]
        self.assertTrue(len(missing) >= 1, "Should flag genuinely missing text")


class TestTagStructure(unittest.TestCase):
    """Tags from the original must appear in the same order in the French."""

    def _run(self, orig_html, fr_html, txt_fr=""):
        with tempfile.TemporaryDirectory() as d:
            entries = os.path.join(d, "Entries")
            entries_fr = os.path.join(d, "Entries_fr")
            txt_fr_dir = os.path.join(d, "Entries_txt_fr")
            os.makedirs(entries)
            os.makedirs(entries_fr)
            os.makedirs(txt_fr_dir)

            for path, content in [
                (os.path.join(entries, "BDB10.html"), orig_html),
                (os.path.join(entries_fr, "BDB10.html"), fr_html),
                (os.path.join(txt_fr_dir, "BDB10.txt"), txt_fr),
            ]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

            return validate_file(
                "BDB10",
                entries_dir=entries,
                entries_fr_dir=entries_fr,
                txt_fr_dir=txt_fr_dir,
            )

    def test_dropped_descrip_tag_flagged(self):
        """BDB133 scenario: LLM drops <descrip> tag to avoid &amp;/et mismatch."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> '
            '<descrip>same official, under David</descrip> '
            '<ref ref="2Sam 20:24" b="10" cBegin="20" vBegin="24"'
            ' cEnd="20" vEnd="24" onclick="bcv(10,20,24)">2Sam 20:24</ref>, '
            '<descrip>&amp; Rehoboam</descrip> '
            '<ref ref="1Kgs 12:18" b="11" cBegin="12" vBegin="18"'
            ' cEnd="12" vEnd="18" onclick="bcv(11,12,18)">1Kgs 12:18</ref>'
            '</p></body></html>'
        )
        # French HTML drops the second <descrip> entirely
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb> '
            '<descrip>m\u00eame fonctionnaire, sous David</descrip> '
            '<ref ref="2Sam 20:24" b="10" cBegin="20" vBegin="24"'
            ' cEnd="20" vEnd="24" onclick="bcv(10,20,24)">2 S 20,24</ref>, '
            'et Roboam '
            '<ref ref="1Kgs 12:18" b="11" cBegin="12" vBegin="18"'
            ' cEnd="12" vEnd="18" onclick="bcv(11,12,18)">1 R 12,18</ref>'
            '</p></body></html>'
        )
        issues = self._run(orig, fr)
        tag_issues = [i for i in issues if "descrip" in i[1].lower()]
        self.assertTrue(len(tag_issues) >= 1,
                        f"Should flag dropped <descrip>: {issues}")

    def test_tag_order_preserved(self):
        """Tags should appear in the same order as the original."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        # French swaps <pos> and <primary>
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><primary>\u00eatre en deuil</primary> <pos>verbe</pos></p>'
            '</body></html>'
        )
        issues = self._run(orig, fr)
        tag_issues = [i for i in issues if "tag" in i[1].lower()
                      and ("sequence" in i[1].lower()
                           or "missing" in i[1].lower()
                           or "extra" in i[1].lower())]
        self.assertTrue(len(tag_issues) >= 1,
                        f"Should flag swapped tag order: {issues}")

    def test_matching_tags_passes(self):
        """Correct translation with same tag structure should pass."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary> '
            '<descrip>note</descrip></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>\u00eatre en deuil</primary> '
            '<descrip>note</descrip></p>'
            '</body></html>'
        )
        issues = self._run(orig, fr)
        tag_issues = [i for i in issues if "tag" in i[1].lower()
                      and ("sequence" in i[1].lower()
                           or "missing" in i[1].lower()
                           or "extra" in i[1].lower())]
        self.assertEqual(tag_issues, [],
                         f"False positive on matching tags: {tag_issues}")


if __name__ == "__main__":
    unittest.main()
