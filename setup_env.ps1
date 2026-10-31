# ==============================================================================
# Avatar2 OxxxSec - Automated Virtual Environment Setup (PowerShell)
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  🚀 Avatar2 Master Playbook - Virtual Environment Setup (PowerShell)  " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$VenvDir = Join-Path $PSScriptRoot ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[*] Creating Python virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Failed to create virtual environment! Ensure Python 3.8+ is installed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[+] Virtual environment already exists." -ForegroundColor Green
}

Write-Host "[*] Upgrading pip, setuptools, and wheel..." -ForegroundColor Yellow
& $PythonExe -m pip install --upgrade pip "setuptools<70" wheel

Write-Host "[*] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $PythonExe -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

Write-Host "[*] Running verification suite..." -ForegroundColor Yellow
& $PythonExe (Join-Path $PSScriptRoot "verify_all.py")

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[+] Environment setup completed successfully!" -ForegroundColor Green
    Write-Host "[*] To activate: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
} else {
    Write-Host "`n[-] Verification reported issues. Please check logs above." -ForegroundColor Red
}
