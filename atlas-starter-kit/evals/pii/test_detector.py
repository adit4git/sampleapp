"""Free-text identifier detector eval. Cases come from the prototype's labeled set.

The detector does not exist yet, so this module skips until `atlas_guard.detect` is
importable. Expected interface:

    detect(text: str) -> list[str]   # identifier types found, e.g. ["Person name", "Phone"]
"""
import json
from pathlib import Path

import pytest

guard = pytest.importorskip("atlas_guard", reason="PII guard not built yet (chat-mode slice)")

CASES = [
    json.loads(line)
    for line in (Path(__file__).parent / "detector_cases.jsonl").read_text().splitlines()
    if line.strip()
]
STRUCTURED = {"SSN or tax ID", "Email", "Phone", "Account number", "Date of birth"}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["text"][:40])
def test_structured_identifiers_are_always_caught(case):
    found = set(guard.detect(case["text"]))
    missing = (set(case["expected"]) & STRUCTURED) - found
    assert not missing, f"missed {missing}"


def test_name_recall_meets_band():
    want = hit = 0
    for case in CASES:
        found = guard.detect(case["text"])
        for kind in case["expected"]:
            if kind in STRUCTURED:
                continue
            want += 1
            hit += kind in found
    assert want and hit / want >= 0.98


def test_clean_messages_raise_no_alarm():
    for case in CASES:
        if not case["expected"]:
            assert guard.detect(case["text"]) == []
