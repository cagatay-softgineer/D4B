import math
import re
import shutil
from PIL import Image, ImageDraw, ImageFont

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def render_image_as_braille_banner(
    path: str,
    banner_width: int = None,
    title_text: str = None,
    logo_cols: int = None,
    logo_and_banner_split_size: int = None,
    title_cols: int = None,
    threshold: int = 128,
    auto_threshold: bool = False,
    invert: bool = False,
    color_mode: bool = True,
    dither: bool = True,
    border: bool = True,
    title_font_path: str = None,
):
    """
    Advanced Braille banner with side-by-side logo and Braille-rendered title.

    Args:
      path: image file path
      banner_width: total characters (auto-detect if None)
      title_text: text to render in Braille mosaic beside the logo
      logo_cols: Braille columns for logo (default half width)
      title_cols: Braille columns for title (default half width)
      threshold, auto_threshold, invert: mask options
      color_mode, dither: styling flags
      border: draw box border if True
      title_font_path: TTF font path for title
    """
    # 1) Determine banner width
    if banner_width is None:
        try:
            banner_width = shutil.get_terminal_size().columns
        except:
            banner_width = 80
    inner_width = banner_width - (2 if border else 0)

    # 2) Determine layout columns
    has_title = bool(title_text)
    if has_title:
        # default split if none provided
        if logo_cols is None and title_cols is None:
            logo_cols = inner_width // 2
            title_cols = inner_width - logo_cols
        elif logo_cols is None:
            logo_cols = inner_width - title_cols
        elif title_cols is None:
            title_cols = inner_width - logo_cols
        # clamp
        logo_cols = max(1, min(logo_cols, inner_width - 1))
        title_cols = inner_width - logo_and_banner_split_size
    else:
        logo_cols = inner_width
        title_cols = 0

    # 3) Load and prepare logo image
    logo_img = Image.open(path)
    if logo_img.mode in ("RGBA","LA") or (logo_img.mode=="P" and "transparency" in logo_img.info):
        alpha = logo_img.convert("RGBA").split()[-1]
        bg = Image.new("RGBA", logo_img.size, (255,255,255,255))
        bg.paste(logo_img, mask=alpha)
        logo_img = bg.convert("RGB")
    else:
        logo_img = logo_img.convert("RGB")

    # 4) Resize logo to fit logo_cols
    cell_w, cell_h = 2, 4
    target_w = logo_and_banner_split_size * cell_w + logo_cols//2
    w, h = logo_img.size
    scale = target_w / w
    new_w = target_w
    new_h = math.ceil(h * scale / cell_h) * cell_h
    logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)

    # 5) Build mask and color for logo
    logo_gray = logo_img.convert("L")
    if auto_threshold:
        # compute threshold via Otsu (omitted for brevity)
        pass
    if dither:
        logo_mask = logo_gray.convert('1')
    else:
        logo_mask = logo_gray.point(lambda p:255 if (p < threshold) ^ invert else 0).convert('1')
    lmask = logo_mask.load()
    lcolor = logo_img.load() if color_mode else None

    # 6) Render title text to Braille mosaic if needed
    title_rows = []
    if has_title:
        title_w = title_cols * cell_w
        title_img = Image.new("RGB", (title_w, new_h), (255,255,255))
        draw = ImageDraw.Draw(title_img)
        try:
            font = ImageFont.truetype(title_font_path or "", size=new_h - 8)
        except:
            font = ImageFont.load_default()
        # Measure text
        try:
            bbox = draw.textbbox((0,0), title_text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = font.getsize(title_text)
        x0 = (title_w - tw) // 2 + (math.log(logo_and_banner_split_size) * 5)
        y0 = (new_h - th) // 2
        draw.text((x0, y0), title_text, fill=(0,0,0), font=font)
        # Build mask/color for title
        title_gray = title_img.convert("L")
        if dither:
            title_mask = title_gray.convert('1')
        else:
            title_mask = title_gray.point(lambda p:255 if (p < threshold) ^ invert else 0).convert('1')
        tmask = title_mask.load()
        tcolor = title_img.load() if color_mode else None
        # Render rows
        for y in range(0, new_h, cell_h):
            row = []
            for x in range(0, title_w, cell_w):
                dots = 0; csum = [0,0,0]; cnt = 0
                for dy, bit in enumerate((0x01,0x02,0x04,0x40)):
                    if tmask[x, y+dy] == 0:
                        dots |= bit
                        if color_mode:
                            r,g,b = tcolor[x, y+dy]; csum[0]+=r; csum[1]+=g; csum[2]+=b; cnt+=1
                for dy, bit in enumerate((0x08,0x10,0x20,0x80)):
                    if tmask[x+1, y+dy] == 0:
                        dots |= bit
                        if color_mode:
                            r,g,b = tcolor[x+1, y+dy]; csum[0]+=r; csum[1]+=g; csum[2]+=b; cnt+=1
                ch = chr(0x2800 + dots)
                if color_mode and cnt:
                    r, g, b = [csum[i]//cnt for i in range(3)]
                    row.append(f"\033[38;2;{r};{g};{b}m{ch}\033[0m")
                else:
                    row.append(ch)
            title_rows.append("".join(row))

    # 7) Generate logo rows
    logo_rows = []
    for y in range(0, new_h, cell_h):
        row = []
        for x in range(0, new_w, cell_w):
            dots = 0; csum = [0,0,0]; cnt = 0
            for dy, bit in enumerate((0x01,0x02,0x04,0x40)):
                if lmask[x, y+dy] == 0:
                    dots |= bit
                    if color_mode:
                        r,g,b = lcolor[x, y+dy]; csum[0]+=r; csum[1]+=g; csum[2]+=b; cnt+=1
            for dy, bit in enumerate((0x08,0x10,0x20,0x80)):
                if lmask[x+1, y+dy] == 0:
                    dots |= bit
                    if color_mode:
                        r,g,b = lcolor[x+1, y+dy]; csum[0]+=r; csum[1]+=g; csum[2]+=b; cnt+=1
            ch = chr(0x2800 + dots)
            if color_mode and cnt:
                r, g, b = [csum[i]//cnt for i in range(3)]
                row.append(f"\033[38;2;{r};{g};{b}m{ch}\033[0m")
            else:
                row.append(ch)
        logo_rows.append("".join(row))

    # 8) Combine
    combined = []
    for i in range(len(logo_rows)):
        if has_title:
            combined.append(logo_rows[i] + title_rows[i] + logo_rows[i])
        else:
            combined.append(logo_rows[i])

    # 9) Print
    if border:
        print("╔" + "═"*inner_width + "╗")
        for row in combined:
            vis = ANSI_ESCAPE.sub('', row)
            pad = (inner_width - len(vis)) // 2
            print("║" + " "*pad + row + " "*(inner_width - len(vis) - pad) + "║")
        print("╚" + "═"*inner_width + "╝")
    else:
        for row in combined:
            print(row)