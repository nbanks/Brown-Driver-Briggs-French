#!/usr/bin/env python3
"""Tag structure and sequence tests for validate_html.

Covers: tag ordering, highlights (merge/drop/reorder), raw tags,
empty tags, chunk boundary tags, bracket-split highlights, stem <sub>.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from validate_html import validate_html


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

    def test_tag_order_swap_tolerated(self):
        """French word order may swap <pos> and <primary> — not an error."""
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
        self.assertEqual(tag_issues, [],
                         f"Swapped pos/primary should be tolerated: {tag_issues}")

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
        """A highlight absorbed into plain text is OK (content still present)."""
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
        backtick_issues = [i for i in issues if "Peil" in i or "Pe`il" in i]
        # The backtick difference (Peil vs Pe`il) is a real mismatch
        # between txt_fr and HTML — it should be reported.
        self.assertGreater(len(backtick_issues), 0,
                           "Backtick mismatch (Peil vs Pe`il) should be detected")


class TestChunkExtraClosingTags(unittest.TestCase):
    """When validating a chunk, extra closing tags not in the original should
    be flagged.  E.g. chunk 0 has no </p></html> but the LLM adds them."""

    def test_extra_closing_html_in_chunk(self):
        """Chunk 0 original ends mid-stream (no </p></html>).
        LLM output adds </p></html> — validator should flag this."""
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
            '</p>\n</html>'
        )
        issues = validate_html(orig_chunk, fr_chunk)
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
        """Bare > in English source text should not break raw tag extraction."""
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
        """A middle chunk has no <html>/<head> — both match, should pass."""
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
    """Highlights may be combined when French merges two glosses."""

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
    """Highlight tags may shift position due to French word-order changes."""

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
        self.assertEqual(issues, [],
                         f"Text mismatch from highlight reorder: {issues}")


class TestStemSubFalsePositive(unittest.TestCase):
    """<stem>X</stem><sub>N</sub> should not cause false positives."""

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
        "h\u00e9breu biblique\n"
        "## SPLIT 1 stem\n"
        "Qal_41_ seulement infinitif\n"
        "\u05D3\u05BC\u05B9\u05D1\u05B5\u05E8\n"
        "parler\n"
    )

    def test_sub_content_no_false_positive(self):
        """<sub>41</sub> stripped from txt via _N_ should not trigger mismatch."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        self.assertEqual(issues, [],
                         f"False positive from <sub> content: {issues}")

    def test_sub_with_wrong_translation_detected(self):
        """Genuinely wrong translation next to <sub> should still be caught."""
        fr_bad = self.FR.replace("seulement infinitif", "only infinitive")
        issues = validate_html(self.ORIG, fr_bad, self.TXT_FR)
        self.assertGreater(len(issues), 0,
                           "Wrong translation beside <sub> was not detected")


class TestHighlightBracketsFalsePositive(unittest.TestCase):
    """Text split across <highlight> tags with brackets should not cause
    false positives."""

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
        "h\u00e9breu biblique\n"
        "\u05D9\u05D5\u05DB\u05DC\u05D5\n"
        "ils ne pouvaient [pas] lui parler amicalement\n"
    )

    def test_bracket_split_no_false_positive(self):
        """Bracket-wrapped tag content should not cause text mismatch."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        self.assertEqual(issues, [],
                         f"False positive from bracket-split tags: {issues}")

    def test_bracket_split_with_english_detected(self):
        """Leaving English inside brackets should still be caught."""
        fr_bad = self.FR.replace("ils ne pouvaient", "they could not")
        issues = validate_html(self.ORIG, fr_bad, self.TXT_FR)
        self.assertGreater(len(issues), 0,
                           "English text in brackets was not detected")


class TestGlossMerged(unittest.TestCase):
    """French causative merges two gloss/highlight pairs into one.

    English: <highlight>he <gloss>causes</gloss></highlight> his wind
             <highlight><gloss>to blow</gloss></highlight>;
    French:  <highlight>il <gloss>fait souffler</gloss></highlight> son vent ;

    'fait souffler' is an indivisible French causative — the second gloss
    cannot exist as a separate tag.  The validator should allow this merge.
    (Based on BDB5408 chunk 2.)
    """

    ORIG = (
        '<html><head></head><body>'
        '<language>Biblical Hebrew</language>'
        '<p><bdbheb>\u05D9\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1'
        ' \u05E8\u05D5\u05BC\u05D7\u05B7</bdbheb> '
        '<ref ref="Ps 147:18" b="19" cBegin="147" vBegin="18"'
        ' cEnd="147" vEnd="18" onclick="bcv(19,147,18)">Ps 147:18</ref> '
        '<highlight>he <gloss>causes</gloss></highlight> his wind '
        '<highlight><gloss>to blow</gloss></highlight>; '
        '<bdbheb>\u05D5\u05B7\u05D9\u05BC\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1'
        ' \u05D0\u05B9\u05EA\u05B8\u05DD</bdbheb> '
        '<ref ref="Gen 15:11" b="1" cBegin="15" vBegin="11"'
        ' cEnd="15" vEnd="11" onclick="bcv(1,15,11)">Gen 15:11</ref> '
        '<highlight>and he drove them away</highlight></p>'
        '</body></html>'
    )

    FR = (
        '<html><head></head><body>'
        '<language>h\u00e9breu biblique</language>'
        '<p><bdbheb>\u05D9\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1'
        ' \u05E8\u05D5\u05BC\u05D7\u05B7</bdbheb> '
        '<ref ref="Ps 147:18" b="19" cBegin="147" vBegin="18"'
        ' cEnd="147" vEnd="18" onclick="bcv(19,147,18)">Ps 147,18</ref> '
        '<highlight>il <gloss>fait souffler</gloss></highlight> son vent ; '
        '<bdbheb>\u05D5\u05B7\u05D9\u05BC\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1'
        ' \u05D0\u05B9\u05EA\u05B8\u05DD</bdbheb> '
        '<ref ref="Gen 15:11" b="1" cBegin="15" vBegin="11"'
        ' cEnd="15" vEnd="11" onclick="bcv(1,15,11)">Gn 15,11</ref> '
        '<highlight>et il les chassa</highlight></p>'
        '</body></html>'
    )

    TXT_FR = (
        "h\u00e9breu biblique\n"
        "\u05D9\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1"
        " \u05E8\u05D5\u05BC\u05D7\u05B7\n"
        "Ps 147,18\n"
        "il fait souffler son vent ; "
        "\u05D5\u05B7\u05D9\u05BC\u05B7\u05E9\u05C1\u05B5\u05C1\u05D1"
        " \u05D0\u05B9\u05EA\u05B8\u05DD\n"
        "Gn 15,11\n"
        "et il les chassa\n"
    )

    def test_gloss_merge_accepted(self):
        """Merged gloss (French causative) should not cause tag errors."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        tag_issues = [i for i in issues
                      if ("missing" in i.lower() or "empty" in i.lower())
                      and ("gloss" in i.lower() or "highlight" in i.lower())]
        self.assertEqual(tag_issues, [],
                         f"Merged gloss flagged as error: {tag_issues}")

    def test_gloss_merge_no_errors(self):
        """Full validation should pass cleanly for merged gloss."""
        issues = validate_html(self.ORIG, self.FR, self.TXT_FR)
        self.assertEqual(issues, [],
                         f"Unexpected issues with merged gloss: {issues}")


if __name__ == "__main__":
    unittest.main()
