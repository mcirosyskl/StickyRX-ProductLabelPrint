# ---------------------------------------------------------------
# install.ps1
# One-time installer for ProductLabelPrint.
# Run this as Administrator from the folder containing all the
# project files (launcher.py, setup_config.py, generate_barcode.py,
# print_listener.py, config.json, StickyRxLogo.jpg).
#
# NOTE: $InstallDir below is intentionally left at its original path
# (C:\Program Files\KanbanLabelPrinter) rather than renamed to match
# the new "ProductLabelPrint" name, so this doesn't break your existing
# live install or its Git connection. Everything the user actually
# sees - the app window title, the Desktop shortcut, this installer's
# own messages - now says "ProductLabelPrint". Let me know if you'd
# like the install folder itself renamed too; it's doable, just needs
# some care around the Git remote pointed at that folder.
# ---------------------------------------------------------------

$InstallDir = "C:\Program Files\KanbanLabelPrinter"

Write-Host "== ProductLabelPrint - Installer ==" -ForegroundColor Cyan

# ---------------------------------------------------------------
# 1. Check for Python; install if missing
# ---------------------------------------------------------------
Write-Host "`nChecking for Python..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCmd) {
    Write-Host "Python not found - installing via winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --scope machine --override "/quiet InstallAllUsers=1 PrependPath=1"
    Write-Host "Python installed. You may need to close and reopen this window for PATH changes to take effect." -ForegroundColor Yellow
} else {
    Write-Host "Python found: $($pythonCmd.Source)"
}

# ---------------------------------------------------------------
# 2. Copy project files to the install directory
# ---------------------------------------------------------------
Write-Host "`nInstalling to $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$filesToCopy = @(
    "launcher.py",
    "setup_config.py",
    "generate_barcode.py",
    "print_listener.py",
    "config.json",
    "StickyRxLogo.jpg"
)

foreach ($file in $filesToCopy) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination $InstallDir -Force
        Write-Host "  Copied: $file"
    } else {
        Write-Host "  Skipped (not found next to installer): $file" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------
# 3. Install required Python packages
# ---------------------------------------------------------------
Write-Host "`nInstalling required Python packages..."
& python -m pip install --upgrade pip
& python -m pip install pywin32 pywinauto python-barcode pillow

# ---------------------------------------------------------------
# 4. Create a Desktop shortcut for the launcher
# ---------------------------------------------------------------
Write-Host "`nCreating desktop shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")

# Use pythonw.exe specifically (not python.exe) so no console window
# appears alongside the app - this is also enforced defensively inside
# launcher.py itself now, in case anyone creates their own shortcut
# straight to the .py file instead of using this one.
$pythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($pythonwCmd) {
    $pythonwPath = $pythonwCmd.Source
} else {
    $pythonwPath = (Get-Command python).Source
}

# Remove any old "Product Label Print" shortcut (previous naming) so it
# doesn't sit next to the new one and cause confusion.
$oldShortcutPath = "$Desktop\Product Label Print.lnk"
if (Test-Path $oldShortcutPath) {
    Remove-Item $oldShortcutPath -Force
    Write-Host "  Removed old shortcut: Product Label Print"
}

$shortcut = $WshShell.CreateShortcut("$Desktop\ProductLabelPrint.lnk")
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$InstallDir\launcher.py`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Save()
Write-Host "  Created shortcut: ProductLabelPrint"

Write-Host "`n== Install complete ==" -ForegroundColor Green
Write-Host "Installed to: $InstallDir"
Write-Host "Next step: double-click the 'ProductLabelPrint' shortcut on your Desktop,"
Write-Host "click Setup Config first, and confirm your printer name, label size, and app paths."
Write-Host ""
Write-Host "IMPORTANT: If you have an existing Desktop shortcut named 'launcher.py - Shortcut'"
Write-Host "(created by right-clicking launcher.py and choosing 'Create shortcut'), delete it"
Write-Host "and use only the 'ProductLabelPrint' shortcut above. That other shortcut points"
Write-Host "directly at the .py file, which Windows opens with a console window attached -"
Write-Host "that's the extra window that stays open and closes the app when you close it." -ForegroundColor Yellow
