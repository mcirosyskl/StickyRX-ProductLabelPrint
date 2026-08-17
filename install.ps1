# ---------------------------------------------------------------
# install.ps1
# One-time installer for Product Label Print.
# Run this as Administrator from the folder containing all the
# project files (launcher.py, setup_config.py, generate_barcode.py,
# print_listener.py, config.json, StickyRxLogo.jpg).
# ---------------------------------------------------------------

$InstallDir = "C:\Program Files\KanbanLabelPrinter"

Write-Host "== Product Label Print - Installer ==" -ForegroundColor Cyan

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

$pythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($pythonwCmd) {
    $pythonwPath = $pythonwCmd.Source
} else {
    $pythonwPath = (Get-Command python).Source
}

$shortcut = $WshShell.CreateShortcut("$Desktop\Product Label Print.lnk")
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$InstallDir\launcher.py`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Save()
Write-Host "  Created shortcut: Product Label Print"

Write-Host "`n== Install complete ==" -ForegroundColor Green
Write-Host "Installed to: $InstallDir"
Write-Host "Next step: double-click the 'Product Label Print' shortcut on your Desktop,"
Write-Host "click Setup Config first, and confirm your printer name, label size, and app paths."
