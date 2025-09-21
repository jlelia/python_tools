"""
Concatenate PDF files (head-to-toe) using PyPDF2.
Usage:
    from pdf_merger import concat_pdfs
    concat_pdfs(["file1.pdf", "file2.pdf"], "file1_file2.pdf")
"""

from typing import Iterable
import os

# support both modern and older PyPDF2 names
try:
    from PyPDF2 import PdfMerger
except Exception:
    # older PyPDF2 used PdfFileMerger
    from PyPDF2 import PdfFileMerger as PdfMerger  # type: ignore


def concat_pdfs(pdfs: Iterable[str], out_path: str) -> None:
    """
    Concatenate PDFs provided in the iterable `pdfs` (in order) and write to `out_path`.
    Raises:
      ValueError: if `pdfs` is empty
      FileNotFoundError: if any input path doesn't exist
    """
    pdf_list = list(pdfs)
    if not pdf_list:
        raise ValueError("`pdfs` must contain at least one file path.")

    for p in pdf_list:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Input file not found: {p}")

    merger = PdfMerger()
    try:
        for p in pdf_list:
            # PdfMerger.append accepts filenames or file-like objects
            merger.append(p)
        # Write to disk
        with open(out_path, "wb") as out_f:
            merger.write(out_f)
    finally:
        # ensure resources are released
        try:
            merger.close()
        except Exception:
            pass


if __name__ == "__main__":
    # example usage
    concat_pdfs(["file1.pdf", "file2.pdf"], "file1_file2.pdf")
