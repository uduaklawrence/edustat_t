## import necessary libraries
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
import reportlab.lib.colors as colors
from PIL import Image

# define watermark function
def watermark(input_pdf_stream, text = None, image_path = None):
    reader = PdfReader(input_pdf_stream)
    first_page = reader.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)

    watermark_buffer = BytesIO()
    # define page size
    c = canvas.Canvas(watermark_buffer, pagesize=(width, height)) 
    

    # condition to check if text or image is provided
    if text:
        # text watermark
        c.setFont("Helvetica", 100) # set font and size
        c.setFillColor(colors.gray , alpha=0.3)
        c.translate(width/2, height/2)  # move origin to center of page
        c.rotate(45)  # rotate text
        c.drawCentredString(0, 0, text)  # draw the watermark text

    # image watermark
    elif image_path:
        logo_width, logo_height = width * 0.7, height * 0.3
        x = -logo_width / 2
        y = -logo_height / 2

        c.translate(width/2, height/2)  # move origin to center of page
        c.rotate(40)  # rotate image
        c.drawImage(image_path,
                    x = x,
                    y = y,
                    width=logo_width, 
                    height=logo_height, 
                    mask='auto')

    c.save()
    # save watermark PDF to buffer
    watermark_buffer.seek(0)
    return watermark_buffer
    # image watermark

# define add_watermark function
def add_watermark(input_pdf_stream, watermarktext=None, watermark_image_path=None):
    # adds image
    if not(watermarktext or watermark_image_path):
        raise ValueError("Either watermarktext or watermark_image_path must be provided.")
    
    # create watermark PDF
    watermark_pdf = watermark(input_pdf_stream, text=watermarktext, image_path=watermark_image_path)
    watermark_reader = PdfReader(watermark_pdf)
    watermark_page = watermark_reader.pages[0]

    # read input PDF
    reader = PdfReader(input_pdf_stream)
    writer = PdfWriter()

    # merge watermark with each page
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        page.merge_page(watermark_page)
        writer.add_page(page)

    # write to output PDF stream
    output_pdf_stream = BytesIO()
    writer.write(output_pdf_stream)
    output_pdf_stream.seek(0)
    return output_pdf_stream