import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import os
import numpy as np
import cv2
from braille_core import img_to_braille_cells, braille_cells_to_image
import braille_core
# Patch braille_cells_to_image to return PIL.Image if out_path=None
from PIL import ImageDraw

def braille_cells_to_image_patched(
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

braille_core.braille_cells_to_image = braille_cells_to_image_patched

# Frame to braille utility
def frame_to_braille(frame, width=80, dot_radius=5, sat_factor=1.6, bri_factor=1.0, vspace=0, hspace=0, border=True):
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    h, w = img.height, img.width
    aspect = h / w
    new_w = width * 2
    new_h = int(width * aspect * 4 // 2)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    cells = img_to_braille_cells(img, sat_factor=sat_factor, bri_factor=bri_factor)
    out_img = braille_cells_to_image(
        cells, out_path=None,
        dot_radius=dot_radius,
        vertical_spacing=vspace, horizontal_spacing=hspace,
        dot_border=border,
        return_image=True
    )
    return out_img

class VideoBrailleGUI:
    def __init__(self, root):
        self.root = root
        root.title("Video to Colored Braille Mosaic")

        self.input_path = None
        self.output_path = None

        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky="ew")

        ttk.Button(frm, text="Select Video...", command=self.select_video).grid(row=0, column=0, sticky="w")
        self.lbl_input = ttk.Label(frm, text="No video selected", width=40)
        self.lbl_input.grid(row=0, column=1, sticky="w")

        row = 1
        self.var_width = tk.IntVar(value=80)
        self.var_dot = tk.IntVar(value=5)
        self.var_sat = tk.DoubleVar(value=1.6)
        self.var_bri = tk.DoubleVar(value=1.0)
        self.var_vspace = tk.IntVar(value=0)
        self.var_hspace = tk.IntVar(value=0)
        self.var_border = tk.BooleanVar(value=True)
        self.var_maxframes = tk.IntVar(value=0)  # 0 = all frames
        self.var_fps = tk.DoubleVar(value=0.0)

        ttk.Label(frm, text="Braille Width:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_width, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="Dot Radius:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_dot, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="Saturation:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_sat, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="Brightness:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_bri, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="V Spacing:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_vspace, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="H Spacing:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_hspace, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Checkbutton(frm, text="Show Dot Border", variable=self.var_border).grid(row=row, column=0, columnspan=2, sticky="w")

        row += 1
        ttk.Label(frm, text="Output FPS (0=source):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_fps, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(frm, text="Max Frames (0=all):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_maxframes, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Button(frm, text="Preview Frame", command=self.preview_frame).grid(row=row, column=0, sticky="we")
        ttk.Button(frm, text="Convert Video", command=self.start_convert).grid(row=row, column=1, sticky="we")

        self.progress = ttk.Progressbar(root, length=400)
        self.progress.grid(row=1, column=0, pady=5)

        self.img_panel_preview = ttk.Label(root)
        self.img_panel_preview.grid(row=2, column=0, pady=5)

        self.processing = False

    def select_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4;*.avi;*.mov;*.mkv;*.webm")]
        )
        if path:
            self.input_path = path
            self.lbl_input.config(text=os.path.basename(path))

    def preview_frame(self):
        if not self.input_path:
            messagebox.showwarning("No input video", "Please select an input video first.")
            return

        cap = cv2.VideoCapture(self.input_path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            messagebox.showerror("Error", "Could not read first frame.")
            return

        out_img = frame_to_braille(
            frame,
            width=self.var_width.get(),
            dot_radius=self.var_dot.get(),
            sat_factor=self.var_sat.get(),
            bri_factor=self.var_bri.get(),
            vspace=self.var_vspace.get(),
            hspace=self.var_hspace.get(),
            border=self.var_border.get()
        )
        img = out_img.copy()
        img.thumbnail((400, 300), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self.img_panel_preview.image = tkimg
        self.img_panel_preview.config(image=tkimg)

    def start_convert(self):
        if self.processing:
            return
        if not self.input_path:
            messagebox.showwarning("No input video", "Please select an input video first.")
            return

        savepath = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not savepath:
            return
        self.output_path = savepath
        t = threading.Thread(target=self.convert_video)
        t.start()

    def convert_video(self):
        self.processing = True
        self.progress["value"] = 0
        cap = cv2.VideoCapture(self.input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps_src = cap.get(cv2.CAP_PROP_FPS)
        out_fps = self.var_fps.get() or fps_src
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Could not read video.")
            self.processing = False
            cap.release()
            return

        # Get output frame size
        out_img = frame_to_braille(
            frame,
            width=self.var_width.get(),
            dot_radius=self.var_dot.get(),
            sat_factor=self.var_sat.get(),
            bri_factor=self.var_bri.get(),
            vspace=self.var_vspace.get(),
            hspace=self.var_hspace.get(),
            border=self.var_border.get()
        )
        w, h = out_img.size

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_path, fourcc, out_fps, (w, h))

        maxf = self.var_maxframes.get()
        count = 0
        while ret:
            braille_img = frame_to_braille(
                frame,
                width=self.var_width.get(),
                dot_radius=self.var_dot.get(),
                sat_factor=self.var_sat.get(),
                bri_factor=self.var_bri.get(),
                vspace=self.var_vspace.get(),
                hspace=self.var_hspace.get(),
                border=self.var_border.get()
            )
            outframe = cv2.cvtColor(np.array(braille_img), cv2.COLOR_RGB2BGR)
            out.write(outframe)
            count += 1
            if maxf and count >= maxf:
                break
            self.progress["value"] = 100 * count / max(total_frames, 1)
            self.root.update_idletasks()
            ret, frame = cap.read()

        cap.release()
        out.release()
        self.processing = False
        self.progress["value"] = 100
        messagebox.showinfo("Done", f"Saved: {self.output_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoBrailleGUI(root)
    root.mainloop()
