import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os

# Import your core functions (must be in same folder)
from braille_core import main as braille_main

class BrailleApp:
    def __init__(self, root):
        self.root = root
        root.title("Image to Colored Braille Dot Mosaic")

        self.input_path = None
        self.output_path = None

        # --- Controls ---
        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky="ew")

        ttk.Button(frm, text="Select Image...", command=self.select_image).grid(row=0, column=0, sticky="w")
        self.lbl_input = ttk.Label(frm, text="No image selected", width=40)
        self.lbl_input.grid(row=0, column=1, sticky="w")

        row = 1
        self.var_width = tk.IntVar(value=80)
        self.var_dot = tk.IntVar(value=5)
        self.var_sat = tk.DoubleVar(value=1.6)
        self.var_bri = tk.DoubleVar(value=1.0)
        self.var_vspace = tk.IntVar(value=0)
        self.var_hspace = tk.IntVar(value=0)
        self.var_border = tk.BooleanVar(value=True)

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
        ttk.Button(frm, text="Generate", command=self.run_braille).grid(row=row, column=0, sticky="we")
        ttk.Button(frm, text="Save Output", command=self.save_output).grid(row=row, column=1, sticky="we")

        # --- Image Previews ---
        self.img_panel_input = ttk.Label(root)
        self.img_panel_input.grid(row=1, column=0, pady=5)
        self.img_panel_output = ttk.Label(root)
        self.img_panel_output.grid(row=2, column=0, pady=5)

        self.generated_img = None  # PIL image object

    def select_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if path:
            self.input_path = path
            self.lbl_input.config(text=os.path.basename(path))
            self.show_preview(path, self.img_panel_input, maxsize=(300, 200))

    def show_preview(self, img_path, panel, maxsize=(300, 200)):
        img = Image.open(img_path)
        img.thumbnail(maxsize, Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        panel.image = tkimg
        panel.config(image=tkimg)

    def run_braille(self):
        if not self.input_path:
            messagebox.showwarning("No input image", "Please select an input image first.")
            return

        outpath = "_braille_preview.png"

        try:
            braille_main(
                self.input_path, outpath,
                width=self.var_width.get(),
                dot_radius=self.var_dot.get(),
                sat_factor=self.var_sat.get(),
                bri_factor=self.var_bri.get(),
                vertical_spacing=self.var_vspace.get(),
                horizontal_spacing=self.var_hspace.get(),
                dot_border=self.var_border.get()
            )
            # Properly open, copy, and close the image before delete
            img = Image.open(outpath)
            img.thumbnail((400, 300), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            self.img_panel_output.image = tkimg
            self.img_panel_output.config(image=tkimg)
            img.close()  # <--- this is important on Windows!
            if os.path.exists(outpath):
                os.remove(outpath)
        except Exception as ex:
            messagebox.showerror("Error", f"Could not generate braille image:\n{ex}")

    def save_output(self):
        if not self.input_path:
            messagebox.showwarning("No input image", "Please select an input image first.")
            return
        savepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if not savepath:
            return
        try:
            braille_main(
                self.input_path, savepath,
                width=self.var_width.get(),
                dot_radius=self.var_dot.get(),
                sat_factor=self.var_sat.get(),
                bri_factor=self.var_bri.get(),
                vertical_spacing=self.var_vspace.get(),
                horizontal_spacing=self.var_hspace.get(),
                dot_border=self.var_border.get()
            )
            messagebox.showinfo("Saved", f"Image saved to:\n{savepath}")
        except Exception as ex:
            messagebox.showerror("Error", f"Could not save image:\n{ex}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BrailleApp(root)
    root.mainloop()
