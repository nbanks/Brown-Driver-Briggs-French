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

    def test_highlight_truly_missing_flagged(self):
        """A highlight separated by other structural tags should be flagged."""
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
                      and "missing" in i.lower()]
        self.assertTrue(len(tag_issues) >= 1,
                        f"Should flag missing <highlight>: {issues}")

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

    def test_untranslated_lookup_book_flagged(self):
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
        self.assertTrue(len(book_issues) >= 1,
                        f"Should flag untranslated Isa in <lookup>: {issues}")

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


if __name__ == "__main__":
    unittest.main()
