# ============================================================================
#  install_background.ps1
#  Registers a hidden, auto-starting Scheduled Task for the lyrics updater.
#
#  Result: widget.py runs via pythonw.exe (no window / taskbar / tray),
#          starts automatically at logon, and restarts itself if it crashes.
#
#  Run it once, from THIS folder, in a normal PowerShell window:
#      .\install_background.ps1
#
#  (No admin needed — it registers under your own user account.)
#  Prerequisite: finish config.json + `python get_spotify_token.py` first, and
#  ideally run `python widget.py` once interactively to confirm it works.
# ============================================================================
$ErrorActionPreference = "Stop"

$taskName  = "SpotifyLyricsWidget"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$widget    = Join-Path $scriptDir "widget.py"

if (-not (Test-Path $widget)) { throw "widget.py not found at $widget" }

# --- Resolve pythonw.exe (it sits next to python.exe; works for Store + normal installs) ---
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw "Could not find python on PATH. Open a new shell after installing Python and retry." }

$pythonw = Join-Path (Split-Path -Parent $python) "pythonw.exe"
if (-not (Test-Path $pythonw)) {
    # Ask the interpreter itself where it lives (handles Store-Python redirects).
    $exe = & $python -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"
    if ($exe -and (Test-Path $exe)) { $pythonw = $exe } else { throw "Could not locate pythonw.exe near $python" }
}

Write-Host "pythonw : $pythonw"
Write-Host "widget  : $widget"
Write-Host ""

# --- Replace any previous version of the task ---
Stop-ScheduledTask  -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction -Execute $pythonw -Argument ('"{0}"' -f $widget) -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew
# Interactive logon type = runs in your session with no stored password, no admin.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Realtime Spotify lyrics -> Discord profile widget (hidden background updater)." | Out-Null

Start-ScheduledTask -TaskName $taskName

Write-Host "Installed and started '$taskName'."
Write-Host "It now runs hidden and auto-starts at every logon."
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Status :  Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo"
Write-Host "  Logs   :  Get-Content -Wait `"$scriptDir\widget.log`""
Write-Host "  Stop   :  Stop-ScheduledTask -TaskName $taskName"
Write-Host "  Remove :  .\uninstall_background.ps1"
