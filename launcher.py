"""
launcher.py
-----------
The main entry point for the Product Label Print system. Shows the
StickyRx logo, a title, and three buttons that launch the individual
tools:

    Scan / Print Label   -> print_listener.py   (the main, day-to-day action)
    Setup Config         -> setup_config.py     (occasional)
    Generate Barcode     -> generate_barcode.py (occasional)

Scan / Print Label is the big, prominent button since it's what gets
used constantly at the scanning station, shown right below the logo and
title. Setup Config and Generate Barcode are small, muted, centered
links below that - still one click away, but visually out of the way
so they don't compete with the main action.

This is the app the Desktop shortcut points to - nobody at the scanning
station needs to know the individual script names.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(SCRIPT_DIR, "StickyRxLogo.jpg")

BRAND_RED = "#c8102e"
BRAND_BLACK = "#111111"
BG_COLOR = "#ffffff"
MUTED_TEXT = "#8a8a8a"
MUTED_BORDER = "#d9d9d9"


def get_pythonw_executable() -> str:
    """
    Prefer pythonw.exe (no console window) if it lives alongside the
    interpreter currently running this launcher; otherwise fall back to
    whatever interpreter is running now.
    """
    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw_path):
        return pythonw_path
    return sys.executable


def launch_script(script_name: str) -> None:
    script_path = os.path.join(SCRIPT_DIR, script_name)
    try:
        subprocess.Popen([get_pythonw_executable(), script_path], cwd=SCRIPT_DIR)
    except Exception as exc:
        messagebox.showerror("Couldn't open", f"Couldn't launch {script_name}:\n{exc}")


class LauncherWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Product Label Print")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        outer = tk.Frame(self, bg=BG_COLOR)
        outer.pack(padx=28, pady=22)

        # --- Logo + title, balanced, not overpowering --------------------
        header = tk.Frame(outer, bg=BG_COLOR)
        header.pack(pady=(0, 22))

        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH)
                img.thumbnail((130, 130))  # ~18% larger than the previous 110x110 cap
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(header, image=self._logo_img, bg=BG_COLOR).pack()
            except Exception:
                pass

        tk.Label(
            header,
            text="PRODUCT LABEL PRINT",
            font=("Arial", 15, "bold"),
            fg=BRAND_BLACK,
            bg=BG_COLOR,
        ).pack(pady=(8, 0))

        # --- The main event: Scan / Print Label ---------------------------
        main_button = tk.Button(
            outer,
            text="SCAN / PRINT LABEL",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg=BRAND_RED,
            activebackground="#a80d25",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=36,
            pady=22,
            cursor="hand2",
            command=lambda: launch_script("print_listener.py"),
        )
        main_button.pack(fill="x")

        # --- Small, muted secondary actions, centered below the main button
        secondary_row = tk.Frame(outer, bg=BG_COLOR)
        secondary_row.pack(pady=(18, 0))

        self._make_secondary_button(
            secondary_row, "Setup Config", lambda: launch_script("setup_config.py")
        ).pack(side="left")

        self._make_secondary_button(
            secondary_row, "Generate Barcode", lambda: launch_script("generate_barcode.py")
        ).pack(side="left", padx=(14, 0))

    def _make_secondary_button(self, parent, text, command):
        """
        A deliberately low-key button: small text, thin border, no fill
        color, so it reads as a minor/administrative action rather than
        competing with the main Scan / Print Label button.
        """
        return tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 9),
            fg=MUTED_TEXT,
            bg=BG_COLOR,
            activebackground="#f2f2f2",
            activeforeground=BRAND_BLACK,
            relief="solid",
            bd=1,
            highlightbackground=MUTED_BORDER,
            padx=10,
            pady=4,
            cursor="hand2",
            command=command,
        )


if __name__ == "__main__":
    app = LauncherWindow()
    app.mainloop()
