# -*- coding: utf-8 -*-
"""
CamAI - DO CHI PHI VE LAI (repaint) KHI KEO CUA SO + THU NGHIEM A/B.

Khac voi _kk_do_giat.py (do "gap"), ban nay do truc tiep thoi gian ve lai:
  1) MoveWindow cua so 1 pixel  ->  app.update()  ->  do thoi gian ve lai.
  2) Lap lai o 5 trang thai: day du, an dai video mau, an khung video,
     an cot su kien, an ca 3.
  3) Ket qua: khoi nao lam thoi gian ve lai giam nhieu nhat la thu pham.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_do_chi_phi_ve.py
"""

from __future__ import annotations

import ctypes
import os
import statistics
import sys
import time

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


u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.MoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                           ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
u32.MoveWindow.restype = ctypes.c_int
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def duyet(widget, ket_qua=None):
    if ket_qua is None:
        ket_qua = []
    ket_qua.append(widget)
    for con in widget.winfo_children():
        duyet(con, ket_qua)
    return ket_qua


def do_ve_lai(app, hwnd, rong, cao, so_lan=12):
    """Di chuyen 1px roi do thoi gian ve lai (update)."""
    mau = []
    rc = RECT()
    u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    x, y = rc.left, rc.top
    for i in range(so_lan):
        u32.MoveWindow(ctypes.c_void_p(hwnd), x + (i % 2), y, rong, cao, 0)
        t0 = time.perf_counter()
        app.update()
        mau.append((time.perf_counter() - t0) * 1000.0)
    mau = mau[2:]          # bo 2 mau dau (warm-up)
    return mau


def tom_tat(mau):
    if not mau:
        return "khong co mau"
    sap = sorted(mau)
    return (f"tb={statistics.mean(mau):6.1f} ms | tb50={sap[len(sap)//2]:6.1f} | "
            f"max={max(mau):6.1f} | tren 30ms={sum(1 for m in mau if m > 30):2d}")


def chay() -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    rong, cao = 1610, 980
    app.geometry(f"{rong}x{cao}+40+40")
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)

    in_ky("=" * 78)
    in_ky("CamAI - CHI PHI VE LAI KHI KEO CUA SO")
    in_ky("=" * 78)
    in_ky(f"  cua so {rong}x{cao} | tong widget = {len(duyet(app))}")

    # tim cac khoi
    dai = []
    cot_trai = []
    for w in duyet(app):
        if type(w).__name__ != "CTkFrame":
            continue
        for con in w.winfo_children():
            try:
                txt = str(con.cget("text"))
            except Exception:  # noqa: BLE001
                continue
            if "Video mẫu" in txt and not dai:
                dai.append(w)
            if txt.strip().upper() == "NGUỒN" and not cot_trai:
                cot_trai.append(w)

    khung_video = getattr(app, "khung_den", None)
    su_kien = getattr(app, "panel_su_kien", None)

    def an(widgets):
        luu = []
        for w in widgets:
            if w is None:
                continue
            q = w.grid_info()
            w.grid_remove()
            luu.append((w, q))
        app.update()
        time.sleep(0.25)
        app.update()
        return luu

    def hien(luu):
        for w, q in luu:
            if q:
                w.grid(**q)
        app.update()

    truoc = do_ve_lai(app, hwnd, rong, cao)
    in_ky("")
    in_ky(f"  [DAY DU]            {tom_tat(truoc)}")

    truoc_goc = [mau for mau in truoc]
    ket_qua = {"day du": truoc_goc}

    truong_hop = [
        ("an dai 13 the video mau", dai[:1]),
        ("an khung video lon nhat", [khung_video]),
        ("an cot su kien ben phai", [su_kien]),
        ("an cot trai (12 nhom)", cot_trai[:1]),
    ]
    for ten, ds in truong_hop:
        if not ds:
            in_ky(f"  [{ten}] KHONG tim thay")
            continue
        luu = an(ds)
        mau = do_ve_lai(app, hwnd, rong, cao)
        hien(luu)
        in_ky(f"  [{ten}] {tom_tat(mau)}")
        ket_qua[ten] = mau

    # an ca 3 khoi lon nhat
    luu = an(dai[:1] + [khung_video, su_kien])
    mau = do_ve_lai(app, hwnd, rong, cao)
    hien(luu)
    in_ky(f"  [an ca 3 khoi lon]  {tom_tat(mau)}")
    ket_qua["an ca 3 khoi lon"] = mau

    in_ky("")
    in_ky("  -> Ket luan: khoi nao lam thoi gian ve lai GIAM NHIEU nhat la thu pham chinh.")
    in_ky("=" * 78)

    try:
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        sys.exit(2)
