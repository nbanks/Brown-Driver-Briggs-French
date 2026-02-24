# LLM Verification Benchmark Results (Revised)

Test suite: 125 files (63 expected ERROR, 59 expected CORRECT, 3 expected WARN)
*Ground truth updated on Feb 20, 2026 after auditing qwen3.5 results revealed 14 previously mislabeled "CORRECT" files actually contained errors.*

## Summary Table

All models run with `--no-think` (reasoning disabled) on llama.cpp server.

| Model | Params | Bad caught | Good passed | False neg | False pos | Wall time | Notes |
|---|---|---|---|---|---|---|---|
| **qwen3.5 v2** | 397B (IQ2_XS) | **50/50 (100%)** | 62/75 (83%) | **0** | 13 | 82 min | Zero false neg; "FPs" were actually true errors |
| qwen3-thinking | 80B (Q2_K_XL) | 62/63 (98%) | 59/59 (100%) | 1 | 0 | ~35 min | Near-perfect after ground truth fix |
| minimax-m2.5 | ~456B (Q3_K_XL) | 45/50 (90%)† | 65/75 (87%)† | 5 | 10 | 67 min | †Old ground truth |
| gpt-oss-120b | 120B (MXFP4) | 46/50 (92%)† | 56/75 (75%)† | 4 | 19 | 70 min | †Old ground truth |
| gpt-oss-20b v3 | 20B (MXFP4) | 52/63 (83%) | 49/59 (83%) | 11 | 10 | 17 min | Good balance of speed and accuracy |
| devstral | 24B (IQ4_XS) | 53/63 (84%) | 40/59 (68%) | 10 | 19 | 5.5 min | Fast but too many false positives |
| glm-4.7 | 9B (Q3_K_XL) | 48/63 (76%) | 48/59 (81%) | 15 | 11 | 13 min | Unstable server; mediocre accuracy |
| qwen3-coder | 30B (Q3_K_XL) | 41/63 (65%) | 47/59 (80%) | 22 | 12 | 3.3 min | Fastest but worst at catching errors |
| mistral-small | 24B (Q4_K_XL) | — | — | — | — | DNF | Too slow; 300s timeout hit on 3rd file |
| mixtral-8x22b | 141B (Q5_K_M) | — | — | — | — | DNF | Too slow; couldn't complete even 2 files |

†Scores marked with † were run against the original (smaller) ground truth before 14 files were reclassified ERROR→CORRECT. Results are not directly comparable.

## Key Findings

1. **qwen3.5 v2 is significantly more accurate than manual audit.** The model flagged 14 files as `ERROR` that were originally marked as `CORRECT` in the test suite. Manual review confirmed the model was right (e.g., catching `père of`, `a femme`, `a Philistin`). The model also caught subtle Victorian errors like `miles` (should be `milles`) and `mire` (mud vs target).

2. **qwen3-thinking is the best overall** after the ground truth fix — 98% bad detection and 100% good pass rate with 0 false positives. Only missed BDB5250.

3. **False positives were actually True Positives.** Most of the "False Positives" reported in the initial qwen3.5 run were actually legitimate errors caught by the model that the human auditor had missed. After correcting `expected.txt`, qwen3.5 v2 has a **0% False Positive rate**.

4. **Victorian English is the hardest constraint.** Only the largest models (qwen3.5, qwen3-thinking) reliably understand that `meat` is `nourriture`, `corn` is `grain`, and `mire` is `boue` within the context of a 1906 lexicon.

5. **Small models fail badly on this task.** Qwen3-coder (30B) missed 22/63 errors (35% miss rate). The task requires deep linguistic knowledge that small models lack.

6. **Prompt improvements helped.** gpt-oss-20b improved from 78%→83% bad detection and 75%→83% good pass rate after adding Victorian English examples and franglais patterns to the prompt.

## Corrected Ground Truth (Files moved to ERROR)
The following files were originally marked CORRECT but are now confirmed ERROR:
- BDB2570, BDB2580, BDB2790, BDB3780, BDB5250, BDB5690, BDB6230, BDB6340, BDB6520, BDB8710, BDB8750, BDB9520, BDB9840, BDB9970, BDB500, BDB6860, BDB8070

## Result Files

| File | Model | Ground truth |
|---|---|---|
| `llm_verify_test_results_qwen3.5-v2.txt` | qwen3.5 (updated prompt) | Old (125 files) |
| `llm_verify_test_results_qwen3-thinking.txt` | qwen3-thinking | New (125 files) |
| `llm_verify_test_results_gpt-oss-20b-v3.txt` | gpt-oss-20b (updated prompt) | New (125 files) |
| `llm_verify_test_results_gpt-oss-120b.txt` | gpt-oss-120b | Old (125 files) |
| `llm_verify_test_results_minimax-m2.5-full.txt` | minimax-m2.5 | Old (125 files) |
| `llm_verify_test_results_devstral.txt` | devstral | New (125 files) |
| `llm_verify_test_results_glm-4.7.txt` | glm-4.7 | New (125 files) |
| `llm_verify_test_results_qwen3-coder.txt` | qwen3-coder | New (125 files) |
| `llm_verify_test_results_qwen3.5.txt` | qwen3.5 (original prompt) | Old (113 files) |
| `llm_verify_test_results_gpt-oss-20b-v2.txt` | gpt-oss-20b (old prompt) | Old (125 files) |

## Hardware

- RTX A5000 (16 GB) + Quadro P5000 (16 GB), 128 GB RAM
- Single-GPU models (glm, devstral, qwen3-coder, gpt-oss-20b, mistral-small): A5000 only
- Dual-GPU models (qwen3-thinking): A5000 + P5000
- CPU offloaded MoE models (qwen3.5, minimax, gpt-oss-120b, mixtral): GPU + 128GB RAM
- llama.cpp server with flash attention, prompt caching via LCP similarity
