<#
.SYNOPSIS
Sync & bootstrap of PBL6 (slr-m2 Pi-split + TTS + stt-app standalone) onto Raspberry Pi 4B.
Supports -FastSync to push only updated Pi runtime scripts, pipeline.py, and sanitized Deepgram settings.json.
#>
[CmdletBinding()]
param(
  [string]$PiHost = "192.168.1.136",
  [string]$PiUser = "pi",
  [switch]$SetupKey,
  [switch]$SkipBootstrap,
  [switch]$Benchmark,
  [switch]$FastSync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$M2Dir = $PSScriptRoot
$SlrM2Root = Split-Path -Parent (Split-Path -Parent $M2Dir)
$Pbl6Root = Split-Path -Parent $SlrM2Root
$TtsParent = Join-Path $Pbl6Root "slr-app\MVP\local_data"
$StandaloneDir = Join-Path $Pbl6Root "stt-app\.next\standalone"
$Target = "${PiUser}@${PiHost}"

$RequiredPaths = @(
  (Join-Path $M2Dir "pipeline.py"),
  (Join-Path $M2Dir "remote_clients.py"),
  (Join-Path $M2Dir "pi_bootstrap.sh"),
  (Join-Path $M2Dir "pi_start.sh"),
  (Join-Path $StandaloneDir "server.js")
)
if (-not $FastSync) {
  $RequiredPaths += @(
    (Join-Path $M2Dir "server.py"),
    (Join-Path $SlrM2Root "models\checkpoints\sl_gcn_bone_07b\07b_bone_seed42\best.pt"),
    (Join-Path $SlrM2Root "outputs\sample_014159_landmarks.npz"),
    (Join-Path $TtsParent "tts")
  )
}
foreach ($p in $RequiredPaths) {
  if (-not (Test-Path $p)) {
    throw "Missing required source artifact: $p"
  }
}

$SlrTar = Join-Path $env:TEMP "slr-m2-pi.tar.gz"
$TtsTar = Join-Path $env:TEMP "pbl6-tts.tar.gz"
$SttTar = Join-Path $env:TEMP "stt-app-standalone.tar.gz"
$TempSettings = Join-Path $env:TEMP "pbl6-settings.json"
$PubKeyPath = Join-Path $HOME ".ssh\id_ed25519.pub"
$WinSettingsPath = Join-Path $env:LOCALAPPDATA "PBL6-STT\settings.json"

try {
  $ScpItems = @()
  $RemoteLines = @("set -euo pipefail")

  if ($SetupKey) {
    if (-not (Test-Path $PubKeyPath)) {
      throw "SSH public key not found: $PubKeyPath"
    }
    $ScpItems += $PubKeyPath
    $RemoteLines += @(
      'mkdir -p ~/.ssh && chmod 700 ~/.ssh',
      'touch ~/.ssh/authorized_keys',
      'tr -d "\r" < /tmp/id_ed25519.pub >> ~/.ssh/authorized_keys',
      'sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys',
      'chmod 600 ~/.ssh/authorized_keys',
      'rm -f /tmp/id_ed25519.pub'
    )
  }

  $SyncedSettings = $false
  if (Test-Path $WinSettingsPath) {
    $SettingsObj = Get-Content $WinSettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $SettingsObj | Add-Member -NotePropertyName "selectedMicrophoneId" -NotePropertyValue "default" -Force
    $SanitizedJson = ($SettingsObj | ConvertTo-Json -Depth 8) + "`n"
    [System.IO.File]::WriteAllText($TempSettings, $SanitizedJson, (New-Object System.Text.UTF8Encoding($false)))
    $ScpItems += $TempSettings
    $RemoteLines += @(
      'mkdir -p ~/.config/pbl6-stt',
      'mv /tmp/pbl6-settings.json ~/.config/pbl6-stt/settings.json',
      'chmod 600 ~/.config/pbl6-stt/settings.json',
      'echo "[OK] Installed sanitized Deepgram settings.json (selectedMicrophoneId=default)"'
    )
    $SyncedSettings = $true
  }

  if ($FastSync) {
    Write-Host "[1/3] Packing stt-app standalone UI & preparing fast sync (SettingsSynced=$SyncedSettings)..."
    & tar -C $StandaloneDir --exclude "*win32*" -czf $SttTar .
    if ($LASTEXITCODE -ne 0) { throw "Failed to create $SttTar" }

    $ScpItems += @(
      $SttTar,
      (Join-Path $M2Dir "pipeline.py"),
      (Join-Path $M2Dir "remote_clients.py"),
      (Join-Path $M2Dir "pi_bootstrap.sh"),
      (Join-Path $M2Dir "pi_start.sh")
    )

    Write-Host "[2/3] Uploading updated UI, runtime scripts, pipeline.py & settings to ${Target}:/tmp/ via scp..."
    & scp @ScpItems "${Target}:/tmp/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed to ${Target}" }

    $LaptopIp = "192.168.1.155"
    if ($PiHost -match '^\d+\.\d+\.\d+\.') {
      $Prefix = $Matches[0]
      $Cand = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
        Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.IPAddressToString.StartsWith($Prefix) } |
        Select-Object -First 1
      if ($Cand) { $LaptopIp = $Cand.IPAddressToString }
    }

    $RemoteLines += @(
      'pkill -f "deployment\.m2\.server" 2>/dev/null || true',
      'pkill -f "next-server" 2>/dev/null || true',
      'pkill -f "PBL6/stt-app/server\.js" 2>/dev/null || true',
      'fuser -k 3100/tcp 2>/dev/null || true',
      'fuser -k 8765/tcp 2>/dev/null || true',
      'sleep 1',
      'rm -rf ~/PBL6/stt-app && mkdir -p ~/PBL6/stt-app ~/PBL6/slr-m2/deployment/m2',
      'tar -C ~/PBL6/stt-app -xzf /tmp/stt-app-standalone.tar.gz && rm -f /tmp/stt-app-standalone.tar.gz',
      'mv /tmp/pipeline.py /tmp/remote_clients.py /tmp/pi_bootstrap.sh /tmp/pi_start.sh ~/PBL6/slr-m2/deployment/m2/',
      "sed -i 's/\r$//' ~/PBL6/slr-m2/deployment/m2/pipeline.py ~/PBL6/slr-m2/deployment/m2/remote_clients.py ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh ~/PBL6/slr-m2/deployment/m2/pi_start.sh",
      'chmod +x ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh ~/PBL6/slr-m2/deployment/m2/pi_start.sh',
      'if [ ! -x "$HOME/pbl6-venv/bin/python" ] || [ ! -x "$HOME/.local/node/bin/node" ]; then bash ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh; fi',
      'echo "=== Pi Hardware Diagnostics ==="',
      'ls -l /dev/video[0-9] 2>/dev/null || echo "NO /dev/video0..9"',
      'command -v lsusb >/dev/null 2>&1 && lsusb || true',
      '(dmesg 2>/dev/null || sudo -n dmesg 2>/dev/null || true) | grep -iE "usb|uvc|video|voltage" | tail -n 15 || true',
      'arecord -l 2>/dev/null || echo "NO ALSA capture devices"',
      "bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh ${LaptopIp}",
      'echo "Active BUILD_ID: $(cat ~/PBL6/stt-app/.next/BUILD_ID)"',
      'echo "Verified UI button: $(curl -fsS http://127.0.0.1:3100/ | grep -o "osk-button" | head -n 1)"',
      'echo "Verified Settings: $(curl -fsS http://127.0.0.1:3100/api/settings)"',
      'echo -n "Verified OSK: "; curl -fsS -X POST http://127.0.0.1:3100/api/osk -H "Origin: http://127.0.0.1:3100" -H "Host: 127.0.0.1:3100" -H "Content-Type: application/json" -d "{\"visible\":false}"; echo ""',
      'echo "Verified VNC (5900): $(ss -tln 2>/dev/null | grep -o ":5900" | head -n 1 || echo "NOT_LISTENING")"'
    )

    $RemoteScript = ($RemoteLines -join "`n") + "`n"
    $B64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($RemoteScript))

    Write-Host "[3/3] Applying fast sync, checking Pi hardware, and restarting services on ${Target}..."
    & ssh $Target "printf '%s' '$B64' | base64 -d | bash -s"
    if ($LASTEXITCODE -ne 0) { throw "Remote fast sync failed on ${Target}" }
  }
  else {
    Write-Host "[1/4] Packing clean .tar.gz archives in `$env:TEMP (SettingsSynced=$SyncedSettings)..."
    & tar -C $SlrM2Root --exclude "__pycache__" -czf $SlrTar deployment models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42 outputs/sample_014159_landmarks.npz
    if ($LASTEXITCODE -ne 0) { throw "Failed to create $SlrTar" }

    & tar -C $TtsParent -czf $TtsTar tts
    if ($LASTEXITCODE -ne 0) { throw "Failed to create $TtsTar" }

    & tar -C $StandaloneDir --exclude "*win32*" -czf $SttTar .
    if ($LASTEXITCODE -ne 0) { throw "Failed to create $SttTar" }

    $ScpItems += @($SlrTar, $TtsTar, $SttTar)

    Write-Host "[2/4] Uploading archives to ${Target}:/tmp/ via scp..."
    & scp @ScpItems "${Target}:/tmp/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed to ${Target}" }

    $RemoteLines += @(
      'pkill -f "deployment\.m2\.server" 2>/dev/null || true',
      'pkill -f "next-server" 2>/dev/null || true',
      'pkill -f "PBL6/stt-app/server\.js" 2>/dev/null || true',
      'fuser -k 3100/tcp 2>/dev/null || true',
      'fuser -k 8765/tcp 2>/dev/null || true',
      'sleep 1',
      'rm -rf ~/PBL6/slr-m2 ~/PBL6/slr-app/MVP/local_data/tts ~/PBL6/stt-app',
      'mkdir -p ~/PBL6/slr-m2 ~/PBL6/slr-app/MVP/local_data ~/PBL6/stt-app',
      'tar -C ~/PBL6/slr-m2 -xzf /tmp/slr-m2-pi.tar.gz',
      'tar -C ~/PBL6/slr-app/MVP/local_data -xzf /tmp/pbl6-tts.tar.gz',
      'tar -C ~/PBL6/stt-app -xzf /tmp/stt-app-standalone.tar.gz',
      'rm -f /tmp/slr-m2-pi.tar.gz /tmp/pbl6-tts.tar.gz /tmp/stt-app-standalone.tar.gz',
      "sed -i 's/\r$//' ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh ~/PBL6/slr-m2/deployment/m2/pi_start.sh",
      'chmod +x ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh ~/PBL6/slr-m2/deployment/m2/pi_start.sh'
    )

    if (-not $SkipBootstrap) {
      $BenchFlag = if ($Benchmark) { " --benchmark" } else { "" }
      $RemoteLines += "bash ~/PBL6/slr-m2/deployment/m2/pi_bootstrap.sh${BenchFlag}"
    }

    $RemoteScript = ($RemoteLines -join "`n") + "`n"
    $B64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($RemoteScript))

    Write-Host "[3/4] Running remote extract & bootstrap on ${Target}..."
    & ssh $Target "printf '%s' '$B64' | base64 -d | bash -s"
    if ($LASTEXITCODE -ne 0) { throw "Remote extract/bootstrap failed on ${Target}" }

    Write-Host "`n[4/4] Done! Next on Pi ($PiHost): bash ~/PBL6/slr-m2/deployment/m2/pi_start.sh" -ForegroundColor Green
  }
}
finally {
  Remove-Item $SlrTar, $TtsTar, $SttTar, $TempSettings -Force -ErrorAction SilentlyContinue
}
