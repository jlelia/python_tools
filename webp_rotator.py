from PIL import Image
import os

def rotate_webp_images(input_directory, output_directory):
    # Ensure output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Loop through all files in the input directory
    for filename in os.listdir(input_directory):
        if filename.endswith('.webp'):
            # Define full file paths
            input_path = os.path.join(input_directory, filename)
            output_path = os.path.join(output_directory, filename)

            # Open the image
            with Image.open(input_path) as img:
                # Rotate the image by x degrees
                rotated_img = img.rotate(180, expand=True)
                
                # Save the rotated image as WebP
                rotated_img.save(output_path, format="WEBP")
                print(f"Image rotated and saved: {output_path}")

# Set your input and output directories
input_dir = r'C:\Users\james\Documents\Programming\Pi5selfhost\WebPconversion\rotation'
output_dir = input_dir

# Call the function to rotate images
rotate_webp_images(input_dir, output_dir)
