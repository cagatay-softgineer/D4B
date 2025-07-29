from PIL import Image, ImageDraw, ImageFont

font_path = "br.ttf"
font = ImageFont.truetype(font_path, 64)
img = Image.new("RGB", (800, 100), "white")
draw = ImageDraw.Draw(img)
# Try to draw the Unicode braille block (from U+2800)
draw.text((10, 10), "⠁⠃⠉⠙⠑⠋⠛⠓", font=font, fill="black")
img.save("braille_test.png")
print("Test image saved as braille_test.png")
