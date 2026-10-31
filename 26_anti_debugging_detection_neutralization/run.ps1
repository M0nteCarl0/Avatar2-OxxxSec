# Quick launcher for post 26: Embedded Anti-Debugging Detection & Neutralization
# Usage: .\run.ps1   (extra arguments are forwarded to example.py)
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

$PythonExe = "python"
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    $PythonExe = "python3"
}
foreach ($Candidate in @(
    (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
    (Join-Path $RepoRoot ".venv/bin/python")
)) {
    if (Test-Path $Candidate) {
        $PythonExe = $Candidate
        break
    }
}

Push-Location $ScriptDir
try {
    & $PythonExe "example.py" @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
