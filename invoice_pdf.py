import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT
from watermark import add_watermark

COLOR_NAVY = colors.HexColor("#5D768D")
COLOR_TOTAL_BAR = colors.HexColor("#4B6584")
COLOR_LIGHT_GRAY = colors.HexColor("#F4F7F9")

def generate_invoice_pdf(invoice_ref, user_email, amount, description, selected_group, selected_columns, status="Pending Payment"):
    safe_ref = invoice_ref.replace("/", "_")
    pdf_path = os.path.join("generated_invoices", f"Invoice_{safe_ref}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, margin=30)
    elements = []
    styles = getSampleStyleSheet()

    # ── Header ──
    elements.append(Paragraph("<font size=8 color='#777'><i>Powered by Sidmach</i></font>", ParagraphStyle('P', alignment=TA_RIGHT)))
    
    header_data = [[
        Paragraph(f"<b><font size=18 color='#1E293B'>EDUSTAT REPORTING SYSTEM</font></b>", styles['Normal']),
        Paragraph("<font size=40 color='#5D768D'>INVOICE</font>", ParagraphStyle('Inv', alignment=TA_RIGHT))
    ]]
    elements.append(Table(header_data, colWidths=[350, 180]))
    elements.append(Spacer(1, 30))

    # ── Info ──
    user_display = user_email.split("@")[0].title()
    customer_info = [[f"Customer Name: {user_display}", f"Invoice REF: {invoice_ref}"],
                     ["+234 XXX XXX XXXX", datetime.now().strftime("%B %d, %Y")],
                     [user_email, ""]]
    info_table = Table(customer_info, colWidths=[265, 265])
    info_table.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 10)]))
    elements.append(info_table)
    elements.append(Spacer(1, 40))

    # ── Items ──
    table_data = [["REPORT GROUPS", "DETAILS", "QTY", "AMOUNT"]]
    for col in selected_columns:
        table_data.append([selected_group, col, "1", ""])
    table_data[-1][3] = f"{amount:,.0f}"

    item_table = Table(table_data, colWidths=[150, 170, 80, 130])
    style = [
        ('BACKGROUND', (0,0), (-1,0), COLOR_NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0: style.append(('BACKGROUND', (0,i), (-1,i), COLOR_LIGHT_GRAY))
    
    item_table.setStyle(TableStyle(style))
    elements.append(item_table)

    # ── Total Bar ──
    total_table = Table([["TOTAL", f"₦{amount:,.2f}"]], colWidths=[320, 210])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_TOTAL_BAR),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('FONTSIZE', (0,0), (-1,-1), 22),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 20))

    # ── Footer ──
    status_color = 'green' if 'PAID' in status.upper() else 'red'
    elements.append(Paragraph(f"STATUS: &nbsp;&nbsp; <font color='{status_color}'><b>{status.upper()}</b></font>", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"<b>DESCRIPTION:</b><br/>{description}", styles['Normal']))

    doc.build(elements)

    # Apply diagonal watermark (Ensure watermark.py uses rotate(-45))
    with open(pdf_path, "rb") as f:
        pdf_stream = BytesIO(f.read())
    final_pdf = add_watermark(pdf_stream, watermark_image_path="altered_edustat.jpg")
    with open(pdf_path, "wb") as f:
        f.write(final_pdf.read())

    return pdf_path