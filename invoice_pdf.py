# ==============================
# 🧾 invoice_pdf.py (Final - Local Image Watermark + Modern Layout)
# ==============================

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os
from datetime import datetime
from db_queries import fetch_data

# Register font for ₦ and Unicode support
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))


def add_image_watermark(canvas_obj, watermark_path):
    """Draws a semi-transparent watermark image in the center."""
    canvas_obj.saveState()
    try:
        width, height = A4
        img_width, img_height = 300, 300  # adjust as needed
        x = (width - img_width) / 2
        y = (height - img_height) / 2
        canvas_obj.setFillAlpha(0.15)  # transparency
        canvas_obj.drawImage(watermark_path, x, y, width=img_width, height=img_height, mask='auto')
        canvas_obj.setFillAlpha(1)  # reset
    except Exception as e:
        print(f"⚠️ Watermark error: {e}")
    finally:
        canvas_obj.restoreState()


def generate_invoice_pdf(
    invoice_ref: str,
    user_email: str,
    amount: float,
    description: str,
    selected_group: str,
    selected_columns: list,
    status: str = "Pending Payment",
    watermark_path: str = r"C:\Users\uludoh\Desktop\edustat_t\assets\image 2.jpg",  # ✅ your local project folder image
) -> str:
    """
    Generates a professional invoice with watermark and detailed layout.
    """

    # Ensure invoices folder exists
    os.makedirs("invoices", exist_ok=True)
    filename = f"invoices/{invoice_ref}.pdf"

    # Get user name
    user_df = fetch_data(f"SELECT name FROM users WHERE email_address='{user_email}' LIMIT 1")
    user_name = user_df["name"].iloc[0] if not user_df.empty else user_email.split("@")[0].title()

    # PDF Layout setup
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=40,
        bottomMargin=25,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("Normal", parent=styles["Normal"], fontName="HeiseiMin-W3", fontSize=11)
    bold = ParagraphStyle("Bold", parent=styles["Normal"], fontName="HeiseiMin-W3", fontSize=12, leading=14)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontName="HeiseiMin-W3", fontSize=10, textColor=colors.gray)

    elements = []

    # Header
    elements.append(Paragraph("<b>EDUSTAT ANALYTICS</b>", bold))
    elements.append(Paragraph("Custom Report Invoice", normal))
    elements.append(Spacer(1, 10))

    # Info Section
    info_data = [
        [f"<b>Name:</b> {user_name}", f"<b>Invoice Date:</b> {datetime.now().strftime('%b %d, %Y')}"],
        [f"<b>Invoice Reference:</b> {invoice_ref}", f"<b>Status:</b> {status}"],
        [f"<b>Report Group:</b> {selected_group}", f"<b>Email:</b> {user_email}"],
    ]
    info_table = Table(info_data, colWidths=[100 * mm, 80 * mm])
    info_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "HeiseiMin-W3"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Items Table
    item_data = [["Item", "Quantity"]]
    for col in selected_columns:
        item_data.append([col, "1"])
    item_data.append(["Grand Total", f"₦{amount:,.2f}"])

    item_table = Table(item_data, colWidths=[120 * mm, 50 * mm])
    item_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f7e186")),
            ("FONTNAME", (0, 0), (-1, -1), "HeiseiMin-W3"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ])
    )
    elements.append(item_table)
    elements.append(Spacer(1, 15))

    # Subtotal and Notes
    elements.append(Paragraph(f"<b>Sub Total:</b> ₦{amount:,.2f}", bold))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Please complete your payment via Paystack to activate your report access.", small))
    elements.append(Paragraph("For support, contact support@edustat.ng", small))

    # Watermark callback
    def add_watermark(canvas_obj, doc):
        add_image_watermark(canvas_obj, watermark_path)

    # Build PDF
    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)

    return filename
