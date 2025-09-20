"""
This script concatenates PDFs head to toe into a single PDF.
I used it for concatenating my transcripts for a job application.
"""

from pypdf import PdfWriter

pdfs = ['file1.pdf','file2.pdf'] # head-to-toe joining

merger = PdfWriter()

for pdf in pdfs:
    merger.append(pdf)

merger.write("file1_file2.pdf") # desired file name
merger.close()