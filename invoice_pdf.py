from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from datetime import datetime
import os
 
 
# ------------------ CONFIG ------------------
OUTPUT_DIR = "generated_invoices"
 
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
 
 
# ------------------ MAIN FUNCTION ------------------
def generate_invoice_pdf(
    invoice_ref: str,
    user_email: str,
    amount: float,
    description: str,
    selected_group: str,
    selected_columns: list,
    status: str = "Pending Payment",
):
    """
    Generates a professional invoice PDF with dynamic diagonal watermark (INVOICE or PAID)
    """
 
    # Prepare file name
    safe_ref = invoice_ref.replace("/", "_")
    pdf_path = os.path.join(OUTPUT_DIR, f"Invoice_{safe_ref}.pdf")
 
    # Create the document
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=80, bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()
 
    # Custom styles
    title_style = styles["Title"]
    title_style.alignment = TA_CENTER
    normal = styles["Normal"]
    normal.spaceAfter = 12
 
    # ---------------- HEADER ----------------
    elements.append(Paragraph("<b>EDUSTAT REPORTING PLATFORM</b>", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>INVOICE</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
 
    # Invoice Info
    invoice_date = datetime.now().strftime("%B %d, %Y")
    user_display = user_email.split("@")[0].replace(".", " ").title()
 
    info_data = [
        ["Invoice Reference:", invoice_ref],
        ["Customer Name:", user_display],
        ["Email Address:", user_email],
        ["Report Group:", selected_group],
        ["Date:", invoice_date],
    ]
 
    from reportlab.platypus import Table, TableStyle
 
    info_table = Table(info_data, colWidths=[150, 350])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 20))
 
    # ---------------- TABLE OF ITEMS ----------------
    table_data = [["Selected Item", "Quantity", "Amount (₦)"]]
    for col in selected_columns:
        table_data.append([col, "1", "-"])
 
    table_data.append(["", "Grand Total", f"₦{amount:,.2f}"])
 
    table = Table(table_data, colWidths=[250, 100, 150])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (-3, -1), (-1, -1), colors.whitesmoke),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 20))
 
    # ---------------- STATUS ----------------
    if "PAID" in status.upper():
        status_html = '<b>Status:</b> <font color="green">PAID ✅</font>'
    else:
        status_html = '<b>Status:</b> <font color="orange">Pending Payment</font>'
    elements.append(Paragraph(status_html, normal))
    elements.append(Spacer(1, 10))
 
    # ---------------- DESCRIPTION ----------------
    elements.append(Paragraph(f"<b>Description:</b> {description}", normal))
    elements.append(Spacer(1, 30))
 
    # ---------------- FOOTER ----------------
    elements.append(Paragraph("<i>Thank you for using Edustat Reporting Platform.</i>", normal))
 
    # ---------------- WATERMARK FUNCTION ----------------
    def add_watermark(canvas_obj, doc):
        """Draws diagonal watermark and PAID banner if applicable"""
        page_width, page_height = A4
        canvas_obj.saveState()
 
        # Determine watermark text and color
        if "PAID" in status.upper():
            watermark_text = "PAID ✅"
            color = colors.Color(0, 0.6, 0, alpha=0.12)  # light green transparent
        else:
            watermark_text = "INVOICE"
            color = colors.Color(0.6, 0.6, 0.6, alpha=0.12)  # light gray transparent
 
        # Draw diagonal watermark
        canvas_obj.setFont("Helvetica-Bold", 70)
        canvas_obj.setFillColor(color)
        canvas_obj.translate(page_width / 2, page_height / 2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, watermark_text)
        canvas_obj.restoreState()
 
        # Optional top banner for PAID
        if "PAID" in status.upper():
            canvas_obj.setFont("Helvetica-Bold", 28)
            canvas_obj.setFillColor(colors.green)
            canvas_obj.drawCentredString(page_width / 2, page_height - 100, "PAID ✅")
 
    # ---------------- BUILD PDF ----------------
    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
 
    return pdf_path