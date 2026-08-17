# Product Label Print System

**launcher.py** is the app everyone actually opens — it shows the StickyRx
logo and title, with three buttons: SETUP CONFIG, GENERATE BARCODE, and
SCAN / PRINT LABEL. Each button opens the matching tool below. Nobody at
the scanning station needs to know the individual script names.

1. **install.bat** — double-click this to install. It requests
   Administrator permission and runs `install.ps1` for you, with no
   PowerShell command typing required and no "running scripts is
   disabled" errors.
2. **install.ps1** — the actual installer logic (checks for Python,
   installs it if missing, copies everything into
   `C:\Program Files\KanbanLabelPrinter`, installs the required Python
   packages, and adds a Desktop shortcut). `install.bat` runs this for
   you — you shouldn't need to touch it directly.
3. **launcher.py** — the main window with the logo, title, and the three
   buttons described above.
4. **setup_config.py** — settings: printer name, label size, PDF cache
   subfolder name, and where Affinity Designer / Acrobat are installed.
   Saves to `config.json`.
5. **generate_barcode.py** — pick an `.afdesign` file, get back a barcode
   image (Code128) encoding its full file path. Print that onto your
   product label/card.
6. **print_listener.py** — the scan station app. Scan the artwork
   barcode, then the quantity barcode, and it prints silently — no
   dialog boxes, no typing.
7. **StickyRxLogo.jpg** — the logo shown in the launcher window.

## Installing on a new workstation (recommended path)

1. Copy the whole `label_print_system` folder (all files, including
   `install.bat`) onto the new workstation — anywhere is fine, e.g. the
   Desktop or Downloads, since the installer moves everything to its
   permanent home for you.
2. Double-click **install.bat**.
   - A UAC prompt will pop up asking for permission — click **Yes**.
     (This is expected: the installer needs Administrator rights to
     write to Program Files.)
   - A console window will open and run the installer automatically —
     no PowerShell commands to type, and no "running scripts is
     disabled on this system" error, since install.bat handles that for
     you.
3. The installer will:
   - Check for Python. If it's missing, it downloads and installs Python
     3.12 with **"Add to PATH" turned on automatically** — this avoids
     the exact PATH problem we ran into on the first workstation, where
     `pip` and `python` weren't recognized as commands.
   - Install to `C:\Program Files\KanbanLabelPrinter`.
   - Install the four required Python packages (`pywin32`, `pywinauto`,
     `python-barcode`, `pillow`).
   - Add one Desktop shortcut: **Kanban Label Printer**.
4. Double-click **Kanban Label Printer** on the Desktop, click
   **SETUP CONFIG**, and confirm the printer name (must match exactly
   what Windows calls it — check Settings > Printers & Scanners), label
   size (4x6 is the default), and the install paths for Affinity
   Designer and Acrobat.
5. From the same launcher window, click **GENERATE BARCODE** to make a
   barcode for each product.
6. Click **SCAN / PRINT LABEL** and leave that window open and focused
   on the scanning station PC.

## Manual install (if you ever need to skip install.bat)

Adobe Acrobat Pro (not Reader) and Affinity Designer both need to
already be installed, since the scripts drive the real applications
rather than reimplementing PDF export or printing themselves.

If you'd rather run the PowerShell installer directly instead of
double-clicking install.bat, open PowerShell **as Administrator** and
run:
```
powershell -ExecutionPolicy Bypass -File "C:\path\to\label_print_system\install.ps1"
```
(This is exactly what install.bat does for you automatically.)

If you want to install the Python packages by hand instead:
```
python -m pip install pywin32 pywinauto python-barcode pillow
```

If `python` or `pip` "isn't recognized" as a command like we saw on the
first workstation, it almost always means Python was installed without
its "Add to PATH" option checked. Two ways around it:
  - Reinstall Python from python.org and check **"Add python.exe to
    PATH"** during setup, or
  - Find the full path to your python.exe (Windows Explorer search for
    `python.exe` works) and call everything through it directly, e.g.:
    ```
    C:\Users\<you>\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install pywin32 pywinauto python-barcode pillow
    C:\Users\<you>\AppData\Local\Python\pythoncore-3.14-64\python.exe "C:\Program Files\KanbanLabelPrinter\setup_config.py"
    ```
    (This is exactly the workaround we used before install.bat existed —
    install.bat exists specifically so nobody has to do this by hand
    again.)

## The one piece you should test by itself first

`export_pdf_via_affinity()` in `print_listener.py` opens Affinity
Designer and sends keystrokes to reach File > Export and save a PDF.
Affinity doesn't have a documented command-line export option, so this
is UI automation, not a supported API — the exact keystroke sequence can
depend on your Affinity version and on whatever export settings it last
remembered.

Before trusting this unattended, test it on one file: watch what happens
when `EXPORT_KEYSTROKES` fires, and adjust the shortcut or add extra
`window.type_keys(...)` / `time.sleep(...)` steps to match what you
actually see on screen. Once a file's PDF has been exported successfully
one time, the cache logic means Affinity won't need to be touched again
for that product until you edit the source file — so this only has to be
reliable for new or updated artwork, not for every scan.

## How the quantity prompt works

There's no typing required. The same always-focused text box that reads
the artwork barcode also reads the quantity barcode — your scanner sends
the digits and an Enter keystroke automatically, exactly like a keyboard.

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
