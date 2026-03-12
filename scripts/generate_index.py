#!/usr/bin/env python3
"""Generate static HTML index pages for the BDB lexicon.

Outputs:
    index.html               – Copy of site/index_fr.html (root landing page)
    site/index_fr.html       – French index with alphabet grid
    site/index_en.html       – English index with alphabet grid
    site/index_fr_all.html   – All entries, French
    site/index_en_all.html   – All entries, English
    site/index_fr_aleph.html – French entries for Aleph
    site/index_en_aleph.html – English entries for Aleph
    ...etc for each Hebrew letter

Usage:
    python3 scripts/generate_index.py
"""

import json
import glob
import os
import html
from pathlib import Path

SITE_DIR = 'site'

# Hebrew alphabet: (letter, conventional name, latin slug for filenames)
HEBREW_ALPHABET = [
    ('א', 'Aleph',   'aleph'),
    ('ב', 'Bet',     'bet'),
    ('ג', 'Gimel',   'gimel'),
    ('ד', 'Dalet',   'dalet'),
    ('ה', 'He',      'he'),
    ('ו', 'Vav',     'vav'),
    ('ז', 'Zayin',   'zayin'),
    ('ח', 'Chet',    'chet'),
    ('ט', 'Tet',     'tet'),
    ('י', 'Yod',     'yod'),
    ('כ', 'Kaf',     'kaf'),
    ('ל', 'Lamed',   'lamed'),
    ('מ', 'Mem',     'mem'),
    ('נ', 'Nun',     'nun'),
    ('ס', 'Samekh',  'samekh'),
    ('ע', 'Ayin',    'ayin'),
    ('פ', 'Pe',      'pe'),
    ('צ', 'Tsade',   'tsade'),
    ('ק', 'Qof',     'qof'),
    ('ר', 'Resh',    'resh'),
    ('ש', 'Shin',    'shin'),
    ('ת', 'Tav',     'tav'),
]

HEBREW_LETTER_SET = {ch for ch, _, _ in HEBREW_ALPHABET}

# Localised UI strings
L10N = {
    'fr': {
        'title': 'Lexique hébreu Brown-Driver-Briggs (français)',
        'subtitle_prefix': 'Index de',
        'subtitle_entries': 'entrées',
        'all_link': 'Toutes les entrées',
        'by_letter': 'Par lettre hébraïque',
        'other_lang': 'English',
        'search_all': 'Rechercher mot, glose ou numéro BDB...',
        'search_short': 'Rechercher...',
        'label': 'Français',
        'col_word': 'Mot',
        'col_pos': 'Cat.',
        'col_gloss': 'Glose',
        'all_title': 'BDB Lexique — Français',
    },
    'en': {
        'title': 'Brown-Driver-Briggs Hebrew Lexicon (English)',
        'subtitle_prefix': 'Index of',
        'subtitle_entries': 'entries',
        'all_link': 'All entries',
        'by_letter': 'By Hebrew Letter',
        'other_lang': 'Français',
        'search_all': 'Search headword, gloss, or BDB number...',
        'search_short': 'Search...',
        'label': 'English',
        'col_word': 'Word',
        'col_pos': 'POS',
        'col_gloss': 'Gloss',
        'all_title': 'BDB Lexicon — English',
    },
}

CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
       background: #fafaf9; color: #1c1917; line-height: 1.5; }
.container { max-width: 960px; margin: 0 auto; padding: 1.5em 1em; }
h1 { font-size: 1.6em; margin-bottom: 0.3em; color: #292524; }
h2 { font-size: 1.2em; margin: 1em 0 0.5em; color: #44403c; }
.subtitle { color: #78716c; font-size: 0.95em; margin-bottom: 1.2em; }
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
.nav { margin-bottom: 1.5em; font-size: 0.9em; }
.nav a { margin-right: 0.8em; }

/* Alphabet grid */
.alpha-grid { display: flex; flex-wrap: wrap; gap: 8px; margin: 1em 0; }
.alpha-card { display: flex; flex-direction: column; align-items: center;
              padding: 10px 14px; border: 1px solid #d6d3d1; border-radius: 8px;
              background: #fff; text-decoration: none !important; color: #1c1917;
              min-width: 70px; transition: box-shadow 0.15s, border-color 0.15s; }
.alpha-card:hover { border-color: #2563eb; box-shadow: 0 2px 8px rgba(37,99,235,0.12); }
.alpha-letter { font-size: 1.8em; direction: rtl; unicode-bidi: isolate; }
.alpha-name { font-size: 0.75em; color: #78716c; }
.alpha-count { font-size: 0.7em; color: #a8a29e; margin-top: 2px; }

/* Search */
.search-box { width: 100%; padding: 8px 12px; font-size: 1em; border: 1px solid #d6d3d1;
              border-radius: 6px; margin-bottom: 1em; }
.search-box:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }

/* Entry table */
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #d6d3d1;
     font-size: 0.8em; color: #78716c; text-transform: uppercase; letter-spacing: 0.05em;
     position: sticky; top: 0; background: #fafaf9; z-index: 1; }
td { padding: 5px 8px; border-bottom: 1px solid #e7e5e4; vertical-align: top; }
tr:hover { background: #f5f5f4; }
.hw { font-size: 1.15em; direction: rtl; unicode-bidi: isolate; }
.pos { color: #78716c; font-size: 0.85em; font-style: italic; }
.gloss { color: #292524; }
.bdb-id { color: #a8a29e; font-size: 0.8em; }
.count-info { color: #78716c; font-size: 0.9em; margin-bottom: 1em; }
"""

SEARCH_JS = """\
<script>
document.addEventListener('DOMContentLoaded', function() {
    var input = document.getElementById('search');
    if (!input) return;
    var rows = document.querySelectorAll('tbody tr');
    input.addEventListener('input', function() {
        var q = this.value.toLowerCase();
        rows.forEach(function(r) {
            r.style.display = r.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
        });
    });
});
</script>
"""


def load_entries():
    """Load all JSON entries, both English and French."""
    entries = []
    for fpath in sorted(glob.glob('json_output/BDB*.json')):
        bdb_id = Path(fpath).stem
        bdb_num = int(bdb_id[3:])
        try:
            with open(fpath) as f:
                en = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        fr_path = f'json_output_fr/{bdb_id}.json'
        fr = None
        if os.path.exists(fr_path) and os.path.getsize(fr_path) > 0:
            try:
                with open(fr_path) as f:
                    fr = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        head_word = en.get('head_word') or ''
        first_letter = head_word[0] if head_word else ''

        entries.append({
            'id': bdb_id,
            'num': bdb_num,
            'head_word': head_word,
            'first_letter': first_letter,
            'en_pos': en.get('pos') or '',
            'en_primary': en.get('primary') or '',
            'en_desc': en.get('description') or '',
            'fr_pos': (fr.get('pos') or '') if fr else '',
            'fr_primary': (fr.get('primary') or '') if fr else '',
            'fr_desc': (fr.get('description') or '') if fr else '',
        })
    return entries


def entry_gloss(entry, lang):
    """Short gloss for display: primary if available, else truncated description."""
    primary = entry[f'{lang}_primary']
    if primary:
        return primary if len(primary) <= 80 else primary[:77] + '...'
    desc = entry[f'{lang}_desc']
    if desc:
        return desc if len(desc) <= 80 else desc[:77] + '...'
    return ''


def html_page(title, body, extra_head='', include_search=False):
    """Wrap body in a full HTML page."""
    search = SEARCH_JS if include_search else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
{extra_head}
{search}
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>
"""


def nav_bar(lang, slug='all', from_site=True):
    """Navigation bar."""
    s = L10N[lang]
    other = 'fr' if lang == 'en' else 'en'
    prefix = '' if from_site else 'site/'
    index_href = f'{prefix}index_{lang}.html' if not from_site else f'index_{lang}.html'
    other_suffix = f'_{slug}' if slug != 'index' else ''
    other_href = f'index_{other}{other_suffix}.html'
    if not from_site:
        other_href = f'site/{other_href}'
    all_href = f'index_{lang}_all.html'
    if not from_site:
        all_href = f'site/{all_href}'
    parts = [
        '<div class="nav">',
        f'<a href="{index_href}">Index</a>',
        f' | <a href="{all_href}">{s["all_link"]}</a>',
        f' | <a href="{other_href}">{s["other_lang"]}</a>',
        '</div>',
    ]
    return ''.join(parts)


def entry_link(bdb_id, lang, from_site=True):
    """Return the href for an entry."""
    prefix = '../' if from_site else ''
    has_fr = os.path.exists(f"Entries_fr/{bdb_id}.html")
    has_en = os.path.exists(f"Entries/{bdb_id}.html")
    if lang == 'fr' and has_fr:
        return f'{prefix}Entries_fr/{bdb_id}.html'
    elif has_en:
        return f'{prefix}Entries/{bdb_id}.html'
    return '#'


def entry_table(entries, lang, from_site=True):
    """Build an HTML table of entries."""
    s = L10N[lang]
    rows = []
    for e in entries:
        gloss = html.escape(entry_gloss(e, lang))
        pos = html.escape(e[f'{lang}_pos'])
        hw = html.escape(e['head_word'])
        bdb = e['id']
        link = entry_link(bdb, lang, from_site)
        rows.append(
            f'<tr>'
            f'<td><a href="{link}"><span class="hw">{hw}</span></a></td>'
            f'<td class="bdb-id">{bdb}</td>'
            f'<td class="pos">{pos}</td>'
            f'<td class="gloss">{gloss}</td>'
            f'</tr>'
        )
    return (
        f'<table><thead><tr>'
        f'<th>{s["col_word"]}</th><th>ID</th>'
        f'<th>{s["col_pos"]}</th><th>{s["col_gloss"]}</th>'
        f'</tr></thead><tbody>\n'
        + '\n'.join(rows)
        + '\n</tbody></table>'
    )


def generate_all_page(entries, lang):
    """Single page with all entries + search box."""
    s = L10N[lang]
    body = (
        nav_bar(lang, 'all')
        + f'<h1>{s["all_title"]}</h1>'
        + f'<p class="count-info">{len(entries):,} {s["subtitle_entries"]}</p>'
        + f'<input type="text" id="search" class="search-box" '
        + f'placeholder="{s["search_all"]}">'
        + entry_table(entries, lang)
    )
    return html_page(s['all_title'], body, include_search=True)


def generate_letter_page(entries, letter, letter_name, slug, lang):
    """Page for a single Hebrew letter."""
    s = L10N[lang]
    title = f'{letter_name} ({letter}) — BDB {s["label"]}'
    body = (
        nav_bar(lang, slug)
        + f'<h1><span class="hw" style="font-size:1.4em">{letter}</span> '
        + f'{letter_name} — {s["label"]}</h1>'
        + f'<p class="count-info">{len(entries):,} {s["subtitle_entries"]}</p>'
        + f'<input type="text" id="search" class="search-box" '
        + f'placeholder="{s["search_short"]}">'
        + entry_table(entries, lang)
    )
    return html_page(title, body, include_search=True)


def generate_index_page(entries, lang, letter_counts, from_site=True):
    """Index page with alphabet grid. Used for both site/ and root."""
    s = L10N[lang]
    other = 'fr' if lang == 'en' else 'en'
    prefix = '' if from_site else 'site/'

    cards = []
    for letter, name, slug in HEBREW_ALPHABET:
        count = letter_counts.get(letter, 0)
        if count == 0:
            continue
        cards.append(
            f'<a class="alpha-card" href="{prefix}index_{lang}_{slug}.html">'
            f'<span class="alpha-letter">{letter}</span>'
            f'<span class="alpha-name">{name}</span>'
            f'<span class="alpha-count">{count:,}</span>'
            f'</a>'
        )

    other_index = f'{prefix}index_{other}.html'
    all_href = f'{prefix}index_{lang}_all.html'

    body = f"""\
<h1>{s['title']}</h1>
<p class="subtitle">{s['subtitle_prefix']} {len(entries):,} {s['subtitle_entries']} &mdash;
    <a href="{all_href}">{s['all_link']}</a> |
    <a href="{other_index}">{s['other_lang']}</a>
</p>

<h2>{s['by_letter']}</h2>
<div class="alpha-grid">
{''.join(cards)}
</div>
"""
    return html_page(s['title'], body)


def main():
    print('Loading entries...')
    entries = load_entries()
    print(f'Loaded {len(entries)} entries.')

    os.makedirs(SITE_DIR, exist_ok=True)

    by_letter = {}
    for e in entries:
        ch = e['first_letter']
        by_letter.setdefault(ch, []).append(e)

    letter_counts = {ch: len(lst) for ch, lst in by_letter.items()}

    # site/index_fr.html and site/index_en.html
    for lang in ('fr', 'en'):
        fname = f'{SITE_DIR}/index_{lang}.html'
        print(f'Writing {fname}')
        with open(fname, 'w') as f:
            f.write(generate_index_page(entries, lang, letter_counts,
                                        from_site=True))

    # index.html in project root — same content as site/index_fr.html
    # but with links prefixed by site/
    print('Writing index.html')
    with open('index.html', 'w') as f:
        f.write(generate_index_page(entries, 'fr', letter_counts,
                                    from_site=False))

    # All-entries pages
    for lang in ('fr', 'en'):
        fname = f'{SITE_DIR}/index_{lang}_all.html'
        print(f'Writing {fname}')
        with open(fname, 'w') as f:
            f.write(generate_all_page(entries, lang))

    # Per-letter pages
    for letter, name, slug in HEBREW_ALPHABET:
        letter_entries = by_letter.get(letter, [])
        if not letter_entries:
            continue
        for lang in ('fr', 'en'):
            fname = f'{SITE_DIR}/index_{lang}_{slug}.html'
            print(f'Writing {fname} ({len(letter_entries)} entries)')
            with open(fname, 'w') as f:
                f.write(generate_letter_page(
                    letter_entries, letter, name, slug, lang
                ))

    # Entries with non-standard first chars
    misc = [e for e in entries if e['first_letter'] not in HEBREW_LETTER_SET]
    if misc:
        for lang in ('fr', 'en'):
            fname = f'{SITE_DIR}/index_{lang}_misc.html'
            print(f'Writing {fname} ({len(misc)} entries)')
            with open(fname, 'w') as f:
                f.write(generate_letter_page(
                    misc, '?', 'Other', 'misc', lang
                ))

    # 1 root index + 2 site indexes + 2 all + per-letter + misc
    total_files = 1 + 2 + 2 + sum(
        2 for l, _, _ in HEBREW_ALPHABET if l in by_letter
    ) + (2 if misc else 0)
    print(f'Done. Generated {total_files} HTML files.')


if __name__ == '__main__':
    main()
