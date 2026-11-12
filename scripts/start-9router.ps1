# Start 9Router on localhost only. Idempotent: exits if the port is already open.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$gw = Join-Path $root "gateway"
New-Item -ItemType Directory -Force $gw | Out-Null

$pwFile = Join-Path $gw ".9router-password"
if (-not (Test-Path $pwFile)) {
    $pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    Set-Content -Path $pwFile -Value $pw -NoNewline
    Write-Host "Generated dashboard password: $pwFile"
}
$env:INITIAL_PASSWORD = (Get-Content $pwFile -Raw).Trim()

if (Test-NetConnection 127.0.0.1 -Port 20128 -InformationLevel Quiet) {
    Write-Host "9Router already running at http://127.0.0.1:20128"
    exit 0
}

$cli = Join-Path $env:APPDATA "npm\9router.cmd"
if (-not (Test-Path $cli)) {
    Write-Host "9router.cmd not found. Run: npm install -g 9router"
    exit 1
}

Start-Process -FilePath $cli `
    -ArgumentList "--host", "127.0.0.1", "--port", "20128", "--no-browser", "--skip-update", "--log" `
    -WorkingDirectory $gw `
    -RedirectStandardOutput (Join-Path $gw "9router.out.log") `
    -RedirectStandardError (Join-Path $gw "9router.err.log") `
    -WindowStyle Hidden

Start-Sleep -Seconds 15
if (-not (Test-NetConnection 127.0.0.1 -Port 20128 -InformationLevel Quiet)) {
    Write-Host "9Router did not start. See gateway\9router.err.log"
    exit 1
}
Write-Host "9Router up: http://127.0.0.1:20128 (dashboard: /dashboard)"

# 9Router uses INITIAL_PASSWORD from the environment until a hash is stored in
# settings, and shows a "no password set" warning in that state. Persist the
# generated password once so the dashboard is authenticated by a real hash.
$marker = Join-Path $gw ".9router-hashed"
$setter = Join-Path $gw "set-password.js"
if (-not (Test-Path $marker) -and (Test-Path $setter)) {
    node $setter 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $marker -Value "ok" -NoNewline }
}
