#!/usr/bin/env python3
"""Detect franglais (mixed English/French) in translated BDB files.

Works on both Entries_txt_fr/ (.txt) and json_output_fr/ (.json) directories.
For JSON files, only examines translatable fields (pos, primary, description,
senses[].primary, senses[].description) — ignores head_word, number, keys, etc.

Two detection methods:
  1. Dictionary check: flags ASCII words found in English aspell but not French
  2. Source bigram comparison: flags 2-word phrases copied verbatim from the
     English source file, if at least one word is English-only

Usage:
    python3 scripts/detect_franglais.py                        # scan Entries_txt_fr/
    python3 scripts/detect_franglais.py --dir json_output_fr   # scan JSON files
    python3 scripts/detect_franglais.py --count                # summary only
    python3 scripts/detect_franglais.py --words                # show English words found
    python3 scripts/detect_franglais.py -n 20                  # top 20 worst files
    python3 scripts/detect_franglais.py --threshold 5          # files with ≥5 English words
    python3 scripts/detect_franglais.py 3 7                    # only entries ending in 3 or 7
"""

import argparse
import json
import os
import re
import subprocess
import sys


def load_aspell_dict(lang):
    """Dump aspell dictionary as a set of lowercase words."""
    result = subprocess.run(
        ["aspell", "-d", lang, "dump", "master"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error: aspell -d {lang} dump master failed. "
              f"Is aspell-{lang} installed?", file=sys.stderr)
        sys.exit(2)
    words = set()
    for line in result.stdout.splitlines():
        w = line.strip().lower()
        if w:
            words.add(w)
    return words


# Scholarly abbreviations that appear in BDB and should never be flagged.
# These are author codes, manuscript sigla, and technical shorthand that
# are language-independent. Kept minimal to avoid masking real problems.
IGNORE_WORDS = {
    # Scholar/author abbreviations (from <lookup> tags in BDB)
    'mt', 'lxx', 'aq', 'symm', 'theod', 'tg', 'dl', 'dr', 'ges', 'bev',
    'kau', 'cot', 'ke', 'bu', 'gr', 'hi', 'di', 'ew', 'th', 'ol', 'de',
    'ko', 'sta', 'nes', 'vb', 'rss', 'lag', 'fl', 'mv',
    'che', 'gfm', 'rob', 'sm', 'kit', 'duhm', 'marti', 'now', 'we',
    'gie', 'benz', 'perles', 'hpt', 'id', 'cf', 'al',
    'co', 'be', 'str', 'stb', 'ba', 'bdb', 'gi', 'kb',
    'weid', 'nö', 'jäg',
    # Scholar names that are also English words
    'lane', 'toy', 'cooke', 'frey', 'hal', 'levy', 'caleb',
    'dozy', 'brock', 'cook',
    # Publication/reference abbreviations
    'pap', 'rel',
    # Latin scholarly phrases
    'vera', 'lectio', 'sub', 'comm',
    # Publication abbreviations
    'cis', 'bib', 'eur', 'survey',
    # Technical scholarly terms (used untranslated in French biblical studies)
    'gloss',
    # Aramaic verb stem (like Qal)
    'peal',
    # Hebrew verb stems (kept as-is per project rules)
    'qal', 'niphal', 'piel', 'pual', 'hiphil', 'hophal', 'hithpael',
    "niph'al", "pi'el", "pu'al", "hiph'il", "hoph'al", "hithpa'el",
    # Roman numerals
    'ii', 'iii', 'iv', 'vi', 'vii', 'viii', 'ix', 'xi', 'xii',
    'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx',
    # Technical notation
    'sq', 'sqq', 'abs', 'sg', 'pl', 'fs', 'ms', 'sf', 'ff',
    # French biblical abbreviations (so they don't flag if in English dict)
    'gn', 'lv', 'nb', 'dt', 'jos', 'jg', 'rt', 'ch', 'esd',
    'ne', 'est', 'jb', 'ps', 'pr', 'qo', 'ct', 'es', 'jr', 'lm',
    'ez', 'dn', 'os', 'jl', 'am', 'ab', 'jon', 'mi', 'na', 'ha',
    'so', 'ag', 'za', 'ml', 'ex',
}

# Add single letters
for c in 'abcdefghijklmnopqrstuvwxyz':
    IGNORE_WORDS.add(c)

# English function words that should NEVER appear in French text.
# These are English-only (not in French dict) and too short or ambiguous
# for the dictionary check alone. Used by bigram detection.
ENGLISH_FUNCTION_WORDS = {
    'of', 'the', 'and', 'in', 'to', 'for', 'with', 'from', 'by', 'at',
    'on', 'or', 'as', 'is', 'was', 'are', 'were', 'been', 'an', 'be',
    'that', 'this', 'which', 'who', 'whom', 'whose', 'what', 'where',
    'when', 'how', 'not', 'but', 'if', 'then', 'than', 'its',
    'his', 'her', 'their', 'our', 'your', 'my', 'he', 'she', 'it',
    'they', 'we', 'you', 'him', 'them', 'us', 'me',
    'has', 'had', 'have', 'do', 'does', 'did', 'will', 'would', 'shall',
    'should', 'may', 'might', 'can', 'could', 'must',
}

# Regex: match ASCII-only words (letters, hyphens, apostrophes).
# This naturally skips Hebrew, Greek, and accented French words.
ASCII_WORD_RE = re.compile(r"\b([a-zA-Z][a-zA-Z'-]*[a-zA-Z]|[a-zA-Z])\b")

# English ordinals: 1st, 2nd, 3rd, 4th, 5th, etc.
ENGLISH_ORDINAL_RE = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.IGNORECASE)


def tokenize(text):
    """Extract ASCII-only word tokens from text."""
    tokens = []
    for line in text.splitlines():
        if '[placeholder' in line:
            continue
        for match in ASCII_WORD_RE.finditer(line):
            tokens.append(match.group())
    return tokens


def make_bigrams(tokens):
    """Create set of lowercase bigrams from token list."""
    bigrams = set()
    lowers = [t.lower() for t in tokens]
    for i in range(len(lowers) - 1):
        bigrams.add((lowers[i], lowers[i + 1]))
    return bigrams


def extract_translatable_text_json(filepath):
    """Extract only the translatable field values from a JSON entry."""
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return ""

    parts = []
    for field in ('pos', 'primary', 'description'):
        val = data.get(field)
        if isinstance(val, str):
            parts.append(val)

    for sense in data.get('senses', []) or []:
        if not isinstance(sense, dict):
            continue
        for field in ('primary', 'description'):
            val = sense.get(field)
            if isinstance(val, str):
                parts.append(val)

    return '\n'.join(parts)


def extract_translatable_text_txt(filepath):
    """Read the full text content of a .txt file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def get_source_dir(scan_dir, file_ext):
    """Determine the English source directory for bigram comparison."""
    project_root = os.path.dirname(scan_dir)
    basename = os.path.basename(scan_dir)

    if file_ext == '.json':
        # json_output_fr -> json_output
        source = os.path.join(project_root, 'json_output')
    else:
        # Entries_txt_fr -> Entries_txt
        source = os.path.join(project_root, 'Entries_txt')

    if os.path.isdir(source):
        return source
    return None


def load_source_text(source_dir, fname, file_ext):
    """Load the English source text for a given translated file."""
    source_path = os.path.join(source_dir, fname)
    if not os.path.isfile(source_path):
        return ""
    if file_ext == '.json':
        return extract_translatable_text_json(source_path)
    else:
        return extract_translatable_text_txt(source_path)


def analyze_file(filepath, english_words, french_words,
                 source_dir=None, file_ext='.txt'):
    """Analyze a single file for English-only words and copied bigrams.

    Returns (english_only_words, total_checked_words) where english_only_words
    is a list of (word, count) tuples.
    """
    if filepath.endswith('.json'):
        text = extract_translatable_text_json(filepath)
    else:
        text = extract_translatable_text_txt(filepath)

    tokens = tokenize(text)
    if not tokens:
        return [], 0

    # --- Method 1: Dictionary check ---
    english_hits = {}
    total_checked = 0
    _unknown_words = set()  # words in neither dict, checked against source later

    # Method 0: English ordinals (1st, 2nd, 3rd, 4th, etc.)
    # In French these should be 1er, 2e, 3e, 4e, etc.
    for match in ENGLISH_ORDINAL_RE.finditer(text):
        ordinal = match.group().lower()
        english_hits[ordinal] = english_hits.get(ordinal, 0) + 1

    for original in tokens:
        lower = original.lower()

        # Skip single characters
        if len(lower) <= 1:
            continue

        # Skip ignored words
        if lower in IGNORE_WORDS:
            continue

        # For 2-char words: only check known English function words to
        # avoid false positives from abbreviation fragments (qr, kt, etc.)
        if len(lower) == 2 and lower not in ENGLISH_FUNCTION_WORDS:
            continue

        total_checked += 1

        # Is it in the French dictionary? (exact match, no accent stripping)
        if lower in french_words:
            continue

        # Is it in the English dictionary?
        if lower in english_words:
            english_hits[lower] = english_hits.get(lower, 0) + 1
        # Also flag words in NEITHER dictionary if they appear in the
        # English source — likely copied verbatim or garbled during
        # translation (e.g., "sousstanding", "follwing", "asumed")
        elif len(lower) >= 7 and lower not in french_words:
            _unknown_words.add(lower)

    # --- Method 2: English function word patterns ---
    # Catch English function words that are also valid French words (in, as,
    # and, or, on, an, a) by looking at context.
    #
    # Re-tokenize including accented words for context checking, since
    # "in Édom" needs to see "Édom" as the next word.
    ALL_WORD_RE = re.compile(
        r"\b([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ'-]*[a-zA-ZÀ-ÿ]|[a-zA-ZÀ-ÿ])\b")
    all_tokens = []
    for line in text.splitlines():
        if '[placeholder' in line:
            continue
        for match in ALL_WORD_RE.finditer(line):
            all_tokens.append(match.group())

    AMBIGUOUS_EN = {'in', 'as', 'and', 'or', 'a', 'an', 'on'}
    for i, original in enumerate(all_tokens):
        lower = original.lower()
        if lower not in AMBIGUOUS_EN:
            continue
        next_word = all_tokens[i + 1] if i + 1 < len(all_tokens) else None
        prev_word = all_tokens[i - 1] if i > 0 else None
        if not next_word:
            continue
        nw_lower = next_word.lower()

        # "in" + capitalized word (proper noun) = English preposition
        # e.g., "in Juda", "in Édom", "in Nephthali"
        if (lower == 'in' and next_word[0].isupper() and i > 3
                and nw_lower not in IGNORE_WORDS):
            english_hits['in'] = english_hits.get('in', 0) + 1

        # "a" as English article — deferred to bigram check (Method 3)
        # where we verify "a X" appears in the English source too

        # "and" + word ≥ 3 chars = English conjunction
        # e.g., "and grandson", "and dérivés"
        elif (lower == 'and' and len(nw_lower) >= 3
              and nw_lower not in IGNORE_WORDS):
            english_hits['and'] = english_hits.get('and', 0) + 1

        # "as" before a French word in non-French syntax
        # e.g., "as nom collectif"
        elif (lower == 'as' and len(nw_lower) >= 3
              and nw_lower in french_words
              and prev_word and prev_word.lower() not in french_words):
            english_hits['as'] = english_hits.get('as', 0) + 1

    # --- Method 3: Source bigram comparison ---
    # Find bigrams in the translation that also exist in the English source.
    # A bigram flags if it contains an English function word (of, in, as, and,
    # etc.) paired with a word of ≥ 3 chars. This catches phrases like
    # "of Gomer", "and grandson", "as nom", "in Juda" copied from the source.
    if source_dir:
        fname = os.path.basename(filepath)
        source_text = load_source_text(source_dir, fname, file_ext)
        if source_text:
            source_tokens = tokenize(source_text)
            source_bigrams = make_bigrams(source_tokens)
            trans_tokens_lower = [t.lower() for t in tokens]

            for i in range(len(trans_tokens_lower) - 1):
                w1 = trans_tokens_lower[i]
                w2 = trans_tokens_lower[i + 1]
                bigram = (w1, w2)

                if bigram not in source_bigrams:
                    continue

                # Skip if both words are in the ignore list
                if w1 in IGNORE_WORDS and w2 in IGNORE_WORDS:
                    continue

                # Require: one word is an English function word (and NOT in
                # ignore list), the other is ≥ 3 chars.
                # Also check "a" as English article (not in
                # ENGLISH_FUNCTION_WORDS to avoid false positives in
                # the context check, but valid here since we confirmed
                # the bigram exists in the English source).
                func_word = None
                en_func = ENGLISH_FUNCTION_WORDS | {'a'}
                if (w1 in en_func and w1 not in IGNORE_WORDS
                        and len(w2) >= 3):
                    func_word = w1
                elif (w2 in en_func and w2 not in IGNORE_WORDS
                      and len(w1) >= 3):
                    func_word = w2

                if func_word:
                    english_hits[func_word] = \
                        english_hits.get(func_word, 0) + 1

            # Method 4: Unknown words that appear in the source
            # Words in neither dictionary that also exist in the English
            # source are likely copied verbatim or garbled translations.
            if _unknown_words:
                source_words = {t.lower() for t in source_tokens}
                for uw in _unknown_words:
                    if uw in source_words:
                        english_hits[uw] = english_hits.get(uw, 0) + 1

    # Sort by frequency
    sorted_hits = sorted(english_hits.items(), key=lambda x: -x[1])
    return sorted_hits, total_checked


def main():
    parser = argparse.ArgumentParser(
        description='Detect franglais in translated BDB files (.txt or .json).'
    )
    parser.add_argument('digits', nargs='*', type=int, choices=range(10),
                        metavar='DIGIT',
                        help='Filter by last digit of BDB number (0-9)')
    parser.add_argument('-n', '--top', type=int, default=0,
                        help='Show only top N worst files (0=all)')
    parser.add_argument('--threshold', type=int, default=1,
                        help='Min English-only words to flag (default: 1)')
    parser.add_argument('--count', action='store_true',
                        help='Show summary counts only')
    parser.add_argument('--words', action='store_true',
                        help='Show English words found in each file')
    parser.add_argument('--dir', default='Entries_txt_fr',
                        help='Directory to scan (default: Entries_txt_fr)')
    args = parser.parse_args()

    # Find project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    scan_dir = os.path.join(project_root, args.dir)

    if not os.path.isdir(scan_dir):
        print(f"Error: directory not found: {scan_dir}", file=sys.stderr)
        sys.exit(2)

    digits = set(args.digits) if args.digits else None

    # Auto-detect file type from directory contents
    sample = os.listdir(scan_dir)[:10]
    if any(f.endswith('.json') for f in sample):
        file_ext = '.json'
    else:
        file_ext = '.txt'

    print("Loading dictionaries...", file=sys.stderr)
    english_words = load_aspell_dict('en')
    french_words = load_aspell_dict('fr')
    print(f"  English: {len(english_words):,} words", file=sys.stderr)
    print(f"  French:  {len(french_words):,} words", file=sys.stderr)

    # Find source directory for bigram comparison
    source_dir = get_source_dir(scan_dir, file_ext)
    if source_dir:
        print(f"  Source:  {source_dir}", file=sys.stderr)
    else:
        print("  Source:  (not found, bigram check disabled)", file=sys.stderr)

    # Collect files
    files = sorted(f for f in os.listdir(scan_dir)
                   if f.endswith(file_ext) and f.startswith('BDB'))

    if digits is not None:
        def last_digit(fname):
            num = re.search(r'(\d+)', fname)
            return int(num.group(1)) % 10 if num else -1
        files = [f for f in files if last_digit(f) in digits]

    print(f"Scanning {len(files)} {file_ext} files...", file=sys.stderr)

    # Analyze
    results = []
    total_files_flagged = 0
    total_english_words = 0
    all_english_words = {}

    for fname in files:
        fpath = os.path.join(scan_dir, fname)
        if os.path.getsize(fpath) == 0:
            continue
        hits, total_checked = analyze_file(
            fpath, english_words, french_words,
            source_dir=source_dir, file_ext=file_ext)
        if not hits:
            continue
        eng_count = sum(c for _, c in hits)
        if eng_count >= args.threshold:
            results.append((fname, eng_count, total_checked, hits))
            total_files_flagged += 1
            total_english_words += eng_count
            for word, count in hits:
                all_english_words[word] = all_english_words.get(word, 0) + count

    # Sort by English word count descending
    results.sort(key=lambda x: -x[1])

    if args.top > 0:
        results = results[:args.top]

    # Output
    if args.count:
        print(f"\nFiles scanned:  {len(files)}")
        print(f"Files flagged:  {total_files_flagged}")
        print(f"Total English-only words found: {total_english_words}")
        if all_english_words:
            top_words = sorted(all_english_words.items(),
                               key=lambda x: -x[1])[:30]
            print(f"\nTop 30 most common English-only words:")
            for word, count in top_words:
                print(f"  {count:5d}  {word}")
    else:
        print(f"\n{'File':<25} {'Eng words':>10} {'Checked':>10} {'Ratio':>8}")
        print("-" * 55)
        for fname, eng_count, total_checked, hits in results:
            ratio = eng_count / total_checked if total_checked > 0 else 0
            print(f"{fname:<25} {eng_count:>10} {total_checked:>10}"
                  f" {ratio:>7.1%}")
            if args.words:
                sample = hits[:20]
                words_str = ', '.join(f"{w}({c})" for w, c in sample)
                if len(hits) > 20:
                    words_str += f", ... +{len(hits)-20} more"
                print(f"  → {words_str}")

        print("-" * 55)
        print(f"Total: {total_files_flagged} files flagged, "
              f"{total_english_words} English-only words")

    return 1 if total_files_flagged > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
