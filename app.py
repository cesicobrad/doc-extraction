"""Streamlit UI: pick or upload a document, extract, review, approve.

    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium
import streamlit as st
from dotenv import load_dotenv
from PIL import ImageOps

from extractor import IMAGE_TYPES, MODEL, Extraction, LineItem, arithmetic_checks, content_from_file, extract

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
APPROVED = ROOT / "data" / "approved"
SAVED_OUTPUTS = ROOT / "eval" / "outputs" / MODEL
DOC_TYPES = ["invoice", "quote", "purchase_order", "order_request", "other"]
SAMPLE_SUFFIXES = {".pdf", ".eml", ".txt", *IMAGE_TYPES}

load_dotenv(ROOT / ".env")
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:  # Streamlit Community Cloud passes the key as a secret.
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
# Without a key the app runs on the bundled samples using results saved by the eval.
DEMO_MODE = not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("DEMO_MODE") == "1"
st.set_page_config(page_title="Document extraction", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:2.5rem;max-width:1600px}</style>",
    unsafe_allow_html=True,
)


# --- Input -----------------------------------------------------------------

def choose_input() -> tuple[str, bytes] | None:
    with st.sidebar:
        st.header("Input")
        mode = st.radio("Source", ["Sample document", "Upload a file", "Paste text"], label_visibility="collapsed")
        if mode == "Sample document":
            files = sorted(p for p in SAMPLES.iterdir() if p.suffix.lower() in SAMPLE_SUFFIXES)
            path = st.selectbox("Sample", files, format_func=lambda p: p.name)
            return path.name, path.read_bytes()
        if DEMO_MODE:
            st.info("Uploads and pasted text need an Anthropic API key. "
                    "This demo runs on the bundled samples; see the README to run it with your own key.")
            return None
        if mode == "Upload a file":
            up = st.file_uploader("PDF, photo or scan, email (.eml) or text",
                                  type=["pdf", "eml", "txt", "md", *(s.lstrip(".") for s in IMAGE_TYPES)])
            return (up.name, up.getvalue()) if up else None
        text = st.text_area("Paste an email or a plain-language description", height=260)
        return ("pasted.txt", text.encode("utf-8")) if text.strip() else None


def show_source(name: str, data: bytes) -> None:
    if name.lower().endswith(".pdf"):
        pdf = pdfium.PdfDocument(data)
        for i in range(len(pdf)):
            img = pdf[i].render(scale=2).to_pil().convert("RGB")
            # Trim the blank page margins so the content is readable at column width.
            box = ImageOps.invert(img).getbbox()
            if box:
                pad = 30
                img = img.crop((max(box[0] - pad, 0), max(box[1] - pad, 0),
                                min(box[2] + pad, img.width), min(box[3] + pad, img.height)))
            st.image(img, width="stretch")
    elif Path(name).suffix.lower() in IMAGE_TYPES:
        st.image(data, width="stretch")
    else:
        st.code(data.decode("utf-8", errors="replace"), language=None, wrap_lines=False)


# --- Review ----------------------------------------------------------------

def clean(value: str) -> str:
    return value.strip()


def review_form(x: Extraction, k: str) -> Extraction:
    """Editable fields pre-filled from the extraction; returns the reviewed record."""
    c1, c2, c3 = st.columns(3)
    doc_type = c1.selectbox("Type", DOC_TYPES, index=DOC_TYPES.index(x.document_type), key=f"type{k}")
    number = c2.text_input("Number", x.document_number, key=f"num{k}")
    currency = c3.text_input("Currency", x.currency, key=f"cur{k}")

    c1, c2 = st.columns(2)
    issuer = c1.text_input("From (issuer)", x.issuer.name, key=f"iss{k}")
    recipient = c2.text_input("To (recipient)", x.recipient.name, key=f"rec{k}")

    c1, c2, c3 = st.columns(3)
    issue_date = c1.text_input("Issue date", x.issue_date, key=f"idate{k}")
    due_date = c2.text_input("Due / valid until", x.due_date, key=f"ddate{k}")
    delivery_date = c3.text_input("Delivery date", x.delivery_date, key=f"deldate{k}")
    delivery_address = st.text_input("Delivery address", x.delivery_address, key=f"addr{k}")

    st.markdown("**Line items**")
    items = st.data_editor(
        pd.DataFrame([i.model_dump() for i in x.line_items], columns=list(LineItem.model_fields)),
        num_rows="dynamic", width="stretch", hide_index=True, key=f"items{k}",
        column_config={
            "description": st.column_config.TextColumn("Description", width="medium"),
            "quantity": st.column_config.NumberColumn("Qty"),
            "unit": st.column_config.TextColumn("Unit", width="small"),
            "unit_price": st.column_config.NumberColumn("Unit price", format="%.2f"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        },
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    subtotal = c1.number_input("Subtotal", value=x.subtotal, format="%.2f", key=f"sub{k}")
    discount = c2.number_input("Discount", value=x.discount_amount, format="%.2f", key=f"disc{k}")
    tax_rate = c3.number_input("Tax %", value=x.tax_rate, format="%g", key=f"rate{k}")
    tax = c4.number_input("Tax", value=x.tax_amount, format="%.2f", key=f"tax{k}")
    total = c5.number_input("Total", value=x.total, format="%.2f", key=f"tot{k}")

    line_items = [
        LineItem(**{f: (("" if f in ("description", "unit") else None) if pd.isna(v) else v)
                    for f, v in row.items()})
        for row in items.to_dict("records")
        if isinstance(row.get("description"), str) and row["description"].strip()
    ]
    return x.model_copy(update={
        "document_type": doc_type, "document_number": clean(number), "currency": clean(currency),
        "issuer": x.issuer.model_copy(update={"name": clean(issuer)}),
        "recipient": x.recipient.model_copy(update={"name": clean(recipient)}),
        "issue_date": clean(issue_date), "due_date": clean(due_date), "delivery_date": clean(delivery_date),
        "delivery_address": clean(delivery_address), "line_items": line_items,
        "subtotal": subtotal, "discount_amount": discount, "tax_rate": tax_rate, "tax_amount": tax, "total": total,
    })


def money(v, cur) -> str:
    return "-" if v is None else f"{v:,.2f} {cur or ''}".strip()


def summary_table(x: Extraction) -> pd.DataFrame:
    rows = {
        "Type": x.document_type.replace("_", " "),
        "Number": x.document_number or "-",
        "From": x.issuer.name,
        "To": x.recipient.name or "-",
        "Issued": x.issue_date or "-",
        "Due / valid until": x.due_date or "-",
        "Delivery": " · ".join(filter(None, [x.delivery_date, x.delivery_address])) or "-",
        "Line items": str(len(x.line_items)),
        "Subtotal": money(x.subtotal, x.currency),
        "Discount": money(x.discount_amount, x.currency) if x.discount_amount else "-",
        "Tax": money(x.tax_amount, x.currency) + (f" ({x.tax_rate:g}%)" if x.tax_rate is not None else ""),
        "Total": money(x.total, x.currency),
    }
    return pd.DataFrame(rows.items(), columns=["Field", "Value"])


def save(x: Extraction, source: str, edited: bool) -> str:
    """Write the approved record to data/approved/ (in demo mode, keep it in this session only)."""
    record = {"approved_at": datetime.now().isoformat(timespec="seconds"), "source": source,
              "edited_by_reviewer": edited, "data": x.model_dump()}
    if DEMO_MODE:
        st.session_state.setdefault("demo_records", []).append(record)
        return "this session (demo mode: nothing is written to disk)"
    APPROVED.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", x.document_number or x.document_type).strip("-")
    path = APPROVED / f"{datetime.now():%Y%m%d-%H%M%S}_{slug}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"`{path.relative_to(ROOT)}`"


def saved_records() -> pd.DataFrame:
    if DEMO_MODE:
        records = st.session_state.get("demo_records", [])[::-1]
    else:
        records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(APPROVED.glob("*.json"), reverse=True)]
    rows = []
    for r in records:
        d = r["data"]
        rows.append({"Approved": r["approved_at"].replace("T", " "), "Type": d["document_type"],
                     "Number": d["document_number"], "From": d["issuer"]["name"],
                     "Total": money(d["total"], d["currency"]), "Edited": r["edited_by_reviewer"],
                     "Source": r["source"]})
    return pd.DataFrame(rows)


# --- Page ------------------------------------------------------------------

st.title("Document extraction")
st.caption(f"Emails, PDFs, scans and plain-language requests → structured data, "
           f"checked by a person before saving. Model: `{MODEL}`")
if DEMO_MODE:
    st.warning(f"**Demo mode, saved results.** No API key is configured, so the samples show the output "
               f"`{MODEL}` produced in the last evaluation run. Review, checks and approval work as normal.")

picked = choose_input()
if picked is None:
    st.info("Choose a sample in the sidebar." if DEMO_MODE
            else "Choose a sample, upload a file, or paste text in the sidebar.")
    st.stop()

name, data = picked
source_id = f"{name}:{hash(data)}"
if st.session_state.get("source_id") != source_id:
    st.session_state.update(source_id=source_id, result=None, saved=None)
    st.session_state.setdefault("run", 0)

left, right = st.columns([4, 7], gap="large")
with left:
    st.subheader("Source")
    st.caption(name)
    with st.container(height=760, border=False):
        show_source(name, data)

with right:
    st.subheader("Extracted data")
    if st.session_state.result is None:
        if st.button("Load saved result" if DEMO_MODE else "Extract", type="primary"):
            with st.spinner("Reading the document..."):
                try:
                    if DEMO_MODE:
                        saved = SAVED_OUTPUTS / f"{Path(name).stem}.json"
                        st.session_state.result = Extraction.model_validate_json(saved.read_text(encoding="utf-8"))
                    else:
                        st.session_state.result = extract(content_from_file(name, data))
                    st.session_state.run += 1
                    st.rerun()
                except Exception as e:  # shown to the reviewer instead of a stack trace
                    st.error(f"Extraction failed: {e}")
        st.stop()

    original: Extraction = st.session_state.result
    st.info(original.summary)
    tab_review, tab_summary, tab_json = st.tabs(["Review & edit", "Summary", "JSON"])
    with tab_review:
        reviewed = review_form(original, str(st.session_state.run))
    with tab_summary:
        st.dataframe(summary_table(reviewed), hide_index=True, width="stretch")
        if reviewed.line_items:
            st.dataframe(pd.DataFrame([i.model_dump() for i in reviewed.line_items]),
                         hide_index=True, width="stretch")
    with tab_json:
        st.json(reviewed.model_dump())

    st.markdown("**Checks before approving**")
    checks = arithmetic_checks(reviewed)
    for flag in original.review_flags:
        st.warning(f"Model note: {flag}")
    for issue in checks:
        st.error(f"Arithmetic: {issue}")
    if not original.review_flags and not checks:
        st.success("No issues found. Line items, subtotal, tax and total are consistent.")

    if st.session_state.saved:
        st.success(f"Approved and saved to {st.session_state.saved}")
    else:
        c1, c2, _ = st.columns([2, 1, 3])
        if c1.button("Approve & save", type="primary", width="stretch"):
            st.session_state.saved = save(reviewed, name, edited=reviewed != original)
            st.rerun()
        if c2.button("Discard", width="stretch"):
            st.session_state.result = None
            st.rerun()

records = saved_records()
if not records.empty:
    st.divider()
    st.subheader("Approved records")
    st.dataframe(records, hide_index=True, width="stretch")
