#!/usr/bin/env python3
"""Test harness for llm_verify.py against known good/bad translations.

Runs llm_verify.py on the test/ directory, then compares actual results
against expected.txt. Reports:
  - FALSE NEGATIVES: bad files that weren't flagged (ERROR expected, got CORRECT)
  - FALSE POSITIVES: good files flagged as broken (CORRECT expected, got ERROR)
  - WARN results are shown separately (acceptable for both categories)

Usage:
  python3 test/run_test.py                    # run all 119 files
  python3 test/run_test.py --compare-only     # skip LLM, just compare existing results
  python3 test/run_test.py -n 20              # random sample of 20 files (stratified)
  python3 test/run_test.py --fresh -n 10      # clear old results first, test 10 random
"""

import argparse
import random
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parent
RESULTS_FILE = TEST_DIR / "llm_verify_test_results.txt"
EXPECTED_FILE = TEST_DIR / "expected.txt"


def load_expected() -> dict[str, str]:
    """Load expected verdicts from expected.txt."""
    expected = {}
    for line in EXPECTED_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            expected[parts[0]] = parts[1]
    return expected


def load_results() -> dict[str, str]:
    """Load actual verdicts from results file (newest wins)."""
    results = {}
    if not RESULTS_FILE.exists():
        return results
    for line in RESULTS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip().strip('"') for f in line.split(",")]
        if len(fields) >= 2:
            results[fields[0]] = fields[1]
    return results


def compare(expected: dict[str, str], actual: dict[str, str]):
    """Compare and report."""
    false_negatives = []  # bad files missed (expected ERROR, got CORRECT)
    false_positives = []  # good files flagged (expected CORRECT, got ERROR)
    warn_on_bad = []      # expected ERROR, got WARN (acceptable)
    warn_on_good = []     # expected CORRECT, got WARN (acceptable)
    correct_matches = 0
    missing = []

    for filename, exp in sorted(expected.items()):
        if filename not in actual:
            missing.append(filename)
            continue

        act = actual[filename]

        if exp == "ERROR":
            if act == "CORRECT":
                false_negatives.append(filename)
            elif act == "WARN":
                warn_on_bad.append(filename)
            else:
                correct_matches += 1
        elif exp == "CORRECT":
            if act == "ERROR":
                false_positives.append(filename)
            elif act == "WARN":
                warn_on_good.append(filename)
            else:
                correct_matches += 1

    total = len(expected)
    checked = total - len(missing)

    print(f"=== Test Results ({checked}/{total} checked) ===")
    print()

    if missing:
        print(f"  NOT YET CHECKED: {len(missing)}")
        if len(missing) <= 10:
            for f in missing:
                print(f"    {f}")
        print()

    print(f"  EXACT MATCH:     {correct_matches}/{checked}")

    # False negatives are the worst
    if false_negatives:
        print()
        print(f"  FALSE NEGATIVES (bad file missed!): {len(false_negatives)}")
        for f in false_negatives:
            print(f"    {f}  expected ERROR, got CORRECT")

    if false_positives:
        print()
        print(f"  FALSE POSITIVES (good file flagged): {len(false_positives)}")
        for f in false_positives:
            print(f"    {f}  expected CORRECT, got ERROR")

    if warn_on_bad:
        print()
        print(f"  WARN on bad files (acceptable): {len(warn_on_bad)}")
        for f in warn_on_bad:
            print(f"    {f}")

    if warn_on_good:
        print()
        print(f"  WARN on good files (acceptable): {len(warn_on_good)}")
        for f in warn_on_good:
            print(f"    {f}")

    print()

    # Summary score
    bad_total = sum(1 for v in expected.values() if v == "ERROR")
    good_total = sum(1 for v in expected.values() if v == "CORRECT")
    bad_checked = bad_total - sum(1 for f in missing if expected.get(f) == "ERROR")
    good_checked = good_total - sum(1 for f in missing if expected.get(f) == "CORRECT")

    bad_caught = bad_checked - len(false_negatives)
    good_passed = good_checked - len(false_positives)

    print(f"  Bad files caught:  {bad_caught}/{bad_checked} ({100*bad_caught/bad_checked:.0f}%)" if bad_checked else "")
    print(f"  Good files passed: {good_passed}/{good_checked} ({100*good_passed/good_checked:.0f}%)" if good_checked else "")

    if false_negatives:
        print()
        print("FAIL: false negatives detected")
        return 1
    return 0


def sample_files(expected: dict[str, str], n: int, seed: int | None = None) -> list[str]:
    """Stratified random sample: proportional ERROR/CORRECT, minimum 1 of each."""
    bad = [f for f, v in expected.items() if v == "ERROR"]
    good = [f for f, v in expected.items() if v == "CORRECT"]
    rng = random.Random(seed)
    rng.shuffle(bad)
    rng.shuffle(good)
    # Proportional split, at least 1 from each
    n_bad = max(1, round(n * len(bad) / len(expected)))
    n_good = n - n_bad
    if n_good < 1:
        n_good = 1
        n_bad = n - 1
    return sorted(bad[:n_bad] + good[:n_good])


def write_subset_dir(filenames: list[str], fr_dir: Path, en_dir: Path,
                     sub_fr: Path, sub_en: Path):
    """Symlink selected files into temporary subset directories."""
    for d in (sub_fr, sub_en):
        if d.exists():
            import shutil
            shutil.rmtree(d)
        d.mkdir()
    for f in filenames:
        src_fr = fr_dir / f
        src_en = en_dir / f
        if src_fr.exists():
            (sub_fr / f).symlink_to(src_fr.resolve())
        if src_en.exists():
            (sub_en / f).symlink_to(src_en.resolve())


def main():
    parser = argparse.ArgumentParser(description="Test llm_verify.py against known test cases.")
    parser.add_argument("--compare-only", action="store_true",
                        help="Skip LLM run, just compare existing results.")
    parser.add_argument("-n", "--max", type=int, default=0, metavar="N",
                        help="Random sample of N files (stratified). 0 = all.")
    parser.add_argument("--fresh", action="store_true",
                        help="Clear previous results before running.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible sampling.")
    parser.add_argument("--server", default="http://127.0.0.1:8080",
                        help="llama.cpp server URL.")
    args = parser.parse_args()

    expected = load_expected()

    if args.fresh and RESULTS_FILE.exists():
        RESULTS_FILE.unlink()

    if not args.compare_only:
        # Determine which files to test
        fr_dir = TEST_DIR / "Entries_txt_fr"
        en_dir = TEST_DIR / "Entries_txt"
        use_subset = args.max > 0 and args.max < len(expected)

        if use_subset:
            sample = sample_files(expected, args.max, args.seed)
            n_bad = sum(1 for f in sample if expected.get(f) == "ERROR")
            n_good = len(sample) - n_bad
            print(f"Sampling {len(sample)} files ({n_bad} bad, {n_good} good)")
            # Create temp subset dirs with symlinks
            sub_fr = TEST_DIR / "_subset_fr"
            sub_en = TEST_DIR / "_subset_en"
            write_subset_dir(sample, fr_dir, en_dir, sub_fr, sub_en)
            run_fr, run_en = str(sub_fr), str(sub_en)
        else:
            run_fr, run_en = str(fr_dir), str(en_dir)

        cmd = [
            sys.executable, str(ROOT / "scripts" / "llm_verify.py"),
            "--mode", "txt",
            "--dir", run_fr,
            "--source-dir", run_en,
            "--results", str(RESULTS_FILE),
            "--server", args.server,
        ]

        print(f"Running llm_verify.py ...")
        print()
        result = subprocess.run(cmd)

        # Clean up subset dirs
        if use_subset:
            import shutil
            shutil.rmtree(sub_fr, ignore_errors=True)
            shutil.rmtree(sub_en, ignore_errors=True)

        if result.returncode != 0:
            print("llm_verify.py failed", file=sys.stderr)
            sys.exit(result.returncode)
        print()

    actual = load_results()

    if not actual:
        print("No results found. Run without --compare-only first.", file=sys.stderr)
        sys.exit(1)

    sys.exit(compare(expected, actual))


if __name__ == "__main__":
    main()
