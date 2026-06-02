from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter # Use pypdf (modern PyPDF2)

def add_watermark(input_pdf_stream, watermark_image_path):
    reader = PdfReader(input_pdf_stream)
    writer = PdfWriter()
    
    # Get A4 dimensions
    width, height = A4 

    # Create Watermark Layer
    wm_buffer = BytesIO()
    c = canvas.Canvas(wm_buffer, pagesize=A4)
    
    # Move origin to center for easier rotation
    c.translate(width/2, height/2)
    
    # DIAGONAL: -45 degrees flows from Top-Right to Bottom-Left
    c.rotate(-45)
    
    # Set transparency
    c.setFillAlpha(0.15) # Subtle background look
    
    # Draw image centered at the new origin
    img_width, img_h = 550, 550 # Large enough to cover the page diagonally
    c.drawImage(watermark_image_path, -img_width/2, -img_h/2, 
                width=img_width, height=img_h, mask='auto', preserveAspectRatio=True)
    
    c.save()
    wm_buffer.seek(0)
    wm_reader = PdfReader(wm_buffer)
    wm_page = wm_reader.pages[0]

    # Merge with all pages
    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream