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
    option, so export_pdf_via_affinity() below drives it through the UI.
    The keyboard shortcut and dialog flow (Ctrl+Alt+Shift+W -> Affinity's
    Export panel -> a native Save As dialog -> an optional overwrite
    confirmation) were confirmed from a screen recording of the actual
    flow on this installation. The PDF format preset is selected
    explicitly every time (see PDF_CATEGORY_NAME / PDF_PRESET_NAME) -
    an earlier version of this code assumed the panel would keep
    remembering PDF as the last-used format, but that turned out to be
    wrong: it can drift to a completely different format (confirmed:
    PNG) after any unrelated export in Affinity, not just this app's
    own. Test end-to-end after any Affinity update, since a version
    change could shift a shortcut, dialog layout, or the exact preset
    name again. Once a file's PDF has been exported successfully one
    time, the cache logic means Affinity won't need to be touched again
    for that product until you edit the source file.

    If Affinity is already open, export_pdf_via_affinity() reuses that
    instance via a File > Open keystroke (OPEN_FILE_KEYSTROKES) instead
    of launching a second one - this avoids paying the cold-start wait
    on every scan, only the first one. Unlike the export flow above,
    this reuse-instance path has NOT been confirmed against a recording
    yet, so it's the first thing to check if reusing an already-open
    Affinity misbehaves. It also matters most if multiple documents can
    end up open in tabs at once: the export keystrokes that follow act
    on whichever document currently has focus, so confirm the newly
    opened file is the active tab/window before export happens
    unattended for the first time.

Requires:
    pip install pywin32 pywinauto
    (win32print, from pywin32, is used to temporarily set the configured
    printer as the Windows default before calling Acrobat's /t switch -
    see print_pdf_via_acrobat for why.)
"""

import os
import subprocess
import time
import tkinter as tk
from tkinter import messagebox

from setup_config import load_config
from generate_barcode import parse_barcode_payload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Keystrokes sent to Affinity Designer to reach File > Export > Export...
# Confirmed from a screen recording of the actual dialog flow on your
# installed version: this is Ctrl+Alt+Shift+W, NOT Ctrl+Shift+E.
EXPORT_KEYSTROKES = ["^%+w"]  # Ctrl+Alt+Shift+W

# Keystrokes sent to an already-open Affinity instance to reach File > Open
# so a new source file can be loaded into it, instead of launching a whole
# second instance of the app. NOT YET VERIFIED against a recording like
# EXPORT_KEYSTROKES was - if reusing an open instance misbehaves, this is
# the first thing to check.
OPEN_FILE_KEYSTROKES = ["^o"]  # Ctrl+O - adjust if your version differs

# How long (seconds) to wait after the export shortcut for Affinity's
# Export panel to fully render (format list, live preview, file size
# estimate) before interacting with it. This is a bigger, more complex
# panel than a plain confirm dialog, so it gets its own wait separate
# from export_wait_seconds (which covers the file opening beforehand).
EXPORT_DIALOG_WAIT_SECONDS = 2.0

# How long (seconds) to wait, after sending the export keystrokes, for the
# PDF to actually appear on disk before giving up and reporting a clear
# error. This is what turns a silent failure (the automation misfiring)
# into a message you can actually see and act on.
EXPORT_VERIFY_TIMEOUT_SECONDS = 10

# How long (seconds) to give each Acrobat /t invocation to spool a print
# job before this app closes that Acrobat instance itself. Acrobat
# doesn't reliably exit on its own after /t hands a job to the printer -
# confirmed by a successful physical print happening even when the old,
# stricter 30-second wait-for-exit logic reported a "failure." This is
# just a reasonable spooling window, not a strict success/failure check.
PRINT_SPOOL_WAIT_SECONDS = 8

# Names of the format entries in Affinity's Export panel, as they appear
# in the format list. Confirmed against a screen recording. The panel
# can remember a completely different format (PNG has been observed) if
# ANY export was done more recently for any other purpose - so these are
# selected explicitly every export rather than trusting what's already
# highlighted.
PDF_CATEGORY_NAME = "PDF"
PDF_PRESET_NAME = "PDF (for export)"


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
    pdf_path. Confirmed from a screen recording of the real dialog flow,
    the export is actually THREE layered dialogs, not one:

        1. Affinity's own "Export" panel (Ctrl+Alt+Shift+W) - a bespoke
           format-picker + settings panel, not a plain confirm box. Its
           remembered format can drift to whatever was used most
           recently for ANY export in Affinity (confirmed: it drifted to
           PNG), so this code explicitly clicks the PDF preset every
           time rather than trusting it's already selected, then clicks
           the panel's own "Export..." button.
        2. A native Windows "Save As" file dialog, prefilled with the
           source file's name and defaulting to whatever folder was used
           last time (NOT necessarily the source file's folder) - the
           full destination path gets typed directly into its filename
           field, which Windows resolves correctly on its own.
        3. If a file already exists at that destination, a native
           "already exists - replace it?" confirmation, with "Yes" as
           the default (focused) button.

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
    main_window = app.top_window()
    main_window.set_focus()

    # --- Dialog 1: Affinity's own Export panel ----------------------
    for keys in EXPORT_KEYSTROKES:
        main_window.type_keys(keys, pause=0.2)
    time.sleep(EXPORT_DIALOG_WAIT_SECONDS)

    # This panel remembers whatever format was used most recently for
    # ANY export in Affinity - not just this app's own exports - so it
    # can drift to something completely unrelated (confirmed: it drifted
    # to PNG after unrelated manual testing). Never trust it's still set
    # to PDF; select the PDF preset explicitly every time instead.
    try:
        export_panel = app.window(title="Export")
        export_panel.wait("visible", timeout=10)

        try:
            pdf_preset_item = export_panel.child_window(title=PDF_PRESET_NAME, control_type="ListItem")
            pdf_preset_item.click_input()
        except Exception:
            # The PDF sub-presets are likely collapsed under the
            # top-level "PDF" category (as opposed to whatever category
            # - e.g. PNG - was last expanded) - click that first to
            # reveal them, then retry selecting the specific preset.
            pdf_category_item = export_panel.child_window(title=PDF_CATEGORY_NAME, control_type="ListItem")
            pdf_category_item.click_input()
            time.sleep(0.5)
            pdf_preset_item = export_panel.child_window(title=PDF_PRESET_NAME, control_type="ListItem")
            pdf_preset_item.click_input()

        # Selecting a preset makes the whole right-hand settings panel
        # re-render (file size estimate, DPI options, etc all change) -
        # give that a moment to finish. Critically, the export_button
        # reference is looked up FRESH after this wait rather than
        # captured earlier - grabbing it before the re-render finishes
        # produces a stale/disconnected element reference, which showed
        # up as a COM "event was unable to invoke any of the
        # subscribers" error when clicked.
        time.sleep(1.0)

        export_button = None
        last_click_error = None
        for attempt in range(3):
            try:
                export_panel = app.window(title="Export")  # re-fetch, not reused
                export_button = export_panel.child_window(title="Export...", control_type="Button")
                export_button.wait("enabled", timeout=5)
                export_button.click_input()
                last_click_error = None
                break
            except Exception as click_exc:
                last_click_error = click_exc
                time.sleep(0.75)
        if last_click_error is not None:
            raise last_click_error
    except Exception:
        # Fallback: send Enter to whatever currently has focus at the OS
        # level, rather than a specific window reference - main_window
        # was captured before the Export panel opened, so it may no
        # longer be the right target to send keys to directly.
        pywinauto.keyboard.send_keys("{ENTER}", pause=0.2)
    time.sleep(1.0)

    # --- Dialog 2: native Windows "Save As" file dialog --------------
    # This is a real Windows common dialog, so its filename field is
    # reliably focused by default the moment it opens - no need to
    # click into it first. Using the global keyboard (not
    # main_window.type_keys) is important here: calling type_keys on a
    # specific window wrapper forces THAT window back into focus first,
    # which would fight the separate Save As dialog for focus and send
    # keystrokes to the wrong place. Select-all before typing so the
    # pre-filled default name (the source file's own name) gets replaced
    # outright rather than partially overwritten.
    pywinauto.keyboard.send_keys("^a", pause=0.2)
    pywinauto.keyboard.send_keys(pdf_path, with_spaces=True, pause=0.02)
    pywinauto.keyboard.send_keys("{ENTER}", pause=0.2)
    time.sleep(2.0)

    # --- Dialog 3: "already exists - replace it?" (only if applicable) ---
    # Only appears if pdf_path already existed. "Yes" is the default
    # (focused) button, so Enter accepts it; if the dialog never opened,
    # this Enter is harmless (it just reaches whatever currently has
    # focus, typically the Affinity canvas).
    pywinauto.keyboard.send_keys("{ENTER}", pause=0.2)

    # --- Verify the export actually happened -----------------------
    # Everything above is keystrokes/clicks fired at whatever dialog is
    # currently in front - if any step doesn't match what's actually on
    # screen (a version difference, unexpected timing), this won't raise
    # an error on its own. Without this check, print_listener.py would
    # go on to try printing a PDF that was never created. So: poll for
    # the file to actually show up, and fail loudly and specifically if
    # it doesn't.
    poll_interval = 0.5
    max_wait = EXPORT_VERIFY_TIMEOUT_SECONDS
    waited = 0.0
    while waited < max_wait:
        if os.path.exists(pdf_path):
            return
        time.sleep(poll_interval)
        waited += poll_interval

    raise RuntimeError(
        f"Affinity did not produce a PDF at:\n{pdf_path}\n\n"
        "The export panel or Save As dialog may not have appeared the "
        "way this app expected. Try it manually: open this file in "
        "Affinity, press Ctrl+Alt+Shift+W, and watch exactly what "
        "appears and in what order - then EXPORT_KEYSTROKES / the "
        "steps in export_pdf_via_affinity() near the top of "
        "print_listener.py may need further adjustment to match."
    )


def print_pdf_via_acrobat(pdf_path: str, copies: int, config: dict) -> None:
    """
    Prints pdf_path silently using Acrobat's own command-line silent-print
    switch (/t), once per requested copy. No print dialog is shown.

    NOTE: this used to drive Acrobat's internal JavaScript print API
    (getPrintParams / printWithParams) through COM automation. Modern
    Acrobat DC blocks external callers from invoking privileged JS
    methods like those, for security reasons - that's what produced the
    "(-2147467263, 'Not implemented', None, None)" error, and it has
    nothing to do with which printer is configured. The /t switch is
    Adobe's own documented mechanism for unattended silent printing and
    isn't subject to that restriction.

    /t's documented syntax is either "/t <path>" (2 args, prints to
    whatever the Windows default printer is) or the full 4-argument form
    "/t <path> <printername> <drivername> <portname>" - there's no
    supported 3-argument form with just a printer name and no
    driver/port. Passing exactly 3 args (as an earlier version of this
    function did) landed in that unsupported middle ground and could
    make Acrobat misparse its own arguments, producing a confusing
    "this file cannot be found" error despite the file being right
    there. To sidestep that entirely: the configured printer is set as
    the temporary Windows default (restored afterward) and Acrobat is
    always called with just the 2-argument form.

    /t prints exactly one copy per invocation with no dialog, so
    multiple copies means launching Acrobat that many times in a row.
    Acrobat is not required to fully close itself after each one - this
    function gives it a reasonable window to spool the job, then closes
    that instance itself either way (see PRINT_SPOOL_WAIT_SECONDS).
    """
    import win32print

    acrobat_exe = config["acrobat_exe_path"]
    printer_name = (config.get("printer_name") or "").strip()

    original_default_printer = None
    if printer_name:
        try:
            original_default_printer = win32print.GetDefaultPrinter()
        except Exception:
            original_default_printer = None
        if printer_name != original_default_printer:
            try:
                win32print.SetDefaultPrinter(printer_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Couldn't set '{printer_name}' as the Windows default "
                    f"printer:\n{exc}\n\n"
                    "Check Setup Config - the printer name has to match "
                    "exactly what Windows calls it (Settings > Printers & "
                    "Scanners)."
                ) from exc

    try:
        for copy_number in range(1, int(copies) + 1):
            args = [acrobat_exe, "/t", pdf_path]
            proc = subprocess.Popen(args)
            try:
                # Acrobat doesn't reliably self-close after handing a job
                # off to the printer via /t - it can just sit open
                # afterward, which is normal, not a failure (confirmed:
                # a physical label printed successfully even when this
                # wait "timed out" under the old logic). So: give it a
                # reasonable window to actually spool the job, and don't
                # treat "still running" past that point as an error.
                proc.wait(timeout=PRINT_SPOOL_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                pass  # expected/normal - see comment above
            finally:
                # Close this instance ourselves so scanning all day
                # doesn't pile up dozens of leftover Acrobat windows.
                if proc.poll() is None:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
            # A short pause between copies avoids overlapping launches, which
            # can otherwise confuse the printer's spool order.
            time.sleep(1.5)
    finally:
        # Always restore whatever the default printer was before, even
        # if printing failed partway through - this app shouldn't leave
        # a machine-wide setting changed behind it.
        if original_default_printer and printer_name != original_default_printer:
            try:
                win32print.SetDefaultPrinter(original_default_printer)
            except Exception:
                pass  # best-effort restore - not worth failing the print over


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
        self.detail_var.set(f"File: {self.pending_pdf_path}")
        self.update_idletasks()

        try:
            print_pdf_via_acrobat(self.pending_pdf_path, quantity, self.config_data)
        except Exception as exc:
            self.status_var.set("Print failed. See detail below.")
            self.detail_var.set(f"{exc}\n\nFile: {self.pending_pdf_path}")
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
