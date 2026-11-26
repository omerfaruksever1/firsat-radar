@echo off
cd /d "%~dp0"
echo FirsatRadar testleri calisiyor (gercek kayitlara dokunulmaz)...
".venv\Scripts\python.exe" -m pytest tests -q
pause
