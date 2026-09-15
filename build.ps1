# Gera dist\GridNote.exe. Uso: powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt pyinstaller

& $py -m unittest discover tests
if ($LASTEXITCODE -ne 0) { throw "Testes falharam; build cancelado." }

& $py tools\make_icon.py
& $py -m PyInstaller --noconfirm --clean gridnote.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }

$exe = Get-Item "dist\GridNote.exe"
"Pronto: $($exe.FullName) ({0:N1} MB)" -f ($exe.Length / 1MB)
