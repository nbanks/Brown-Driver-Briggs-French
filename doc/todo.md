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

## Notes

- The llama.cpp server must be running before any verification steps
- If the machine is turned off, resume from wherever you left off — the scripts
  are idempotent (results append, duplicates resolved by newest-wins)
- Only check `--mode txt` for now — html and json verification will come later
  once those translation steps are further along
- Previous test results are saved in `test/llm_verify_test_results_*.txt` for
  comparison across models and prompt versions
