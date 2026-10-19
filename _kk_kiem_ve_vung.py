"""Kiem chung that ve_vung.py (che do --manual) + app.py doc duoc vung do.

Chay: .venv\\Scripts\\python.exe _kk_kiem_ve_vung.py
"""
import os
import subprocess
import sys

ROOT = r"H:\AI Project\cam-ai"
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
OUT = os.path.join(ROOT, "_kk_out", "pc_audit", "C1_tools_phu")
VUNG = os.path.join(OUT, "vung_moi.txt")
VIDEO = os.path.join(ROOT, "video_test.mp4")
TOA_DO = "0.2 0.15 0.8 0.95\n"

os.makedirs(OUT, exist_ok=True)


def chay(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=ROOT, **kw)
    return p


print("=" * 60)
print("C2: ve_vung.py --manual (nhan toa do qua stdin)")
p = chay([PY, "-W", "ignore", os.path.join(ROOT, "ve_vung.py"),
          "--input", VIDEO, "--out", VUNG, "--manual"], input=TOA_DO)
print(p.stdout)
if p.stderr.strip():
    print("[stderr]", p.stderr.strip()[:800])
print("EXIT =", p.returncode)

if not os.path.isfile(VUNG):
    print("KET QUA: FAIL - khong tao duoc file vung")
    sys.exit(1)

with open(VUNG, "r", encoding="utf-8") as f:
    noi_dung = f.read()
print("--- noi dung vung_moi.txt ---")
for dong in noi_dung.splitlines():
    print("   ", dong)

so = [d for d in noi_dung.splitlines() if d.strip() and not d.startswith("#")]
if len(so) != 1:
    print("KET QUA: FAIL - file vung khong co dung 1 dong toa do")
    sys.exit(1)
x1, y1, x2, y2 = (float(v) for v in so[0].split())
print(f"toa do doc duoc: x1={x1} y1={y1} x2={x2} y2={y2}")
if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
    print("KET QUA: FAIL - toa do ngoai [0,1] hoac x1>=x2")
    sys.exit(1)

print()
print("=" * 60)
print("C2b: app.py --vung vung_moi.txt (kiem chung app doc duoc vung)")
p2 = chay([PY, "-W", "ignore", os.path.join(ROOT, "app.py"),
           "--input", VIDEO, "--vung", VUNG,
           "--output", os.path.join(OUT, "C2b_ket_qua")])
dong = [ln for ln in p2.stdout.splitlines() if ln.strip()]
for ln in dong[:6]:
    print("   ", ln)
print("   ...")
for ln in dong[-8:]:
    print("   ", ln)
if p2.stderr.strip():
    print("[stderr]", p2.stderr.strip()[:500])
print("EXIT =", p2.returncode)

# app.py them hau to "_ket_qua" vao ten file video va "_bao_cao" cho CSV
video_ra = os.path.join(OUT, "C2b_ket_qua_ket_qua.mp4")
csv_ra = os.path.join(OUT, "C2b_ket_qua_bao_cao.csv")
for duong_dan, ten in ((video_ra, "video"), (csv_ra, "csv")):
    if os.path.isfile(duong_dan):
        print(f"  {ten}: {os.path.getsize(duong_dan)} bytes")
    else:
        print(f"  {ten}: KHONG CO")

if p2.returncode == 0 and os.path.isfile(video_ra):
    print("KET QUA: PASS")
else:
    print("KET QUA: FAIL")
    sys.exit(1)
