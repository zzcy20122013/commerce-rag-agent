$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "web-debug"

Push-Location $web
try {
  & npm.cmd run dev -- --host 127.0.0.1
}
finally {
  Pop-Location
}
