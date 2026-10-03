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
$backend = Join-Path $root "backend"
while ($true) {
    Add-Content -Encoding UTF8 $log "$(Get-Date -Format s) starting the UVERA API"
    # cmd.exe redirection keeps the log plain UTF-8 (PowerShell 5.1 redirection would write UTF-16)
    cmd /c "`"$python`" -m uvicorn app.main:app --app-dir `"$backend`" --host 127.0.0.1 --port 8000 >> `"$log`" 2>&1"
    Add-Content -Encoding UTF8 $log "$(Get-Date -Format s) the API stopped (exit $LASTEXITCODE); restarting in 5 seconds"
    Start-Sleep -Seconds 5
}
