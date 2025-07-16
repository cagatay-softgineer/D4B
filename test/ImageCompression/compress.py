from PIL import Image
import os

def compress_to_webp(input_path, output_path=None, quality=85, max_size=None):
    """
    Compress and convert an image to .webp format.

    Args:
        input_path (str): Path to the source image file.
        output_path (str): Destination path for the .webp file. If None, auto-generated.
        quality (int): Quality for .webp (default: 85).
        max_size (tuple): (width, height) to resize image if set, else original size.

    Returns:
        str: Path to the resulting .webp file.
    """
    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".webp"

    with Image.open(input_path) as img:
        # Optionally resize
        if max_size:
            img.thumbnail(max_size, Image.LANCZOS)
        img.save(output_path, "WEBP", quality=quality)

    return output_path

if __name__ == "__main__":
    # Example usage/test: python image_compress.py input.jpg [output.webp]
    import sys
    if len(sys.argv) < 2:
        print("Usage: python image_compress.py input.jpg [output.webp]")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    webp_path = compress_to_webp(input_file, output_file)
    print(f"Compressed and saved as: {webp_path}")
