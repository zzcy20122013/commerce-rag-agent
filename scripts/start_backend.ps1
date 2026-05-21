$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
  $python = "python"
}

Push-Location $backend
try {
  & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
finally {
  Pop-Location
}
