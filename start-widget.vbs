' ============================================================================
'  start-widget.vbs  —  launch the Spotify lyrics updater with NO window.
'
'  Runs widget.py via pythonw.exe (which has no console), completely hidden:
'  no console window, no taskbar button, no system-tray icon.
'
'  Two ways to use it:
'    1. Double-click it to start the updater in the background right now.
'    2. Auto-start at logon: press Win+R, type  shell:startup , Enter, and drop
'       a SHORTCUT to this file into the folder that opens.
'
'  To stop it later: open Task Manager -> Details -> end "pythonw.exe".
'  To check it's alive: look at widget.log next to this file.
' ============================================================================
Option Explicit
Dim sh, scriptDir
Set sh = CreateObject("WScript.Shell")

' Folder this .vbs lives in (includes the trailing backslash).
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.CurrentDirectory = scriptDir

' 0 = hidden window, False = don't wait for it to exit.
sh.Run "pythonw.exe """ & scriptDir & "widget.py""", 0, False
