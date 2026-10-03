# Starts the UVERA API on this Windows computer and restarts it if it ever stops.
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_api.ps1
# Expects the virtual environment in .venv (see README: Installation and setup). Settings come from .env in the repo root.
# The API listens on 127.0.0.1 only; a tunnel (Tailscale Funnel or Cloudflare) makes it public, no open ports needed.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$log = Join-Path $root "_outputs\api.log"
New-Item -ItemType Directory -Force (Join-Path $root "_outputs") | Out-Null
if (-not (Test-Path $python)) { Write-Error "No .venv found in $root. Create it first (README: Installation and setup)."; exit 1 }
$env:PYTHONIOENCODING = "utf-8"
while ($true) {
    Add-Content $log "$(Get-Date -Format s) starting the UVERA API"
    & $python -m uvicorn app.main:app --app-dir (Join-Path $root "backend") --host 127.0.0.1 --port 8000 *>> $log
    Add-Content $log "$(Get-Date -Format s) the API stopped (exit $LASTEXITCODE); restarting in 5 seconds"
    Start-Sleep -Seconds 5
}
