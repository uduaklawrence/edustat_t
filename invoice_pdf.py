# ==============================
# invoice_pdf.py
# ==============================
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from datetime import datetime
import tempfile

def generate_invoice_pdf(invoice_ref: str, user_email: str, total_amount: float, report_group: str):
    """
    Generate an invoice PDF and return its file path.
    """
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = tmpfile.name

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            rightMargin=25*mm, leftMargin=25*mm,
                            topMargin=25*mm, bottomMargin=25*mm)

    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("<b>EDUSTAT ANALYTICS</b>", styles["Title"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("📊 Intelligent Educational Analytics Platform", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Invoice table
    info_data = [
        ["Invoice Reference:", invoice_ref],
        ["Customer Email:", user_email],
        ["Report Group:", report_group],
        ["Invoice Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Amount (₦):", f"{total_amount:,.2f}"],
        ["Status:", "PAID"]
    ]
    table = Table(info_data, colWidths=[100*mm, 70*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "Thank you for your payment and continued support for Edustat Analytics.",
        styles["Italic"]
    ))

    doc.build(elements)
    return pdf_path
