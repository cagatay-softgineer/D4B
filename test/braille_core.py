from PIL import Image, ImageDraw
import numpy as np
import colorsys

BRAILLE_DOTS = [
    (0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)
]

def boost_saturation_brightness(rgb, sat_factor=1.6, bri_factor=1.0):
    """Increase saturation and brightness of an RGB tuple."""
    r, g, b = [x/255 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)  # noqa: E741
    s = min(s * sat_factor, 1.0)
    l = min(l * bri_factor, 1.0)  # noqa: E741
    r1, g1, b1 = colorsys.hls_to_rgb(h, l, s)
    return (int(r1*255), int(g1*255), int(b1*255))

def img_to_braille_cells(img, threshold=127, sat_factor=1.6, bri_factor=1.0):
    """Return braille status and enhanced average color for each 2x4-pixel cell."""
    img = img.convert('RGB')
    w, h = img.size
    w_pad = (2 - (w % 2)) % 2
    h_pad = (4 - (h % 4)) % 4
    if w_pad or h_pad:
        new_img = Image.new('RGB', (w + w_pad, h + h_pad), (255, 255, 255))
        new_img.paste(img, (0, 0))
        img = new_img
        w, h = img.size
    arr = np.array(img)
    cells = []
    for y in range(0, h, 4):
        row = []
        for x in range(0, w, 2):
            dot_status = []
            colors = []
            for dx, dy in BRAILLE_DOTS:
                px, py = x+dx, y+dy
                r, g, b = arr[py, px]
                colors.append((r, g, b))
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                dot_status.append(lum < threshold)
            # average color for the cell
            r_avg = int(np.mean([c[0] for c in colors]))
            g_avg = int(np.mean([c[1] for c in colors]))
            b_avg = int(np.mean([c[2] for c in colors]))
            avg_color = boost_saturation_brightness(
                (r_avg, g_avg, b_avg), sat_factor=sat_factor, bri_factor=bri_factor
            )
            row.append((dot_status, avg_color))
        cells.append(row)
    return cells

def braille_cells_to_image(
    cells, out_path=None, dot_radius=5, vertical_spacing=0, horizontal_spacing=0,
    bg_color=(255,255,255), dot_border=True, return_image=False
):
    BRAILLE_DOTS = [
        (0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)
    ]
    rows = len(cells)
    cols = max(len(row) for row in cells)
    cell_width = dot_radius * 2 + horizontal_spacing
    cell_height = dot_radius * 4 + vertical_spacing
    img_width = max(1, cols * cell_width)
    img_height = max(1, rows * cell_height)
    img = Image.new('RGB', (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(img)
    border_color = (0, 0, 0) if dot_border else None
    for row_idx, row in enumerate(cells):
        for col_idx, (dot_status, color) in enumerate(row):
            cell_x = col_idx * cell_width
            cell_y = row_idx * cell_height
            for dot_idx, (dx, dy) in enumerate(BRAILLE_DOTS):
                if dot_status[dot_idx]:
                    cx = cell_x + dx * dot_radius
                    cy = cell_y + dy * dot_radius
                    draw.ellipse(
                        [cx, cy, cx + dot_radius, cy + dot_radius],
                        fill=color, outline=border_color
                    )
    if return_image or not out_path:
        return img
    img.save(out_path)


def main(
    input_path, output_path, width=80, dot_radius=5, 
    sat_factor=1.6, bri_factor=1.0,
    vertical_spacing=0, horizontal_spacing=0, dot_border=True
):
    img = Image.open(input_path)
    w, h = img.size
    aspect = h / w
    new_w = width * 2
    new_h = int(width * aspect * 4 // 2)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    cells = img_to_braille_cells(img, sat_factor=sat_factor, bri_factor=bri_factor)
    braille_cells_to_image(
        cells, output_path, dot_radius=dot_radius,
        vertical_spacing=vertical_spacing, horizontal_spacing=horizontal_spacing,
        dot_border=dot_border
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Convert images to colored braille dot mosaics with vivid color and adjustable spacing."
    )
    parser.add_argument("input_image", help="Input image file")
    parser.add_argument("output_image", help="Output image file")
    parser.add_argument("--width", type=int, default=80, help="Output width in braille cells (default: 80)")
    parser.add_argument("--dot_radius", type=int, default=5, help="Radius of braille dot (default: 5)")
    parser.add_argument("--sat", type=float, default=1.6, help="Saturation boost (default: 1.6)")
    parser.add_argument("--bri", type=float, default=1.0, help="Brightness boost (default: 1.0)")
    parser.add_argument("--vspace", type=int, default=0, help="Vertical spacing between cells (default: 0)")
    parser.add_argument("--hspace", type=int, default=0, help="Horizontal spacing between cells (default: 0)")
    parser.add_argument("--no-border", action="store_true", help="Disable black border around dots")
    args = parser.parse_args()
    main(
        args.input_image, args.output_image,
        width=args.width,
        dot_radius=args.dot_radius,
        sat_factor=args.sat,
        bri_factor=args.bri,
        vertical_spacing=args.vspace,
        horizontal_spacing=args.hspace,
        dot_border=not args.no_border
    )
