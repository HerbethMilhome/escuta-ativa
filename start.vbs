Set objShell = CreateObject("WScript.Shell")
strDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strDir
objShell.Run """" & strDir & "\venv312\Scripts\pythonw.exe"" """ & strDir & "\main.py"" --model small", 0, False
