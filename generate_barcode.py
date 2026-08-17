"""
generate_barcode.py
--------------------
GUI tool to create a scannable barcode that encodes BOTH the full file
path of an Affinity Designer (.afdesign) source file AND a default print
quantity, separated by a "|" character (e.g. "C:\\Products\\WidgetA.afdesign|50").

That way, scanning the barcode at the print station tells the system
which artwork to print AND pre-fills a default quantity in one step —
the operator can still change the quantity before printing if a
particular run needs more or fewer than usual.

Usage:
    1. Run this script (or launch it from the launcher's "Generate
       Barcode" button).
    2. Browse to (or paste) the full path of the .afdesign file.
    3. Enter the default quantity for this product (how many labels get
       printed most of the time you scan it).
    4. Click "Generate Barcode".
    5. A PNG image is saved into the barcode output folder chosen in
       Setup Config (Documents\\KanbanLabelPrinter\\Barcodes by default),
       named after the source file. Print that PNG onto your label sheet
       or product card.

Requires:
    pip install python-barcode pillow
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import barcode
from barcode.writer import ImageWriter

from setup_config import load_config, resolve_barcode_output_dir

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Separator between the file path and the default quantity inside the
# barcode's encoded text. "|" is not a legal character in Windows file
# paths, so it can never collide with the path itself.
BARCODE_FIELD_SEPARATOR = "|"

DEFAULT_QUANTITY = 1


def build_barcode_payload(file_path: str, quantity: int) -> str:
    return f"{file_path}{BARCODE_FIELD_SEPARATOR}{quantity}"


def parse_barcode_payload(payload: str):
    """
    Splits a scanned barcode's text back into (file_path, quantity).
    Older barcodes generated before the quantity field existed won't
    contain the separator - those fall back to DEFAULT_QUANTITY so they
    still work.
    """
    if BARCODE_FIELD_SEPARATOR in payload:
        path_part, _, qty_part = payload.rpartition(BARCODE_FIELD_SEPARATOR)
        try:
            return path_part, int(qty_part)
        except ValueError:
            return payload, DEFAULT_QUANTITY
    return payload, DEFAULT_QUANTITY


def generate_barcode_for_path(file_path: str, quantity: int) -> str:
    """
    Generates a Code128 barcode image encoding "file_path|quantity".
    Code128 is used because it supports the full range of characters
    that can appear in a Windows file path (letters, numbers, spaces,
    backslashes, colons, etc.) plus the "|" separator and digits.
    Returns the path to the saved PNG.
    """
    config_data = load_config()
    barcode_output_dir = resolve_barcode_output_dir(config_data)

    try:
        os.makedirs(barcode_output_dir, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(
            f"Could not write to the barcode output folder:\n{barcode_output_dir}\n\n"
            "Open Setup Config and choose a different folder (e.g. somewhere "
            "under Documents) — locations like C:\\Program Files require admin "
            "rights."
        ) from exc

    payload = build_barcode_payload(file_path, quantity)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base_name)
    output_base = os.path.join(barcode_output_dir, safe_name)

    code128 = barcode.get("code128", payload, writer=ImageWriter())
    saved_path = code128.save(output_base, options={
        "module_height": 12.0,
        "font_size": 8,
        "text_distance": 3.0,
        "quiet_zone": 4.0,
        "write_text": False,  # the raw payload is long; skip printing it under the bars
    })
    return saved_path


class BarcodeGeneratorWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Label Print System - Barcode Generator")
        self.resizable(False, False)

        pad = {"padx": 10, "pady": 8}

        tk.Label(self, text="Affinity Designer file (.afdesign):").grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        self.path_var = tk.StringVar()
        tk.Entry(self, textvariable=self.path_var, width=55).grid(row=1, column=0, sticky="w", padx=(10, 0))
        tk.Button(self, text="Browse...", command=self.browse_file).grid(row=1, column=1, sticky="w", padx=(6, 10))

        tk.Label(self, text="Default quantity to print each time this is scanned:").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(14, 0)
        )
        self.quantity_var = tk.StringVar(value=str(DEFAULT_QUANTITY))
        tk.Entry(self, textvariable=self.quantity_var, width=10).grid(row=3, column=0, sticky="w", padx=10, pady=(2, 0))

        note = "You (or whoever scans it) can still type a different quantity at print time."
        tk.Label(self, text=note, fg="gray30", font=("Segoe UI", 8)).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 0)
        )

        tk.Button(self, text="Generate Barcode", width=20, command=self.on_generate).grid(
            row=5, column=0, columnspan=2, pady=14
        )

        self.status_label = tk.Label(self, text="", fg="green", wraplength=420, justify="left")
        self.status_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Affinity Designer file",
            filetypes=[("Affinity Designer files", "*.afdesign"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)

    def on_generate(self):
        file_path = self.path_var.get().strip()
        if not file_path:
            messagebox.showerror("Missing path", "Please choose or enter a file path first.")
            return

        try:
            quantity = int(self.quantity_var.get().strip())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid quantity", "Default quantity must be a whole number greater than 0.")
            return

        if not os.path.exists(file_path):
            proceed = messagebox.askyesno(
                "File not found",
                "That file doesn't exist on this computer. Generate the barcode anyway?",
            )
            if not proceed:
                return
        try:
            saved_path = generate_barcode_for_path(file_path, quantity)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not generate barcode:\n{exc}")
            return

        self.status_label.config(text=f"Saved: {saved_path}\nDefault quantity: {quantity}")
        messagebox.showinfo("Done", f"Barcode saved to:\n{saved_path}\n\nDefault quantity: {quantity}")


if __name__ == "__main__":
    app = BarcodeGeneratorWindow()
    app.mainloop()
