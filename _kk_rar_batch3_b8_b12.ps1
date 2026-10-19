$ErrorActionPreference = 'Continue'
$py  = 'H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$root = 'H:\AI Project\cam-ai'
$base = Join-Path $root '_kk_out\pc_audit'

function Run-Case($ten, $extra, $cwd) {
    $out = Join-Path $base $ten
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $args = "import os,sys,runpy; sys.path.insert(0, r'$root'); os.chdir(r'$cwd'); sys.argv=['app.py','--input',r'$root\video_test.mp4','--output',r'$out\ket_qua'] + $extra; runpy.run_path(r'$root\app.py', run_name='__main__')"
    $log = & $py -W ignore -c $args 2>&1
    $ec = $LASTEXITCODE
    Write-Host "===== $ten EXIT=$ec ====="
    $log | Select-String -Pattern '\[video\]|\[bien so\]|\[bien_so\]|\[tuc chup\]|\[tu chup\]|\[canh bao\]|\[loi\]|WARNING|khong doc duoc|OCR' | Select-Object -Last 20 | ForEach-Object { $_.Line }
    $mp4 = Join-Path $out 'ket_qua_ket_qua.mp4'
    if (Test-Path $mp4) {
        $len = (Get-Item $mp4).Length
        $probe = & ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 $mp4
        Write-Host "  MP4: $len bytes | $probe"
    } else {
        Write-Host "  MP4: KHONG CO"
    }
    $csv = Join-Path $out 'ket_qua_bao_cao.csv'
    if (Test-Path $csv) {
        $lines = (Get-Content $csv).Count
        Write-Host "  CSV: $lines dong"
    } else { Write-Host "  CSV: KHONG CO" }
    Get-ChildItem $out -Filter '*.jpg' | ForEach-Object { Write-Host "  JPG: $($_.Name) $($_.Length) bytes" }
    Get-ChildItem $out -Filter '*.mp4' | ForEach-Object { Write-Host "  MP4file: $($_.Name) $($_.Length) bytes" }
}

Run-Case 'B8_min_face_40'      "['--min-face','40']" 'C:\Windows'
Run-Case 'B9_vung_bien_so'     "['--doc-bien-so','--vung-bien-so','0.1,0.3,0.9,0.8']" 'C:\Windows'
Run-Case 'B10_tu_chup'         "['--tu-chup','--tu-chup-dir',r'$base\B10_tu_chup\anh','--tu-chup-nhoan-lai-giay','5']" 'C:\Windows'
Run-Case 'B11_bien_so_tin_cay' "['--doc-bien-so','--bien-so-tin-cay','0.7','--bien-so-nhoan-lai-giay','10']" 'C:\Windows'
Run-Case 'B12_pixelate_vung'   "['--pixelate','--vung',r'$root\vung.txt']" 'C:\Windows'
Write-Host "HET BATCH B8-B12"
