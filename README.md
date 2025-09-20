# Python Tools
## Summary
This repo is a dumping ground for the little scripts I make to automate the annoying stuff.

The scripts mainly focus on image file handling, like reformatting image file extensions, checking the compression status of TIFFs, rotating or merging images, etc.

## Script Descriptions
Below is a list of the scripts with brief descriptions. I put ⭐ next to the scripts that I believe to be the highest quality and most generally useful.

[Bitscale Converter](scripts/bitscale_converter.py): turns bitmap (BMP) images to 8-bit greyscale

[jpg2pdf](scripts/jpg2pdf.py): converts JPEG images to PDF

[PDF Merger](scripts/pdf_merger.py): concatenates PDFs head-to-toe into a single PDF

[PDF Rotator](scripts/pdf_rotator.py): rotates PDFs a specified number of degrees

[CLI QR Code Generator](scripts/qr_gen_cli.py): creates custom QR code images with color gradients, frames, fun shapes, etc.

[GUI QR Code Generator](scripts/qr_gen_gui.py) ⭐: uses a GUI with live viewing of the output to create custom QR code images with color gradients, frames, fun shapes, etc.

[Image Reformatter](scripts/reformat_images.py) ⭐: changes image file format (e.g. .png -> .webp) with a single-file and directory/recursive modes. Works for JPEG, PNG, GIF, TIFF, BMP, WEBP.

[TIFF Compression Checker](scripts/tiff_compression_check.py): checks all TIFFs in an array for compression algorithms compatible with CellProfiler

[WebP Rotator](scripts/webp_rotator.py): rotates WebPs in a directory a specified number of degrees
