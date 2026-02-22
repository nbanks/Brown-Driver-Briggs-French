# Qwen 3.5 397B quantization comparison: IQ2_XS vs mxfp_moe

Does the 4-bit quantization of Qwen 3.5 produce meaningfully better results
than the 2-bit quantization for verifying BDB French translations? This
document compares their accuracy on the same set of entries.

## Methodology

The `llm_verify` script checks each French translation (`Entries_txt_fr/`)
against its English original (`Entries_txt/`) and produces a verdict: CORRECT,
WARN, or ERROR. Both quantizations were run from the same starting results
file; after the runs diverged (at entry 3337), each machine continued
independently, resulting in 177 entries that happened to be verified by both.
The overlap was incidental — the remote machine processed entries in sorted
order while the local machine used a shuffled order, so the 177 duplicates
are effectively a random sample within the BDB3989–BDB6303 range.

| Label | Quantization | Hardware |
|-------|-------------|----------|
| Q4 | mxfp_moe (4-bit MoE experts) | Remote server (RTX 5090) |
| Q2 | IQ2_XS (2-bit) | Local machine |

Both used the same prompt (`scripts/llm_verify_txt.md`).

## Overall agreement

Of 177 entries verified by both:

- **154 agreements (87%)** — both models gave the same verdict
- **23 disagreements (13%)** — one said CORRECT, the other ERROR/WARN

When both models agreed, spot-checks confirmed the verdict was correct in
14 out of 15 cases (93%). The one exception was BDB4075, where both models
claimed "Manasseh" and "Shechem" were untranslated — but the French file
actually contains "Manasse" and "Sichem". Both hallucinated the file contents.

## Disagreement analysis

All 23 disagreements were manually reviewed by reading the actual English and
French translation files. Results:

| | Q4 correct | Q2 correct |
|---|---|---|
| **Count** | 16 (70%) | 7 (30%) |

**Q4 (mxfp_moe) was the more accurate quantization**, getting the right answer
in 70% of disagreements.

### Q2 failure mode: too picky (15 of 16 Q2 errors)

Q2 consistently flagged acceptable translations as errors. Its dominant
confusion was mistaking French words for untranslated English, or flagging
standard scholarly conventions as problems:

- **BDB3989**: Flagged "propose" as untranslated English — but "propose" is
  also the correct French word.
- **BDB5121**: Flagged "compassion" and "suffixe" as English — both are
  standard French.
- **BDB5208**: Flagged "alienus" and "alienavit" as untranslated — these are
  scholarly Latin citations that must be preserved per project rules.
- **BDB5548**: Flagged "si vera lectio" — standard Latin in biblical
  scholarship.
- **BDB5303**: Claimed "Eng. Tr." was untranslated, but the French file
  actually has "trad. angl." — Q2 misread its own input.
- **BDB5154**: Insisted "ville en Juda" should be "ville de Juda" — both are
  acceptable French.

### Q4 failure mode: mixed (7 errors)

Q4's errors were less uniform:

- **Too lenient (3 cases)**: Missed real problems. E.g. BDB4982 where
  "arbitrary" (Victorian English for "despotic") was rendered as "arbitraire"
  (a false friend), and BDB5710 where "Num 26:26" was not converted to
  "Nb 26,26".
- **Wrong analysis (3 cases)**: Hallucinated errors that didn't exist. E.g.
  BDB6173 where Q4 claimed "Exod" was untranslated but the file clearly has
  "Ex"; BDB4536 where Q4 flagged "Moab" as English (it's identical in French).
- **Too picky (1 case)**: BDB5367 flagged the correct abbreviation "Ps" (which
  maps to itself in French).

## Conclusions

1. **Q4 (mxfp_moe) is the better quantization for this verification task.**
   It produces fewer false positives and has better language discrimination —
   it correctly recognizes that words like "compassion", "propose", and "Moab"
   are shared between French and English.

2. **Q2 (IQ2_XS) is usable but noisy.** Its excess pickiness means ~15% of
   its ERROR verdicts on entries Q4 marks CORRECT are false alarms. This would
   generate unnecessary rework if used as the sole verifier.

3. **Agreement between both models is a strong signal.** When Q4 and Q2 agree,
   the verdict was correct 93% of the time. The main risk is shared
   hallucination of file contents (1 confirmed case out of 15 spot-checks).

4. **Neither model is fully reliable alone.** Both occasionally hallucinate
   what files contain rather than accurately reporting it. Human review remains
   necessary for ERROR entries.

5. **False negatives are the bigger risk.** A too-picky verifier generates
   extra review work, but a too-lenient one lets errors slip through
   undetected. Q4 was too lenient in 3 disagreements (missed real issues like
   the "arbitrary"/"arbitraire" false friend in BDB4982 and an unconverted
   "Num 26:26" in BDB5710). Q2 was too lenient in only 1 case (BDB4672).

6. **For the remaining ~3800 unverified entries**, Q4 is the primary verifier
   but its CORRECT verdicts should not be fully trusted — some real errors will
   slip through. If resources allow, running Q2 as a second pass and treating
   any entry flagged by either model as needing review would catch more errors
   at the cost of ~15% extra false positives to triage.
