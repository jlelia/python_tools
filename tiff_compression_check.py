"""
The purpose of this script is to check if TIFF files were compressed with
an incompatible algorithim for CellProfiler. Java JAI is apparently necessary
for CellProfiler to read certain TIFFs, and MacOS does not have it installed
by default. 
"""

from tifffile import TiffFile
import glob

bad_files = []

for path in glob.glob("test/test_GDA/*.tif"):
    with TiffFile(path) as tif:
        for page in tif.pages:
            if page.compression.name not in ('NONE', 'PACKBITS'):
                bad_files.append((path, page.index, page.compression.name))
                break  # only need to report once per file

if bad_files:
    for path, index, comp in bad_files:
        print(f"{path} uses {comp} compression on page {index}")
else:
    print("✅ All TIFFs have compatible compression.")
