from PIL import Image, ImageDraw, ImageFont
import random
import os

def ansi_color(r, g, b, text):
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

def random_bright_color():
    r = random.randint(180, 255)
    g = random.randint(180, 255)
    b = random.randint(180, 255)
    return r, g, b

def find_ttf_font():
    # Try some common locations
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    print("WARNING: No TTF font found, using default font (fixed size, font_size will not work properly).")
    return None

def text_to_centered_inverted_braille_colored(text, font_size=24, padding=8, font_path=None):
    if font_path is None:
        font_path = find_ttf_font()
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()
    dummy_img = Image.new("L", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    braille_cell_w, braille_cell_h = 2, 4
    img_w = ((text_width + 2*padding + braille_cell_w - 1) // braille_cell_w) * braille_cell_w
    img_h = ((text_height + 2*padding + braille_cell_h - 1) // braille_cell_h) * braille_cell_h
    img = Image.new("L", (img_w, img_h), 255)
    draw = ImageDraw.Draw(img)
    text_x = (img_w - text_width) // 2
    text_y = (img_h - text_height) // 2
    draw.text((text_x, text_y), text, fill=0, font=font)
    threshold = 128
    binary_img = img.point(lambda p: 0 if p < threshold else 1, '1')
    arr = binary_img.load()
    lines = []
    for y in range(0, img_h, 4):
        line = ""
        for x in range(0, img_w, 2):
            dots = 0
            for dy, mask in enumerate([0x01, 0x02, 0x04, 0x40]):
                if y+dy < img_h and x < img_w and arr[x, y+dy] == 1:
                    dots |= mask
            for dy, mask in enumerate([0x08, 0x10, 0x20, 0x80]):
                if y+dy < img_h and x+1 < img_w and arr[x+1, y+dy] == 1:
                    dots |= mask
            braille = chr(0x2800 + dots)
            r, g, b = random_bright_color()
            line += ansi_color(r, g, b, braille)
        lines.append(line)
    return "\n".join(lines)

# Example usage:
#print(text_to_centered_inverted_braille_colored("Hello!", font_size=32))


