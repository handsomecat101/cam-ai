$ErrorActionPreference = 'Continue'
$py   = 'H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$root = 'H:\AI Project\cam-ai'
$out  = Join-Path $root '_kk_out\pc_audit\C1_tools_phu'
New-Item -ItemType Directory -Force -Path $out | Out-Null

Write-Host '===== C1: dang_ky_anh.py (dang ky nguoi quen tu video) ====='
$o = & $py -W ignore (Join-Path $root 'dang_ky_anh.py') --input (Join-Path $root 'video_test.mp4') --names 'An,Binh' --out (Join-Path $out 'known_faces_moi') 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | ForEach-Object { "  $_" }
Write-Host '--- file tao ra ---'
Get-ChildItem (Join-Path $out 'known_faces_moi') -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { "  $($_.FullName.Replace($root,'')) | $($_.Length) bytes" }

Write-Host ''
Write-Host '===== C2: ve_vung.py --manual (ve vung canh tu video) ====='
$o = "0.2 0.15 0.8 0.95" | & $py -W ignore (Join-Path $root 've_vung.py') --input (Join-Path $root 'video_test.mp4') --out (Join-Path $out 'vung_moi.txt') --manual 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | ForEach-Object { "  $_" }
if (Test-Path (Join-Path $out 'vung_moi.txt')) {
  Write-Host '  --- noi dung vung_moi.txt ---'
  Get-Content (Join-Path $out 'vung_moi.txt') | ForEach-Object { "  $_" }
}

Write-Host ''
Write-Host '===== C2b: app.py dung vung vua ve (kiem chung vung moi doc duoc) ====='
$o = & $py -W ignore (Join-Path $root 'app.py') --input (Join-Path $root 'video_test.mp4') --vung (Join-Path $out 'vung_moi.txt') --output (Join-Path $out 'C2b_ket_qua') 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | Select-Object -Last 8 | ForEach-Object { "  $_" }

Write-Host ''
Write-Host '===== C3: bao_cao_tong_ket.py (xuat Excel + HTML) ====='
$csv = Join-Path $root '_kk_out\gui_e2e\video_test_bao_cao.csv'
$mp4 = Join-Path $root '_kk_out\gui_e2e\video_test_ket_qua.mp4'
$o = & $py -W ignore (Join-Path $root 'bao_cao_tong_ket.py') --csv $csv --video $mp4 --xuat $out 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | ForEach-Object { "  $_" }
Get-ChildItem $out -File | Where-Object { $_.Extension -in '.xlsx','.html' } | ForEach-Object { "  FILE: $($_.Name) $($_.Length) bytes" }
Write-Host 'HET TOOLS PHU 2'
