# -*- coding: utf-8 -*-
"""
CamAI - THI NGHIEM TIM NGUYEN NHAN GIAT KHI KEO CUA SO.

Da biet:
  - chi phi ve lai chi 0.5 ms  -> KHONG phai do ve lai
  - CPU idle = 0              -> KHONG phai app chay nen
  - gia xuat hien o dang "mot lan tre lon" (647 ms) + vai lan > 30 ms

Gia thuyet: khi keo cua so, chuot DI CHUYEN TUONG DOI so voi app -> Tk phat
sinh hang loat su kien <Enter>/<Leave> -> CustomTkinter bat dau ANIMATION
hover tren tung widget -> moi vong animation ve lai canvas -> UI thread bi tre.

Thi nghiem:
  [A] Nen (khong can thay gi)
  [B] Bo tat ca binding <Enter>/<Leave> tren moi widget
  [C] An dai 13 the video mau (giam so widget)
  [D] Bo binding + an dai video mau

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_do_giat_thu_nghiem.py
"""

from __future__ import annotations

import ctypes
import os
import statistics
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


def do_keo(app, hwnd, rong, cao, giay=3.0):
    gaps = []
    trang_thai = {"buoi_dau": time.perf_counter(), "het": False}

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
        return "khong co mau"
    sap = sorted(gaps)
    p90 = sap[-max(1, len(sap) // 10)]
    return (f"n={len(gaps):3d} | tb={statistics.mean(gaps):6.1f} | "
            f"tb50={sap[len(sap)//2]:6.1f} | p90={p90:6.1f} | max={max(gaps):7.1f} | "
            f">30ms={sum(1 for g in gaps if g > 30):2d} | >100ms={sum(1 for g in gaps if g > 100):2d}")


def bo_binding_hover(app):
    """Bo tat ca binding <Enter>/<Leave> tren moi widget (ke ca con)."""
    n = 0
    for w in duyet(app):
        for su_kien in ("<Enter>", "<Leave>", "<Motion>"):
            try:
                if w.bind(su_kien):
                    w.unbind(su_kien)
                    n += 1
            except Exception:  # noqa: BLE001
                pass
    return n


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
    in_ky("CamAI - THI NGHIEM TIM NGUYEN NHAN GIAT KHI KEO CUA SO")
    in_ky("=" * 78)
    in_ky(f"  tong widget = {len(duyet(app))}")

    # [A] nen
    g = do_keo(app, hwnd, rong, cao)
    in_ky(f"  [A] NEN (khong can thay gi)          {tom_tat(g)}")

    # tim dai video mau
    dai = []
    for w in duyet(app):
        if type(w).__name__ != "CTkFrame":
            continue
        for con in w.winfo_children():
            try:
                if "Video mẫu" in str(con.cget("text")):
                    dai.append(w)
                    break
            except Exception:  # noqa: BLE001
                pass

    # [B] bo binding hover
    n = bo_binding_hover(app)
    app.update()
    time.sleep(0.3)
    app.update()
    g = do_keo(app, hwnd, rong, cao)
    in_ky(f"  [B] BO BINDING HOVER ({n} binding)  {tom_tat(g)}")

    # [C] an dai video mau (bo binding van con)
    luu = []
    for w in dai[:1]:
        q = w.grid_info()
        w.grid_remove()
        luu.append((w, q))
    app.update()
    time.sleep(0.3)
    app.update()
    g = do_keo(app, hwnd, rong, cao)
    in_ky(f"  [C] + AN DAI VIDEO MAU             {tom_tat(g)}")

    # khoi lai binding de so sanh cong bang
    for w, q in luu:
        if q:
            w.grid(**q)
    app.update()
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
