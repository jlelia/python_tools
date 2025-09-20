"""
I made this script because I accidentally photocopied my wife's passport
upside down, so I rotated the saved .pdf 180 degrees before submitting it.
"""

from PyPDF2 import PdfReader, PdfWriter

def rotate_pdf(input_path: str, degrees: int, output_path: str):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # could add individual page rotation in place of loop
    for page in reader.pages:
        # Rotate the page _ degrees
        page.rotate(degrees)
        writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)

    print(f"Flipped PDF saved as: {output_path}")

# Example usage
rotate_pdf("file.pdf", 180, "file_correct.pdf")