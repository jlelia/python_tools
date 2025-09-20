"""
Convert all .jpg/.jpeg files in a directory to individual PDF files.
If remove_original is True, the .jpg files are deleted after conversion.
I made this script for a painful experience with the Capital One dispute team LOL
"""

from pathlib import Path
from PIL import Image, UnidentifiedImageError

def jpgs_to_pdfs(directory, remove_original=False):
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory!r} is not a directory")

    for img_path in directory.iterdir():
        # skip anything that isn’t .jpg or .jpeg
        if img_path.suffix.lower() not in ('.jpg', '.jpeg'):
            continue

        try:
            img = Image.open(img_path)
        except UnidentifiedImageError:
            print(f"Skipping {img_path.name}: not a valid image")
            continue

        # ensure RGB (some JPEGs might be CMYK or palette-based)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        pdf_path = img_path.with_suffix('.pdf')
        try:
            img.save(pdf_path, 'PDF', resolution=100.0)
            print(f"{img_path.name} → {pdf_path.name}")
        except Exception as e:
            print(f"Failed to save {pdf_path.name}: {e}")
            continue

        if remove_original:
            img_path.unlink()
            print(f"  - Removed original {img_path.name}")

if __name__ == "__main__":
    # Example usage: convert everything in current folder, keep the JPGs
    jpgs_to_pdfs('.', remove_original=False)
