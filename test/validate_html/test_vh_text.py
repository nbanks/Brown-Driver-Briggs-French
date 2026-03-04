#!/usr/bin/env python3
"""Text content matching tests for validate_html.

Covers: ampersand handling, strict text matching, scholarly ampersands,
French articles/prepositions, repeated phrases, translated tag divergence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
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


class TestAmpersandScholarly(unittest.TestCase):
    """&amp; in scholarly sigla (present in original) should be allowed in
    French HTML. Bare & (not &amp;) should be flagged as bad encoding."""

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

    def test_txtfr_ampersand_correctly_encoded(self):
        """txt_fr has &, HTML has &amp; — correct, no error."""
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
        amp_issues = [i for i in issues if "amp" in i.lower()
                      or "omitted" in i.lower() or "fabricated" in i.lower()]
        self.assertEqual(amp_issues, [],
                         f"Correct &amp; encoding should not be flagged: {amp_issues}")

    def test_txtfr_ampersand_omitted_in_html(self):
        """txt_fr has & but HTML omits it entirely — should be flagged."""
        fr_no_amp = (
            '<html><head><link rel="stylesheet" href="style.css"></head>\n'
            '<h1>\n'
            '    <entry onclick="bdbid(\'BDB107\')">BDB107</entry>\n'
            '</h1>\n'
            '<language>h\u00e9breu biblique</language>\n'
            '<p>I. <bdbheb>\u05D0\u05D3\u05DD</bdbheb> (comparer assyrien '
            '[<highlight>ad\u00e2mu</highlight>] '
            '<highlight>faire, produire</highlight> (?)\n'
            '    <lookup onclick="bdbabb(\'Dl\')">Dl<sup>W</sup> '
            '<sup>Pr 104</sup></lookup>). </p>\n'
            '<hr>\n\n</html>'
        )
        issues = validate_html(self._ORIG, fr_no_amp, self._TXT_FR)
        amp_issues = [i for i in issues if "omitted" in i.lower()]
        self.assertTrue(len(amp_issues) >= 1,
                        f"Should flag omitted &: {issues}")

    def test_ampersand_fabricated_in_html(self):
        """txt_fr has no &, but HTML introduces &amp; — should be flagged."""
        orig_no_amp = (
            '<html><head></head><body>'
            '<language>Biblical Hebrew</language>'
            '<p><pos>verb</pos> <primary>mourn</primary></p>'
            '</body></html>'
        )
        txt_fr_no_amp = (
            "=== BDB50 ===\n"
            "h\u00e9breu biblique\n"
            "\n"
            "verbe pleurer\n"
            "\n"
            "---\n"
        )
        fr_with_amp = (
            '<html><head></head><body>'
            '<language>h\u00e9breu biblique</language>'
            '<p><pos>verbe</pos> <primary>pleurer</primary> &amp; plus</p>'
            '</body></html>'
        )
        issues = validate_html(orig_no_amp, fr_with_amp, txt_fr_no_amp)
        amp_issues = [i for i in issues if "fabricated" in i.lower()]
        self.assertTrue(len(amp_issues) >= 1,
                        f"Should flag fabricated &amp;: {issues}")


class TestFrenchArticlesPrepositions(unittest.TestCase):
    """French prose has articles/contractions absent in English."""

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


class TestRepeatedPhraseFalsePositive(unittest.TestCase):
    """When the same French phrase appears in multiple senses, the validator
    should not match against the wrong occurrence."""

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


class TestTranslatedTagDivergence(unittest.TestCase):
    """Catch word-level divergence inside translated tags (e.g. <meta>).

    Reproduces BDB9907: txt_fr has 'figuré' but the LLM wrote 'figuratif'
    inside <meta>.  The divergence is past the 40% prefix mark, so the old
    _find_mismatch returned None and the user got the unhelpful fallback
    'French text missing from HTML: ...' with no indication of what differs.
    """

    ORIG = (
        '<html><head><link rel="stylesheet" href="style.css"></head>'
        '<h1><entry onclick="bdbid(\'BDB9907\')">BDB9907</entry> '
        '[<entry onclick="sn(\'H7487\')">H7487</entry> '
        '<entry onclick="sn(\'H7488\')">H7488</entry>]</h1>'
        '<language>Biblical Aramaic</language>'
        '<p><bdbarc>\u05E8\u05B7\u05E2\u05B2\u05E0\u05B7\u05DF</bdbarc> '
        '<pos>adjective</pos> '
        '<primary>flourishing</primary> (perhaps loan-word from Biblical '
        'Hebrew <bdbarc>\u05E8\u05B7\u05E2\u05B2\u05E0\u05B8\u05DF</bdbarc> '
        '<highlight>luxuriant</highlight>, \u221A '
        '<bdbarc>\u05E8\u05E2\u05DF</bdbarc>); \u2014 '
        '<descrip><meta>figurative</meta> of person</descrip> '
        '<ref ref="Dan 4:1" b="27" cBegin="4" vBegin="1" cEnd="4" vEnd="1" '
        'onclick="bcv(27,4,1)">Dan 4:1</ref> (compare Biblical Hebrew '
        '<ref ref="Ps 92:15" b="19" cBegin="92" vBegin="15" cEnd="92" '
        'vEnd="15" onclick="bcv(19,92,15)">Ps 92:15</ref>).</p>'
        '<hr></html>'
    )

    TXT_FR = (
        '=== BDB9907 H7487 H7488 ===\n'
        'aram\u00e9en biblique\n'
        '\n'
        '\u05E8\u05B7\u05E2\u05B2\u05E0\u05B7\u05DF\n'
        'adjectif\n'
        'florissant (peut-\u00eatre emprunt \u00e0 l\u2019h\u00e9breu '
        'biblique \u05E8\u05B7\u05E2\u05B2\u05E0\u05B8\u05DF\n'
        'luxuriant, \u221A \u05E8\u05E2\u05DF) ; \u2014 figur\u00e9 de '
        'personne Dn 4,1 (comparer h\u00e9breu biblique Ps 92,15).\n'
        '\n'
        '---\n'
    )

    def _make_fr(self, meta_word):
        """Build French HTML, varying only the <meta> content."""
        return (
            '<html><head><link rel="stylesheet" href="style.css"></head>'
            '<h1><entry onclick="bdbid(\'BDB9907\')">BDB9907</entry> '
            '[<entry onclick="sn(\'H7487\')">H7487</entry> '
            '<entry onclick="sn(\'H7488\')">H7488</entry>]</h1>'
            '<language>aram\u00e9en biblique</language>'
            '<p><bdbarc>\u05E8\u05B7\u05E2\u05B2\u05E0\u05B7\u05DF</bdbarc> '
            '<pos>adjectif</pos> '
            '<primary>florissant</primary> (peut-\u00eatre emprunt '
            '\u00e0 l\u2019h\u00e9breu biblique '
            '<bdbarc>\u05E8\u05B7\u05E2\u05B2\u05E0\u05B8\u05DF</bdbarc> '
            '<highlight>luxuriant</highlight>, \u221A '
            '<bdbarc>\u05E8\u05E2\u05DF</bdbarc>) ; \u2014 '
            f'<descrip><meta>{meta_word}</meta> de personne</descrip> '
            '<ref ref="Dan 4:1" b="27" cBegin="4" vBegin="1" cEnd="4" '
            'vEnd="1" onclick="bcv(27,4,1)">Dn 4,1</ref> (comparer '
            'h\u00e9breu biblique '
            '<ref ref="Ps 92:15" b="19" cBegin="92" vBegin="15" cEnd="92" '
            'vEnd="15" onclick="bcv(19,92,15)">Ps 92,15</ref>).</p>'
            '<hr></html>'
        )

    def test_correct_figure_passes(self):
        """HTML with 'figuré' (matching txt_fr) should pass."""
        fr = self._make_fr('figur\u00e9')
        issues = validate_html(self.ORIG, fr, self.TXT_FR)
        text_issues = [i for i in issues
                       if 'French text' in i and ('missing' in i or 'match' in i.lower())]
        self.assertEqual(text_issues, [],
                         f"False positive on correct translation: {text_issues}")

    def test_figuratif_pinpoints_divergence(self):
        """HTML with 'figuratif' instead of 'figuré' must produce a message
        that mentions the actual diverging words, not just 'missing from HTML'.
        """
        fr = self._make_fr('figuratif')
        issues = validate_html(self.ORIG, fr, self.TXT_FR)
        text_issues = [i for i in issues
                       if 'French text' in i and ('missing' in i or 'match' in i.lower())]
        self.assertGreater(len(text_issues), 0,
                           "Divergence not detected at all")
        # The message should pinpoint the difference, not be a generic fallback
        for msg in text_issues:
            self.assertNotIn('missing from HTML', msg,
                             f"Got unhelpful fallback instead of pinpointed "
                             f"divergence: {msg}")
            self.assertIn('figur', msg,
                          f"Message doesn't mention the diverging word: {msg}")


if __name__ == "__main__":
    unittest.main()
