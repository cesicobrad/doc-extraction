"""Generate the two PDF samples. All companies, people and numbers are fictional.

    python scripts/make_samples.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "samples"
styles = getSampleStyleSheet()
small = styles["BodyText"].clone("small", fontSize=8.5, leading=11)


def p(text, style=styles["BodyText"]):
    return Paragraph(text, style)


def build(path, story):
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm).build(story)


def invoice():
    rows = [
        ["Item", "Qty", "Unit", "Unit price", "Amount"],
        ["Ready-mix concrete C25/30, S3, 16 mm aggregate", "7.5", "m3", "112.00", "840.00"],
        ["Concrete pump hire incl. operator", "3", "h", "95.00", "285.00"],
        ["Part-load delivery surcharge", "1", "", "60.00", "60.00"],
    ]
    items = Table(rows, colWidths=[86 * mm, 16 * mm, 14 * mm, 25 * mm, 25 * mm])
    items.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    totals = Table([
        ["Net amount", "EUR 1,185.00"],
        ["VAT 22%", "EUR 260.70"],
        ["Amount due", "EUR 1,445.70"],
    ], colWidths=[40 * mm, 30 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    header = Table([[
        p("<b><font size=15>GREYFIELD READY-MIX</font></b><br/>Gramozna pot 2, 1218 Komenda<br/>"
          "billing@greyfield-mix.example | VAT ID DEMO-GRM-7731", small),
        p("<b><font size=13>INVOICE</font></b><br/>No. <b>GRM-2026-1043</b><br/>"
          "Issued: 02/10/2026<br/>Delivery: 01/10/2026<br/>Terms: 30 days net", small),
    ]], colWidths=[110 * mm, 60 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    build(OUT / "02_concrete_invoice.pdf", [
        header, Spacer(1, 10 * mm),
        p("<b>Bill to</b><br/>Hollis Renovations<br/>Delavska ulica 41<br/>1000 Ljubljana", small),
        Spacer(1, 4 * mm),
        p("Site: Vrtna ulica 12, Kamnik (foundation pour, delivery note DN-55810)", small),
        Spacer(1, 6 * mm), items, Spacer(1, 4 * mm), totals, Spacer(1, 10 * mm),
        p("Please pay by 01/11/2026 quoting the invoice number. "
          "IBAN SI56 0000 0000 0000 001 (demo account).", small),
    ])


def purchase_order():
    rows = [
        ["#", "Description", "Qty", "Price/unit", "Line total"],
        ["1", "C24 kiln-dried structural timber 47 x 150 mm, 4.8 m lengths", "60 pcs", "18.40", "1,104.00"],
        ["2", "OSB3 board 18 mm, 2500 x 1250", "25 sheets", "21.60", "540.00"],
        ["3", "Joist hangers 47 mm, galvanised", "120 pcs", "1.35", "162.00"],
    ]
    items = Table(rows, colWidths=[8 * mm, 92 * mm, 22 * mm, 22 * mm, 24 * mm])
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e6e1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ]))
    totals = Table([
        ["Subtotal", "1,806.00"],
        ["VAT (22%)", "397.32"],
        ["Order total (EUR)", "2,203.32"],
    ], colWidths=[40 * mm, 28 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    build(OUT / "03_timber_purchase_order.pdf", [
        p("<b><font size=16>PURCHASE ORDER</font></b>"),
        p("Hollis Renovations | Delavska ulica 41, 1000 Ljubljana | orders@hollis-renovations.example", small),
        Spacer(1, 6 * mm),
        Table([
            ["PO number:", "HR-PO-0412", "Supplier:", "Fernhill Timber Yard"],
            ["Order date:", "6 Oct 2026", "", "Skladiscna cesta 18, 4000 Kranj"],
            ["Deliver by:", "13 Oct 2026", "Deliver to:", "Vrtna ulica 12, 1241 Kamnik"],
        ], colWidths=[24 * mm, 40 * mm, 24 * mm, 80 * mm],
              style=[("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                     ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]),
        Spacer(1, 8 * mm), items, Spacer(1, 4 * mm), totals, Spacer(1, 10 * mm),
        p("Please confirm availability by return email. Deliveries accepted 7:00-15:00. "
          "Quote this PO number on the delivery note and invoice.", small),
        Spacer(1, 12 * mm),
        p("Authorised by: J. Hollis, Director", small),
    ])


if __name__ == "__main__":
    invoice()
    purchase_order()
    print("Wrote PDFs to", OUT)
