$ErrorActionPreference = 'Continue'
$py   = 'H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$root = 'H:\AI Project\cam-ai'
$out  = Join-Path $root '_kk_out\pc_audit\C1_tools_phu'
New-Item -ItemType Directory -Force -Path $out | Out-Null

Write-Host '===== C1: dang_ky_anh.py (dang ky nguoi quen tu video) ====='
$o = & $py -W ignore (Join-Path $root 'dang_ky_anh.py') --input (Join-Path $root 'video_test.mp4') --names 'An,Binh' --out (Join-Path $out 'known_faces_moi') 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | Select-Object -Last 12 | ForEach-Object { $_.ToString() }
Get-ChildItem (Join-Path $out 'known_faces_moi') -Recurse -ErrorAction SilentlyContinue | ForEach-Object { "  $($_.FullName.Replace($root,'')) $($_.Length) bytes" }

Write-Host ''
Write-Host '===== C2: ve_vung.py (ve vung canh tu video) ====='
$o = & $py -W ignore (Join-Path $root 've_vung.py') --input (Join-Path $root 'video_test.mp4') --out (Join-Path $out 'vung_moi.txt') 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | Select-Object -Last 10 | ForEach-Object { $_.ToString() }
if (Test-Path (Join-Path $out 'vung_moi.txt')) {
  Write-Host '  --- noi dung vung.txt ---'
  Get-Content (Join-Path $out 'vung_moi.txt') | ForEach-Object { "  $_" }
}

Write-Host ''
Write-Host '===== C3: bao_cao_tong_ket.py (xuat Excel + HTML) ====='
$csv = Join-Path $root '_kk_out\gui_e2e\video_test_bao_cao.csv'
$mp4 = Join-Path $root '_kk_out\gui_e2e\video_test_ket_qua.mp4'
$o = & $py -W ignore (Join-Path $root 'bao_cao_tong_ket.py') --csv $csv --video $mp4 --xuat $out 2>&1
Write-Host "EXIT=$LASTEXITCODE"
$o | Select-Object -Last 12 | ForEach-Object { $_.ToString() }
Get-ChildItem $out -Filter '*.xlsx' | ForEach-Object { "  XLSX: $($_.Name) $($_.Length) bytes" }
Get-ChildItem $out -Filter '*.html' | ForEach-Object { "  HTML: $($_.Name) $($_.Length) bytes" }
Write-Host 'HET TOOLS PHU'
