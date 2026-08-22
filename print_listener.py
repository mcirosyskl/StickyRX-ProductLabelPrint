"""
print_listener.py
------------------
Main app for the barcode-triggered label printing system.

Flow (updated):
    1. Scan a product barcode. It encodes "file_path|default_quantity"
       (see generate_barcode.py). If it's an older barcode without a
       quantity baked in, the quantity defaults to 1.
    2. The script checks for a cached PDF export sitting in the same
       folder as the source file (same base name, .pdf extension). If
       it exists AND is newer than the source file, it's reused.
       Otherwise the source file is opened in Affinity Designer and
       exported fresh (see export_pdf_via_affinity below).
    3. The default quantity from the barcode appears in an editable box
       on screen, already selected. Just press Enter / click Print to
       use it as-is, or type a different number first if this run needs
       more or fewer than usual.
    4. Adobe Acrobat prints that many copies of the PDF silently, using
       the printer name and label size from config.json. No print
       dialog box.

This window should stay open and focused on your scanning station PC.
A barcode scanner behaves like a keyboard that types fast and hits Enter,
so the always-focused text box below is all that's needed to "listen"
for scans.

IMPORTANT - the pieces that need hands-on testing:
    Affinity Designer does not have a documented command-line export
    option, so export_pdf_via_affinity() below drives it by opening the
    file and sending a keyboard shortcut for File > Export. The exact
    shortcut/dialog flow can vary by Affinity version and by how your
    dialog remembers its last-used settings (format, DPI, etc). Test
    this step by itself first and adjust EXPORT_KEYSTROKES /
    export_wait_seconds (in Setup Config) as needed for your installed
    version before relying on it unattended. Once a file's PDF has been
    exported successfully one time, the cache logic means Affinity won't
    need to be touched again for that product until you edit the source
    file.

    If Affinity is already open, export_pdf_via_affinity() reuses that
    instance via a File > Open keystroke (OPEN_FILE_KEYSTROKES) instead
    of launching a second one - this avoids paying the cold-start wait
    on every scan, only the first one. This also needs verification on
    your installed version, and matters most if multiple documents can
    end up open in tabs at once: the export keystrokes that follow act
    on whichever document currently has focus, so confirm the newly
    opened file is the active tab/window before export happens
    unattended for the first time.

Requires:
    pip install pywin32 pywinauto
"""

import os
import subprocess
import time
import tkinter as tk
from tkinter import messagebox

import win32com.client

from setup_config import load_config
from generate_barcode import parse_barcode_payload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Keystrokes sent to Affinity Designer to reach File > Export and confirm
# a PDF export using the dialog's last-used settings. VERIFY THIS on your
# installed version before relying on it - see module docstring above.
EXPORT_KEYSTROKES = ["^+e"]  # Ctrl+Shift+E - adjust if your version differs

# Keystrokes sent to an already-open Affinity instance to reach File > Open
# so a new source file can be loaded into it, instead of launching a whole
# second instance of the app. VERIFY THIS on your installed version too.
OPEN_FILE_KEYSTROKES = ["^o"]  # Ctrl+O - adjust if your version differs


def is_affinity_running(affinity_exe: str) -> bool:
    """
    Checks (via the Windows `tasklist` command) whether an Affinity
    Designer process is already running, so export_pdf_via_affinity can
    reuse it instead of paying the cold-start cost of launching a new
    instance every single scan.
    """
    exe_name = os.path.basename(affinity_exe)
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
            capture_output=True, text=True, timeout=5,
        )
        return exe_name.lower() in result.stdout.lower()
    except Exception:
        # If the check itself fails for any reason, fall back to treating
        # Affinity as "not running" - export_pdf_via_affinity will just
        # launch a fresh instance, which is the safe default behavior.
        return False


def get_pdf_path_for_source(source_path: str, config: dict) -> str:
    """
    Returns the path the cached PDF export should live at: the same
    folder as the source .afdesign file, with the same base name and a
    .pdf extension.
    """
    source_dir = os.path.dirname(source_path)
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    return os.path.join(source_dir, base_name + ".pdf")


def pdf_cache_is_current(source_path: str, pdf_path: str) -> bool:
    if not os.path.exists(pdf_path):
        return False
    return os.path.getmtime(pdf_path) >= os.path.getmtime(source_path)


def export_pdf_via_affinity(source_path: str, pdf_path: str, config: dict) -> None:
    """
    Gets the source file open in Affinity Designer and exports a PDF to
    pdf_path, then drives the export dialog. See the module docstring -
    both this step and the reuse-existing-instance step below need to be
    verified against your installed Affinity version.

    If Affinity is already running (e.g. left open from a previous scan
    or opened manually), this reuses that instance via File > Open
    instead of launching a second one - a full cold start only happens
    the first time Affinity needs to be opened.
    """
    import pywinauto

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    affinity_exe = config["affinity_exe_path"]

    if is_affinity_running(affinity_exe):
        # Reuse the existing window - open the target file into it via
        # File > Open rather than starting a whole second process.
        app = pywinauto.Application(backend="uia").connect(path=affinity_exe)
        window = app.top_window()
        window.set_focus()

        for keys in OPEN_FILE_KEYSTROKES:
            window.type_keys(keys, pause=0.2)
            time.sleep(1.0)

        window.type_keys(source_path, with_spaces=True, pause=0.02)
        window.type_keys("{ENTER}", pause=0.2)

        # Loading a file into an already-running instance is usually
        # faster than a full cold start, but give it a beat - reuses the
        # same export_wait_seconds setting from Setup Config.
        time.sleep(config.get("export_wait_seconds", 6))
    else:
        # No running instance found - launch fresh, same as before.
        subprocess.Popen([affinity_exe, source_path])
        time.sleep(config.get("export_wait_seconds", 6))

    app = pywinauto.Application(backend="uia").connect(path=affinity_exe)
    window = app.top_window()
    window.set_focus()

    for keys in EXPORT_KEYSTROKES:
        window.type_keys(keys, pause=0.2)
        time.sleep(1.5)

    # At this point Affinity's export dialog should be open with PDF as
    # the format (set that as the default once, manually, so it's
    # remembered). Confirm the export:
    window.type_keys("{ENTER}", pause=0.2)
    time.sleep(1.0)

    # The Save-As style dialog that follows needs the destination path
    # typed in and confirmed.
    window.type_keys(pdf_path, with_spaces=True, pause=0.02)
    window.type_keys("{ENTER}", pause=0.2)
    time.sleep(2.0)

    # Overwrite confirmation, if the file already exists.
    window.type_keys("{ENTER}", pause=0.2)


def print_pdf_via_acrobat(pdf_path: str, copies: int, config: dict) -> None:
    """
    Prints pdf_path silently through Adobe Acrobat's COM interface,
    using the printer name from config.json and the requested copy count.
    No print dialog is shown.
    """
    app = win32com.client.Dispatch("AcroExch.App")
    avdoc = win32com.client.Dispatch("AcroExch.AVDoc")

    if not avdoc.Open(pdf_path, ""):
        raise RuntimeError(f"Acrobat could not open: {pdf_path}")

    pddoc = avdoc.GetPDDoc()
    jsobj = pddoc.GetJSObject()

    print_params = jsobj.getPrintParams()
    print_params.copies = int(copies)
    print_params.interactive = print_params.constants.interactionLevel.silent
    if config.get("printer_name"):
        print_params.printerName = config["printer_name"]

    jsobj.printWithParams(print_params)

    time.sleep(1.0)  # give the print job a moment to spool before closing
    avdoc.Close(True)
    app.Exit()


class ListenerWindow(tk.Tk):
    STATE_WAIT_ARTWORK = "wait_artwork"
    STATE_CONFIRM_QUANTITY = "confirm_quantity"

    def __init__(self):
        super().__init__()
        self.title("ProductLabelPrint - Scan / Print")
        self.geometry("480x280")
        self.attributes("-topmost", True)

        self.config_data = load_config()
        self.state = self.STATE_WAIT_ARTWORK
        self.pending_pdf_path = None
        self.pending_source_path = None

        self.status_var = tk.StringVar(value="Scan a product barcode to begin.")
        tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 13), wraplength=440, justify="left").pack(
            padx=16, pady=(20, 10), anchor="w"
        )

        self.detail_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.detail_var, font=("Segoe UI", 9), fg="gray30", wraplength=440, justify="left").pack(
            padx=16, anchor="w"
        )

        # Scan-entry box: reads the artwork barcode. Scanners act like a
        # keyboard that types fast and hits Enter.
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.entry_var, font=("Segoe UI", 12))
        self.entry.pack(padx=16, pady=(16, 6), fill="x")
        self.entry.bind("<Return>", self.on_scan_submitted)
        self.entry.bind("<FocusOut>", self.refocus)

        # Quantity box: hidden/disabled until a product has been scanned,
        # then shows the barcode's default quantity, editable, with focus
        # so the operator can just press Enter to accept it or type a
        # replacement number first.
        qty_frame = tk.Frame(self)
        qty_frame.pack(padx=16, pady=(6, 4), fill="x")
        tk.Label(qty_frame, text="Quantity to print:", font=("Segoe UI", 11)).pack(side="left")
        self.quantity_var = tk.StringVar(value="")
        self.quantity_entry = tk.Entry(qty_frame, textvariable=self.quantity_var, font=("Segoe UI", 12), width=8,
                                        state="disabled")
        self.quantity_entry.pack(side="left", padx=(8, 8))
        self.quantity_entry.bind("<Return>", self.on_quantity_confirmed)

        self.print_button = tk.Button(qty_frame, text="Print", width=10, state="disabled",
                                       command=self.on_quantity_confirmed)
        self.print_button.pack(side="left")

        self.entry.focus_set()
        self.after(500, self.periodic_refocus)

    def refocus(self, _event=None):
        # Only steal focus back to the scan box while we're waiting for a
        # scan - once quantity confirmation is showing, let the operator
        # click/type in that box instead.
        if self.state == self.STATE_WAIT_ARTWORK:
            self.entry.focus_set()

    def periodic_refocus(self):
        if self.state == self.STATE_WAIT_ARTWORK:
            self.entry.focus_set()
        self.after(500, self.periodic_refocus)

    def on_scan_submitted(self, _event=None):
        scanned_text = self.entry_var.get().strip()
        self.entry_var.set("")
        if not scanned_text or self.state != self.STATE_WAIT_ARTWORK:
            return
        self.handle_artwork_scan(scanned_text)

    def handle_artwork_scan(self, payload: str):
        source_path, default_quantity = parse_barcode_payload(payload)

        if not os.path.exists(source_path):
            self.status_var.set("That file path wasn't found. Scan the artwork barcode again.")
            self.detail_var.set(source_path)
            return

        pdf_path = get_pdf_path_for_source(source_path, self.config_data)

        try:
            if pdf_cache_is_current(source_path, pdf_path):
                self.detail_var.set(f"Using cached PDF: {pdf_path}")
            else:
                self.status_var.set("Exporting fresh PDF from Affinity, please wait...")
                self.detail_var.set(os.path.basename(source_path))
                self.update_idletasks()
                export_pdf_via_affinity(source_path, pdf_path, self.config_data)
        except Exception as exc:
            self.status_var.set("Export failed. Scan the artwork barcode to try again.")
            self.detail_var.set(str(exc))
            return

        self.pending_pdf_path = pdf_path
        self.pending_source_path = source_path

        # Show the quantity box with the barcode's default, pre-selected
        # so typing immediately replaces it if the operator wants to.
        self.quantity_var.set(str(default_quantity))
        self.quantity_entry.config(state="normal")
        self.print_button.config(state="normal")
        self.quantity_entry.focus_set()
        self.quantity_entry.select_range(0, tk.END)

        self.state = self.STATE_CONFIRM_QUANTITY
        self.status_var.set("Confirm or edit the quantity, then press Enter / Print.")
        self.detail_var.set(os.path.basename(source_path))

    def on_quantity_confirmed(self, _event=None):
        if self.state != self.STATE_CONFIRM_QUANTITY:
            return

        try:
            quantity = int(self.quantity_var.get().strip())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            self.status_var.set("That's not a valid quantity - enter a whole number greater than 0.")
            return

        self.status_var.set(f"Printing {quantity} copies...")
        self.update_idletasks()

        try:
            print_pdf_via_acrobat(self.pending_pdf_path, quantity, self.config_data)
        except Exception as exc:
            self.status_var.set("Print failed. See detail below.")
            self.detail_var.set(str(exc))
            self.reset_to_wait_artwork()
            return

        self.status_var.set(f"Sent {quantity} copies to {self.config_data['printer_name']}.\nScan the next product barcode.")
        self.detail_var.set("")
        self.reset_to_wait_artwork()

    def reset_to_wait_artwork(self):
        self.state = self.STATE_WAIT_ARTWORK
        self.pending_pdf_path = None
        self.pending_source_path = None
        self.quantity_var.set("")
        self.quantity_entry.config(state="disabled")
        self.print_button.config(state="disabled")
        self.entry.focus_set()


if __name__ == "__main__":
    app = ListenerWindow()
    app.mainloop()
