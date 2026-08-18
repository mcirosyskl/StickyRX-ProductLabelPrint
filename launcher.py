"""
launcher.py
-----------
The main entry point for the Product Label Print system. Shows the
StickyRx logo, a title, and the one button used constantly at the
scanning station:

    Scan / Print Label   -> print_listener.py   (the main, day-to-day action)

The occasional/admin tools live behind a small cog-wheel icon in the
top-right corner instead of their own buttons, so they stay out of the
way but are still one click away:

    Setup Config         -> setup_config.py
    Generate Barcode     -> generate_barcode.py

Clicking the cog pops up a small menu with those two options right
under the icon.

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
COG_COLOR = "#8a8a8a"
COG_HOVER_COLOR = "#111111"


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

        # --- Cog-wheel icon, top-right corner, opens the admin menu -------
        self._settings_menu = tk.Menu(self, tearoff=0)
        self._settings_menu.add_command(
            label="Setup Config", command=lambda: launch_script("setup_config.py")
        )
        self._settings_menu.add_command(
            label="Generate Barcode", command=lambda: launch_script("generate_barcode.py")
        )

        cog_label = tk.Label(
            self,
            text="\u2699",  # gear/cog glyph
            font=("Segoe UI", 15),
            fg=COG_COLOR,
            bg=BG_COLOR,
            cursor="hand2",
        )
        cog_label.place(relx=1.0, x=-14, y=10, anchor="ne")
        cog_label.bind("<Button-1>", self._show_settings_menu)
        cog_label.bind("<Enter>", lambda e: cog_label.configure(fg=COG_HOVER_COLOR))
        cog_label.bind("<Leave>", lambda e: cog_label.configure(fg=COG_COLOR))

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

    def _show_settings_menu(self, event):
        """Pop the Setup Config / Generate Barcode menu up under the cog."""
        self._settings_menu.tk_popup(event.widget.winfo_rootx(), event.widget.winfo_rooty() + event.widget.winfo_height())



if __name__ == "__main__":
    app = LauncherWindow()
    app.mainloop()
