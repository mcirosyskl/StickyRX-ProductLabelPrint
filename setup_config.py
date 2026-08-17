"""
setup_config.py
----------------
A small GUI for configuring the label print system:
  - Printer name (as it appears in Windows > Devices and Printers)
  - Label width / height (inches)
  - Name of the PDF cache subfolder (created next to each source file)
  - Where generated barcode images are saved
  - Paths to Affinity Designer and Adobe Acrobat executables

Run this once to set things up, and again any time you need to change
the printer, label size, barcode output folder, or software paths.
Settings are saved to config.json in the same folder as this script,
and are read by print_listener.py and generate_barcode.py.
"""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# A blank barcode_output_dir means "use the default", which is resolved
# at runtime to a folder under the current user's Documents folder. That
# location is always writable without admin rights, unlike the install
# folder under C:\Program Files, which is locked down for regular users.
DEFAULT_CONFIG = {
    "printer_name": "Afinia",
    "label_width_in": 4.0,
    "label_height_in": 6.0,
    "pdf_subfolder_name": "PDFs",
    "barcode_output_dir": "",
    "affinity_exe_path": r"C:\Program Files\Affinity\Designer 2\Designer.exe",
    "acrobat_exe_path": r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
    "export_wait_seconds": 6,
    "quantity_prompt_timeout_seconds": 30,
}


def get_default_barcode_output_dir() -> str:
    """
    Per-user, always-writable fallback location for barcode images,
    used whenever barcode_output_dir is blank in config.json.
    """
    return os.path.join(os.path.expanduser("~"), "Documents", "KanbanLabelPrinter", "Barcodes")


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def resolve_barcode_output_dir(config_data) -> str:
    """
    Returns the folder barcodes should be saved to: the user's chosen
    path if set, otherwise the safe per-user default.
    """
    chosen = (config_data.get("barcode_output_dir") or "").strip()
    return chosen if chosen else get_default_barcode_output_dir()


class SetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Label Print System - Setup")
        self.resizable(False, False)
        self.config_data = load_config()

        pad = {"padx": 10, "pady": 6}

        row = 0
        tk.Label(self, text="Printer name", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.printer_var = tk.StringVar(value=self.config_data["printer_name"])
        tk.Entry(self, textvariable=self.printer_var, width=40).grid(row=row, column=1, columnspan=2, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Label width (in)", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.width_var = tk.StringVar(value=str(self.config_data["label_width_in"]))
        tk.Entry(self, textvariable=self.width_var, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Label height (in)", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.height_var = tk.StringVar(value=str(self.config_data["label_height_in"]))
        tk.Entry(self, textvariable=self.height_var, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="PDF cache subfolder name", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.pdf_folder_var = tk.StringVar(value=self.config_data["pdf_subfolder_name"])
        tk.Entry(self, textvariable=self.pdf_folder_var, width=20).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Barcode output folder", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        current_barcode_dir = self.config_data.get("barcode_output_dir", "") or get_default_barcode_output_dir()
        self.barcode_dir_var = tk.StringVar(value=current_barcode_dir)
        tk.Entry(self, textvariable=self.barcode_dir_var, width=40).grid(row=row, column=1, sticky="w", **pad)
        tk.Button(self, text="Browse...", command=self.browse_barcode_dir).grid(row=row, column=2, sticky="w", **pad)

        row += 1
        note = ("Tip: pick a folder outside C:\\Program Files — standard user\n"
                "accounts can't write there, which causes a WinError 5\n"
                "access-denied error when generating barcodes.")
        tk.Label(self, text=note, anchor="w", justify="left", fg="gray30", font=("Segoe UI", 8)).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 6)
        )

        row += 1
        tk.Label(self, text="Affinity Designer .exe", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.affinity_var = tk.StringVar(value=self.config_data["affinity_exe_path"])
        tk.Entry(self, textvariable=self.affinity_var, width=40).grid(row=row, column=1, sticky="w", **pad)
        tk.Button(self, text="Browse...", command=self.browse_affinity).grid(row=row, column=2, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Adobe Acrobat .exe", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.acrobat_var = tk.StringVar(value=self.config_data["acrobat_exe_path"])
        tk.Entry(self, textvariable=self.acrobat_var, width=40).grid(row=row, column=1, sticky="w", **pad)
        tk.Button(self, text="Browse...", command=self.browse_acrobat).grid(row=row, column=2, sticky="w", **pad)

        row += 1
        tk.Label(self, text="Export wait time (seconds)", anchor="w").grid(row=row, column=0, sticky="w", **pad)
        self.export_wait_var = tk.StringVar(value=str(self.config_data["export_wait_seconds"]))
        tk.Entry(self, textvariable=self.export_wait_var, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=12)
        tk.Button(btn_frame, text="Save", width=12, command=self.on_save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", width=12, command=self.destroy).pack(side="left", padx=6)

    def browse_barcode_dir(self):
        path = filedialog.askdirectory(title="Choose a folder for generated barcode images")
        if path:
            self.barcode_dir_var.set(path)

    def browse_affinity(self):
        path = filedialog.askopenfilename(title="Locate Affinity Designer executable",
                                           filetypes=[("Executable", "*.exe")])
        if path:
            self.affinity_var.set(path)

    def browse_acrobat(self):
        path = filedialog.askopenfilename(title="Locate Adobe Acrobat executable",
                                           filetypes=[("Executable", "*.exe")])
        if path:
            self.acrobat_var.set(path)

    def on_save(self):
        try:
            width = float(self.width_var.get())
            height = float(self.height_var.get())
            export_wait = int(self.export_wait_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Width, height, and export wait must be numbers.")
            return

        barcode_dir = self.barcode_dir_var.get().strip()
        try:
            os.makedirs(barcode_dir, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(
                "Can't use that folder",
                f"Couldn't create or write to:\n{barcode_dir}\n\n{exc}\n\n"
                "Choose a different folder (e.g. somewhere under Documents)."
            )
            return

        new_config = {
            "printer_name": self.printer_var.get().strip(),
            "label_width_in": width,
            "label_height_in": height,
            "pdf_subfolder_name": self.pdf_folder_var.get().strip() or "PDFs",
            "barcode_output_dir": barcode_dir,
            "affinity_exe_path": self.affinity_var.get().strip(),
            "acrobat_exe_path": self.acrobat_var.get().strip(),
            "export_wait_seconds": export_wait,
            "quantity_prompt_timeout_seconds": self.config_data.get("quantity_prompt_timeout_seconds", 30),
        }
        save_config(new_config)
        messagebox.showinfo("Saved", "Settings saved to config.json")
        self.destroy()


if __name__ == "__main__":
    app = SetupWindow()
    app.mainloop()
