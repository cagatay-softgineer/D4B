from compress import compress_to_webp  # Make sure image_compress.py is in your project
import os

INPUT_DIR = "images"
OUTPUT_DIR = "output"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

for i in range(1, 9):
    input_path = os.path.join(INPUT_DIR, f"{i}.png")
    output_path = os.path.join(OUTPUT_DIR, f"{i}.webp")
    if os.path.exists(input_path):
        compress_to_webp(input_path, output_path)
        print(f"Compressed {input_path} → {output_path}")
    else:
        print(f"File not found: {input_path}")
