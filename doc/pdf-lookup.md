# Looking up corrupted text in the BDB PDF

When the HTML source (`Entries/`) contains mojibake or corrupted characters,
the original BDB PDF (`BDB.pdf`) can be used as ground truth.

## Quick reference

```bash
# 1. Convert the full PDF to searchable text (one-time, ~30s)
pdftotext BDB.pdf /tmp/bdb-full.txt

# 2. Search for context around the corruption
grep -n 'as name of stone' /tmp/bdb-full.txt

# 3. Find the PDF page number (pages separated by form feeds)
python3 -c "
with open('/tmp/bdb-full.txt') as f:
    pages = f.read().split('\f')
for i, page in enumerate(pages):
    if 'YOUR SEARCH TEXT' in page:
        print(f'Page {i+1}')
        break
"

# 4. Render that page as an image for visual confirmation
pdftoppm -f 320 -l 320 -r 300 -png BDB.pdf /tmp/bdb-page

# 5. Inspect the Unicode codepoints of the corrupted vs correct text
python3 -c "
for c in 'MaÁÁeba':
    print(f'{c} U+{ord(c):04X}')
"
```

## Why this works

`pdftotext` (poppler) extracts Unicode from the PDF's embedded fonts, which
often preserves the correct codepoints even when the HTML extraction pipeline
mangled them. The BDB PDF uses proper Unicode for Semitic transliteration
characters (ṣ, ṭ, ḥ, etc.) that may have been corrupted during the original
HTML digitisation.

## Example: MaÁÁeba → Maṣṣeba

In `Entries/BDB1045.html`, the text `MaÁÁeba` appeared in the context of
Gen 28:22 (Jacob's standing stone). The `Á` (U+00C1, Latin capital A with
acute) was a corruption.

- `pdftotext` output: `Mac̦c̦eba` (c + U+0326, combining comma below)
- PDF page 320 visual: confirmed ṣ glyphs (s with dot below)
- Correct modern transliteration: **Maṣṣeba** (מַצֵּבָה, standing stone/pillar)

The BDB original (1906) used `c̦` as a transliteration for צ (tsade). The
standard modern convention is `ṣ` (U+1E63). We used the modern form.

## Tools required

- `pdftotext` (poppler-utils, `pacman -S poppler`)
- `pdftoppm` (same package, for rendering pages as images)
- Python 3 (for page-finding and codepoint inspection)

## When to use this

- Unrecognisable characters in `Entries/*.html` that look like mojibake
- Transliteration characters (Arabic, Syriac, Ethiopic) that seem wrong
- Any text where the HTML has `Á`, `Â`, `Ã`, or other accented Latin capitals
  in the middle of a Semitic transliteration — likely a corruption
