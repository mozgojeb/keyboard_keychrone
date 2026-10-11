# Build Keyboard Companion as a PyInstaller onedir folder (+ optional zip).
#
# Usage (PowerShell, from this folder):
#   .\build_exe.ps1            # dist\KeyboardCompanion\ + dist\KeyboardCompanion-v<ver>-win64.zip
#   .\build_exe.ps1 -Clean     # remove previous build artifacts first
#
param([switch]$Clean)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Prefer a stable Python 3.13 install for PyInstaller builds (3.14 has
# intermittent crashes even with JIT disabled). Fall back to whatever
# "python" points to if 3.13 is not available.
$PythonExe = "C:\Python313\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$InitPy = Join-Path $PSScriptRoot "keeb_assistant\__init__.py"
if (-not (Test-Path $InitPy)) {
    Write-Error "Missing $InitPy (cannot read __version__ for the zip name)."
}
$Version = (Select-String -Path $InitPy -Pattern '^\s*__version__\s*=\s*"([^"]+)"').Matches.Groups[1].Value
if (-not $Version) {
    Write-Error "Could not parse __version__ from $InitPy"
}

$AppDir = "dist\KeyboardCompanion"
$AppExe = "$AppDir\KeyboardCompanion.exe"
$ZipPath = "dist\KeyboardCompanion-v$Version-win64.zip"

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    Remove-Item -Force *.spec -ErrorAction SilentlyContinue
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt pyinstaller

& $PythonExe -c "import tkinter, _tkinter; print('Tk runtime:', tkinter.TkVersion)"
if ($LASTEXITCODE -ne 0) { throw 'Python must include tkinter before building.' }

# Python 3.14's experimental JIT crashes PyInstaller's module analysis.
# When building with 3.13 this env var is harmless; with 3.14 it makes
# the build more reliable.
$env:PYTHON_JIT = "0"

# Regenerate the app icon (battery glyph) if missing.
if (-not (Test-Path assets\app.ico)) { & $PythonExe make_app_icon.py }

# PyInstaller prints its INFO log to stderr. With $ErrorActionPreference="Stop"
# (and PS 7.4+ defaults) PowerShell would treat that as a fatal error and abort,
# so relax it for the native build and check the exit code ourselves instead.
$ErrorActionPreference = "Continue"

# onedir: a normal exe + bundled deps in the same folder (no temp self-extract).
# --noupx avoids UPX compression, which AV heuristics often flag.
# --collect-all bundles the hidapi DLL and the pystray win32 backend.
& $PythonExe -m PyInstaller --noconfirm --noconsole --onedir --noupx `
    --name KeyboardCompanion `
    --icon assets\app.ico `
    --version-file version_info.txt `
    --collect-all hid `
    --collect-all pystray `
    --hidden-import tkinter `
    --hidden-import tkinter.ttk `
    --hidden-import tkinter.colorchooser `
    --hidden-import tkinter.messagebox `
    --hidden-import tkinter.filedialog `
    --add-binary "vendor\qmk_flashutils\dfu-util.exe;." `
    --add-data "KeyboardBatteryWidget.ps1;." `
    run_tray.py

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $AppExe)) {
    Write-Error "Build failed (PyInstaller exit code $LASTEXITCODE)."
    exit 1
}

if (-not (Test-Path "$AppDir\_internal\_tkinter.pyd") -or
    -not (Test-Path "$AppDir\_internal\_tcl_data\init.tcl") -or
    -not (Test-Path "$AppDir\_internal\_tk_data\tk.tcl")) {
    throw 'Build is missing the Tk UI runtime; do not distribute this package.'
}

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Done."
Write-Host "  Run:       $AppExe"
Write-Host "  Folder:    $AppDir  (keep all files together)"
Write-Host "  Zip:       $ZipPath  (for distribution)"
