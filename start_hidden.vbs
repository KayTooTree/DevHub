' DEVHUB Autostart-Launcher
' Startet den Server komplett unsichtbar (kein Konsolenfenster)
' und oeffnet danach automatisch das Dashboard im Standardbrowser.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Server im Hintergrund starten (pythonw = ohne Konsolenfenster)
objShell.CurrentDirectory = strPath
objShell.Run "pythonw.exe server.py", 0, False

' Kurz warten bis der Server hochgefahren ist
WScript.Sleep 1800

' Dashboard im Standardbrowser oeffnen
objShell.Run "http://127.0.0.1:5050"
