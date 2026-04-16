"""Launcher sem terminal - executa main.py usando pythonw (sem janela de console)."""

import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
venv_pythonw = os.path.join(script_dir, "venv", "Scripts", "pythonw.exe")
main_py = os.path.join(script_dir, "main.py")
log_file = os.path.join(script_dir, "assistant.log")

# Usar pythonw do venv se existir, senao o do sistema
if not os.path.exists(venv_pythonw):
    venv_pythonw = "pythonw.exe"

# Repassar argumentos da linha de comando
args = [venv_pythonw, main_py] + sys.argv[1:]

with open(log_file, "w") as log:
    subprocess.Popen(args, stdout=log, stderr=log, cwd=script_dir)
