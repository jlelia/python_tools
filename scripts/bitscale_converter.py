"""
I made this script to deal with BMP (bitmap) incompatibility with certain
software programs like CometScore. It converts files to 8-bit greyscale BMP.
"""

from PIL import Image
import os

input_folder = r""
output_folder = r""

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for filename in os.listdir(input_folder):
    if filename.endswith(".bmp"):
        img_path = os.path.join(input_folder, filename)
        img = Image.open(img_path)
        
        # Convert image to 8-bit grayscale
        img = img.convert("L")  # "L" mode means 8-bit pixels, grayscale
        
        output_path = os.path.join(output_folder, filename)
        img.save(output_path, "BMP")
        
        print(f"Converted {filename} to 8-bit grayscale.")
