# Document extraction with human review

Turns messy business paperwork (forwarded emails, PDF invoices and orders, notes from a
phone call) into structured JSON and a clean summary table. A person checks and corrects
the result before anything is saved.

![Review screen: a PDF invoice on the left, extracted fields and line items on the right, with checks and an Approve button](docs/screenshot.png)

## What it does

1. **Input:** pick a sample, upload a PDF / `.eml` / `.txt`, or paste text.
2. **Extract:** Claude (`claude-opus-5-5`) reads the document and returns data that must
   match a fixed schema (structured outputs, validated with Pydantic). It covers parties,
   document number, dates, currency, line items, subtotal, discount, tax and total. PDFs
   go to the model as-is, so the layout, including tables, is preserved.
3. **Review:** every field and line item can be edited. Two kinds of checks appear before
   approval:
   - **Model notes:** anything the model thinks a person should look at, e.g. *"site lead
     thinks the adhesive quantity may be too high"* or *"no prices given, apply account rates"*.
   - **Arithmetic checks:** deterministic code verifies quantity × price, the line item
     sum, tax at the stated rate, and the total. These re-run live as you edit.
4. **Approve & save:** the reviewed record is written to `data/approved/` as JSON, marked
   with whether the reviewer changed anything. Discard drops it.

Nothing is saved without a person approving it. The model proposes, the reviewer decides.

## Samples

Five made-up documents from a renovation contractor's inbox, each with a different shape:

| File | What it is | What makes it awkward |
|---|---|---|
| `01_forwarded_quote.eml` | Tile supplier quote, forwarded internally | Forwarding header, signature and disclaimer around the real content; European number format |
| `02_concrete_invoice.pdf` | Ready-mix concrete invoice | DD/MM/YYYY dates, delivery date separate from issue date |
| `03_timber_purchase_order.pdf` | Purchase order sent to a timber yard | The contractor is the *issuer* here, not the recipient |
| `04_phone_order_note.txt` | Notes from a phone call | No prices, "Thursday this week" instead of a date, quantities written in words |
| `05_subcontractor_invoice.eml` | Electrician's invoice typed into an email | Informal, early-payment discount, `1.345,14 €` formatting |

All companies, people, addresses, IDs and bank details are fictional. Email domains use
the reserved `.example` TLD.

## Evaluation

`eval/expected/` holds the correct values for each sample, written by hand. The eval runs
extraction on every sample and checks 58 fields: document type, number, parties, dates,
currency, subtotal, discount, tax rate, tax, total, and the line item amounts (or
quantities, for the order with no prices).

```
01_forwarded_quote           12/12
02_concrete_invoice          13/13
03_timber_purchase_order     13/13
04_phone_order_note           7/7
05_subcontractor_invoice     13/13

Score: 58/58 fields correct (100%)
PASS
```

The run passes at 95% or above. Raw model outputs from the last run are in
`eval/outputs/`, so `--rescore` can re-check them without calling the API.

## Run it

Requires Python 3.11+ and an [Anthropic API key](https://platform.claude.com/settings/keys).

```bash
python -m venv .venv
.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your ANTHROPIC_API_KEY
streamlit run app.py
```

Evaluation:

```bash
python eval/run_eval.py            # extract all samples (5 API calls), then score
python eval/run_eval.py --rescore  # score the saved outputs, no API calls
```

Extracting one document typically takes under 20 seconds and costs a few cents.

## Project layout

```
extractor.py          schema, prompt, Claude call, arithmetic checks
app.py                Streamlit review UI
eval/run_eval.py      field-level scoring against eval/expected/
samples/              the five test documents
scripts/              regenerate the PDF samples and the screenshot (requirements-dev.txt)
```

## Design notes

- **Structured outputs, not "please reply in JSON".** The response is constrained to the
  schema, so it always parses. Missing text fields come back as empty strings and missing
  numbers as `null`, and the prompt forbids guessing values.
- **The model flags, the code verifies.** Arithmetic is checked in Python, not by the
  model, so a wrong total is caught even if the model copies it faithfully from the document.
- **One call per document.** No agent loop is needed for this task. That keeps it fast,
  cheap and easy to reason about.
- **Refusal fallback** is turned on for the API call, so a false positive from a safety
  classifier doesn't stop a legitimate document.
- **For production** you would add OCR for scanned images, a queue for bulk inbox
  processing, and an export to the accounting or ERP system instead of JSON files.
