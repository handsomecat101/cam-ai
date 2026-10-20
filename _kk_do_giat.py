# -*- coding: utf-8 -*-
"""
CamAI - DO DO GIA KHI KEO CUA SO + THI NGHIEM A/B TIM THU PHAM (coordinator).

Cach do (khong doan):
  [1] Idle: app co chay lien tuc khong? (CPU trong 3 giay khi khong bam gi).
  [2] Keo cua so that: 1 thread khac di chuyen cua so 1 pixel moi ~12ms, trong
      khi UI thread chay event loop that (`after(10ms)`). Neu app nhe, cac
      callback ve dung moc (gap ~10ms). Neu app GIAT, gap bi tre len 30-100ms.
  [3] A/B: lan luot AN cac khoi (dai video mau / cot trai / khung video / cot
      phai) roi do lai. Khoi nao lam gap giam nhieu nhat la thu pham chinh.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_do_giat.py
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
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


THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "kiem_giat")
KICH_THUOC = (1610, 980)
GIAY_KEO = 2.2

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


def do_keo(app, hwnd, rong, cao, giay=GIAY_KEO):
    """Keo cua so 1 pixel lien tuc, do gap giua cac callback after(10ms)."""
    gaps = []
    trang_thai = {"x": 0, "het": False, "buoi_dau": time.perf_counter()}

    def tick():
        if trang_thai["het"]:
            app.quit()
            return
        bay = time.perf_counter()
        gaps.append((bay - trang_thai["buoi_dau"]) * 1000.0)
        trang_thai["buoi_dau"] = bay
        app.after(10, tick)

    app.after(10, tick)

    def keo():
        rc = RECT()
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
        x, y = rc.left, rc.top
        bat_dau = time.perf_counter()
        i = 0
        while time.perf_counter() - bat_dau < giay:
            i += 1
            u32.MoveWindow(ctypes.c_void_p(hwnd), x + (i % 2), y, rong, cao, 0)
            time.sleep(0.012)
        trang_thai["het"] = True

    threading.Thread(target=keo, daemon=True).start()
    app.mainloop()
    return gaps


def tom_tat(gaps):
    if not gaps:
        return None
    sap = sorted(gaps)
    p90 = sap[-max(1, len(sap) // 10)]
    return {
        "n": len(gaps),
        "tb": sum(gaps) / len(gaps),
        "p90": p90,
        "max": max(gaps),
        "tre30": sum(1 for g in gaps if g > 30),
        "tre50": sum(1 for g in gaps if g > 50),
    }


def chay() -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    os.makedirs(THU_MUC_KQ, exist_ok=True)
    dong = []

    def ghi(s=""):
        in_ky(s)
        dong.append(str(s))

    ghi("=" * 78)
    ghi("CamAI - DO GIA KHI KEO CUA SO + TIM THU PHAM")
    ghi("=" * 78)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.geometry(f"{KICH_THUOC[0]}x{KICH_THUOC[1]}+40+40")
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()

    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    ghi(f"  tieu de = {app.title()!r} | hwnd = {hwnd}")

    # ---------- [1] so widget + CPU khi idle ----------
    ghi("")
    ghi("[1] SO WIDGET + CPU KHI IDLE")
    tat_ca = duyet(app)
    ghi(f"  tong widget Tk    = {len(tat_ca)}")
    ghi(f"  trong do CustomTk = {sum(1 for w in tat_ca if type(w).__name__.startswith('CTk'))}")
    cpu0, t0 = time.process_time(), time.perf_counter()
    time.sleep(3.0)
    cpu1, t1 = time.process_time(), time.perf_counter()
    ghi(f"  CPU khi idle 3s   = {(cpu1 - cpu0) * 1000:.0f} ms "
        f"({(cpu1 - cpu0) / (t1 - t0) * 100:.1f}% cua 1 core)")

    # ---------- [2] keo co ban ----------
    ghi("")
    ghi("[2] KEO CUA SO - TRUONG HOP CO BAN")
    ghi(f"  (gap nho = app nhe; gap lon = app bi tre; muc 10ms = khoi han)")
    app.update()
    t = tom_tat(do_keo(app, hwnd, *KICH_THUOC))
    if t:
        ghi(f"  n={t['n']} | tb={t['tb']:.1f} ms | p90={t['p90']:.1f} ms | "
            f"max={t['max']:.1f} ms | tre 30ms={t['tre30']} | tre 50ms={t['tre50']}")
    else:
        ghi("  khong lay duoc mau")

    # ---------- [3] A/B: an tung khoi ----------
    ghi("")
    ghi("[3] A/B - AN TUNG KHOI ROI DO LAI")

    def tim_theo(app, tu_khoa, attr=None):
        ket = []
        for w in duyet(app):
            for ten in dir(w):
                if tu_khoa.lower() in ten.lower():
                    try:
                        gia_tri = getattr(w, ten)
                    except Exception:  # noqa: BLE001
                        continue
                    if attr is None or isinstance(gia_tri, attr):
                        ket.append((w, ten, gia_tri))
        return ket

    # khoi 1: dai video mau (13 the o day) -> tim frame co chua "Video mau"
    dai = []
    for w in duyet(app):
        if type(w).__name__ == "CTkFrame":
            for con in w.winfo_children():
                try:
                    if "Video mẫu" in str(con.cget("text")):
                        dai.append(w)
                        break
                except Exception:  # noqa: BLE001
                    pass
    # khoi 2: cot trai (khung chua 12 nhom) -> tim khung chua "NGUON"
    cot_trai = []
    for w in duyet(app):
        if type(w).__name__ == "CTkFrame":
            for con in w.winfo_children():
                try:
                    if "NGUỒN" in str(con.cget("text")).upper():
                        cot_trai.append(w)
                        break
                except Exception:  # noqa: BLE001
                    pass
    # khoi 3: khung video lon nhat
    khung_video = getattr(app, "khung_den", None)
    # khoi 4: cot su kien ben phai
    su_kien = getattr(app, "panel_su_kien", None)
    # khoi 5: khung nhat ky
    khung_log = getattr(app, "khung_log", None)

    khoi = [
        ("dai 13 the video mau", dai[:1]),
        ("cot trai (12 nhom cau hinh)", cot_trai[:1]),
        ("khung video lon nhat", [khung_video] if khung_video is not None else []),
        ("cot su kien ben phai", [su_kien] if su_kien is not None else []),
        ("khung nhat ky", [khung_log] if khung_log is not None else []),
    ]
    for ten, ds in khoi:
        if not ds:
            ghi(f"  - {ten}: KHONG tim thay de an")
            continue
        w = ds[0]
        quy = w.grid_info()
        w.grid_remove()
        app.update()
        time.sleep(0.3)
        app.update()
        t = tom_tat(do_keo(app, hwnd, *KICH_THUOC))
        if quy:
            w.grid(**quy)
        app.update()
        if t:
            ghi(f"  - {ten}: tb={t['tb']:.1f} | p90={t['p90']:.1f} | "
                f"max={t['max']:.1f} | tre30={t['tre30']} | tre50={t['tre50']}")
        else:
            ghi(f"  - {ten}: khong lay duoc mau")

    duong = os.path.join(THU_MUC_KQ, "do_giat.txt")
    with open(duong, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    ghi("")
    ghi(f"  da luu: {duong}")
    ghi("=" * 78)

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
