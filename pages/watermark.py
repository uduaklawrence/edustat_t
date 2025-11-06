from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
import reportlab.lib.colors as colors
from PIL import Image

# define watermark function
def watermark(text = None, image_path = None):
    watermark_buffer = BytesIO()
    # define page size
    c = canvas.Canvas(watermark_buffer, pagesize=A4) 
    width, height = A4

    if text:
        # text watermark
        c.setFont("Helvetica", 100) # set font and size
        c.setFillColor(colors.gray , alpha=0.8)
        #c.setFillGray(0.9, 0.5)  # set colour and transparency: light gray, semi-transparent
        c.translate(width/2, height/2)  # move origin to center of page
        c.rotate(45)  # rotate text
        c.drawCentredString(0, 0, text)  # draw the watermark text

    elif image_path:
        logo_width, logo_height = width * 0.7, height * 0.3
        x = -logo_width / 2
        y = -logo_height / 2

        c.translate(width/2, height/2)  # move origin to center of page
        c.rotate(45)  # rotate image
        c.drawImage(image_path,
                    x = -logo_width / 2,
                    y = -logo_height / 2,
                    width=logo_width, 
                    height=logo_height, 
                    mask='auto')

    c.save()
    watermark_buffer.seek(0)
    return watermark_buffer
    # image watermark

def add_watermark(input_pdf_stream, watermarktext=None, watermark_image_path=None):
    # adds image
    if not(watermarktext or watermark_image_path):
        raise ValueError("Either watermarktext or watermark_image_path must be provided.")
    
    watermark_pdf = watermark(text=watermarktext, image_path=watermark_image_path)
    watermark_reader = PdfReader(watermark_pdf)
    watermark_page = watermark_reader.pages[0]

    reader = PdfReader(input_pdf_stream)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        page.merge_page(watermark_page)
        writer.add_page(page)

    output_pdf_stream = BytesIO()
    writer.write(output_pdf_stream)
    output_pdf_stream.seek(0)
    return output_pdf_stream

final = add_watermark('dummy.pdf', watermark_image_path = 'dummy_altered.png')

final = add_watermark('dummy.pdf', watermarktext="Edustat ni o")