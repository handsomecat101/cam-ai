$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'
$py = 'H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$root = 'H:\AI Project\cam-ai'
$log = Join-Path $root '_kk_out\kiem_giao_dien\hoi_quy_34.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"" | Set-Content -Path $log -Encoding UTF8

function Run-Suite ($ten, $file) {
    Write-Output "" | Out-Null
    Write-Output "=== $ten ===" | Tee-Object -FilePath $log -Append
    & $py -W ignore (Join-Path $root $file) 2>&1 | Tee-Object -FilePath $log -Append |
        Select-String -Pattern 'PASS|FAIL|TONG KET|KET QUA|EXIT|error|Error|Traceback' |
        Select-Object -First 40 | ForEach-Object { $_.Line }
    Write-Output "EXIT_$ten=$LASTEXITCODE" | Tee-Object -FilePath $log -Append
}

Run-Suite 'A_E2E_7'    '_kk_kiem_gui_chay_thuc.py'
Run-Suite 'B_B3_4'     '_kk_kiem_gui_b3.py'
Run-Suite 'C_PREVIEW'  '_kk_kiem_gui_batch_preview.py'
Run-Suite 'D_EN'       '_kk_kiem_ngon_ngu_v3_3.py'
Run-Suite 'E_DESIGN'   '_kk_kiem_giao_dien.py'
Run-Suite 'F_CANVAS'   '_kk_kiem_canvas_vung.py'

Write-Output "" | Out-Null
Write-Output "=== TOM TAT ===" | Tee-Object -FilePath $log -Append
Select-String -Path $log -Pattern 'EXIT_' | ForEach-Object { $_.Line } | Tee-Object -FilePath $log -Append
