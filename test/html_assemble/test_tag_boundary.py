#!/usr/bin/env python3
"""Regression tests for tag-boundary alignment in validation.

BDB1816 chunk 6 failed on all 6 LLM attempts because the txt_fr text
doesn't map cleanly onto HTML tag boundaries:

1. txt_fr has "les paroles de Dieu" but the LLM translated
   <highlight>words of God</highlight> → <highlight>paroles de Dieu</highlight>,
   dropping the article "les".  The correct output is
   <highlight>les paroles de Dieu</highlight> (article inside the tag).

2. txt_fr has "affaire, chose dont on parle" as one string but the HTML
   splits it across <gloss>matter, affair</gloss>, <descrip>thing about
   which one speaks</descrip>.  The LLM maps "matter, affair" → "affaire,
   chose" and "thing about which one speaks" → "chose dont on parle",
   producing a doubled "chose" when flattened.  The correct mapping is
   <gloss>affaire</gloss>, <descrip>chose dont on parle</descrip>.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_html import validate_html


# Verbatim from the English HTML (Entries/BDB1816.html chunk 6)
ORIG_HTML = (
    '<div class="sense">\n'
    '        <sense>2.</sense>\n'
    '        <descrip><highlight>of God</highlight></descrip>.'
    ' <descrip>It is difficult to determine how many of the following\n'
    '        should\n'
    '        come under\n'
    '        <section>II</section>.<sense>2</sense></descrip>.'
    ' The plural for <highlight>words of God</highlight> is\n'
    '        relatively seldom:'
    ' <ref ref="Gen 20:8" b="1" cBegin="20" vBegin="8"'
    ' cEnd="20" vEnd="8" onclick="bcv(1,20,8)">Gen\n'
    '            20:8</ref>;'
    ' <ref ref="Exod 19:6" b="2" cBegin="19" vBegin="6"'
    ' cEnd="19" vEnd="6" onclick="bcv(2,19,6)">Exod\n'
    '            19:6</ref>;\n'
    '        <ref ref="Jer 3:12" b="24" cBegin="3" vBegin="12"'
    ' cEnd="3" vEnd="12"\n'
    '            onclick="bcv(24,3,12)">Jer 3:12</ref> + 30 t.\n'
    '        Jeremiah.\n'
    '    </div>\n'
    '    <div class="subsense">\n'
    '        <section>IV.</section>\n'
    '        <gloss>matter, affair</gloss>,'
    ' <descrip>thing about which one speaks</descrip>: —\n'
    '        \n'
)

# Verbatim from Entries_txt_fr/BDB1816.txt (chunk 6 portion)
TXT_FR = (
    '## SPLIT 6 sense\n'
    '2.\n'
    'de Dieu. Il est difficile de déterminer combien des suivants\n'
    'devraient\n'
    'relever de\n'
    'II.2. Le pluriel pour les paroles de Dieu est\n'
    'relativement rare : Gn\n'
    '20,8 ; Ex\n'
    '19,6 ;\n'
    'Jr 3,12 + 30 t.\n'
    'Jérémie.\n'
    '\n'
    'IV.\n'
    'affaire, chose dont on parle : —\n'
)

# What the LLM actually produced on all 6 attempts — a reasonable
# translation where "matter, affair" → "affaire, chose" in <gloss>
# and "thing about which one speaks" → "chose dont on parle" in <descrip>.
# This causes "chose" to appear twice when text is flattened.
LLM_ACTUAL_FR_HTML = (
    '<div class="sense">\n'
    '        <sense>2.</sense>\n'
    '        <descrip><highlight>de Dieu</highlight></descrip>.'
    ' <descrip>Il est difficile de déterminer combien des suivants\n'
    '        devraient\n'
    '        relever de\n'
    '        <section>II</section>.<sense>2</sense></descrip>.'
    ' Le pluriel pour <highlight>paroles de Dieu</highlight> est\n'
    '        relativement rare :'
    ' <ref ref="Gen 20:8" b="1" cBegin="20" vBegin="8"'
    ' cEnd="20" vEnd="8" onclick="bcv(1,20,8)">Gn\n'
    '            20,8</ref> ;'
    ' <ref ref="Exod 19:6" b="2" cBegin="19" vBegin="6"'
    ' cEnd="19" vEnd="6" onclick="bcv(2,19,6)">Ex\n'
    '            19,6</ref> ;\n'
    '        <ref ref="Jer 3:12" b="24" cBegin="3" vBegin="12"'
    ' cEnd="3" vEnd="12"\n'
    '            onclick="bcv(24,3,12)">Jr 3,12</ref> + 30 t.\n'
    '        Jérémie.\n'
    '    </div>\n'
    '    <div class="subsense">\n'
    '        <section>IV.</section>\n'
    '        <gloss>affaire, chose</gloss>,'
    ' <descrip>chose dont on parle</descrip> : —\n'
    '        \n'
)

# The ideal split — "affaire" alone in <gloss> avoids duplication
IDEAL_FR_HTML = (
    '<div class="sense">\n'
    '        <sense>2.</sense>\n'
    '        <descrip><highlight>de Dieu</highlight></descrip>.'
    ' <descrip>Il est difficile de déterminer combien des suivants\n'
    '        devraient\n'
    '        relever de\n'
    '        <section>II</section>.<sense>2</sense></descrip>.'
    ' Le pluriel pour les <highlight>paroles de Dieu</highlight> est\n'
    '        relativement rare :'
    ' <ref ref="Gen 20:8" b="1" cBegin="20" vBegin="8"'
    ' cEnd="20" vEnd="8" onclick="bcv(1,20,8)">Gn\n'
    '            20,8</ref> ;'
    ' <ref ref="Exod 19:6" b="2" cBegin="19" vBegin="6"'
    ' cEnd="19" vEnd="6" onclick="bcv(2,19,6)">Ex\n'
    '            19,6</ref> ;\n'
    '        <ref ref="Jer 3:12" b="24" cBegin="3" vBegin="12"'
    ' cEnd="3" vEnd="12"\n'
    '            onclick="bcv(24,3,12)">Jr 3,12</ref> + 30 t.\n'
    '        Jérémie.\n'
    '    </div>\n'
    '    <div class="subsense">\n'
    '        <section>IV.</section>\n'
    '        <gloss>affaire</gloss>,'
    ' <descrip>chose dont on parle</descrip> : —\n'
    '        \n'
)


def test_ideal_split_validates_clean():
    """The ideal tag split (affaire in gloss, chose dont on parle in
    descrip) should validate clean."""
    errors = validate_html(ORIG_HTML, IDEAL_FR_HTML, TXT_FR)
    assert len(errors) == 0, (
        f"Ideal split should validate clean, got {len(errors)} "
        f"errors:\n" + "\n".join(f"  - {e}" for e in errors)
    )


@pytest.mark.xfail(strict=True,
                   reason="LLM output has real errors: missing 'les' and "
                          "duplicated 'chose' — validator correctly rejects")
def test_llm_actual_output_is_rejected():
    """The LLM's actual output has genuine errors and SHOULD be rejected.

    The LLM made two mistakes on all 6 attempts:
    1. Dropped article 'les' — wrote <highlight>paroles de Dieu</highlight>
       instead of <highlight>les paroles de Dieu</highlight>
    2. Duplicated 'chose' — wrote <gloss>affaire, chose</gloss>,
       <descrip>chose dont on parle</descrip> instead of
       <gloss>affaire</gloss>, <descrip>chose dont on parle</descrip>

    The validator correctly catches both.  This test is strict-xfail:
    if the LLM output ever validates clean, something is wrong with
    the validator (it became too lenient).
    """
    errors = validate_html(ORIG_HTML, LLM_ACTUAL_FR_HTML, TXT_FR)
    assert len(errors) == 0
