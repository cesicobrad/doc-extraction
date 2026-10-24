"""Tests for the deterministic parts of extractor.py. No network calls."""

import base64

import pytest

from extractor import Extraction, LineItem, Party, arithmetic_checks, content_from_file


def party(name: str) -> Party:
    return Party(name=name, address="", email="", tax_id="")


def doc(**overrides) -> Extraction:
    """A consistent invoice: 2 x 50 + 3 x 100 = 400, 22% tax = 88, total 488."""
    base = dict(
        document_type="invoice", document_number="T-1", issuer=party("Seller"), recipient=party("Buyer"),
        issue_date="2026-10-01", due_date="", delivery_date="", delivery_address="", currency="EUR",
        line_items=[
            LineItem(description="A", quantity=2, unit="pcs", unit_price=50, amount=100),
            LineItem(description="B", quantity=3, unit="pcs", unit_price=100, amount=300),
        ],
        subtotal=400, discount_amount=None, tax_rate=22, tax_amount=88, total=488,
        summary="", review_flags=[],
    )
    return Extraction(**{**base, **overrides})


# --- arithmetic_checks ------------------------------------------------------

def test_consistent_document_has_no_issues():
    assert arithmetic_checks(doc()) == []


def test_line_quantity_times_price_mismatch():
    items = [LineItem(description="A", quantity=2, unit="pcs", unit_price=50, amount=110),
             LineItem(description="B", quantity=3, unit="pcs", unit_price=100, amount=300)]
    issues = arithmetic_checks(doc(line_items=items, subtotal=410, tax_amount=90.2, total=500.2))
    assert len(issues) == 1 and issues[0].startswith("Line 1:")


def test_line_items_do_not_sum_to_subtotal():
    issues = arithmetic_checks(doc(subtotal=420, tax_amount=92.4, total=512.4))
    assert issues == ["Line items sum to 400.00, subtotal is 420.00"]


def test_wrong_total_is_caught():
    # Transposed digits, as in samples/07_scaffolding_invoice_wrong_total.pdf
    issues = arithmetic_checks(doc(total=848))
    assert issues == ["Subtotal - discount + tax = 488.00, total is 848.00"]


def test_tax_not_matching_rate():
    issues = arithmetic_checks(doc(tax_amount=80, total=480))
    assert issues == ["Tax at 22% should be 88.00, document says 80.00"]


def test_discount_is_applied_before_tax():
    # 400 - 20 = 380, 22% = 83.60, total 463.60
    assert arithmetic_checks(doc(discount_amount=20, tax_amount=83.6, total=463.6)) == []


def test_rounding_within_two_cents_is_accepted():
    assert arithmetic_checks(doc(tax_amount=88.01, total=488.01)) == []


def test_missing_numbers_skip_checks_instead_of_failing():
    items = [LineItem(description="Cement", quantity=40, unit="bag", unit_price=None, amount=None)]
    assert arithmetic_checks(doc(line_items=items, subtotal=None, tax_rate=None, tax_amount=None, total=None)) == []


def test_wrong_total_sample_values_are_flagged():
    # The exact figures printed on the deliberately wrong sample invoice.
    items = [LineItem(description="Hire", quantity=4, unit="wk", unit_price=310, amount=1240),
             LineItem(description="Erect", quantity=1, unit="", unit_price=480, amount=480),
             LineItem(description="Net", quantity=60, unit="m2", unit_price=2.4, amount=144)]
    issues = arithmetic_checks(doc(line_items=items, subtotal=1864, tax_amount=410.08, total=2247.08))
    assert issues == ["Subtotal - discount + tax = 2274.08, total is 2247.08"]


# --- content_from_file ------------------------------------------------------

def test_pdf_becomes_base64_document_block():
    block = content_from_file("Invoice.PDF", b"%PDF-1.4 test")
    assert block["type"] == "document"
    assert block["source"]["media_type"] == "application/pdf"
    assert base64.standard_b64decode(block["source"]["data"]) == b"%PDF-1.4 test"


@pytest.mark.parametrize("name,media_type", [
    ("scan.jpg", "image/jpeg"), ("scan.JPEG", "image/jpeg"), ("photo.png", "image/png"), ("x.webp", "image/webp"),
])
def test_images_become_image_blocks(name, media_type):
    block = content_from_file(name, b"\x89fake")
    assert block["type"] == "image"
    assert block["source"]["media_type"] == media_type
    assert base64.standard_b64decode(block["source"]["data"]) == b"\x89fake"


@pytest.mark.parametrize("name", ["mail.eml", "note.txt", "readme.md"])
def test_text_files_become_text_blocks(name):
    assert content_from_file(name, "Račun št. 1".encode()) == {"type": "text", "text": "Račun št. 1"}


def test_invalid_utf8_does_not_crash():
    assert content_from_file("a.txt", b"ok \xff")["text"].startswith("ok ")


@pytest.mark.parametrize("name", ["sheet.xlsx", "noextension"])
def test_unsupported_types_raise(name):
    with pytest.raises(ValueError, match="Unsupported file type"):
        content_from_file(name, b"")
