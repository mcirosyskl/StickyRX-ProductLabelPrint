"""
launcher.py
-----------
The main entry point for the Kanban Label Print System. Shows the
StickyRx logo, a title, and three buttons that launch the individual
tools:

    Setup Config        -> setup_config.py
    Generate Barcode    -> generate_barcode.py
    Scan / Print Label  -> print_listener.py

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


def get_pythonw_executable() -> str:
    """
    Prefer pythonw.exe (no console window) if it lives alongside the
    interpreter currently running this launcher; otherwise fall back to
    whatever interpreter is running now.
    """
    exe_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(exe_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    return sys.executable


def launch_script(script_name: str):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        messagebox.showerror("Not found", f"Couldn't find {script_name} in:\n{SCRIPT_DIR}")
        return
    subprocess.Popen([get_pythonw_executable(), script_path], cwd=SCRIPT_DIR)


class LauncherWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kanban Label Printer")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        outer = tk.Frame(self, bg=BG_COLOR)
        outer.pack(padx=36, pady=28)

        # --- Logo ---
        logo_img = Image.open(LOGO_PATH)
        logo_width = 260
        aspect = logo_img.height / logo_img.width
        logo_img = logo_img.resize((logo_width, int(logo_width * aspect)), Image.LANCZOS)
        self.logo_photo = ImageTk.PhotoImage(logo_img)
        tk.Label(outer, image=self.logo_photo, bg=BG_COLOR).pack(pady=(0, 6))

        # --- Title ---
        tk.Label(
            outer,
            text="KANBAN LABEL PRINTER",
            font=("Arial", 18, "bold"),
            fg=BRAND_BLACK,
            bg=BG_COLOR,
        ).pack(pady=(0, 4))

        # thin red divider, echoing the line under the logo wordmark
        tk.Frame(outer, bg=BRAND_RED, height=2, width=260).pack(pady=(0, 22))

        # --- Buttons ---
        button_style = {
            "font": ("Arial", 12, "bold"),
            "fg": "white",
            "bg": BRAND_BLACK,
            "activebackground": BRAND_RED,
            "activeforeground": "white",
            "bd": 0,
            "width": 26,
            "height": 2,
            "cursor": "hand2",
        }

        tk.Button(
            outer, text="SETUP CONFIG",
            command=lambda: launch_script("setup_config.py"),
            **button_style
        ).pack(pady=6)

        tk.Button(
            outer, text="GENERATE BARCODE",
            command=lambda: launch_script("generate_barcode.py"),
            **button_style
        ).pack(pady=6)

        tk.Button(
            outer, text="SCAN / PRINT LABEL",
            command=lambda: launch_script("print_listener.py"),
            **button_style
        ).pack(pady=6)


if __name__ == "__main__":
    app = LauncherWindow()
    app.mainloop()
