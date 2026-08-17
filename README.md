# Product Label Print

**launcher.py** is the app everyone actually opens — it shows the StickyRx
logo and the "PRODUCT LABEL PRINT" title, with three buttons:

- **SCAN / PRINT LABEL** — the large, prominent button. This is the
  day-to-day action used constantly at the scanning station.
- **Setup Config** and **Generate Barcode** — small, low-key buttons near
  the top. These are occasional/admin actions, so they're deliberately
  out of the way and don't compete with Scan / Print Label.

Nobody at the scanning station needs to know the individual script names.

## Files

1. **install.ps1** — one-time installer. Checks for Python, installs it
   if missing, copies everything into `C:\Program Files\KanbanLabelPrinter`,
   installs the required Python packages, and adds a single Desktop
   shortcut named **Product Label Print** for the launcher.
2. **launcher.py** — the main window: logo, title, and the three buttons
   described above.
3. **setup_config.py** — settings: printer name, label size, PDF cache
   subfolder name, barcode output folder, and where Affinity Designer /
   Acrobat are installed. Saves to `config.json`.
4. **generate_barcode.py** — pick an `.afdesign` file and a default
   quantity, get back a barcode image (Code128) encoding both as
   `filepath|quantity`. Print that onto your product label/card.
5. **print_listener.py** — the scan station app. Scan a product barcode;
   it pulls out both the file path and default quantity, shows the
   quantity in an editable box, and prints on Enter / Print. No dialog
   boxes, no typing required for a normal run.
6. **StickyRxLogo.jpg** — the logo shown in the launcher window.
7. **config.example.json** — a template config with placeholder values.
   Copy this to `config.json` on a fresh setup and fill in real values;
   `config.json` itself is intentionally left out of version control
   since it holds machine-specific settings.

## Installing on a new workstation

1. Copy all seven files above onto the new workstation (anywhere is
   fine — e.g. the Desktop or Downloads — since the installer moves
   everything to its permanent home for you).
2. Right-click `install.ps1` and choose **Run as Administrator**. It
   will:
   - Check for Python and install it if missing (with PATH already set
     up, so you won't hit "python is not recognized" errors).
   - Install to `C:\Program Files\KanbanLabelPrinter`.
   - Install the required Python packages (`pywin32`, `pywinauto`,
     `python-barcode`, `pillow`).
   - Add a single Desktop shortcut: **Product Label Print**.
3. Double-click **Product Label Print** on the Desktop.
4. Click **Setup Config** and confirm the printer name (must match
   exactly what Windows calls it — check Settings > Printers &
   Scanners), label size (4x6 is the default), and the install paths
   for Affinity Designer and Acrobat.
5. Use **Generate Barcode** to make a barcode for each product.
6. Use **Scan / Print Label** at the scanning station — leave that
   window open and focused.

## The pieces you should test by themselves first

`print_listener.py` drives Affinity Designer and Acrobat via UI
automation rather than a documented API, so both of these are worth
testing on one file before relying on them unattended:

- **Export** (`EXPORT_KEYSTROKES`) — opens the source file and sends a
  keyboard shortcut for File > Export to save a PDF. Once a file's PDF
  has been exported successfully once, the cache logic means Affinity
  won't need to be touched again for that product until you edit the
  source file.
- **Reusing an already-open instance** (`OPEN_FILE_KEYSTROKES`) — if
  Affinity is already running, the app loads the new file into that
  instance via File > Open instead of launching a second one, avoiding
  the cold-start wait on every scan after the first. Worth confirming
  the right file ends up as the active tab/window before trusting this
  unattended, especially if multiple files can end up open at once.

If either proves unreliable on your Affinity version, the fallback is
to pre-export a PDF for each product once and let the cache logic take
over from there — live export is only needed for brand new or updated
artwork.

## How the quantity confirmation works

No typing is required for a normal run. Scan a product barcode once —
the app reads both the file path and its baked-in default quantity from
the barcode (`filepath|quantity`), shows the quantity in an editable
box, pre-selected. Press Enter (or click Print) to accept the default,
or type a different number first if this run needs more or fewer than
usual. Barcodes generated before the quantity field existed still work
— they just fall back to a default of 1.

## PDF cache behavior

For a source file at:

```
C:\Products\Labels\WidgetA.afdesign
```

the cached export lives at:

```
C:\Products\Labels\PDFs\WidgetA.pdf
```

If that PDF is newer than the source file, it's reused as-is. If the
source file has a newer modification date (you edited the artwork),
`print_listener.py` re-exports automatically before printing.
