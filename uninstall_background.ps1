# ============================================================================
#  uninstall_background.ps1
#  Stops and removes the SpotifyLyricsWidget scheduled task.
#      .\uninstall_background.ps1
# ============================================================================
$ErrorActionPreference = "Stop"
$taskName = "SpotifyLyricsWidget"

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Removed '$taskName' (if it existed)."
Write-Host "If an instance is still running, end 'pythonw.exe' in Task Manager -> Details."
