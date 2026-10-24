"""Tests for the eval scoring helpers in eval/run_eval.py. No network calls."""

import json

import pytest

from extractor import DEFAULT_MODEL
from run_eval import EXPECTED, OUTPUTS, check, get, norm, same_number, score

ACTUAL = {
    "document_type": "invoice",
    "issuer": {"name": "Vrhovec Electrical s.p.", "address": "", "email": "", "tax_id": ""},
    "recipient": {"name": "Hollis Renovations", "address": "", "email": "", "tax_id": ""},
    "document_number": "", "issue_date": "2026-10-09", "due_date": "", "delivery_date": "",
    "delivery_address": "", "currency": "EUR",
    "line_items": [
        {"description": "B", "quantity": 1, "unit": "", "unit_price": 20.0, "amount": 20.0},
        {"description": "A", "quantity": 2, "unit": "", "unit_price": 5.0, "amount": 10.0},
    ],
    "subtotal": 30.0, "discount_amount": None, "tax_rate": 22, "tax_amount": 6.6, "total": 36.6,
    "summary": "", "review_flags": [],
}


def test_norm_ignores_case_spacing_and_punctuation():
    assert norm("Q-26 / 0187") == norm("q260187")


def test_get_nested_and_line_items():
    assert get(ACTUAL, "issuer.name") == "Vrhovec Electrical s.p."
    assert get(ACTUAL, "line_items.amount") == [20.0, 10.0]
    assert get(ACTUAL, "missing.field") is None


def test_get_arithmetic_flag():
    assert get(ACTUAL, "_arithmetic_flagged") is False
    assert get({**ACTUAL, "total": 63.6}, "_arithmetic_flagged") is True


def test_same_number_tolerance():
    assert same_number(1.0, 1.009)
    assert not same_number(1.0, 1.02)
    assert not same_number(None, 0)


@pytest.mark.parametrize("key,expected,actual,ok", [
    ("total", 36.6, 36.60, True),
    ("total", 36.6, 36.7, False),
    ("total", None, None, True),
    ("total", None, 36.6, False),
    ("due_date", None, "", True),
    ("currency", "EUR", "eur", True),
    ("currency", "EUR", "", False),
    ("issuer.name", "Vrhovec Electrical", "Vrhovec Electrical s.p.", True),  # contains-match
    ("document_type", "invoice", "invoice copy", False),                  # exact match
    ("line_items.amount", [10.0, 20.0], [20.0, 10.0], True),              # order ignored
    ("line_items.amount", [10.0, 20.0], [10.0], False),
    ("line_items.amount", [10.0, 20.0], [10.0, None], False),
    ("_arithmetic_flagged", True, True, True),
    ("_arithmetic_flagged", False, True, False),
])
def test_check(key, expected, actual, ok):
    assert check(key, expected, actual) is ok


def test_score_lists_only_failures():
    expected = {"currency": "EUR", "total": 99.0, "issuer.name": "Vrhovec"}
    assert score(expected, ACTUAL) == ["total: expected 99.0, got 36.6"]


def test_every_sample_has_expected_values_and_saved_output():
    names = sorted(p.stem for p in EXPECTED.glob("*.json"))
    assert len(names) >= 8
    for name in names:
        expected = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
        assert expected, name
        assert (OUTPUTS / DEFAULT_MODEL / f"{name}.json").exists(), name
