# -*- coding: utf-8 -*-
"""
CamAI - KIEM CHUNG GIAO DIEN (coordinator) sau khi thiet ke lai.

Khong chi kiem chung "app co chay" ma kiem ca ve mat tham my:
  [1] KHONG con emoji lam icon trong gui.py
  [2] Font: khong chu nao < 12px; cac font dung deu co that tren may
  [3] Icon app: assets\\camai.ico co mat va duoc nap vao cua so
  [4] Tuong phan chu >= 4.5:1 cho cac cap mau nen/chu chinh
  [5] Khung video van la vung lon nhat (>= 70% be ngang)
  [6] Khong chu bi cat trong o
  [7] Chup anh de TOI TU XEM bang mat

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_giao_dien.py

File nay KHONG sua file nao khac trong repo.
"""

from __future__ import annotations

import ctypes
import os
import re
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_REAL_STDOUT = sys.stdout
try:
    _REAL_STDOUT.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def in_ky(*args) -> None:
    print(*args, file=_REAL_STDOUT, flush=True)


THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "kiem_giao_dien")
IMG_FULL = os.path.join(THU_MUC_KQ, "gd_full.png")

# Ky tu bi cam: emoji + hinh vuong/ngon sao hay dung lam icon.
# KHONG cam mui ten (U+2190-U+21FF) - day la ky tu van xu dung trong van ban.
KY_TU_CAM = re.compile(
    "[\u2300-\u23FF\u2460-\u24FF\u25A0-\u25FF\u2600-\u27BF"
    "\U0001F300-\U0001FAFF\uFE0F\u2705\u274C\u26A0\u2B50\u2714\u2716]")

MAU_NEN = {"nen": "#0F172A", "the": "#1B2336", "the_phu": "#272F42"}
MAU_CHU = {"chu": "#F8FAFC", "chu_phu": "#94A3B8", "chu_phu_the": "#CBD5E1",
           "nut": "#22C55E"}

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def hex_rgb(s: str) -> tuple:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def tuong_phan(a: str, b: str) -> float:
    def do_sang(c):
        r, g, bl = [v / 255 for v in c]

        def f(u):
            return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4

        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bl)

    la, lb = do_sang(hex_rgb(a)), do_sang(hex_rgb(b))
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def chup(app, duong_dan):
    from PIL import ImageGrab

    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    app.update()
    app.update_idletasks()
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.4)
    app.update()
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    if hwnd:
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    anh = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                         all_screens=True)
    anh.save(duong_dan)
    return anh


def duyet(widget, ket_qua=None):
    if ket_qua is None:
        ket_qua = []
    ket_qua.append(widget)
    for con in widget.winfo_children():
        duyet(con, ket_qua)
    return ket_qua


def chay() -> int:
    import tkinter.font as tkfont

    import customtkinter as ctk

    from gui import CamAIGui

    in_ky("=" * 78)
    in_ky("CamAI - KIEM CHUNG GIAO DIEN SAU KHI THIET KE LAI")
    in_ky("=" * 78)
    ket_qua = []

    # ---------------------------------------------------------- [1] EMOJI
    in_ky("")
    in_ky("[1] KHONG CON EMOJI LAM ICON")
    duong_gui = os.path.join(APP_DIR, "gui.py")
    with open(duong_gui, "r", encoding="utf-8") as f:
        noi_dung = f.read()
    dong_ky = []
    for i, dong in enumerate(noi_dung.splitlines(), start=1):
        if KY_TU_CAM.search(dong):
            dong_ky.append((i, dong.strip()[:110]))
    in_ky(f"  gui.py: so dong con ky tu cam = {len(dong_ky)}")
    for i, d in dong_ky[:12]:
        in_ky(f"      {i}: {d}")
    ok1 = len(dong_ky) == 0
    in_ky(f"  -> {'PASS' if ok1 else 'FAIL'}")
    ket_qua.append(("khong emoji lam icon", ok1))

    # ------------------------------------------------------------ [2] FONT
    in_ky("")
    in_ky("[2] FONT: KHONG CHU < 12px, DUNG FONT CO THAT")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(1.0)
    app.update()

    co_tren_may = set(tkfont.families())
    dung = {}
    nho_nhat = 999
    vi_tri_nho = ""
    for widget in duyet(app):
        try:
            font = widget.cget("font")
        except Exception:  # noqa: BLE001
            continue
        if not font:
            continue
        gia_dong = ""
        kich = 0
        if isinstance(font, (tuple, list)):
            gia_dong = str(font[0]) if font else ""
            for phan in font[1:]:
                if isinstance(phan, int):
                    kich = phan
                    break
        elif isinstance(font, str):
            # CustomTkinter tra ve CHUOI dang: "Segoe UI -13 {normal roman }"
            chu = font.strip()
            gia_dong = chu.split(" -")[0].strip()
            phan = chu.split(" -")[1] if " -" in chu else ""
            so = ""
            for ky_tu in phan:
                if ky_tu.isdigit():
                    so += ky_tu
                elif so:
                    break
            kich = int(so) if so else 0
        if gia_dong:
            # CTkFont tra ve ten font co dau "{}" (vi du "{Segoe UI}") -> bo di.
            gia_dong = gia_dong.strip("{}")
            dung[gia_dong] = dung.get(gia_dong, 0) + 1
        if kich and kich < nho_nhat:
            nho_nhat = kich
            vi_tri_nho = type(widget).__name__
    in_ky(f"  font dang dung   : {dung}")
    # Font mac dinh cua Tk (TkDefaultFont...) luon tro toi 1 font that tren may.
    mac_dinh_tk = {"TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont",
                   "TkHeadingFont", "TkTooltipFont"}
    thieu = [f for f in dung
             if f not in co_tren_may and f not in mac_dinh_tk]
    in_ky(f"  font KHONG co tren may: {thieu if thieu else 'khong co'}")
    in_ky(f"  co chu nho nhat: {nho_nhat}px ({vi_tri_nho})")
    ok2 = (nho_nhat >= 12) and not thieu
    in_ky(f"  -> {'PASS' if ok2 else 'FAIL'}")
    ket_qua.append(("font >= 12px va co tren may", ok2))

    # ------------------------------------------------- [3] ICON APP + GUI
    in_ky("")
    in_ky("[3] ICON APP + DUNG GUI THAT")
    in_ky(f"  tieu de cua so : {app.title()!r}")
    in_ky(f"  kich thuoc     : {app.winfo_width()}x{app.winfo_height()}")

    duong_ico = os.path.join(APP_DIR, "assets", "camai.ico")
    co_ico = os.path.isfile(duong_ico)
    in_ky(f"  assets/camai.ico : co = {co_ico} "
          f"({os.path.getsize(duong_ico) if co_ico else 0} B)")
    co_anh_ico = False
    for ten in dir(app):
        if "icon" in ten.lower():
            gia_tri = getattr(app, ten, None)
            if gia_tri is not None and not callable(gia_tri):
                co_anh_ico = True
                in_ky(f"  app.{ten} = {type(gia_tri).__name__}")
                break
    ok3 = co_ico and co_anh_ico
    in_ky(f"  -> {'PASS' if ok3 else 'FAIL'} (co file icon va app giu icon)")
    ket_qua.append(("icon app", ok3))

    # ------------------------------------------- [4] TUONG PHAN MAU
    in_ky("")
    in_ky("[4] TUONG PHAN CHU >= 4.5:1")
    ok4 = True
    for nen, nen_hex in MAU_NEN.items():
        for ten_chu, chu_hex in MAU_CHU.items():
            tp = tuong_phan(chu_hex, nen_hex)
            danh_dau = "OK " if tp >= 4.5 else "THIEU"
            if tp < 4.5:
                ok4 = False
            in_ky(f"  {danh_dau} {ten_chu:12s} tren {nen:9s} = {tp:5.2f}:1")
    in_ky(f"  -> {'PASS' if ok4 else 'FAIL'}")
    ket_qua.append(("tuong phan chu >= 4.5:1", ok4))

    # ------------------------------------------- [5] KHUNG VIDEO LON NHAT
    in_ky("")
    in_ky("[5] KHUNG VIDEO VAN LA VUNG LON NHAT (>= 70% be ngang)")
    app.update()
    # Dung CUNG quy uoc voi _kk_kiem_boc_cuc.py: video / (video + cot su kien).
    # (Chia cho be ngang ca cua so se sai, vi ben phai con 1 cot danh sach su kien.)
    ok5 = False
    khung = getattr(app, "khung_den", None)
    su_kien = getattr(app, "panel_su_kien", None)
    if khung is not None and su_kien is not None:
        wv, we = khung.winfo_width(), su_kien.winfo_width()
        tong = wv + we
        ty_le = (wv / tong) if tong else 0
        in_ky(f"  video = {wv}px | cot su kien = {we}px | tong = {tong}px "
              f"| ty le = {ty_le * 100:.1f}%")
        ok5 = ty_le >= 0.70
    in_ky(f"  -> {'PASS' if ok5 else 'FAIL'}")
    ket_qua.append(("video >= 70% be ngang", ok5))

    # ------------------------------------------- [6] CHU BI CAT
    in_ky("")
    in_ky("[6] CHU BI CAT TRONG O")
    # Mo het cac nhom truoc khi do, neu khong thi do se sai (nhom dang thu gon
    # bi co lai kich thuoc nho hon so voi luc mo).
    from gui import NhomTinhNang

    so_nhom = 0
    for widget in duyet(app):
        if isinstance(widget, NhomTinhNang):
            try:
                widget.dat_mo(True)
                so_nhom += 1
            except Exception:  # noqa: BLE001
                pass
    app.update()
    app.update_idletasks()
    time.sleep(0.3)
    app.update()
    in_ky(f"  da mo {so_nhom} nhom truoc khi do kich thuoc")
    cat = []
    for widget in duyet(app):
        if not isinstance(widget, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry)):
            continue
        try:
            text = widget.cget("text")
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            req = widget.winfo_reqwidth()
            real = widget.winfo_width()
        except Exception:  # noqa: BLE001
            continue
        if real > 1 and req > real + 6:
            cat.append((text[:48], req, real))
    in_ky(f"  so widget co chu bi cat = {len(cat)}")
    for t, req, real in cat[:10]:
        in_ky(f"      {t!r} can {req}px nhung chi co {real}px")
    ok6 = len(cat) == 0
    in_ky(f"  -> {'PASS' if ok6 else 'FAIL'}")
    ket_qua.append(("khong chu bi cat", ok6))

    # ------------------------------------------------------- [7] CHUP ANH
    in_ky("")
    in_ky("[7] CHUP ANH")
    anh = chup(app, IMG_FULL)
    in_ky(f"  anh cua so -> {IMG_FULL} {anh.size}")
    from PIL import ImageStat

    stat = ImageStat.Stat(anh.convert("RGB"))
    in_ky(f"  sang trung binh = {sum(stat.mean) / 3:.2f}")
    ket_qua.append(("chup anh", os.path.isfile(IMG_FULL)))

    # ---------------------------------------------------------------- tong
    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA KIEM CHUNG GIAO DIEN")
    in_ky("=" * 78)
    for ten, ok in ket_qua:
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}")
    tong = all(ok for _, ok in ket_qua)
    in_ky(f"  TONG KET: {'PASS' if tong else 'FAIL'}")
    in_ky("=" * 78)

    try:
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if tong else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
