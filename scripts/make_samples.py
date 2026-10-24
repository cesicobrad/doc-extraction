"""Generate the PDF and image samples. All companies, people and numbers are fictional.

    python scripts/make_samples.py
"""

import io
import random
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "samples"
styles = getSampleStyleSheet()
small = styles["BodyText"].clone("small", fontSize=8.5, leading=11)


def p(text, style=styles["BodyText"]):
    return Paragraph(text, style)


def build(path, story):
    SimpleDocTemplate(path if isinstance(path, io.BytesIO) else str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
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


def simple_invoice(target, seller, seller_lines, number, issued, buyer_lines, rows, totals_rows, footer):
    """A plain one-page invoice; used by the scanned and the wrong-total samples."""
    items = Table(rows, colWidths=[90 * mm, 18 * mm, 28 * mm, 30 * mm])
    items.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    totals = Table(totals_rows, colWidths=[40 * mm, 30 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    build(target, [
        p(f"<b><font size=16>{seller}</font></b><br/>{seller_lines}"),
        Spacer(1, 6 * mm),
        p(f"<b>INVOICE {number}</b><br/>Date: {issued}"),
        Spacer(1, 4 * mm),
        p(f"<b>Customer</b><br/>{buyer_lines}"),
        Spacer(1, 6 * mm), items, Spacer(1, 4 * mm), totals, Spacer(1, 8 * mm),
        p(footer, small),
    ])


def scanned_invoice():
    """Render an invoice, then make it look like a phone photo of a paper copy."""
    pdf = io.BytesIO()
    simple_invoice(
        pdf, "IRONBARK HARDWARE", "Trgovska cesta 9, 1290 Grosuplje | shop@ironbark-hw.example",
        "IH-88213", "16.10.2026", "Hollis Renovations<br/>Delavska ulica 41, 1000 Ljubljana",
        [["Item", "Qty", "Price", "Amount"],
         ["Plasterboard screws 3.5x35, box of 1000", "4", "12.90", "51.60"],
         ["Wood glue D3, 750 ml", "3", "8.45", "25.35"],
         ["Masking tape 50 mm", "12", "3.20", "38.40"],
         ["Dust sheet 3.6 x 2.7 m", "5", "6.80", "34.00"]],
        [["Subtotal", "149.35"], ["VAT 22%", "32.86"], ["TOTAL EUR", "182.21"]],
        "Paid by card at counter. Thank you for your business.",
    )
    page = pdfium.PdfDocument(pdf.getvalue())[0].render(scale=1.5).to_pil().convert("RGB")
    page = page.crop((0, 0, page.width, int(page.height * 0.5)))

    try:
        font = ImageFont.truetype("arialbd.ttf", 64)
    except OSError:
        font = ImageFont.load_default(size=64)
    stamp = Image.new("RGBA", (330, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    draw.rounded_rectangle((4, 4, 326, 116), radius=12, outline=(190, 30, 40, 200), width=7)
    draw.text((48, 22), "PAID", font=font, fill=(190, 30, 40, 190))
    stamp = stamp.rotate(14, expand=True)
    page.paste(stamp, (int(page.width * 0.55), int(page.height * 0.28)), stamp)

    # Paper tint, slight rotation, blur, sensor noise and JPEG compression.
    page = Image.blend(page, Image.new("RGB", page.size, (236, 228, 210)), 0.18)
    page = page.rotate(-2.2, resample=Image.BICUBIC, expand=True, fillcolor=(90, 86, 80))
    page = page.filter(ImageFilter.GaussianBlur(0.9))
    rng = random.Random(7)
    px = page.load()
    for _ in range(page.width * page.height // 12):
        x, y = rng.randrange(page.width), rng.randrange(page.height)
        n = rng.randint(-28, 28)
        px[x, y] = tuple(max(0, min(255, c + n)) for c in px[x, y])
    page.thumbnail((1400, 1400))
    page.save(OUT / "06_scanned_hardware_invoice.jpg", quality=55)


def wrong_total_invoice():
    simple_invoice(
        OUT / "07_scaffolding_invoice_wrong_total.pdf", "TALLMAST SCAFFOLDING",
        "Industrijska cona 4, 1360 Vrhnika | accounts@tallmast.example | VAT ID DEMO-TMS-3310",
        "TM-26-0298", "19 October 2026",
        "Hollis Renovations<br/>Delavska ulica 41<br/>1000 Ljubljana",
        [["Description", "Qty", "Unit price", "Amount"],
         ["Scaffold hire, facade, per week", "4", "310.00", "1,240.00"],
         ["Erection and dismantling", "1", "480.00", "480.00"],
         ["Safety netting, per m2", "60", "2.40", "144.00"]],
        # Deliberately wrong (digits transposed): 1,864.00 + 410.08 = 2,274.08.
        [["Net", "1,864.00"], ["VAT 22%", "410.08"], ["Total due EUR", "2,247.08"]],
        "Payment due within 15 days, by 3 November 2026. Site: Vrtna ulica 12, Kamnik.",
    )


def slovenian_invoice():
    font, bold = "Helvetica", "Helvetica-Bold"
    try:  # A TrueType font is needed for č, š, ž; Helvetica drops them.
        pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
        font, bold = "Arial", "Arial-Bold"
    except Exception:
        pass
    body = styles["BodyText"].clone("sl", fontName=font, fontSize=9.5, leading=12.5)
    rows = [
        ["Opis", "Količina", "EM", "Cena (EUR)", "Vrednost (EUR)"],
        ["Zidava predelne stene iz porobetona", "18,5", "m2", "34,00", "629,00"],
        ["Strojni omet sten", "42", "m2", "11,50", "483,00"],
        ["Porobetonski bloki 10 cm", "2", "pal", "186,40", "372,80"],
        ["Prevoz materiala", "1", "kos", "45,00", "45,00"],
    ]
    items = Table(rows, colWidths=[78 * mm, 20 * mm, 14 * mm, 26 * mm, 30 * mm])
    items.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    totals = Table([
        ["Osnova za DDV", "1.529,80 EUR"],
        ["DDV 22 %", "336,56 EUR"],
        ["Za plačilo", "1.866,36 EUR"],
    ], colWidths=[40 * mm, 32 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, -1), (-1, -1), bold),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
    ]))
    build(OUT / "08_racun_slovenian.pdf", [
        Paragraph(f"<font name='{bold}' size=14>ZIDARSTVO JELOVICA d.o.o.</font><br/>"
                  "Pod gozdom 6, 4260 Bled<br/>ID za DDV: DEMO-ZJ-5528 | info@zidarstvo-jelovica.example", body),
        Spacer(1, 8 * mm),
        Paragraph(f"<font name='{bold}' size=13>RAČUN št. 26-0117</font>", body),
        Paragraph("Datum izdaje: 12. 10. 2026<br/>Datum opravljene storitve: 9. 10. 2026<br/>"
                  "Rok plačila: 27. 10. 2026", body),
        Spacer(1, 5 * mm),
        Paragraph(f"<font name='{bold}'>Kupec:</font><br/>Hollis Renovations d.o.o.<br/>"
                  "Delavska ulica 41, 1000 Ljubljana", body),
        Spacer(1, 6 * mm), items, Spacer(1, 4 * mm), totals, Spacer(1, 10 * mm),
        Paragraph("Znesek nakažite na TRR SI56 0000 0000 0000 002 (demo), sklic SI00 26-0117. "
                  "Hvala za zaupanje.", body),
    ])


if __name__ == "__main__":
    invoice()
    purchase_order()
    scanned_invoice()
    wrong_total_invoice()
    slovenian_invoice()
    print("Wrote samples to", OUT)
