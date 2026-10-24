"""Turn a messy business document into structured, validated data with Claude."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You extract structured data from business documents for a construction \
and trades company: supplier quotes, invoices, purchase orders, and informal order requests \
that arrive as forwarded emails, PDFs, or plain-language notes.

Rules:
- Extract only what the document states or clearly implies. For anything missing use an \
empty string (text) or null (numbers); never invent prices, numbers, or dates.
- Dates as YYYY-MM-DD. Resolve relative dates ("Thursday", "next week") against the \
document's own sent or issue date when one is present.
- Amounts as plain numbers (1.240,00 € -> 1240.00). Currency as an ISO 4217 code.
- "issuer" is whoever created the document (the seller on an invoice or quote, the buyer \
on a purchase order or order request). "recipient" is who it is addressed to.
- In forwarded emails, ignore forwarding headers, signatures, and disclaimers of the \
person forwarding; extract the underlying document.
- One line item per product or service. Put a discount in discount_amount (as a positive \
number), not as a line item. subtotal is before discount and tax.
- tax_rate is a percentage (22 for 22%).
- Use review_flags for anything a human should double-check: ambiguous quantities, \
missing prices, figures that don't add up, unclear parties. Keep each flag short."""


class Party(BaseModel):
    name: str
    address: str
    email: str
    tax_id: str


class LineItem(BaseModel):
    description: str
    quantity: Optional[float]
    unit: str = Field(description="e.g. pcs, m2, m3, h, bag, kg, t")
    unit_price: Optional[float]
    amount: Optional[float] = Field(description="Line total before tax")


class Extraction(BaseModel):
    # Text fields use "" for "not stated"; numbers use null. Keeping the number of
    # nullable fields small keeps the schema within structured-output limits.
    document_type: Literal["invoice", "quote", "purchase_order", "order_request", "other"]
    document_number: str
    issuer: Party
    recipient: Party
    issue_date: str
    due_date: str = Field(description="Payment due date or quote expiry")
    delivery_date: str
    delivery_address: str
    currency: str
    line_items: list[LineItem]
    subtotal: Optional[float]
    discount_amount: Optional[float]
    tax_rate: Optional[float]
    tax_amount: Optional[float]
    total: Optional[float]
    summary: str = Field(description="One sentence: who, what, how much")
    review_flags: list[str]


TEXT_SUFFIXES = {".txt", ".eml", ".md"}


def content_from_file(name: str, data: bytes) -> dict:
    """Build the Claude content block for an uploaded or sample file."""
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(data).decode("ascii"),
            },
        }
    if suffix in TEXT_SUFFIXES:
        return {"type": "text", "text": data.decode("utf-8", errors="replace")}
    raise ValueError(f"Unsupported file type: {suffix} (use .pdf, .txt, .eml or .md)")


def extract(block: dict, client: anthropic.Anthropic | None = None) -> Extraction:
    """Send one document to Claude and return the validated extraction."""
    client = client or anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        # Re-run on a fallback model if a safety classifier declines the request.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{
            "role": "user",
            "content": [block, {"type": "text", "text": "Extract the structured data from this document."}],
        }],
        output_format=Extraction,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined to process this document.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("The response was cut off before the extraction was complete.")
    return response.parsed_output


def extract_file(path: str | Path, client: anthropic.Anthropic | None = None) -> Extraction:
    path = Path(path)
    return extract(content_from_file(path.name, path.read_bytes()), client)


def arithmetic_checks(x: Extraction) -> list[str]:
    """Deterministic checks the reviewer sees next to the model's own flags."""
    issues = []
    for i, item in enumerate(x.line_items, 1):
        if None not in (item.quantity, item.unit_price, item.amount):
            if abs(item.quantity * item.unit_price - item.amount) > 0.02:
                issues.append(
                    f"Line {i}: {item.quantity:g} x {item.unit_price:.2f} = "
                    f"{item.quantity * item.unit_price:.2f}, document says {item.amount:.2f}"
                )
    amounts = [i.amount for i in x.line_items]
    if x.subtotal is not None and amounts and None not in amounts:
        if abs(sum(amounts) - x.subtotal) > 0.02:
            issues.append(f"Line items sum to {sum(amounts):.2f}, subtotal is {x.subtotal:.2f}")
    if None not in (x.subtotal, x.tax_amount, x.total):
        expected = x.subtotal - (x.discount_amount or 0) + x.tax_amount
        if abs(expected - x.total) > 0.02:
            issues.append(f"Subtotal - discount + tax = {expected:.2f}, total is {x.total:.2f}")
    if None not in (x.subtotal, x.tax_rate, x.tax_amount):
        expected = (x.subtotal - (x.discount_amount or 0)) * x.tax_rate / 100
        if abs(expected - x.tax_amount) > 0.02:
            issues.append(f"Tax at {x.tax_rate:g}% should be {expected:.2f}, document says {x.tax_amount:.2f}")
    return issues
