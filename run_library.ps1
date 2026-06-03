$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python "library_app.py" --host 127.0.0.1 --port 8010

