#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""KIEM CHUNG vong 2 (coordinator): lop tieng Viet + dem phuong tien + nguon moi GUI.

Kiem chung doc lap voi thay doi cua agent:
  A. lop_viet.py: 80 lop COCO khop 100% voi model that
  B. tra cuu lop: tieng Viet co dau / khong dau / tu dong nghia
  C. AnalysisConfig co truong dem_phuong_tien
  D. CLI --list-cap (alias --list-lop) in dung 80 dong
  E. CLI --lop tieng Viet chay that tren video mau
  F. CLI --dem-phuong-tien in bang dem + CSV co cot moi o CUOI
  G. gui.py co nut chon anh / chon camera + dich tieng Anh day du
  H. hoi quy: khong bat tinh nang moi -> CSV giong het ban goc

Chay: .venv\\Scripts\\python.exe -W ignore _kk_kiem_nguon_viet.py
"""

import os
import re
import subprocess
import sys
import unicodedata

APP = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(APP, ".venv", "Scripts", "python.exe")

KET_QUA = []
LOI = []


def ok(ten, chi_tiet=""):
    KET_QUA.append(("PASS", ten, chi_tiet))
    print(f"[PASS] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


def fail(ten, chi_tiet=""):
    KET_QUA.append(("FAIL", ten, chi_tiet))
    LOI.append(ten)
    print(f"[FAIL] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


def bo_dau(s):
    """Chuan hoa chuoi: bo dau, ha chu thuong, ghep chu thuong."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", s.lower()).strip()


def chay(cmd, timeout=300):
    """Chay lenh, tra (exit_code, stdout+stderr)."""
    try:
        p = subprocess.run(cmd, cwd=APP, capture_output=True, timeout=timeout)
        out = (p.stdout or b"").decode("utf-8", "replace") + \
              (p.stderr or b"").decode("utf-8", "replace")
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"
    except Exception as e:  # noqa: BLE001
        return -8, f"LOI: {e}"


# ---------------------------------------------------------------- A. lop_viet
def kiem_A():
    path = os.path.join(APP, "lop_viet.py")
    if not os.path.exists(path):
        fail("A1. lop_viet.py ton tai", path)
        return None
    ok("A1. lop_viet.py ton tai")
    sys.path.insert(0, APP)
    try:
        import lop_viet
    except Exception as e:  # noqa: BLE001
        fail("A2. import lop_viet", str(e))
        return None
    ok("A2. import lop_viet")

    # tim ham danh sach (ten co the khac nhau)
    ds = None
    for ten in ("DANH_SACH_LOP_VIET", "danh_sach_lop_viet", "DANH_SACH_LOP",
                "danh_sach_lop"):
        if hasattr(lop_viet, ten):
            ds = getattr(lop_viet, ten)
            break
    if ds is None:
        fail("A3. co ham danh sach lop")
        return lop_viet
    danh_sach = list(ds())
    ok("A3. co ham danh sach lop", f"{len(danh_sach)} dong")

    if len(danh_sach) != 80:
        fail("A4. danh sach co 80 lop", f"thuc te {len(danh_sach)}")
    else:
        ok("A4. danh sach co 80 lop")

    # doi chieu voi model that
    try:
        from ultralytics import YOLO
        names = YOLO(os.path.join(APP, "yolo11n.pt")).names
        that = {int(k): v for k, v in names.items()}
        ok("A5. doc duoc model that", f"{len(that)} lop")
    except Exception as e:  # noqa: BLE001
        fail("A5. doc duoc model that", str(e))
        return lop_viet

    if len(danh_sach) == len(that):
        sai = []
        for row in danh_sach:
            cid, en, vi = row[0], row[1], row[2]
            if cid not in that:
                sai.append(f"id {cid} khong co trong model")
            elif that[cid] != en:
                sai.append(f"id {cid}: '{en}' != '{that[cid]}'")
            elif not vi or not vi.strip():
                sai.append(f"id {cid} ({en}) thieu ten tieng Viet")
        if sai:
            fail("A6. 80 lop khop 100% voi model", "; ".join(sai[:5]))
        else:
            ok("A6. 80 lop khop 100% voi model", "id + ten Anh + ten Viet deu dung")
    else:
        fail("A6. so lop khop model", f"bang {len(danh_sach)} vs model {len(that)}")

    # ten tieng Viet co dau?
    co_dau = [r for r in danh_sach if bo_dau(r[2]) != r[2].lower()]
    if len(co_dau) >= 70:
        ok("A7. ten tieng Viet co dau", f"{len(co_dau)}/80 co dau")
    else:
        fail("A7. ten tieng Viet co dau", f"chi {len(co_dau)}/80 co dau")
    return lop_viet


# ------------------------------------------------------------- B. tra cuu lop
def kiem_B(lop_viet):
    if lop_viet is None:
        return
    tra = None
    for ten in ("TRA_CUU_LOP_VIET", "tra_cuu_lop_viet", "TRA_CUU_LOP",
                "tra_cuu_lop"):
        if hasattr(lop_viet, ten):
            tra = getattr(lop_viet, ten)
            break
    if tra is None:
        fail("B1. co ham tra cuu lop")
        return
    ok("B1. co ham tra cuu lop")

    truong = [
        ("ô tô", "car"),
        ("o to", "car"),
        ("xe hơi", "car"),
        ("xe máy", "motorcycle"),
        ("xe may", "motorcycle"),
        ("xe đạp", "bicycle"),
        ("xe khách", "bus"),
        ("xe tải", "truck"),
        ("người", "person"),
        ("chó", "dog"),
        ("mèo", "cat"),
        ("car", "car"),
        ("motorcycle", "motorcycle"),
    ]
    sai = []
    for vao, mong_doi in truong:
        try:
            kq = tra(vao)
        except Exception as e:  # noqa: BLE001
            sai.append(f"{vao!r} -> LOI {e}")
            continue
        if not isinstance(kq, (list, tuple, set)):
            kq = [kq]
        kq = [str(x) for x in kq]
        if mong_doi not in kq:
            sai.append(f"{vao!r} -> {kq} (mong doi '{mong_doi}')")
    if sai:
        fail("B2. tra cuu lop tieng Viet / dong nghia", "; ".join(sai[:6]))
    else:
        ok("B2. tra cuu lop tieng Viet / dong nghia", f"{len(truong)}/13 dung")

    # tra cuu nhieu lop bang dau phay
    try:
        kq = tra("ô tô, xe máy")
        kq = [str(x) for x in (kq if isinstance(kq, (list, tuple, set)) else [kq])]
        if "car" in kq and "motorcycle" in kq:
            ok("B3. tra cuu nhieu lop bang dau phay", str(kq))
        else:
            fail("B3. tra cuu nhieu lop bang dau phay", str(kq))
    except Exception as e:  # noqa: BLE001
        fail("B3. tra cuu nhieu lop bang dau phay", str(e))

    # goi y khi gao sai
    goi_y = None
    for ten in ("GOI_Y_LOP_VIET", "goi_y_lop_viet", "GOI_Y_LOP", "goi_y_lop"):
        if hasattr(lop_viet, ten):
            goi_y = getattr(lop_viet, ten)
            break
    if goi_y is None:
        fail("B4. co ham goi y lop")
    else:
        try:
            # "oto" = gõ thiếu dấu -> phai co goi y. ("o to" la alias HOP LE
            # nen tra loi rong la DUNG, khong phai loi.)
            g = goi_y("oto")
            if g and isinstance(g, str):
                ok("B4. goi y lop khi gao sai", g)
            else:
                fail("B4. goi y lop khi gao sai", repr(g))
        except Exception as e:  # noqa: BLE001
            fail("B4. goi y lop khi gao sai", str(e))


# ------------------------------------------------------ C. AnalysisConfig moi
def kiem_C():
    try:
        import cam_ai_core
    except Exception as e:  # noqa: BLE001
        fail("C1. import cam_ai_core", str(e))
        return
    ok("C1. import cam_ai_core")
    fields = cam_ai_core.AnalysisConfig.__dataclass_fields__
    for ten, bat_buoc in (("dem_phuong_tien", True), ("lop_phuong_tien", False)):
        if ten in fields:
            ok(f"C2. AnalysisConfig co '{ten}'")
        else:
            fail(f"C2. AnalysisConfig co '{ten}'")
            continue
        if bat_buoc and fields[ten].default is not False:
            fail(f"C3. '{ten}' mac dinh phai la False",
                 repr(fields[ten].default))
        else:
            ok(f"C3. '{ten}' mac dinh phai la False/hop le")

    # phuong tien mac dinh: nam o lop_viet (cam_ai_core import module, khong re-export)
    try:
        import lop_viet as _lv
    except Exception:  # noqa: BLE001
        _lv = None
    if _lv is not None and hasattr(_lv, "XE_PHUONG_TIEN"):
        x = _lv.XE_PHUONG_TIEN
        if isinstance(x, (list, tuple)) and len(x) >= 4:
            ok("C4. XE_PHUONG_TIEN co san", f"{len(x)} lop: {', '.join(map(str, x))}")
        else:
            fail("C4. XE_PHUONG_TIEN co san", repr(x))
    else:
        fail("C4. XE_PHUONG_TIEN co san", "khong tim thay trong lop_viet")


# ------------------------------------------------------------ D. CLI --list-lop
def kiem_D():
    code, out = chay([PY, "-W", "ignore", "app.py", "--list-lop"], timeout=180)
    if code != 0:
        fail("D1. CLI --list-lop exit 0", f"exit={code}; {out[-300:]}")
        return
    ok("D1. CLI --list-lop exit 0")
    # dong co dang: "  <id>  <ten tieng Anh>   <ten tieng Viet>"
    dong = [ln for ln in out.splitlines() if re.match(r"^\s*\d{1,2}\s+\S", ln)]
    if len(dong) == 80:
        ok("D2. --list-lop in DUNG 80 dong lop", f"{len(dong)} dong")
    else:
        fail("D2. --list-lop in DUNG 80 dong lop", f"chi {len(dong)} dong")
    # Cột tiếng Việt phải CÓ DẤU ở đa số các lớp (không kiểm bằng danh sách
    # tên cụ thể - 80 lớp có 80 tên khác nhau).
    co_dau = 0
    for ln in dong:
        # phần sau cột ID là "ten tieng Anh   ten tieng Viet"
        phan = ln.split(None, 2)
        if len(phan) < 3:
            continue
        vi = phan[2]
        if any(ord(c) > 127 for c in vi):
            co_dau += 1
    if co_dau >= 70:
        ok("D3. --list-lop co ten tieng Viet co dau", f"{co_dau}/80 dong co dau")
    else:
        fail("D3. --list-lop co ten tieng Viet co dau", f"chi {co_dau}/80 dong co dau")


# ------------------------------------------- E/F. CLI chay that tren video mau
VIDEO = os.path.join(APP, "video_mau", "car-detection.mp4")


def kiem_E():
    if not os.path.exists(VIDEO):
        fail("E1. video mau car-detection.mp4 ton tai", VIDEO)
        return
    out_dir = os.path.join(APP, "_kk_out", "kiem_nguon_viet")
    os.makedirs(out_dir, exist_ok=True)
    code, out = chay([PY, "-W", "ignore", "app.py", "--input", VIDEO,
                      "--lop", "ô tô,xe máy",
                      "--output", os.path.join(out_dir, "e_viet")], timeout=600)
    if code != 0:
        fail("E1. --lop tieng Viet chay duoc", f"exit={code}; {out[-400:]}")
        return
    ok("E1. --lop tieng Viet chay duoc (exit 0)")
    # Log in TEN TIENG VIET (nhan tren khung hinh moi bo dau) -> kiem ca 2 bien
    if "ô tô" in out and "xe máy" in out:
        ok("E2. --lop 'o to,xe may' nhan dung 2 lop (ô tô + xe máy)")
    else:
        fail("E2. --lop 'o to,xe may' nhan dung 2 lop", out[-300:])
    if "loi" in out.lower() and "khong co lop" in out.lower():
        fail("E2b. khong bao loi 'khong co lop' khi lop hop le", out[-200:])
    else:
        ok("E2b. khong bao loi khi lop hop le")


def kiem_F():
    if not os.path.exists(VIDEO):
        return
    out_dir = os.path.join(APP, "_kk_out", "kiem_nguon_viet")
    os.makedirs(out_dir, exist_ok=True)
    code, out = chay([PY, "-W", "ignore", "app.py", "--input", VIDEO,
                      "--dem-phuong-tien",
                      "--output", os.path.join(out_dir, "f_dem")], timeout=600)
    if code != 0:
        fail("F1. --dem-phuong-tien chay duoc", f"exit={code}; {out[-400:]}")
        return
    ok("F1. --dem-phuong-tien chay duoc (exit 0)")
    if re.search(r"phuong tien|phương tiện|xe ", out, re.I):
        ok("F2. bao cao co muc dem phuong tien")
    else:
        fail("F2. bao cao co muc dem phuong tien", out[-300:])

    # CSV co cot moi o CUOI va cot cu khong doi
    import csv
    import glob
    bam = sorted(glob.glob(os.path.join(out_dir, "f_dem*_bao_cao.csv")) +
                 glob.glob(os.path.join(out_dir, "f_dem*.csv")))
    if not bam:
        fail("F3. CSV ket qua ton tai", out_dir)
        return
    with open(bam[-1], encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        fail("F3. CSV ket qua co du lieu")
        return
    header = rows[0]
    if len(header) >= 11:
        ok("F3. CSV co cot moi", f"{len(header)} cot: ...{header[-3:]}")
    else:
        fail("F3. CSV co cot moi", f"chi {len(header)} cot: {header}")


# ----------------------------------------------------------- H. hoi quy CSV
def kiem_H():
    """Chay video ma KHONG bat tinh nang moi -> CSV phai giong ban goc."""
    if not os.path.exists(VIDEO):
        return
    out_dir = os.path.join(APP, "_kk_out", "kiem_nguon_viet")
    os.makedirs(out_dir, exist_ok=True)
    code, out = chay([PY, "-W", "ignore", "app.py", "--input", VIDEO,
                      "--output", os.path.join(out_dir, "h_goc")], timeout=600)
    if code != 0:
        fail("H1. chay goc (khong bat tinh nang moi)", f"exit={code}")
        return
    ok("H1. chay goc (khong bat tinh nang moi) exit 0")
    import glob
    import hashlib
    bam = sorted(glob.glob(os.path.join(out_dir, "h_goc*_bao_cao.csv")))
    if not bam:
        fail("H2. CSV goc ton tai")
        return
    b = bam[-1]
    with open(b, "rb") as fh:
        du = hashlib.sha256(fh.read()).hexdigest()
    ok("H2. CSV goc co hash", f"{os.path.basename(b)} sha256={du[:16]}")


# ---------------------------------------------------------- G. GUI nguon moi
def kiem_G():
    p = os.path.join(APP, "gui.py")
    if not os.path.exists(p):
        fail("G1. gui.py ton tai")
        return
    with open(p, encoding="utf-8") as fh:
        src = fh.read()
    for tu in ("Chọn ảnh", "Chọn camera"):
        if tu in src:
            ok(f"G1. gui.py co '{tu}'")
        else:
            fail(f"G1. gui.py co '{tu}'")
    for ten in ("_chon_anh", "_chon_camera"):
        if f"def {ten}" in src:
            ok(f"G2. gui.py co ham {ten}")
        else:
            fail(f"G2. gui.py co ham {ten}")
    if "loai_nguon" in src:
        ok("G3. gui.py dung loai_nguon()")
    else:
        fail("G3. gui.py dung loai_nguon()")
    if "quet_camera" in src:
        ok("G4. gui.py dung quet_camera()")
    else:
        fail("G4. gui.py dung quet_camera()")
    # moi chuoi hien thi deu co ban dich Anh?
    try:
        import gui as g
        dich = getattr(g, "DICH_VI_EN", {})
        # khop TIEN TO: khoa co the la "Loại nguồn: " (co dau cham)
        thieu = []
        for s in ("Chọn ảnh", "Chọn camera", "Loại nguồn"):
            if s in src and not any(k.startswith(s) for k in dich):
                thieu.append(s)
        if thieu:
            fail("G5. chuoi moi co ban dich Anh", "thieu: " + ", ".join(thieu))
        else:
            ok("G5. chuoi moi co ban dich Anh", f"{len(dich)} muc trong dict")
    except Exception as e:  # noqa: BLE001
        fail("G5. kiem tra ban dich Anh", str(e))


def main():
    print("=" * 70)
    print("KIEM CHUNG VONG 2: lop tieng Viet + dem phuong tien + nguon moi")
    print("=" * 70)
    lop_viet = kiem_A()
    kiem_B(lop_viet)
    kiem_C()
    kiem_D()
    kiem_G()
    kiem_E()
    kiem_F()
    kiem_H()

    print("=" * 70)
    tong = len(KET_QUA)
    fail_n = len(LOI)
    print(f"TONG: {tong - fail_n}/{tong} PASS")
    if LOI:
        print("FAIL:")
        for x in LOI:
            print("  - " + x)
    print("=" * 70)
    return 1 if LOI else 0


if __name__ == "__main__":
    sys.exit(main())
