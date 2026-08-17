<#
install.ps1
-----------
Installer for the Kanban Label Print System.

What this does:
  1. Checks whether Python is already installed and on PATH.
     If not, downloads and silently installs Python 3.12 with
     "Add to PATH" enabled, so you never have to fight PATH issues
     like we did on the first workstation.
  2. Copies setup_config.py, generate_barcode.py, print_listener.py,
     config.json, and README.md into C:\Program Files\KanbanLabelPrinter.
  3. Installs the required Python packages (pywin32, pywinauto,
     python-barcode, pillow).
  4. Creates three Desktop shortcuts:
        - Label System Setup     (run this first)
        - Barcode Generator
        - Label Print Station    (leave running at the scan station)

How to run it:
  Right-click install.ps1 and choose "Run with PowerShell" - if that
  doesn't offer Administrator, instead open PowerShell as Administrator
  and run:
      powershell -ExecutionPolicy Bypass -File "C:\path\to\install.ps1"

  This MUST be run as Administrator, since it installs to Program Files.

Before running: put install.ps1 in the SAME folder as setup_config.py,
generate_barcode.py, print_listener.py, config.json, and README.md -
the installer copies its neighbors, it doesn't download anything except
the Python installer itself (only if Python isn't already present).
#>

$ErrorActionPreference = "Stop"

$InstallDir = "C:\Program Files\KanbanLabelPrinter"
# If you'd rather install a different Python version, change this URL to
# match the "Windows installer (64-bit)" link for that version from
# https://www.python.org/downloads/windows/
$PythonInstallerUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
$PythonInstallerPath = "$env:TEMP\python-installer.exe"

function Test-IsAdmin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "This script needs to run as Administrator (it installs to Program Files)." -ForegroundColor Yellow
    Write-Host "Right-click install.ps1 -> Run as administrator, then try again."
    exit 1
}

Write-Host "== Kanban Label Print System - Installer ==" -ForegroundColor Cyan

# ---------------------------------------------------------------
# 1. Check for Python; install it if missing
# ---------------------------------------------------------------
Write-Host "`nChecking for Python..."
$havePython = $false
try {
    $version = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Found: $version"
        $havePython = $true
    }
} catch {}

if (-not $havePython) {
    Write-Host "Python not found on PATH. Downloading and installing Python..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $PythonInstallerUrl -OutFile $PythonInstallerPath
    Write-Host "Installing Python silently (this can take a minute)..."
    # InstallAllUsers + PrependPath means every account on this PC can run
    # "python" from any prompt afterward - this is the step that was
    # missing on the first workstation.
    Start-Process -FilePath $PythonInstallerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
    Remove-Item $PythonInstallerPath -ErrorAction SilentlyContinue

    # Refresh PATH in this session so the rest of the script can call
    # "python" immediately without closing PowerShell.
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

    try {
        $version = & python --version 2>&1
        Write-Host "Installed: $version"
    } catch {
        Write-Host "Python installed, but this PowerShell window can't see it yet." -ForegroundColor Yellow
        Write-Host "Close this window, reopen PowerShell as Administrator, and run install.ps1 again to finish."
        exit 1
    }
}

# ---------------------------------------------------------------
# 2. Create install directory and copy files
# ---------------------------------------------------------------
Write-Host "`nInstalling to $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesToCopy = @("launcher.py", "setup_config.py", "generate_barcode.py", "print_listener.py", "config.json", "README.md", "StickyRxLogo.jpg")
foreach ($file in $filesToCopy) {
    $source = Join-Path $ScriptRoot $file
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination $InstallDir -Force
        Write-Host "  Copied $file"
    } else {
        Write-Host "  Warning: $file not found next to install.ps1 - skipped." -ForegroundColor Yellow
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

$shortcut = $WshShell.CreateShortcut("$Desktop\Kanban Label Printer.lnk")
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$InstallDir\launcher.py`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Save()
Write-Host "  Created shortcut: Kanban Label Printer"

Write-Host "`n== Install complete ==" -ForegroundColor Green
Write-Host "Installed to: $InstallDir"
Write-Host "Next step: double-click the 'Kanban Label Printer' shortcut on your Desktop,"
Write-Host "click SETUP CONFIG first, and confirm your printer name, label size, and app paths."
