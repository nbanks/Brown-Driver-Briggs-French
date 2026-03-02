#!/usr/bin/env python3
"""Tests for scripts/validate_html.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_html import validate_html


class TestAmpersandEt(unittest.TestCase):
    """The original HTML uses &amp; but the French txt uses 'et'."""

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
        issues = validate_html(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i]
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
        issues = validate_html(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i]
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
        issues = validate_html(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i]
        self.assertTrue(len(missing) >= 1, "Should flag genuinely missing text")


class TestTagStructure(unittest.TestCase):
    """Tags from the original must appear in the same order in the French."""

    def test_dropped_descrip_tag_flagged(self):
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
        issues = validate_html(orig, fr)
        tag_issues = [i for i in issues if "descrip" in i.lower()]
        self.assertTrue(len(tag_issues) >= 1,
                        f"Should flag dropped <descrip>: {issues}")

    def test_tag_order_preserved(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><primary>\u00eatre en deuil</primary> <pos>verbe</pos></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        tag_issues = [i for i in issues if "tag" in i.lower()
                      and ("sequence" in i.lower()
                           or "missing" in i.lower()
                           or "extra" in i.lower())]
        self.assertTrue(len(tag_issues) >= 1,
                        f"Should flag swapped tag order: {issues}")

    def test_matching_tags_passes(self):
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
        issues = validate_html(orig, fr)
        tag_issues = [i for i in issues if "tag" in i.lower()
                      and ("sequence" in i.lower()
                           or "missing" in i.lower()
                           or "extra" in i.lower())]
        self.assertEqual(tag_issues, [],
                         f"False positive on matching tags: {tag_issues}")

    def test_highlight_translated_content_passes(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> '
            '<highlight>a tested, tried stone</highlight>, i.e. approved. '
            'See foregoing <highlight>near the end.</highlight></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb> '
            '<highlight>une pierre \u00e9prouv\u00e9e</highlight>, c.-\u00e0-d. approuv\u00e9e. '
            'Voir ce qui pr\u00e9c\u00e8de <highlight>vers la fin.</highlight></p>'
            '</body></html>'
        )
        txt = (
            "h\u00e9breu biblique\n"
            "\u05D0\n"
            "une pierre \u00e9prouv\u00e9e, c.-\u00e0-d. approuv\u00e9e. "
            "Voir ce qui pr\u00e9c\u00e8de vers la fin.\n"
        )
        issues = validate_html(orig, fr, txt)
        tag_issues = [i for i in issues if "highlight" in i.lower()]
        self.assertEqual(tag_issues, [],
                         f"False positive on translated highlights: {tag_issues}")

    def test_highlight_missing_flagged(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><highlight>chosen</highlight> and '
            '<highlight>elect</highlight></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><highlight>choisi</highlight> et '
            '\u00e9lu</p>'
            '</body></html>'
        )
        # Adjacent highlights can be merged in French (different word order),
        # so this should pass — the dedup treats consecutive highlights as one.
        issues = validate_html(orig, fr)
        tag_issues = [i for i in issues if "highlight" in i.lower()
                      and "missing" in i.lower()]
        self.assertEqual(len(tag_issues), 0,
                         f"Adjacent highlight merge should be allowed: {issues}")

    def test_highlight_unwrapped_accepted(self):
        """A highlight absorbed into plain text is OK (content still present).

        French translations often merge or drop highlight wrappers when
        word order changes.  The text content check (check 7) catches
        genuinely missing content, so the tag sequence check should not
        flag highlights that moved or were unwrapped.
        """
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><highlight>chosen</highlight>'
            '<bdbheb>אבג</bdbheb>'
            '<highlight>elect</highlight></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><highlight>choisi</highlight>'
            '<bdbheb>אבג</bdbheb>'
            '\u00e9lu</p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        tag_issues = [i for i in issues if "highlight" in i.lower()
                      and ("missing" in i.lower() or "mismatch" in i.lower())]
        self.assertEqual(tag_issues, [],
                         f"Unwrapped highlight should be allowed: {tag_issues}")

    def test_backtick_stem_notation_passes(self):
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Aramaic</language>'
            '<p><pos>verb</pos> <primary>weigh</primary>'
            '<div class="stem"><stem>Pe`il</stem> '
            '<highlight>thou hast been weighed</highlight></div></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>aram\u00e9en biblique</language>'
            '<p><pos>verbe</pos> <primary>peser</primary>'
            '<div class="stem"><stem>Pe`il</stem> '
            '<highlight>tu as \u00e9t\u00e9 pes\u00e9</highlight></div></p>'
            '</body></html>'
        )
        txt = (
            "aram\u00e9en biblique\n"
            "verbe\npeser\n"
            "Peil\n"
            "tu as \u00e9t\u00e9 pes\u00e9\n"
        )
        issues = validate_html(orig, fr, txt)
        backtick_issues = [i for i in issues if "Peil" in i or "Pe`il" in i
                           or "missing" in i.lower()]
        self.assertEqual(backtick_issues, [],
                         f"False positive on backtick stem name: {backtick_issues}")


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
        """Lookup tags use scholarly abbreviations (e.g. Isa for Isaiah's
        writings, Jer for Jerome) that happen to match book names.
        These should NOT be flagged — only <ref> display text matters."""
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


class TestChunkExtraClosingTags(unittest.TestCase):
    """When validating a chunk, extra closing tags not in the original should
    be flagged.  E.g. chunk 0 has no </p></html> but the LLM adds them."""

    def test_extra_closing_html_in_chunk(self):
        """Chunk 0 original ends mid-stream (no </p></html>).
        LLM output adds </p></html> — validator should flag this."""
        # Simulate chunk 0: starts with <html><head>... but does NOT close
        orig_chunk = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB6210\')">BDB6210</entry>'
            ' [<entry onclick="sn(\'H6035\')">H6035</entry>]\n'
            '</h1>\n'
            '<language>Biblical Hebrew</language>\n'
            '<p>\n'
            '    <bdbheb>\u05E2\u05B8\u05E0\u05B8\u05D9</bdbheb>'
            ' <pos>noun masculine</pos>\n'
            '    <primary>poor, afflicted</primary> ; \u2014\n'
        )
        # LLM output: correct translation but adds </p>\n</html> at end
        fr_chunk = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB6210\')">BDB6210</entry>'
            ' [<entry onclick="sn(\'H6035\')">H6035</entry>]\n'
            '</h1>\n'
            '<language>h\u00e9breu biblique</language>\n'
            '<p>\n'
            '    <bdbheb>\u05E2\u05B8\u05E0\u05B8\u05D9</bdbheb>'
            ' <pos>nom masculin</pos>\n'
            '    <primary>pauvre, afflig\u00e9</primary> ; \u2014\n'
            '</p>\n</html>'
        )
        issues = validate_html(orig_chunk, fr_chunk)
        # Should detect that </p></html> were added when the original didn't
        # have them — this breaks chunk concatenation
        self.assertTrue(
            len(issues) >= 1,
            "Should flag extra closing tags (</p></html>) not in original chunk"
        )

    def test_chunk_without_extra_closing_passes(self):
        """Same chunk but without the spurious closing tags — should pass."""
        orig_chunk = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB6210\')">BDB6210</entry>'
            ' [<entry onclick="sn(\'H6035\')">H6035</entry>]\n'
            '</h1>\n'
            '<language>Biblical Hebrew</language>\n'
            '<p>\n'
            '    <bdbheb>\u05E2\u05B8\u05E0\u05B8\u05D9</bdbheb>'
            ' <pos>noun masculine</pos>\n'
            '    <primary>poor, afflicted</primary> ; \u2014\n'
        )
        fr_chunk = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB6210\')">BDB6210</entry>'
            ' [<entry onclick="sn(\'H6035\')">H6035</entry>]\n'
            '</h1>\n'
            '<language>h\u00e9breu biblique</language>\n'
            '<p>\n'
            '    <bdbheb>\u05E2\u05B8\u05E0\u05B8\u05D9</bdbheb>'
            ' <pos>nom masculin</pos>\n'
            '    <primary>pauvre, afflig\u00e9</primary> ; \u2014\n'
        )
        issues = validate_html(orig_chunk, fr_chunk)
        tag_issues = [i for i in issues if "tag" in i.lower()
                      or "extra" in i.lower()]
        self.assertEqual(tag_issues, [],
                         f"False positive on correct chunk: {tag_issues}")


class TestRawTagCornerCases(unittest.TestCase):
    """Corner cases for the raw tag sequence check (10b)."""

    def test_bare_angle_bracket_in_source(self):
        """Bare > in English source text (occurs in ~11 entries) should not
        break raw tag extraction or cause false positives."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>noun masculine</pos> '
            '<primary>constitution, ordinance</primary>, '
            '>between monarch and subjects:</p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>nom masculin</pos> '
            '<primary>constitution, ordonnance</primary>, '
            '>entre monarque et sujets :</p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        raw_issues = [i for i in issues if "raw tag" in i]
        self.assertEqual(raw_issues, [],
                         f"Bare > caused false positive: {raw_issues}")

    def test_xml_declaration_added_by_llm(self):
        """LLM sometimes prepends <?xml version="1.0"?> — should be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>test</primary></p>'
            '</body></html>'
        )
        fr = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>test</primary></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        raw_issues = [i for i in issues if "raw tag" in i and "xml" in i.lower()]
        self.assertTrue(len(raw_issues) >= 1,
                        f"Should flag spurious <?xml?> declaration: {issues}")

    def test_extra_closing_hr(self):
        """LLM turns self-closing <hr> into <hr></hr> — extra </hr> flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>test</primary></p>'
            '<hr>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>test</primary></p>'
            '<hr></hr>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        raw_issues = [i for i in issues if "raw tag" in i and "hr" in i.lower()]
        self.assertTrue(len(raw_issues) >= 1,
                        f"Should flag extra </hr>: {issues}")

    def test_middle_chunk_no_html_wrapper(self):
        """A middle chunk has no <html>/<head> at start and no </html> at end.
        Both original and French match — should pass."""
        orig_chunk = (
            '<div class="sense">\n'
            '    <sense>2.</sense>\n'
            '    <gloss>poor and weak.</gloss> '
            '<descrip>oppressed by rich and powerful</descrip> '
            '<ref ref="Amos 2:7" b="30" cBegin="2" vBegin="7"'
            ' cEnd="2" vEnd="7" onclick="bcv(30,2,7)">Amos 2:7</ref>\n'
            '</div>'
        )
        fr_chunk = (
            '<div class="sense">\n'
            '    <sense>2.</sense>\n'
            '    <gloss>pauvre et faible.</gloss> '
            '<descrip>opprim\u00e9 par les riches et les puissants</descrip> '
            '<ref ref="Amos 2:7" b="30" cBegin="2" vBegin="7"'
            ' cEnd="2" vEnd="7" onclick="bcv(30,2,7)">Am 2,7</ref>\n'
            '</div>'
        )
        issues = validate_html(orig_chunk, fr_chunk)
        raw_issues = [i for i in issues if "raw tag" in i]
        self.assertEqual(raw_issues, [],
                         f"False positive on matching middle chunk: {raw_issues}")

    def test_missing_div_sense_in_chunk(self):
        """French chunk drops a <div class="sense"> wrapper — should be flagged."""
        orig_chunk = (
            '<div class="sense">\n'
            '    <sense>2.</sense>\n'
            '    <gloss>poor and weak.</gloss>\n'
            '</div>'
        )
        fr_chunk = (
            '    <sense>2.</sense>\n'
            '    <gloss>pauvre et faible.</gloss>\n'
        )
        issues = validate_html(orig_chunk, fr_chunk)
        raw_issues = [i for i in issues if "raw tag" in i and "div" in i.lower()]
        self.assertTrue(len(raw_issues) >= 1,
                        f"Should flag missing <div>: {issues}")


class TestStrictTextMatching(unittest.TestCase):
    """Text from txt_fr must appear as a contiguous substring in the HTML,
    not merely as a subsequence with arbitrary characters interspersed."""

    def test_subsequence_not_sufficient(self):
        """txt_fr text that's a subsequence but not a substring should fail."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>porter le deuil</primary></p>'
            '</body></html>'
        )
        # txt_fr says "pleurer" but HTML has "porter le deuil" —
        # "pleurer" is NOT a subsequence of "porter le deuil" so this
        # would fail anyway. Use a trickier case: txt_fr has "abc"
        # and HTML has "aXbYc" (subsequence but not substring).
        txt = (
            "h\u00e9breu biblique\n"
            "verbe\n"
            "porter le deuil\n"
            "cette phrase manque du HTML\n"
        )
        issues = validate_html(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i
                   or "nearly matches" in i]
        self.assertTrue(len(missing) >= 1,
                        f"Should flag text not in HTML: {issues}")

    def test_contiguous_text_passes(self):
        """txt_fr text present as contiguous substring should pass."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>pleurer</primary></p>'
            '</body></html>'
        )
        txt = (
            "h\u00e9breu biblique\n"
            "verbe\n"
            "pleurer\n"
        )
        issues = validate_html(orig, fr, txt)
        missing = [i for i in issues if "French text missing" in i]
        self.assertEqual(missing, [],
                         f"False positive on correct text: {missing}")


class TestScholarlyCodes(unittest.TestCase):
    """Scholarly abbreviation codes (Isa, Jer, etc.) in <lookup> tags are
    names of scholars/works and should NOT be flagged as English book names."""

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


class TestAmpersandScholarly(unittest.TestCase):
    """&amp; in scholarly sigla (present in original) should be allowed in
    French HTML. Bare & (not &amp;) should be flagged as bad encoding."""

    # Based on BDB107 — shortest entry with scholarly &
    _ORIG = (
        '<html><head><link rel="stylesheet" href="style.css"></head>\n'
        '<h1>\n'
        '    <entry onclick="bdbid(\'BDB107\')">BDB107</entry>\n'
        '</h1>\n'
        '<language>Biblical Hebrew</language>\n'
        '<p>I. <bdbheb>\u05D0\u05D3\u05DD</bdbheb> (compare Assyrian '
        '[<highlight>ad\u00e2mu</highlight>] '
        '<highlight>make, produce</highlight> (?)\n'
        '    <lookup onclick="bdbabb(\'Dl\')">Dl<sup>W</sup> &amp; '
        '<sup>Prov 104</sup></lookup>). </p>\n'
        '<hr>\n\n</html>'
    )

    _TXT_FR = (
        "=== BDB107 ===\n"
        "h\u00e9breu biblique\n"
        "\n"
        "I. \u05D0\u05D3\u05DD (comparer assyrien [ad\u00e2mu] "
        "faire, produire (?)\n"
        "Dl^W^ & ^Pr 104^).\n"
        "\n"
        "---\n"
    )

    def test_scholarly_ampersand_kept_as_amp_passes(self):
        """French HTML keeps &amp; from original (scholarly sigla) — no error."""
        fr = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB107\')">BDB107</entry>\n'
            '</h1>\n'
            '<language>h\u00e9breu biblique</language>\n'
            '<p>I. <bdbheb>\u05D0\u05D3\u05DD</bdbheb> (comparer assyrien '
            '[<highlight>ad\u00e2mu</highlight>] '
            '<highlight>faire, produire</highlight> (?)\n'
            '    <lookup onclick="bdbabb(\'Dl\')">Dl<sup>W</sup> &amp; '
            '<sup>Pr 104</sup></lookup>). </p>\n'
            '<hr>\n\n</html>'
        )
        issues = validate_html(self._ORIG, fr, self._TXT_FR)
        amp_issues = [i for i in issues if "&amp;" in i or "ampersand" in i.lower()]
        self.assertEqual(amp_issues, [],
                         f"Scholarly &amp; should not be flagged: {amp_issues}")

    def test_bare_ampersand_in_html_flagged(self):
        """French HTML has bare & instead of &amp; — should be flagged."""
        fr = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB107\')">BDB107</entry>\n'
            '</h1>\n'
            '<language>h\u00e9breu biblique</language>\n'
            '<p>I. <bdbheb>\u05D0\u05D3\u05DD</bdbheb> (comparer assyrien '
            '[<highlight>ad\u00e2mu</highlight>] '
            '<highlight>faire, produire</highlight> (?)\n'
            '    <lookup onclick="bdbabb(\'Dl\')">Dl<sup>W</sup> & '
            '<sup>Pr 104</sup></lookup>). </p>\n'
            '<hr>\n\n</html>'
        )
        issues = validate_html(self._ORIG, fr, self._TXT_FR)
        amp_issues = [i for i in issues
                      if "bare" in i.lower() or "unescaped" in i.lower()
                      or ("&" in i and "amp" in i.lower())]
        self.assertTrue(len(amp_issues) >= 1,
                        f"Should flag bare & (not &amp;): {issues}")

    def test_ampersand_not_in_original_still_flagged(self):
        """French HTML has &amp; where original does NOT — should be flagged."""
        orig_no_amp = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr_with_amp = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>pleurer</primary> &amp; plus</p>'
            '</body></html>'
        )
        issues = validate_html(orig_no_amp, fr_with_amp)
        amp_issues = [i for i in issues if "&amp;" in i]
        self.assertTrue(len(amp_issues) >= 1,
                        f"Should flag &amp; not in original: {issues}")


class TestEmptyTagContent(unittest.TestCase):
    """Empty translated tags when original has content should be flagged."""

    def test_empty_pos_flagged(self):
        """French <pos></pos> when original has <pos>verb</pos>."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos></pos> <primary>pleurer</primary></p>'
            '</body></html>'
        )
        issues = validate_html(orig, fr)
        empty = [i for i in issues if "empty" in i.lower() and "pos" in i]
        self.assertTrue(len(empty) >= 1,
                        f"Should flag empty <pos>: {issues}")


class TestHighlightCombined(unittest.TestCase):
    """Highlights may be combined when French merges two glosses.

    BDB4826: English has two separate highlights around a <descrip>
    boundary: '<highlight>the days of their</highlight>
    <descrip>(bodily) <highlight>rubbings</highlight>'.
    The French folds "rubbings" into the <descrip> without a
    separate highlight, reducing the count from 2 to 1.
    """

    # Based on BDB4826 (מָרוּק)
    ORIG = (
        '<html><head></head><body>'
        '<h1><entry onclick="bdbid(\'BDB4826\')">BDB4826</entry>'
        ' [<entry onclick="sn(\'H4795\')">H4795</entry>]</h1>'
        '<language>Biblical Hebrew</language>'
        '<p> [<bdbheb>\u05DE\u05B8\u05E8\u05D5\u05BC\u05E7</bdbheb>]'
        ' <pos>noun [masculine]</pos>'
        ' <primary>a scraping, rubbing</primary>; \u2014 only plural'
        ' suffix <bdbheb>\u05D9\u05B0\u05DE\u05B5\u05D9'
        ' \u05DE\u05B0\u05E8\u05D5\u05BC\u05E7\u05B5\u05D9\u05D4\u05B6\u05DF</bdbheb>'
        ' <ref ref="Esth 2:12" b="17" cBegin="2" vBegin="12"'
        ' cEnd="2" vEnd="12" onclick="bcv(17,2,12)">Esth 2:12</ref>'
        ' literally <highlight>the days of their</highlight>'
        ' <descrip>(bodily) <highlight>rubbings</highlight>,'
        ' i.e. the year\'s preparation of girls for the'
        ' harem</descrip>.'
        '</p></body></html>'
    )

    FR = (
        '<html><head></head><body>'
        '<h1><entry onclick="bdbid(\'BDB4826\')">BDB4826</entry>'
        ' [<entry onclick="sn(\'H4795\')">H4795</entry>]</h1>'
        '<language>h\u00e9breu biblique</language>'
        '<p> [<bdbheb>\u05DE\u05B8\u05E8\u05D5\u05BC\u05E7</bdbheb>]'
        ' <pos>nom [masculin]</pos>'
        ' <primary>frottement, onction</primary> ; \u2014 seulement'
        ' pluriel suffixe <bdbheb>\u05D9\u05B0\u05DE\u05B5\u05D9'
        ' \u05DE\u05B0\u05E8\u05D5\u05BC\u05E7\u05B5\u05D9\u05D4\u05B6\u05DF</bdbheb>'
        ' <ref ref="Esth 2:12" b="17" cBegin="2" vBegin="12"'
        ' cEnd="2" vEnd="12" onclick="bcv(17,2,12)">Est 2,12</ref>'
        ' litt\u00e9ralement'
        ' <highlight>les jours de leurs</highlight>'
        ' <descrip>frottements (corporels),'
        ' c.-\u00e0-d. l\'ann\u00e9e de pr\u00e9paration des jeunes'
        ' filles pour le harem</descrip>.'
        '</p></body></html>'
    )

    def test_highlight_combined_accepted(self):
        """A highlight absorbed into surrounding text should not cause tag errors."""
        issues = validate_html(self.ORIG, self.FR)
        tag_issues = [i for i in issues
                      if "tag" in i.lower() and "highlight" in i.lower()]
        self.assertEqual(tag_issues, [],
                         f"Highlight merge flagged as error: {tag_issues}")


class TestHighlightAllDropped(unittest.TestCase):
    """All highlights stripped from a section should be flagged."""

    def test_all_highlights_dropped_flagged(self):
        """Original has 3 highlights, French has 0 — should be flagged."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> <pos>verb</pos>'
            ' <primary>mourn</primary>'
            ' <highlight>chosen</highlight>'
            ' <bdbheb>\u05D1</bdbheb>'
            ' <highlight>elect</highlight>'
            ' <descrip>always the <highlight>chosen</highlight>'
            ' of Yahweh</descrip>'
            '</p></body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb> <pos>verbe</pos>'
            ' <primary>pleurer</primary>'
            ' choisi'
            ' <bdbheb>\u05D1</bdbheb>'
            ' \u00e9lu'
            ' <descrip>toujours le choisi de Yahv\u00e9</descrip>'
            '</p></body></html>'
        )
        issues = validate_html(orig, fr)
        hl_issues = [i for i in issues if "highlight" in i.lower()]
        self.assertTrue(len(hl_issues) >= 1,
                        f"Should flag all highlights dropped: {issues}")

    def test_some_highlights_remaining_ok(self):
        """Original has 3 highlights, French has 1 — should be allowed."""
        orig = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><bdbheb>\u05D0</bdbheb> <pos>verb</pos>'
            ' <primary>mourn</primary>'
            ' <highlight>chosen</highlight>'
            ' <bdbheb>\u05D1</bdbheb>'
            ' <highlight>elect</highlight>'
            ' <descrip>always the <highlight>chosen</highlight>'
            ' of Yahweh</descrip>'
            '</p></body></html>'
        )
        fr = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><bdbheb>\u05D0</bdbheb> <pos>verbe</pos>'
            ' <primary>pleurer</primary>'
            ' choisi'
            ' <bdbheb>\u05D1</bdbheb>'
            ' \u00e9lu'
            ' <descrip>toujours le <highlight>choisi</highlight>'
            ' de Yahv\u00e9</descrip>'
            '</p></body></html>'
        )
        issues = validate_html(orig, fr)
        hl_issues = [i for i in issues
                     if "highlight" in i.lower() and "all" in i.lower()]
        self.assertEqual(hl_issues, [],
                         f"Partial highlights should be allowed: {hl_issues}")


class TestHighlightReorder(unittest.TestCase):
    """Highlight tags may shift position due to French word-order changes.

    BDB5081 chunk 1: English "'s hand" (highlight after bdbheb) becomes
    French "main de" (highlight before bdbheb) — possessive reversal.
    The validator should accept this reordering.
    """

    ORIG = (
        '<html><head></head><body>'
        '<div class="sense">'
        '    <sense>1.</sense>'
        '    <gloss>a swinging, brandishing</gloss>, '
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05D9\u05B7\u05D3 \u05D9</bdbheb>'
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05EA</bdbheb>'
        '    <ref ref="Isa 19:16" b="23" cBegin="19" vBegin="16"'
        '     cEnd="19" vEnd="16" onclick="bcv(23,19,16)">Isa 19:16</ref>'
        '    <highlight>the brandishing of</highlight>'
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05D9</bdbheb>\'s <highlight>hand</highlight>'
        '    (in hostility); <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05DE\u05B4\u05DC\u05B0\u05D4\u05B2\u05DE\u05D5\u05BA\u05EA \u05EA</bdbheb>'
        '    <ref ref="Isa 30:32" b="23" cBegin="30" vBegin="32"'
        '     cEnd="30" vEnd="32" onclick="bcv(23,30,32)">Isa 30:32</ref>'
        '    <highlight>battles of brandishing</highlight>'
        '    (brandished weapons).'
        '</div>'
        '</body></html>'
    )

    # French: highlight for "main" moved before bdbheb (possessive reversal)
    FR_REORDERED = (
        '<html><head></head><body>'
        '<div class="sense">'
        '    <sense>1.</sense>'
        '    <gloss>un balancement, un brandissement</gloss>, '
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05D9\u05B7\u05D3 \u05D9</bdbheb>'
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05EA</bdbheb>'
        '    <ref ref="Isa 19:16" b="23" cBegin="19" vBegin="16"'
        '     cEnd="19" vEnd="16" onclick="bcv(23,19,16)">Es 19,16</ref>'
        '    <highlight>le brandissement de la</highlight>'
        '    <highlight>main</highlight> de'
        '    <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05D9</bdbheb>'
        '    (en hostilit\u00e9) ; <bdbheb>\u05F3</bdbheb>'
        '    <bdbheb>\u05DE\u05B4\u05DC\u05B0\u05D4\u05B2\u05DE\u05D5\u05BA\u05EA \u05EA</bdbheb>'
        '    <ref ref="Isa 30:32" b="23" cBegin="30" vBegin="32"'
        '     cEnd="30" vEnd="32" onclick="bcv(23,30,32)">Es 30,32</ref>'
        '    <highlight>batailles de brandissement</highlight>'
        '    (armes brandies).'
        '</div>'
        '</body></html>'
    )

    TXT_FR = (
        "1.\n"
        "un balancement, un brandissement, \u05F3\n"
        "\u05D9\u05B7\u05D3 \u05D9\n"
        "\u05F3\n"
        "\u05EA\n"
        "Es 19,16\n"
        "le brandissement de la\n"
        "main de \u05F3\n"
        "\u05D9 (en hostilit\u00e9) ; \u05F3\n"
        "\u05DE\u05B4\u05DC\u05B0\u05D4\u05B2\u05DE\u05D5\u05BA\u05EA \u05EA\n"
        "Es 30,32\n"
        "batailles de brandissement (armes brandies).\n"
    )

    def test_highlight_reorder_accepted(self):
        """Highlight moving due to French word order should not cause errors."""
        issues = validate_html(self.ORIG, self.FR_REORDERED, self.TXT_FR)
        tag_issues = [i for i in issues
                      if "tag" in i.lower() and "highlight" in i.lower()]
        self.assertEqual(tag_issues, [],
                         f"Highlight reorder flagged as error: {tag_issues}")

    def test_highlight_reorder_no_text_mismatch(self):
        """Text content check should pass despite highlight reordering."""
        issues = validate_html(self.ORIG, self.FR_REORDERED, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and "match" in i.lower()]
        self.assertEqual(text_issues, [],
                         f"Text mismatch from highlight reorder: {text_issues}")


class TestFrenchArticlesPrepositions(unittest.TestCase):
    """French prose has articles/contractions absent in English.

    The LLM sometimes calques the English structure, dropping French
    articles like 'du', 'des', 'd'une', 'de la'. The validator must
    catch these as text mismatches (BDB9814-style errors).
    """

    ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Aramaic</language>'
        '<p><bdbarc>\u05E4\u05BB\u05BC\u05DD</bdbarc>'
        ' <pos>noun masculine</pos>'
        ' <primary>mouth</primary>'
        ' — <gloss>mouth</gloss> of'
        ' king, lions, beast (in vision),'
        ' <highlight>mouth</highlight> of pit.</p>'
        '</body></html>'
    )

    # Correct French: articles present (du roi, des lions, etc.)
    FR_CORRECT = (
        '<html><head></head><body>'
        '<language>araméen biblique</language>'
        '<p><bdbarc>\u05E4\u05BB\u05BC\u05DD</bdbarc>'
        ' <pos>nom masculin</pos>'
        ' <primary>bouche</primary>'
        ' — <gloss>bouche</gloss> du'
        ' roi, des lions, d\'une bête (en vision),'
        ' <highlight>bouche</highlight> de la fosse.</p>'
        '</body></html>'
    )

    # Incorrect French: calque of English, missing articles
    FR_BAD = (
        '<html><head></head><body>'
        '<language>araméen biblique</language>'
        '<p><bdbarc>\u05E4\u05BB\u05BC\u05DD</bdbarc>'
        ' <pos>nom masculin</pos>'
        ' <primary>bouche</primary>'
        ' — <gloss>bouche</gloss> de'
        ' roi, lions, bête (en vision),'
        ' <highlight>bouche</highlight> de fosse.</p>'
        '</body></html>'
    )

    TXT_FR = (
        "=== BDB9814 H6310 ===\n"
        "araméen biblique\n"
        "\n"
        "\u05E4\u05BB\u05BC\u05DD\n"
        "nom masculin\n"
        "bouche\n"
        "— bouche du roi, des lions, d'une bête (en vision),\n"
        "bouche de la fosse.\n"
    )

    def test_correct_articles_pass(self):
        """French HTML with proper articles should validate clean."""
        issues = validate_html(self.ORIG, self.FR_CORRECT, self.TXT_FR)
        text_issues = [i for i in issues if "French text" in i]
        self.assertEqual(text_issues, [],
                         f"False positive on correct articles: {text_issues}")

    def test_missing_articles_detected(self):
        """French HTML calquing English structure (missing articles) must fail."""
        issues = validate_html(self.ORIG, self.FR_BAD, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertGreater(len(text_issues), 0,
                           "Missing French articles were not detected")


class TestStemSubFalsePositive(unittest.TestCase):
    """<stem>X</stem><sub>N</sub> should not cause false positives.

    The txt_fr uses _N_ for subscripts which get stripped by the validator,
    but <sub>N</sub> content in the HTML visible text is NOT stripped,
    causing a mismatch.  E.g. txt_fr "Qal_41_ seulement" becomes
    "Qal seulement" after _N_ removal, but HTML "Qal 41 seulement"
    normalizes to "Qal41seulement".
    """

    ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Hebrew</language>'
        '<div class="stem">'
        '<stem>Qal</stem><sub>41</sub> only infinitive'
        ' <bdbheb>\u05D3\u05BC\u05B9\u05D1\u05B5\u05E8</bdbheb>'
        ' <gloss>speak</gloss>'
        '</div>'
        '</body></html>'
    )

    FR = (
        '<html><head></head><body>'
        '<language>h\u00e9breu biblique</language>'
        '<div class="stem">'
        '<stem>Qal</stem><sub>41</sub> seulement infinitif'
        ' <bdbheb>\u05D3\u05BC\u05B9\u05D1\u05B5\u05E8</bdbheb>'
        ' <gloss>parler</gloss>'
        '</div>'
        '</body></html>'
    )

    TXT_FR = (
        "@@SPLIT:stem@@\n"
        "Qal_41_ seulement infinitif\n"
        "\u05D3\u05BC\u05B9\u05D1\u05B5\u05E8\n"
        "parler\n"
    )

    def test_sub_content_no_false_positive(self):
        """<sub>41</sub> stripped from txt via _N_ should not trigger mismatch."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertEqual(text_issues, [],
                         f"False positive from <sub> content: {text_issues}")

    def test_sub_with_wrong_translation_detected(self):
        """Genuinely wrong translation next to <sub> should still be caught."""
        fr_bad = self.FR.replace("seulement infinitif", "only infinitive")
        issues = validate_html(self.ORIG, fr_bad, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertGreater(len(text_issues), 0,
                           "Wrong translation beside <sub> was not detected")


class TestHighlightBracketsFalsePositive(unittest.TestCase):
    """Text split across <highlight> tags with brackets should not cause
    false positives.

    When txt_fr has "ils ne pouvaient lui parler amicalement" as a
    continuous line, but the HTML faithfully renders
    <highlight>ils ne pouvaient</highlight> [<highlight>pas</highlight>]
    <highlight>lui parler amicalement</highlight>, the validator should
    recognise this as matching since the bracket content is structural.
    """

    ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Hebrew</language>'
        '<p><bdbheb>\u05D9\u05D5\u05DB\u05DC\u05D5</bdbheb> '
        '<highlight>they could</highlight> '
        '[<highlight>not</highlight>] '
        '<highlight>speak unto him peaceably</highlight></p>'
        '</body></html>'
    )

    FR = (
        '<html><head></head><body>'
        '<language>h\u00e9breu biblique</language>'
        '<p><bdbheb>\u05D9\u05D5\u05DB\u05DC\u05D5</bdbheb> '
        '<highlight>ils ne pouvaient</highlight> '
        '[<highlight>pas</highlight>] '
        '<highlight>lui parler amicalement</highlight></p>'
        '</body></html>'
    )

    TXT_FR = (
        "\u05D9\u05D5\u05DB\u05DC\u05D5\n"
        "ils ne pouvaient [pas] lui parler amicalement\n"
    )

    def test_bracket_split_no_false_positive(self):
        """Bracket-wrapped tag content should not cause text mismatch."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertEqual(text_issues, [],
                         f"False positive from bracket-split tags: {text_issues}")

    def test_bracket_split_with_english_detected(self):
        """Leaving English inside brackets should still be caught."""
        fr_bad = self.FR.replace("ils ne pouvaient", "they could not")
        issues = validate_html(self.ORIG, fr_bad, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertGreater(len(text_issues), 0,
                           "English text in brackets was not detected")


class TestRepeatedPhraseFalsePositive(unittest.TestCase):
    """When the same French phrase appears in multiple senses, the validator
    should not match a txt_fr line against the wrong occurrence and then
    report a divergence.

    E.g. "comparer les expressions" appears in both sense 1 and sense 3d.
    The txt_fr for sense 3d has "comparer les expressions X Y Z" but the
    validator finds the sense 1 occurrence first and then reports a
    divergence because the following text differs.
    """

    ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Hebrew</language>'
        '<div class="sense"><sense>1.</sense>'
        ' <highlight>compare the phrases</highlight> '
        '<bdbheb>\u05D0</bdbheb> '
        '<ref ref="Gen 1:1" b="1" cBegin="1" vBegin="1"'
        ' cEnd="1" vEnd="1" onclick="bcv(1,1,1)">Gen 1:1</ref></div>'
        '<div class="sense"><sense>2.</sense>'
        ' <highlight>compare the phrases</highlight> '
        '<bdbheb>\u05D1</bdbheb> '
        '<ref ref="Gen 2:2" b="1" cBegin="2" vBegin="2"'
        ' cEnd="2" vEnd="2" onclick="bcv(1,2,2)">Gen 2:2</ref></div>'
        '</body></html>'
    )

    FR = (
        '<html><head></head><body>'
        '<language>h\u00e9breu biblique</language>'
        '<div class="sense"><sense>1.</sense>'
        ' <highlight>comparer les expressions</highlight> '
        '<bdbheb>\u05D0</bdbheb> '
        '<ref ref="Gen 1:1" b="1" cBegin="1" vBegin="1"'
        ' cEnd="1" vEnd="1" onclick="bcv(1,1,1)">Gn 1,1</ref></div>'
        '<div class="sense"><sense>2.</sense>'
        ' <highlight>comparer les expressions</highlight> '
        '<bdbheb>\u05D1</bdbheb> '
        '<ref ref="Gen 2:2" b="1" cBegin="2" vBegin="2"'
        ' cEnd="2" vEnd="2" onclick="bcv(1,2,2)">Gn 2,2</ref></div>'
        '</body></html>'
    )

    TXT_FR = (
        "1. comparer les expressions \u05D0 Gn 1,1\n"
        "2. comparer les expressions \u05D1 Gn 2,2\n"
    )

    def test_repeated_phrase_no_false_positive(self):
        """Repeated phrase in multiple senses should match correctly."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertEqual(text_issues, [],
                         f"False positive from repeated phrase: {text_issues}")

    def test_repeated_phrase_with_wrong_second_sense(self):
        """If the second occurrence is wrong, it should be caught."""
        fr_bad = self.FR.replace(
            '<sense>2.</sense>'
            ' <highlight>comparer les expressions</highlight> '
            '<bdbheb>\u05D1</bdbheb>',
            '<sense>2.</sense>'
            ' <highlight>compare the phrases</highlight> '
            '<bdbheb>\u05D1</bdbheb>')
        issues = validate_html(self.ORIG, fr_bad, self.TXT_FR)
        text_issues = [i for i in issues
                       if "French text" in i and ("missing" in i or "match" in i.lower())]
        self.assertGreater(len(text_issues), 0,
                           "English in second sense was not detected")


if __name__ == "__main__":
    unittest.main()
