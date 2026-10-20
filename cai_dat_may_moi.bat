@echo off
REM ==========================================================================
REM  CamAI - CAI DAT TREN MAY MOI (chi can chay 1 lan)
REM  Tao .venv, cai thu vien, tai model YOLO + model khuon mat.
REM  File nay chi dung KY TU ASCII de moi Windows hien thi dung.
REM ==========================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === CamAI - Cai dat tren may moi ===
echo.

python --version >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong chay duoc lenh "python".
    echo        Hay cai Python 3.13 tu https://www.python.org/downloads/
    echo        va tick "Add python.exe to PATH" khi cai dat.
    echo.
    py -3 --version >nul 2>nul
    if errorlevel 1 (
        echo [LOI] Khong tim thay "py" launcher. Can Python truoc khi chay script nay.
    ) else (
        py -3 cai_dat_may_moi.py
    )
) else (
    python cai_dat_may_moi.py
)

echo.
echo === Ket thuc cai dat. Bam phim bat ky de dong cua so nay. ===
echo.
pause
endlocal
