@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [LOI] Khong tim thay .venv\Scripts\python.exe
  echo       Hay chay lai may nay voi Python 3.13 roi tao lai venv.
  echo.
  pause
  exit /b 1
)

echo.
echo === CamAI - dang mo cua so giao dien ===
echo.

.venv\Scripts\python.exe gui.py

echo.
pause