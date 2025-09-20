from PIL import Image
import os

def rotate_webp_images(input_dir: str, output_dir: str, degrees: int):
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Loop through all files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith('.webp'):
            # Define full file paths
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            # Open the image
            with Image.open(input_path) as img:
                # Rotate the image by _ degrees
                rotated_img = img.rotate(degrees, expand=True)
                
                # Save the rotated image as WebP
                rotated_img.save(output_path, format="WEBP")
                print(f"Image rotated and saved: {output_path}")

# Example usage
rotate_webp_images('path/to/inputs/', 'path/to/outputs/', 90)
