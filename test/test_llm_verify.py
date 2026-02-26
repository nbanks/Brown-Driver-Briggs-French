#!/usr/bin/env python3
"""Unit tests for llm_verify.parse_response."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from llm_verify import parse_response


def test_basic_correct():
    v, e, s = parse_response("Tout est bon.\n>>> CORRECT 0")
    assert v == "CORRECT"
    assert s == 0


def test_error_with_severity():
    v, e, s = parse_response("Franglais.\n>>> ERROR 7")
    assert v == "ERROR"
    assert s == 7
    assert "Franglais" in e


def test_warn_with_severity():
    v, e, s = parse_response("Ambigu.\n>>> WARN 3")
    assert v == "WARN"
    assert s == 3


def test_no_severity_returns_minus_one():
    v, e, s = parse_response("OK.\n>>> CORRECT")
    assert v == "CORRECT"
    assert s == -1


def test_fallback_bare_verdict():
    v, e, s = parse_response("Some analysis\nERROR 5")
    assert v == "ERROR"
    assert s == 5


def test_severity_clamped_to_10():
    v, e, s = parse_response("Bad.\n>>> ERROR 15")
    assert v == "ERROR"
    assert s == 10


def test_empty_returns_overflow():
    v, e, s = parse_response("")
    assert v == "OVERFLOW"
    assert s == -1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  {name}: OK")
    print("All tests passed.")
