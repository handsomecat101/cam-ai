@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%~1"=="" (
  set /p VIDEO=Nhap duong dan video (hoac keo file .mp4 vao shortcut nay): 
) else (
  set VIDEO=%~1
)

echo.
echo === Dang xu ly: %VIDEO% ===
echo.

.venv\Scripts\python.exe app.py --input "%VIDEO%"

echo.
pause