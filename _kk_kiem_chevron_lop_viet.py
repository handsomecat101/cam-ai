# -*- coding: utf-8 -*-
"""Kiem chung BAN VONG 3 (worker C): mui ten muc lon + lop tieng Viet.

Kiem 4 phan:
  [1] MUI TEN MUC LON: NGUON (mo san) phai hien ChevronDown (E70D);
      bam dong -> ChevronRight (E76C); bam mo lai -> ChevronDown.
      Muc con (mo san / mo bang tay) cung phai dung trang thai.
      Doi ngon nung KHONG duoc reset ve glyph cu.
  [2] CHUP ANH cot trai + phong to 3x vung mui ten (de TOI MAT xac nhan).
  [3] LOP TIENG VIET trong khung xem truc tiep: ket qua cua GUI phai
      GIONG HET ket qua cua cam_ai_core (cung class id).
  [4] ENCODING: BOM=False, CR=0.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_kiem_chevron_lop_viet.py
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

from PIL import Image, ImageGrab  # noqa: E402

import customtkinter as ctk  # noqa: E402

OUT = os.path.join(APP_DIR, "_kk_out", "agent_c_vong3")
XE_DOI = "\ue70d"      # ChevronDown
XE_PHAI = "\ue76c"     # ChevronRight

LOI: list[str] = []
KET: list[tuple[str, bool]] = []

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def bao(ten: str, ok: bool, ghi_chu: str = "") -> None:
    KET.append((ten, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {ten}"
          + (f"  ({ghi_chu})" if ghi_chu else ""), flush=True)
    if not ok:
        LOI.append(f"{ten} | {ghi_chu}")


def _rect(app):
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    if hwnd:
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    return rc


# ------------------------------------------------------------------ [1] + [2]

def kiem_chevron(app) -> dict:
    print()
    print("=" * 78)
    print("[1] MUI TEN MUC LON / MUC CON - DUNG TRANG THAI MO / DONG")
    print("=" * 78)

    nhom = app._ds_nhom_lon
    ten_cac_nhom = [str(n.lbl_ten.cget("text")) for n in nhom]
    print(f"  4 muc lon: {ten_cac_nhom}")
    bao("co du 4 muc lon", len(nhom) == 4, f"{len(nhom)}")

    n_nguon = nhom[0]
    ten = str(n_nguon.lbl_ten.cget("text"))
    print(f"  muc '{ten}' (mo san): trang thai noi dung = {n_nguon.trang_thai()}")

    # --- muon XUONG ngay tu dau (mo san) ---
    goc = str(n_nguon.btn_mo.cget("text"))
    print(f"  btn_mo['{ten}'] luc khoi tao = {goc!r} "
          f"({hex(ord(goc)) if goc else 'rong'})")
    bao("NGUON (mo san) muon XUONG ngay tu dau", goc == XE_DOI,
        f"thuc={goc!r} mong doi={XE_DOI!r}")

    # --- 3 muc con lai phai phai sang phai ---
    for n in nhom[1:]:
        t = str(n.btn_mo.cget("text"))
        bao(f"muc '{str(n.lbl_ten.cget('text'))}' (dong) muon PHAI", t == XE_PHAI,
            f"thuc={t!r}")

    # --- bam muon: dong -> phai, mo lai -> xuong ---
    n_nguon._doi_trang_thai()
    app.update_idletasks()
    t1 = str(n_nguon.btn_mo.cget("text"))
    bao("bam muon -> DONG: muon phai (E76C)", t1 == XE_PHAI, f"thuc={t1!r}")

    n_nguon._doi_trang_thai()
    app.update_idletasks()
    t2 = str(n_nguon.btn_mo.cget("text"))
    bao("bam muon -> MO LAI: muon xuong (E70D)", t2 == XE_DOI, f"thuc={t2!r}")

    # --- muc con: mo bang tay ---
    n_con = app.nhom_phat_hien
    n_con.dat_mo(True)
    app.update_idletasks()
    t3 = str(n_con.btn_mo.cget("text"))
    bao("muc con MO: muon xuong (E70D)", t3 == XE_DOI, f"thuc={t3!r}")
    n_con.dat_mo(False)
    app.update_idletasks()
    t4 = str(n_con.btn_mo.cget("text"))
    bao("muc con DONG: muon phai (E76C)", t4 == XE_PHAI, f"thuc={t4!r}")

    # --- doi ngon nung KHONG duoc reset glyph ---
    n_nguon.dat_mo(True)
    app.update_idletasks()
    trc = str(n_nguon.btn_mo.cget("text"))
    nguon_cu = app.ngon_ngu
    app.ngon_ngu = "en"
    app._lam_moi_ngon_ngu()
    app.update_idletasks()
    sau = str(n_nguon.btn_mo.cget("text"))
    app.ngon_ngu = nguon_cu
    app._lam_moi_ngon_ngu()
    app.update_idletasks()
    bao("doi ngon nung KHONG reset muon (van xuong)",
        sau == XE_DOI and trc == XE_DOI, f"truoc={trc!r} sau={sau!r}")
    app.ngon_ngu = nguon_cu
    app._lam_moi_ngon_ngu()
    app.update_idletasks()
    return {"nhom": nhom}


def chup_cot_trai(app, nhom) -> None:
    print()
    print("=" * 78)
    print("[2] CHUP ANH COT TRAI + PHONG TO 3x VUNG MUI TEN")
    print("=" * 78)
    os.makedirs(OUT, exist_ok=True)

    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.5)
    app.update()

    # Vung cot trai = khong chua 4 muc lon.
    khung = nhom[0].master
    x0 = khung.winfo_rootx()
    y0 = khung.winfo_rooty()
    x1 = x0 + khung.winfo_width()
    y1 = y0 + khung.winfo_height()
    duong = os.path.join(OUT, "cot_trai.png")
    ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True).save(duong)
    print(f"  [chup] cot trai: ({x1 - x0}x{y1 - y0}) -> {duong}")

    # Phong to 3x vung muon cua muc NGUON (vai nut 32px + tieu de).
    n0 = nhom[0]
    bx = n0.btn_mo.winfo_rootx()
    by = n0.btn_mo.winfo_rooty()
    bw = n0.btn_mo.winfo_width()
    bh = n0.btn_mo.winfo_height()
    zx0 = max(x0, bx - 8)
    zy0 = max(y0, by - 8)
    zx1 = min(x1, bx + bw + 8)
    zy1 = min(y1, by + bh + 8)
    duong_z = os.path.join(OUT, "zoom_chevron_nguon.png")
    anh = Image.open(duong).crop((zx0 - x0, zy0 - y0, zx1 - x0, zy1 - y0))
    w, h = anh.size
    anh = anh.resize((w * 3, h * 3), Image.LANCZOS)
    anh.save(duong_z)
    print(f"  [zoom] 3x vung muon NGUON: {w}x{h} -> {w * 3}x{h * 3} "
          f"-> {duong_z}")

    # Phong to 3x vung muon cua 4 muc lon (nhieu muc de doi chieu).
    duong_z4 = os.path.join(OUT, "zoom_chevron_4_muc.png")
    a2 = Image.open(duong)
    chon = []
    for n in nhom:
        bx = n.btn_mo.winfo_rootx()
        by = n.btn_mo.winfo_rooty()
        bw = n.btn_mo.winfo_width()
        bh = n.btn_mo.winfo_height()
        chon.append((bx - 6, by - 6, bx + bw + 6, by + bh + 6))
    zx0 = max(0, min(c[0] for c in chon) - x0)
    zy0 = max(0, min(c[1] for c in chon) - y0)
    zx1 = min(a2.width, max(c[2] for c in chon) - x0)
    zy1 = min(a2.height, max(c[3] for c in chon) - y0)
    crop = a2.crop((zx0, zy0, zx1, zy1))
    w, h = crop.size
    crop = crop.resize((w * 3, h * 3), Image.LANCZOS)
    crop.save(duong_z4)
    print(f"  [zoom] 3x vung muon 4 muc: {w}x{h} -> {w * 3}x{h * 3} "
          f"-> {duong_z4}")


# ------------------------------------------------------------------ [3]

def kiem_lop_tieng_viet(app) -> None:
    print()
    print("=" * 78)
    print("[3] LOP TIENG VIET TRONG KHUNG XEM TRUC TIEP (GUI == CLI)")
    print("=" * 78)

    import cam_ai_core as CORE
    import gui as GUI

    # Ten lop cua model yolo11n.pt (0..79) - dung chung thu tu voi core.
    try:
        from ultralytics import YOLO
        names = YOLO(os.path.join(APP_DIR, "yolo11n.pt")).names
        nguon = "YOLO('yolo11n.pt').names"
    except Exception as exc:  # noqa: BLE001
        print(f"  [canh bao] khong nap duoc YOLO ({exc}) -> dung lop_viet")
        import lop_viet
        names = {i: t for i, t in enumerate(lop_viet.TEN_LOP_VIET)}
        nguon = "lop_viet.TEN_LOP_VIET"
    id_lop = {ten: cid for cid, ten in names.items()}
    print(f"  nguon ten lop: {nguon}  ({len(id_lop)} lop)")

    chuoi = "ô tô,xe máy"
    ra_gui, sai_gui = GUI._chon_lop_cho_xem(chuoi, id_lop)
    ra_cli, sai_cli = CORE._chon_lop(chuoi, id_lop)
    print(f"  chuoi nguoi dung = {chuoi!r}")
    print(f"  GUI (_chon_lop_cho_xem) -> hop le={ra_gui}  sai={sai_gui}")
    print(f"  CLI (cam_ai_core._chon_lop) -> hop le={ra_cli}  sai={sai_cli}")
    id_gui = sorted(id_lop[t] for t in ra_gui)
    id_cli = sorted(id_lop[t] for t in ra_cli)
    print(f"  class id GUI = {id_gui}   class id CLI = {id_cli}")
    bao("GUI va CLI cho ra CUNG danh sach lop", ra_gui == ra_cli,
        f"{ra_gui} vs {ra_cli}")
    bao("GUI va CLI cho ra CUNG class id", id_gui == id_cli,
        f"{id_gui} vs {id_cli}")
    bao("chuoi 'ô tô,xe máy' -> DUNG 2 lop", len(ra_gui) == 2, f"{ra_gui}")
    bao("2 lop dung la car + motorcycle",
        sorted(ra_gui) == ["car", "motorcycle"], f"{sorted(ra_gui)}")
    bao("khong co lop sai", not sai_gui, f"{sai_gui}")

    # 'all' + rong + lop sai - phai giong core
    for chuoi2, nhan2 in (("all", "all"), ("", "rong"), ("o to,xe may", "khong dau"),
                          ("xyz", "lop sai")):
        g = GUI._chon_lop_cho_xem(chuoi2, id_lop)
        c = CORE._chon_lop(chuoi2, id_lop)
        bao(f"chuoi {nhan2} {chuoi2!r}: GUI == CLI", g == c, f"{g} vs {c}")

    # --- CHAY THUC khung xem truc tiep voi lop tieng Viet ---
    print()
    print("  --- chay thuc `_vong_xem` voi cfg.lop = 'ô tô,xe máy' ---")
    from cam_ai_core import AnalysisConfig

    video = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
    if not os.path.isfile(video):
        bao("co video mau de chay thuc", False, video)
        return
    cfg = AnalysisConfig(
        input=video,
        output=os.path.join(OUT, "thu"),
        no_face=True,
        model=os.path.join(APP_DIR, "yolo11n.pt"),
        conf=0.25,
        nhan_vat_the=True,
        lop="ô tô,xe máy",
    )
    import threading
    # Dung WRAPPER cua app (`_chay_xem_truc_tiep`) - no bat loi, dung
    # duong chay that cua phan mem.
    th = threading.Thread(target=app._chay_xem_truc_tiep, args=(cfg,),
                          daemon=True)
    th.start()
    dong_log = []
    t0 = time.time()
    while th.is_alive() and time.time() - t0 < 90:
        try:
            while True:
                kind, payload = app.queue.get_nowait()
                if kind == "log":
                    dong_log.append(str(payload))
                else:
                    app.queue.put((kind, payload))   # tra lai frame
        except Exception:
            pass
        app.update()
        time.sleep(0.1)
    app._ket_thuc_xem.set()
    th.join(timeout=15)
    for d in dong_log:
        print(f"    [log] {d}")
    dong = [d for d in dong_log if "Đang nhận" in d or "Bỏ qua" in d]
    bao("vong xem bao 'Dang nhan 2 lop'",
        any("Đang nhận 2 lớp" in d for d in dong), f"{dong}")
    bao("vong xem KHONG bao 'Bo qua lop khong co'",
        not any("Bỏ qua" in d for d in dong), f"{dong}")


# ------------------------------------------------------------------ [4]

def kiem_encoding() -> None:
    print()
    print("=" * 78)
    print("[4] ENCODING FILE DA SUA")
    print("=" * 78)
    p = os.path.join(APP_DIR, "gui.py")
    d = open(p, "rb").read()
    bom = d[:3] == b"\xef\xbb\xbf"
    cr = d.count(b"\r")
    print(f"  gui.py: BOM={bom}  CR={cr}  LF={d.count(chr(10).encode())}")
    bao("gui.py khong co BOM", not bom)
    bao("gui.py LF thuan (CR=0)", cr == 0, f"CR={cr}")


# ------------------------------------------------------------------ chay

def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    print("=" * 78)
    print("CamAI - BAN VONG 3: MUI TEN + LOP TIENG VIET")
    print("=" * 78)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui = None
    from gui import CamAIGui as _CamAIGui
    app = _CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()

    try:
        kiem_chevron(app)
        chup_cot_trai(app, app._ds_nhom_lon)
        kiem_lop_tieng_viet(app)
    finally:
        kiem_encoding()
        try:
            app.stop_flag.set()
            app.destroy()
        except Exception:  # noqa: BLE001
            pass

    print()
    print("=" * 78)
    print("KET LUA")
    print("=" * 78)
    for ten, ok in KET:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ten}")
    tong = sum(1 for _, ok in KET if ok)
    print(f"KET QUA: {tong}/{len(KET)} muc {'PASS' if tong == len(KET) else 'FAIL'}")
    if LOI:
        for d in LOI:
            print(f"  - {d}")
    print(f"Anh chup: {OUT}")
    return 0 if tong == len(KET) else 1


if __name__ == "__main__":
    sys.exit(main())
