# Brown-Driver-Briggs Enhanced -- French Lexicon Project

## What This Is

The Brown-Driver-Briggs Hebrew and English Lexicon (BDB) is the standard
reference dictionary for Biblical Hebrew and Aramaic. Originally published in
1906, its English definitions use archaic, sometimes stilted Victorian prose.

This project maintains a structured JSON extraction of every BDB entry
(`json_output/`, ~10,022 files) alongside the original HTML entries
(`Entries/`). The goal of the **French lexicon conversion** is to produce a
parallel set of JSON files (`json_output.fr/`) where all English-language
content is rendered in clear, modern French while preserving every Hebrew and
Aramaic head word, lemma, and morphological notation exactly as-is.

## Directory Layout

```
Brown-Driver-Briggs-Enhanced/
    Entries/            # Original BDB HTML entries (read-only reference)
    Entries.fr/         # (future) French HTML entries
    json_output/        # English JSON, one file per BDB entry (source of truth)
    json_output.fr/     # French JSON, one file per BDB entry (translation target)
    Placeholders/       # ~6,200 GIF images of cognate-language scripts (see below)
    bdbToStrongsMapping.csv
    placeholders.csv
    untranslated.py     # helper: lists files not yet translated
    CLAUDE.md -> /home/ai/.claude/CLAUDE.md   # system-wide coding conventions
    AGENTS.md           # this file -- project-specific instructions
```

## JSON Entry Schema

Each file in `json_output/` (and its French counterpart) has this shape:

```json
{
    "head_word": "אֵב",              // Hebrew/Aramaic -- NEVER translate
    "pos": "noun [masculine]",       // part of speech -- translate to French
    "primary": "freshness, fresh green",  // gloss -- translate to French
    "description": "one who tries metals", // extended note -- translate
    "senses": [
        {
            "number": 1,
            "primary": "...",        // sense gloss -- translate
            "description": "..."     // sense note -- translate
        }
    ]
}
```

### Translation Rules

1. **`head_word`**: Always Hebrew or Aramaic script. Copy verbatim; never alter.
2. **`pos`** (part of speech): Translate the grammatical label into French.
   Common mappings:
   - "noun masculine" -> "nom masculin"
   - "noun feminine" -> "nom feminin"
   - "noun [masculine]" -> "nom [masculin]"
   - "verb" -> "verbe"
   - "adjective" -> "adjectif"
   - "adverb" -> "adverbe"
   - "preposition" -> "preposition"
   - "conjunction" -> "conjonction"
   - "particle" -> "particule"
   - "pronoun" -> "pronom"
   - "proper name" -> "nom propre"
   - "proper name, masculine" -> "nom propre, masculin"
   - "proper name [of a location]" -> "nom propre [d'un lieu]"
   - "proper name [of a people]" -> "nom propre [d'un peuple]"
   - "proper name [of deity]" -> "nom propre [d'une divinite]"
   - "interjection" -> "interjection"
   - "substantive" -> "substantif"
   - "collective noun feminine" -> "nom collectif feminin"
   - "plural" -> "pluriel"
   - "verbal adjective" -> "adjectif verbal"
   - "verbal noun" -> "nom verbal"
   - Bracket qualifiers like "[of a people]" -> "[d'un peuple]", etc.
   - When unsure, prefer a literal grammatical French equivalent.
3. **`primary`**: The core English gloss. Translate into natural modern French.
   - "freshness, fresh green" -> "fraicheur, vert frais"
   - "mourn" -> "pleurer, porter le deuil"
   - "choose" -> "choisir"
   - "gift" -> "don, cadeau"
   - Proper nouns (place names, personal names) stay unchanged: "Ellasar"
     remains "Ellasar".
4. **`description`**: Longer explanatory text. Translate into modern French.
   Preserve any inline Hebrew/Aramaic strings unchanged. Preserve scholarly
   abbreviations and biblical references as-is.
5. **`senses[].primary`** and **`senses[].description`**: Same rules as the
   top-level `primary` and `description`.
6. **`null` values**: Copy as `null`. Do not invent content.
7. **Empty arrays**: Copy as `[]`.
8. **Formatting**: Match the 4-space indentation of the source JSON.
   No trailing whitespace.

### Biblical Reference Translation

Bible book names must be converted from English abbreviations to their standard
French equivalents. The chapter:verse format stays the same; only the book name
changes. In HTML `<ref>` tags, update the display text but leave the `ref`,
`b`, `cBegin`, `vBegin`, etc. attributes unchanged.

Standard mappings (English -> French):

```
Gen  -> Gn       Exod -> Ex       Lev  -> Lv       Num  -> Nb
Deut -> Dt       Josh -> Jos      Judg -> Jg       Ruth -> Rt
1Sam -> 1 S      2Sam -> 2 S      1Kgs -> 1 R      2Kgs -> 2 R
1Chr -> 1 Ch     2Chr -> 2 Ch     Ezra -> Esd      Neh  -> Ne
Esth -> Est      Job  -> Jb       Ps   -> Ps       Prov -> Pr
Eccl -> Qo       Song -> Ct       Isa  -> Es       Jer  -> Jr
Lam  -> Lm       Ezek -> Ez       Dan  -> Dn       Hos  -> Os
Joel -> Jl       Amos -> Am       Obad -> Ab       Jonah -> Jon
Mic  -> Mi       Nah  -> Na       Hab  -> Ha       Zeph -> So
Hag  -> Ag       Zech -> Za       Mal  -> Ml
```

For multi-word forms commonly seen in BDB:
```
Genesis     -> Genese        Exodus      -> Exode
Leviticus   -> Levitique     Numbers     -> Nombres
Deuteronomy -> Deuteronome   Joshua      -> Josue
Judges      -> Juges         Samuel      -> Samuel
Kings       -> Rois          Chronicles  -> Chroniques
Nehemiah    -> Nehemie       Esther      -> Esther
Psalms      -> Psaumes       Proverbs    -> Proverbes
Ecclesiastes -> Qoheleth     Song of Solomon -> Cantique des Cantiques
Isaiah      -> Esaie         Jeremiah    -> Jeremie
Lamentations -> Lamentations Ezekiel     -> Ezechiel
Daniel      -> Daniel        Hosea       -> Osee
Obadiah     -> Abdias        Jonah       -> Jonas
Micah       -> Michee        Nahum       -> Nahoum
Habakkuk    -> Habacuc       Zephaniah   -> Sophonie
Haggai      -> Aggee         Zechariah   -> Zacharie
Malachi     -> Malachie
```

### What NOT to Translate

- Hebrew and Aramaic text (anything in right-to-left script)
- Strong's numbers ("H8532")
- BDB entry IDs ("BDB10000")
- Scholarly abbreviation codes when they appear inline
- `<ref>` tag attributes (`ref`, `b`, `cBegin`, `vBegin`, etc.)
- Chapter and verse numbers within references

## Workflow

### Helper Script: `untranslated.py`

Shows which files still need translation. It compares `json_output/` against
`json_output.fr/` and `Entries/` against `Entries.fr/`, listing missing files
in numeric BDB order. Displays up to 20 entries by default with relative paths.

The script requires one or more **digit arguments** (0-9) that filter entries
by the last digit of the BDB number. This lets up to 10 workers translate the
corpus in parallel without overlap -- each worker gets a non-overlapping slice.

```
python3 untranslated.py 0            # entries ending in 0
python3 untranslated.py 1 5          # entries ending in 1 or 5
python3 untranslated.py 0 1 2 3 4 5 6 7 8 9   # everything
python3 untranslated.py 3 -n 5       # show 5, ending in 3
python3 untranslated.py 7 --json     # json only, ending in 7
python3 untranslated.py 2 --html     # html only, ending in 2
python3 untranslated.py 9 --count    # just totals, ending in 9
```

Running with no arguments prints help. Exit code 0 when the selected slice is
fully translated, 1 when files remain, 2 on bad arguments.

Worker partitioning example (10-way split):
- Worker A: `untranslated.py 0`  (~1,002 entries)
- Worker B: `untranslated.py 1`  (~1,002 entries)
- ...
- Worker J: `untranslated.py 9`  (~1,002 entries)

### JSON Translation Workflow

The conversion runs in batches. A script reads each file from `json_output/`,
translates the relevant English fields (including Bible book names in
`description` and `senses[].description`), and writes the result to
`json_output.fr/` with the same filename. The script should be idempotent:
re-running it overwrites existing French files without duplication.

### HTML Translation Workflow

HTML entries in `Entries/` contain a mix of custom XML-like tags, Hebrew/Aramaic
script, English prose, and structural markup. Translating them requires a
multi-step approach:

1. **Extract translatable text.** Parse the HTML and pull out only the
   English-language text content, skipping:
   - `<bdbheb>` and `<bdbarc>` tags (Hebrew/Aramaic -- preserve verbatim)
   - `<entry>` tags (BDB IDs and Strong's numbers)
   - `<ref>` tag attributes (keep attributes intact; translate display text)
   - `<lookup>` scholarly abbreviations
   - `<transliteration>` content
   Write the extracted English to a `.txt` working file (one segment per line,
   tagged with its source position so it can be spliced back).

2. **Translate the text.** Convert the extracted English into modern French,
   applying the same rules as for JSON: translate glosses, descriptions, part-
   of-speech labels, and Bible book names. Keep Hebrew/Aramaic strings that
   appear inline in the text unchanged.

3. **Reassemble the HTML.** Splice the French text back into the original HTML
   structure, preserving all tags, attributes, and Hebrew/Aramaic content in
   their original positions. Write the result to `Entries.fr/` with the same
   filename. The `<ref>` display text (e.g. "Dan 7:5") should appear with the
   French book abbreviation (e.g. "Dn 7,5") while `ref=` attributes stay
   unchanged.

Tags and their treatment during extraction:
- `<pos>...</pos>` -- translate content (part of speech)
- `<primary>...</primary>` -- translate content (gloss)
- `<highlight>...</highlight>` -- translate content
- `<descrip>...</descrip>` -- translate content
- `<meta>...</meta>` -- translate content (grammatical terms)
- `<language>...</language>` -- translate content ("Biblical Aramaic" -> "arameen biblique")
- `<bdbheb>...</bdbheb>` -- keep verbatim (Hebrew)
- `<bdbarc>...</bdbarc>` -- keep verbatim (Aramaic)
- `<entry>...</entry>` -- keep verbatim (IDs)
- `<ref ...>...</ref>` -- keep attributes, translate display text (book name)
- `<lookup ...>...</lookup>` -- keep verbatim (scholarly abbreviations)
- `<transliteration>...</transliteration>` -- keep verbatim
- `<reflink>...</reflink>` -- keep verbatim
- `<placeholder*>` -- keep verbatim (cognate-script images; see Placeholders below)
- `<checkingNeeded />`, `<wrongReferenceRemoved />` -- keep verbatim

## Placeholders (Cognate-Language Script Images)

The original BDB lexicon frequently cites cognate words from other Semitic
languages -- Arabic, Syriac, Ethiopic (Ge'ez), Nabataean, Assyrian, etc. --
to illustrate etymological relationships. When the lexicon was digitized, these
non-Hebrew scripts could not be represented in Unicode (or the tooling of the
time did not support them), so each cognate word was saved as a small GIF image
in `Placeholders/` (numbered `1.gif` through `6200.gif`, ~6,200 total).

In the HTML entries, these appear as self-closing tags like `<placeholder1 />`,
`<placeholder6192 />`, etc. The number corresponds to the GIF filename. For
example, `<placeholder8 />` in BDB17 (the entry for אָב "father") is an image
of the Arabic cognate **أَبٌ** ("father").

The file `placeholders.csv` maps each placeholder number to:
- the guessed source language (Arabic, Syriac, Ethiopic, etc.)
- the BDB entry it belongs to
- a snippet of surrounding HTML context

### Translation treatment

Placeholder tags are **not translatable content**. They are opaque references
to script images. During translation:

- **HTML**: Copy every `<placeholder* />` tag verbatim in its exact position.
  Do not remove, renumber, or alter them. They are part of the scholarly
  apparatus, not English text.
- **JSON**: Placeholder tags do not appear in the JSON files (the JSON
  extraction stripped them out), so they are only relevant to HTML translation.
- **Surrounding English text**: The English words around a placeholder (e.g.
  "Arabic `<placeholder7 />`, Assyrian ...") should be translated to French
  ("arabe `<placeholder7 />`, assyrien ...") but the tag itself stays as-is.

## Skeletal Entries (Zero-Byte Files)

872 entries (~8.7%) have no translatable content at all: `pos`, `primary`, and
`description` are all `null` and `senses` is `[]`. The only non-null field is
`head_word`. These are typically redirect stubs or root placeholders that exist
in the dictionary structure but carry no definition.

These have been pre-handled by creating **zero-byte files** in `json_output.fr/`
so that `untranslated.py` skips them. To find them later:

```bash
find json_output.fr/ -empty -name '*.json'   # list all zero-byte placeholders
find json_output.fr/ -empty | wc -l          # count them (expect 872)
```

Do **not** write content into these files. If a skeletal entry later gains
content in the English source, delete the zero-byte file and translate normally.

## Language Names

BDB descriptions frequently mention cognate languages. These should be
translated consistently:

```
English              French
-------              -------
Arabic               arabe
Assyrian             assyrien
Biblical Aramaic     arameen biblique
Biblical Hebrew      hebreu biblique
Ethiopic             ethiopien
Late Hebrew          hebreu tardif
Mandean              mandeen
Nabataean            nabataeen
New Hebrew           neo-hebreu
Old Aramaic          ancien arameen
Palmyrene            palmyreenien
Phoenician           phenicien
Sabean / Sabaean     sabeen
Syriac               syriaque
Targum               targoum
```

The `<language>` tag in HTML entries has only two values: "Biblical Hebrew" and
"Biblical Aramaic". Translate these to "hebreu biblique" and "arameen biblique".

## Cross-References

~400 entries contain cross-references in `description` like "see בחון above" or
"compare גִּלְגָּל". Translate the structural English but preserve the Hebrew
word and any BDB entry references:

```
English pattern              French pattern
---------------              --------------
see X above                  voir X ci-dessus
see X below                  voir X ci-dessous
see X                        voir X
compare X                    comparer X
which see                    q.v.
```

## Grammatical Stem Names

Hebrew verb stems appear throughout BDB. These are conventional transliterations
used in French biblical scholarship as well -- keep them unchanged:

- Qal, Niph'al (Niphal), Pi'el (Piel), Pu'al (Pual)
- Hiph'il (Hiphil), Hoph'al (Hophal), Hithpa'el (Hithpael)

The surrounding English labels should be translated:
- "Qal Perfect" -> "Qal accompli"
- "Hiph'il Imperfect" -> "Hiphil inaccompli"
- "Niph'al Participle" -> "Niphal participe"
- "Infinitive construct" -> "infinitif construit"
- "Infinitive absolute" -> "infinitif absolu"

## Scholarly Abbreviations

BDB uses ~337 unique abbreviation codes for authors, journals, and ancient
versions (e.g. Dl, Dr, Bev, Kau, Tg, Aq, Symm, Theod). These appear inside
`<lookup>` tags in HTML and sometimes inline in JSON descriptions. **Never
translate these.** They are standardized references to scholarly works and are
language-independent. Preserve them exactly, including any superscript notation.

## Embedded Newlines

~10% of entries contain `\n` characters inside `pos`, `primary`, or
`description` fields -- artifacts of the HTML-to-JSON extraction. When
translating:

- Strip leading/trailing whitespace and collapse runs of `\n` + spaces into a
  single space, unless the newline clearly separates distinct items.
- Exception: if a `pos` field contains an entire paragraph of usage notes
  (e.g. BDB2204), translate only the grammatical label at the start and
  preserve the rest as `description`-style content. Flag these for review.

## Overflowing `pos` Fields

A small number of entries (~2) have `pos` values that bleed into full usage
notes or definitions (hundreds of characters with embedded Hebrew, references,
and prose). For these:

- Extract and translate only the grammatical label (e.g. "adverb or
  interjection" -> "adverbe ou interjection").
- The excess content belongs semantically in `description`. In the French
  output, move it there if possible, or preserve it in `pos` with a trailing
  comment noting the irregularity.

## Quality Notes

- The original BDB text is Victorian-era English. The French should be modern,
  accessible, and precise -- not a word-for-word calque. Aim for the register
  of a contemporary French biblical studies reference work.
- French Bible reference style uses a comma between chapter and verse
  (e.g. "Dn 7,5" not "Dn 7:5"), matching the convention of the Bible de
  Jerusalem and TOB.
- The JSON schema is consistent across all 10,022 entries: every `senses`
  element has exactly `{number, primary, description}`. No nested or variant
  structures exist.
