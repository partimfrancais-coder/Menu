@echo off
cd /d "%~dp0"
if exist "C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe" (
  "C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe" server.py
) else (
  py -3 server.py
)
pause
