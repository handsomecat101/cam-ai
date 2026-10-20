@echo off
REM ==========================================================================
REM  CamAI - MO APP (ban co hien cua so lenh, de xem loi neu app khong mo)
REM  Click de mo CamAI. Dong cua so nay sau khi app da mo.
REM ==========================================================================
setlocal
set "THU_MUC=%~dp0"
set "PYTHON=%THU_MUC%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [LOI] Khong tim thay Python trong .venv:
    echo        "%PYTHON%"
    echo.
    echo Hay chay lai "Mo CamAI.vbs" hoac doi lai ban cai dat.
    pause
    exit /b 1
)

cd /d "%THU_MUC%"
start "" "%PYTHON%" gui.py
endlocal
