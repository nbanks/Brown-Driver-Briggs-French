#!/usr/bin/env python3
"""Integration tests for validate_html — full entries and cross-cutting checks.

Covers: full BDB1008 entry, lookup translation, scholarly codes,
Hebrew/Aramaic preservation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from validate_html import validate_html


class TestBDB1008Full(unittest.TestCase):
    """Full BDB1008 entry — lookup display text translated, comma/semicolon
    variation between txt_fr and HTML should not cause a false positive."""

    _ORIG = (
        '<html><head><link rel="stylesheet" href="style.css"></head>\n'
        '<h1>\n'
        '    <entry onclick="bdbid(\'BDB1008\')">BDB1008</entry> '
        '[<entry onclick="sn(\'H972\')">H972</entry>]\n'
        '</h1>\n'
        '<language>Biblical Hebrew</language>\n'
        '<p> [<bdbheb>\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb>] '
        '<pos>noun masculine</pos>\n'
        '    <primary>chosen</primary>, construct '
        '<bdbheb>\u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb>\n'
        '    <ref ref="2Sam 21:6" b="10" cBegin="21" vBegin="6" '
        'cEnd="21" vEnd="6" onclick="bcv(10,21,6)">2Sam 21:6</ref> (but\n'
        '    <lookup onclick="bdbabb(\'We\')">We</lookup>\n'
        '    <lookup onclick="bdbabb(\'Dr\')">Dr</lookup>\n'
        '    <bdbheb>\u05F3</bdbheb>\n'
        '    <bdbheb>\u05D1\u05B0\u05BC\u05D4\u05B7\u05E8 \u05D9</bdbheb>); '
        'suffix <bdbheb>'
        '\u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8\u05B8\u05D9\u05D5</bdbheb>\n'
        '    <ref ref="1Chr 16:13" b="13" cBegin="16" vBegin="13" '
        'cEnd="16" vEnd="13" onclick="bcv(13,16,13)">1Chr 16:13</ref>;\n'
        '    <ref ref="Ps 89:4" b="19" cBegin="89" vBegin="4" '
        'cEnd="89" vEnd="4" onclick="bcv(19,89,4)">Ps 89:4</ref>; '
        '<ref ref="Ps 105:6" b="19" cBegin="105" vBegin="6" '
        'cEnd="105" vEnd="6" onclick="bcv(19,105,6)">Ps 105:6</ref>; '
        '<ref ref="Ps 105:43" b="19" cBegin="105" vBegin="43" '
        'cEnd="105" vEnd="43" onclick="bcv(19,105,43)">Ps 105:43</ref>;\n'
        '    <ref ref="Ps 106:5" b="19" cBegin="106" vBegin="5" '
        'cEnd="106" vEnd="5" onclick="bcv(19,106,5)">Ps 106:5</ref>; '
        '<ref ref="Ps 106:23" b="19" cBegin="106" vBegin="23" '
        'cEnd="106" vEnd="23" onclick="bcv(19,106,23)">Ps 106:23</ref>\n'
        '    <lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup>, '
        '<ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1" '
        'cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Isa 42:1</ref>; '
        '<ref ref="Isa 43:20" b="23" cBegin="43" vBegin="20" '
        'cEnd="43" vEnd="20" onclick="bcv(23,43,20)">Isa 43:20</ref>; '
        '<ref ref="Isa 45:4" b="23" cBegin="45" vBegin="4" '
        'cEnd="45" vEnd="4" onclick="bcv(23,45,4)">Isa 45:4</ref>; '
        '<ref ref="Isa 65:9" b="23" cBegin="65" vBegin="9" '
        'cEnd="65" vEnd="9" onclick="bcv(23,65,9)">Isa 65:9</ref>; '
        '<ref ref="Isa 65:15" b="23" cBegin="65" vBegin="15" '
        'cEnd="65" vEnd="15" onclick="bcv(23,65,15)">Isa 65:15</ref>; '
        '<ref ref="Isa 65:22" b="23" cBegin="65" vBegin="22" '
        'cEnd="65" vEnd="22" onclick="bcv(23,65,22)">Isa 65:22</ref> '
        '<descrip>always the <highlight>chosen</highlight> or\n'
        '    <highlight>elect</highlight> of Yahweh</descrip>.\n'
        '</p>\n'
        '<hr>\n\n'
        '</html>'
    )

    _FR = (
        '<html><head><link rel="stylesheet" href="style.css"></head>\n'
        '<h1>\n'
        '    <entry onclick="bdbid(\'BDB1008\')">BDB1008</entry> '
        '[<entry onclick="sn(\'H972\')">H972</entry>]\n'
        '</h1>\n'
        '<language>h\u00e9breu biblique</language>\n'
        '<p> [<bdbheb>\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb>] '
        '<pos>nom masculin</pos>\n'
        '    <primary>choisi</primary>, construit '
        '<bdbheb>\u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb>\n'
        '    <ref ref="2Sam 21:6" b="10" cBegin="21" vBegin="6" '
        'cEnd="21" vEnd="6" onclick="bcv(10,21,6)">2 S 21,6</ref> (mais\n'
        '    <lookup onclick="bdbabb(\'We\')">We</lookup>\n'
        '    <lookup onclick="bdbabb(\'Dr\')">Dr</lookup>\n'
        '    <bdbheb>\u05F3</bdbheb>\n'
        '    <bdbheb>\u05D1\u05B0\u05BC\u05D4\u05B7\u05E8 \u05D9</bdbheb>) ; '
        'suffixe <bdbheb>'
        '\u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8\u05B8\u05D9\u05D5</bdbheb>\n'
        '    <ref ref="1Chr 16:13" b="13" cBegin="16" vBegin="13" '
        'cEnd="16" vEnd="13" onclick="bcv(13,16,13)">1 Ch 16,13</ref> ;\n'
        '    <ref ref="Ps 89:4" b="19" cBegin="89" vBegin="4" '
        'cEnd="89" vEnd="4" onclick="bcv(19,89,4)">Ps 89,4</ref> ; '
        '<ref ref="Ps 105:6" b="19" cBegin="105" vBegin="6" '
        'cEnd="105" vEnd="6" onclick="bcv(19,105,6)">Ps 105,6</ref> ; '
        '<ref ref="Ps 105:43" b="19" cBegin="105" vBegin="43" '
        'cEnd="105" vEnd="43" onclick="bcv(19,105,43)">Ps 105,43</ref> ;\n'
        '    <ref ref="Ps 106:5" b="19" cBegin="106" vBegin="5" '
        'cEnd="106" vEnd="5" onclick="bcv(19,106,5)">Ps 106,5</ref> ; '
        '<ref ref="Ps 106:23" b="19" cBegin="106" vBegin="23" '
        'cEnd="106" vEnd="23" onclick="bcv(19,106,23)">Ps 106,23</ref>\n'
        '    <lookup onclick="bdbabb(\'Isa\')">Es<sup>3</sup></lookup>, '
        '<ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1" '
        'cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Es 42,1</ref> ; '
        '<ref ref="Isa 43:20" b="23" cBegin="43" vBegin="20" '
        'cEnd="43" vEnd="20" onclick="bcv(23,43,20)">Es 43,20</ref> ; '
        '<ref ref="Isa 45:4" b="23" cBegin="45" vBegin="4" '
        'cEnd="45" vEnd="4" onclick="bcv(23,45,4)">Es 45,4</ref> ; '
        '<ref ref="Isa 65:9" b="23" cBegin="65" vBegin="9" '
        'cEnd="65" vEnd="9" onclick="bcv(23,65,9)">Es 65,9</ref> ; '
        '<ref ref="Isa 65:15" b="23" cBegin="65" vBegin="15" '
        'cEnd="65" vEnd="15" onclick="bcv(23,65,15)">Es 65,15</ref> ; '
        '<ref ref="Isa 65:22" b="23" cBegin="65" vBegin="22" '
        'cEnd="65" vEnd="22" onclick="bcv(23,65,22)">Es 65,22</ref> '
        '<descrip>toujours le <highlight>choisi</highlight> ou\n'
        '    <highlight>l\'\u00e9lu</highlight> de Yahv\u00e9</descrip>.\n'
        '</p>\n'
        '<hr>\n\n'
        '</html>'
    )

    _TXT_FR = (
        "=== BDB1008 H972 ===\n"
        "h\u00e9breu biblique\n"
        "\n"
        "[\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8] nom masculin\n"
        "choisi, construit \u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8\n"
        "2 S 21,6 (mais\n"
        "We\n"
        "Dr\n"
        "\u05F3\n"
        "\u05D1\u05B0\u05BC\u05D4\u05B7\u05E8 \u05D9) ; suffixe "
        "\u05D1\u05B0\u05BC\u05D7\u05B4\u05D9\u05E8\u05B8\u05D9\u05D5\n"
        "1 Ch 16,13 ;\n"
        "Ps 89,4 ; Ps 105,6 ; Ps 105,43 ;\n"
        "Ps 106,5 ; Ps 106,23\n"
        "Es^3^, Es 42,1 ; Es 43,20 ; Es 45,4 ; Es 65,9 ; Es 65,15 ; "
        "Es 65,22 toujours le choisi ou\n"
        "l'\u00e9lu de Yahv\u00e9.\n"
        "\n"
        "---\n"
    )

    def test_correct_bdb1008_no_false_positive(self):
        issues = validate_html(self._ORIG, self._FR, self._TXT_FR)
        serious = [i for i in issues
                   if "missing" in i.lower()
                   or "English book" in i
                   or "English remnant" in i]
        self.assertEqual(serious, [],
                         f"False positive on correct BDB1008: {serious}")


class TestLookupTranslation(unittest.TestCase):
    """Lookup visible text should be translated (book names), attributes kept."""

    _ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Hebrew</language>'
        '<p><bdbheb>\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb> '
        '<pos>noun masculine</pos> '
        '<primary>chosen</primary>, '
        '<ref ref="Ps 106:23" b="19" cBegin="106" vBegin="23"'
        ' cEnd="106" vEnd="23" onclick="bcv(19,106,23)">Ps 106:23</ref> '
        '<lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup>, '
        '<ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1"'
        ' cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Isa 42:1</ref> '
        '<descrip>always the <highlight>chosen</highlight> of Yahweh</descrip>.'
        '</p></body></html>'
    )

    def test_translated_lookup_passes(self):
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb> '
            '<pos>nom masculin</pos> '
            '<primary>choisi</primary>, '
            '<ref ref="Ps 106:23" b="19" cBegin="106" vBegin="23"'
            ' cEnd="106" vEnd="23" onclick="bcv(19,106,23)">Ps 106,23</ref> '
            '<lookup onclick="bdbabb(\'Isa\')">Es<sup>3</sup></lookup> ; '
            '<ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1"'
            ' cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Es 42,1</ref> '
            '<descrip>toujours le <highlight>choisi</highlight> de Yahv\u00e9</descrip>.'
            '</p></body></html>'
        )
        txt = (
            "h\u00e9breu biblique\n"
            "\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8 nom masculin\n"
            "choisi,\n"
            "Ps 106,23\n"
            "Es^3^, Es 42,1 toujours le choisi de Yahv\u00e9.\n"
        )
        issues = validate_html(self._ORIG, fr, txt)
        lookup_issues = [i for i in issues if "lookup" in i.lower()
                         or "English book" in i]
        self.assertEqual(lookup_issues, [],
                         f"False positive on translated lookup: {lookup_issues}")

    def test_lookup_book_abbreviation_not_flagged(self):
        """Lookup tags use scholarly abbreviations that happen to match book
        names. These should NOT be flagged."""
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D1\u05B8\u05BC\u05D7\u05B4\u05D9\u05E8</bdbheb> '
            '<pos>nom masculin</pos> '
            '<primary>choisi</primary>, '
            '<ref ref="Ps 106:23" b="19" cBegin="106" vBegin="23"'
            ' cEnd="106" vEnd="23" onclick="bcv(19,106,23)">Ps 106,23</ref> '
            '<lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup> ; '
            '<ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1"'
            ' cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Es 42,1</ref> '
            '<descrip>toujours le <highlight>choisi</highlight> de Yahv\u00e9</descrip>.'
            '</p></body></html>'
        )
        issues = validate_html(self._ORIG, fr)
        book_issues = [i for i in issues if "English book" in i
                       and "lookup" in i.lower()]
        self.assertEqual(book_issues, [],
                         f"Should not flag scholarly Isa in <lookup>: {book_issues}")

    def test_scholarly_code_preserved_no_flag(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>test</primary> '
            '<lookup onclick="bdbabb(\'We\')">We</lookup> '
            '<lookup onclick="bdbabb(\'Dr\')">Dr</lookup></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>test</primary> '
            '<lookup onclick="bdbabb(\'We\')">We</lookup> '
            '<lookup onclick="bdbabb(\'Dr\')">Dr</lookup></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        lookup_issues = [i for i in issues if "lookup" in i.lower()]
        self.assertEqual(lookup_issues, [],
                         f"Should not flag scholarly codes: {lookup_issues}")

    def test_lookup_attribute_preserved(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>test</primary> '
            '<lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>test</primary> '
            'Es<sup>3</sup></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        lookup_issues = [i for i in issues if "lookup" in i.lower()
                         or "missing tag" in i.lower()]
        self.assertTrue(len(lookup_issues) >= 1,
                        f"Should flag missing lookup tag: {issues}")


class TestScholarlyCodes(unittest.TestCase):
    """Scholarly abbreviation codes in <lookup> tags should NOT be flagged
    as English book names."""

    def test_isa_in_lookup_not_flagged(self):
        """'Isa' in <lookup onclick="bdbabb('Isa')"> is a scholarly code."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>noun masculine</pos> <primary>chosen</primary> '
            '<lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>nom masculin</pos> <primary>choisi</primary> '
            '<lookup onclick="bdbabb(\'Isa\')">Isa<sup>3</sup></lookup></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        book_issues = [i for i in issues if "English book" in i]
        self.assertEqual(book_issues, [],
                         f"Should not flag scholarly Isa in lookup: {book_issues}")

    def test_jer_in_lookup_not_flagged(self):
        """'Jer' in <lookup> referring to Jerome should not be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>test</primary> '
            '<lookup onclick="bdbabb(\'Jer\')">Jerome</lookup></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>test</primary> '
            '<lookup onclick="bdbabb(\'Jer\')">Jerome</lookup></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        book_issues = [i for i in issues if "English book" in i]
        self.assertEqual(book_issues, [],
                         f"Should not flag Jerome/Jer in lookup: {book_issues}")

    def test_isa_in_ref_still_flagged(self):
        """'Isa' in <ref> display text IS an English book name (should be Es)."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1"'
            ' cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Isa 42:1</ref></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><ref ref="Isa 42:1" b="23" cBegin="42" vBegin="1"'
            ' cEnd="42" vEnd="1" onclick="bcv(23,42,1)">Isa 42:1</ref></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        book_issues = [i for i in issues if "English book" in i]
        self.assertTrue(len(book_issues) >= 1,
                        f"Should flag untranslated Isa in <ref>: {issues}")


class TestExtraHebrew(unittest.TestCase):
    """French HTML should not contain Hebrew text absent from the original."""

    def test_extra_hebrew_flagged(self):
        """Hebrew in French not in original should be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> <pos>verb</pos>'
            ' <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb> '
            '<bdbheb>\u05D1\u05D2\u05D3</bdbheb> '
            '<pos>verbe</pos>'
            ' <primary>pleurer</primary></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        extra = [i for i in issues if "extra Hebrew" in i]
        self.assertTrue(len(extra) >= 1,
                        f"Should flag extra Hebrew: {issues}")

    def test_missing_hebrew_flagged(self):
        """Hebrew in original but not in French should be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> <bdbheb>\u05D1\u05D2</bdbheb>'
            ' <pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb>'
            ' <pos>verbe</pos> <primary>pleurer</primary></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        missing = [i for i in issues if "missing Hebrew" in i]
        self.assertTrue(len(missing) >= 1,
                        f"Should flag missing Hebrew: {issues}")

    def test_matching_hebrew_passes(self):
        """Same Hebrew in both should not trigger extra Hebrew warning."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0\u05D1</bdbheb> <pos>verb</pos>'
            ' <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0\u05D1</bdbheb> <pos>verbe</pos>'
            ' <primary>pleurer</primary></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        extra = [i for i in issues if "extra Hebrew" in i]
        self.assertEqual(extra, [],
                         f"False positive on matching Hebrew: {extra}")


if __name__ == "__main__":
    unittest.main()
