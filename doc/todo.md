# TODO — llm_verify test suite and txt verification

## Context

We updated `scripts/llm_verify_txt.md` (the verification prompt) and `AGENTS.md`
to improve accent detection on biblical proper names (Ésaü, Ézéchiel, etc.).
Changes made on 2026-02-20:

- Added "RÈGLE ABSOLUE" table of biblical names requiring accents in llm_verify_txt.md
- Moved section E (Victorian English) next to sections A–D
- Removed duplicate "Biais de détection" section
- Strengthened bias: "En cas de doute, répondez WARN ou ERROR — jamais CORRECT"
- Added Example 11 (BDB956, père d'Ezechiel → ERROR for missing accent)
- Updated AGENTS.md with Ésaü, Éphraïm, Égypte examples and errata workflow

## Step 1: Run the test suite with updated prompt ✅

- [x] Run: `python3 test/run_test.py --fresh`
- [x] Results saved as `test/llm_verify_test_results_qwen3.5-v3.txt`

## Step 2: Save and document the test results ✅

- [x] Results saved and compared against expected.txt
- [x] Key test case BDB1136.txt (Esau without accent) confirmed as ERROR

## Step 3: Run llm_verify on actual translations (txt only) ✅

- [x] Ran `python3 scripts/llm_verify.py --mode txt` on two machines:
  - Remote server (4-bit quantization, Qwen 3.5 397B) → `llm_verify_txt_results.txt` (5925 entries)
  - Local machine (2-bit quantization) → `llm_verify_txt_results-local.txt` (3810 entries)
- [x] First 3336 lines were identical (started as the same file before forking)
- [x] Merged into `llm_verify_txt_results-new.txt` (6222 entries, sorted by BDB number):
  - All entries from Q4 (remote/4-bit) as the primary source
  - 297 unique entries supplemented from Q2 (local/2-bit)
  - 177 entries verified by both → saved in `llm_verify_txt_results-dual.txt`
    with Q4/Q2 prefix for comparison
- [ ] Rename `llm_verify_txt_results-new.txt` → `llm_verify_txt_results.txt`
- [ ] Continue running llm_verify until all ~10022 entries are checked
  (~3800 remaining)

## Step 4: Analyse quantization accuracy (Q4 vs Q2) ✅

See `doc/quantization-comparison.md` for full writeup.

- [x] 87% agreement rate (154/177 entries)
- [x] All 23 disagreements manually reviewed against actual files
- [x] Q4 (mxfp_moe) correct in 70% of disagreements, Q2 (IQ2_XS) in 30%
- [x] Q2's dominant failure: too picky (flagging French words as English)
- [x] Conclusion: Q4 alone is sufficient for remaining entries; Q2 adds noise

## Step 5: Fix ERROR/WARN entries with agent team

After llm_verify is complete, use Claude Code with a team of sub-agents to
review and fix flagged entries. Split work by last digit of BDB number
(matching `untranslated.py` convention) for parallel processing.

- [ ] Write a script to extract ERROR/WARN counts per digit from
  `llm_verify_txt_results.txt`
- [ ] Spawn sub-agents (one per digit or group of digits) to review and fix
  flagged translations
- [ ] Re-run llm_verify on fixed entries to confirm corrections

## Step 6: Validate and fix Entries_fr/ HTML output

The `scripts/validate_html.py` script has been improved and tested (14 test
cases in `test/validate_html/`). Current corpus results (2,393 files):
- 1,738 clean (73%), 655 with issues (27%)
- Most common issues: missing French text, missing refs, missing Hebrew

Known false positives to fix in the validator:
- [ ] HTML entities not decoded (`&amp;` vs `et` in txt_fr)
- [ ] Subscript `_N_` notation not stripped from txt_fr comparison
- [ ] C1 control characters in some HTML files

After fixing false positives:
- [ ] Re-run validator on full corpus to get accurate error count
- [ ] Review and fix flagged Entries_fr/ files (or regenerate them)
- [ ] Generate remaining ~7,600 Entries_fr/ files

HTML assembly improvements (llm_html_assemble.py):
- [x] `extract_html`: strip trailing-only markdown fences (LLM omits opening fence)
- [x] `check_llm_errata`: recover HTML placeholder from errata responses
- [ ] Sub-split oversized HTML chunks (see below)

### Sub-splitting oversized HTML chunks

**Problem:** 79 chunks exceed 30KB of HTML. The largest is BDB2162 chunk 1 at
190KB. Hebrew text inflates token counts ~2-3x vs Latin text, so a 130KB
prompt can exceed the LLM's context window. These entries consistently FAIL
because the LLM returns no output or truncated garbage.

**Top offenders (>60KB HTML):**
```
BDB2162 chunk 1/6  190KB stem   (9 sense, 17 subsense divs inside)
BDB2145 chunk 1/3  148KB stem   (SKIP-FAILED in current run)
BDB4264 chunk 5/8  146KB sense
BDB5441 chunk 1/4  122KB stem
BDB8185 chunk 1/4   84KB stem
BDB8502 chunk 1/6   81KB stem
```

**Approach — HTML-only sub-splitting with letter suffixes (3a, 3b, 3c):**

The txt_fr chunks are tied to `@@SPLIT` markers used by llm_verify and must
not change. Sub-splitting happens only on the HTML side:

1. **In `split_entry.py`**, add a `subsplit_html(chunk, max_bytes=30000)`
   function. For any chunk exceeding `max_bytes`, find nested `div.sense` or
   `div.subsense` boundaries (using the existing `_find_div_spans` machinery)
   and split there. Return a list of sub-chunks.

2. **In `llm_html_assemble.py`**, after pairing HTML and txt_fr chunks, check
   each HTML chunk's size. If it exceeds the threshold, sub-split it. Each
   sub-chunk gets sent to the LLM with the **same full txt_fr chunk** — the
   LLM matches the relevant French text to its HTML fragment.

3. **Numbering:** sub-chunks use letter suffixes: if chunk 3 splits into 3
   pieces, they become 3a, 3b, 3c in logging/debug output. This makes it
   clear they belong to the same logical chunk.

4. **Reassembly:** concatenate sub-chunk outputs (3a + 3b + 3c) back into a
   single chunk 3 output. From that point on, validation sees the same N
   chunks it always did — the sub-splitting is invisible to `validate_html`.

```
txt_fr chunks:   [0]  [1]  [2]      [3]         [4]  [5]
html chunks:     [0]  [1]  [2]  [3a][3b][3c]    [4]  [5]
                                  ↓   ↓   ↓
                               same txt_fr #3
                                  ↓   ↓   ↓
                               concatenate → chunk 3 output
```

**Key constraint:** the nested divs in oversized chunks are always
`div.sense` or `div.subsense` (confirmed for the top 20 offenders). These
are the same div classes that `split_html` already knows how to find. The
sub-splitter just applies the same logic one level deeper within a chunk.

**What NOT to change:**
- `split_txt` — unchanged, same `@@SPLIT`-based chunks
- `validate_html` — unchanged, sees the same chunk count
- `llm_verify` — unchanged, operates on txt files only
- `extract_txt.py` — unchanged, same `@@SPLIT` markers

## Data fixes

- [x] BDB1045: `MaÁÁeba` → `Maṣṣeba` (mojibake from HTML extraction;
  confirmed against PDF page 320). Fixed in Entries/, Entries_txt/,
  Entries_txt_fr/, Entries_fr/. See `doc/pdf-lookup.md` for the technique.
- [x] BDB1045: `dans à l'intérieur de` → `à l'intérieur de` in Entries_txt_fr/
  (pléonasme from literal translation of BDB's compressed "in within").

## Notes

- The llama.cpp server must be running before any verification steps
- If the machine is turned off, resume from wherever you left off — the scripts
  are idempotent (results append, duplicates resolved by newest-wins)
- Only check `--mode txt` for now — html and json verification will come later
  once those translation steps are further along
- Previous test results are saved in `test/llm_verify_test_results_*.txt` for
  comparison across models and prompt versions
