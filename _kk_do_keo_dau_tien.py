# -*- coding: utf-8 -*-
r"""
CamAI - DO "LAN KEO DAU TIEN" (chi lan dau, app vua mo).

Cach do:
  - dung app -> update() -> cho ~1,2 s cho app ve xong
  - 1 thread khac MoveWindow 1px moi ~12 ms trong 3 s (keo qua keo lai)
  - UI thread: after(10 ms) do GAP giua cac callback (gap lon = tre UI)
  - in: n, tb, p90, max, so lan >30 ms, so lan >100 ms

Tien doan cua app khi mo: `CamAIGui()` -> update() -> app da ve xong.
Khung thoi gian do bat dau tu luc import module `gui`.

Chay:
    .venv\Scripts\python.exe -W ignore _kk_do_keo_dau_tien.py
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

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# Moc thoi gian ngay khi bat dau tien bien (truoc khi import gui)
T0 = time.perf_counter()

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.MoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                           ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
u32.MoveWindow.restype = ctypes.c_int
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int

RONG, CAO = 1610, 980


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def duvet(widget, ket_qua=None):
    if ket_qua is None:
        ket_qua = []
    ket_qua.append(widget)
    for con in widget.winfo_children():
        duvet(con, ket_qua)
    return ket_qua


def do_keo(app, hwnd, giay=3.0):
    """Keo cua so qua keo lai, do gap giua cac callback UI."""
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
            u32.MoveWindow(ctypes.c_void_p(hwnd), x + (i % 2), y, RONG, CAO, 0)
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
            f"p90={p90:6.1f} | max={max(gaps):7.1f} | "
            f">30ms={sum(1 for g in gaps if g > 30):3d} | "
            f">100ms={sum(1 for g in gaps if g > 100):3d}")


def cho_app_ve_xong(app, giay=1.2):
    """Cho app 'song' trong `giay` giay: BOM PUMP (update) de cac timer cua app
    (canh giua cua so, hauong ve lai, doc anh xem truoc) chay that nhu khi
    nguoi dung mo app - khong sleep cứng (sleep se lam Tk khong chay timer)."""
    het = time.perf_counter() + giay
    while time.perf_counter() < het:
        app.update()
        time.sleep(0.01)
    app.update()


def tao_app():
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.geometry(f"{RONG}x{CAO}+40+40")
    app.update()
    app.update_idletasks()
    cho_app_ve_xong(app, 1.2)
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    return app, hwnd


def chay() -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    t_import = (time.perf_counter() - T0) * 1000.0

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    t1 = time.perf_counter()
    app = CamAIGui()
    t2 = time.perf_counter()
    app.geometry(f"{RONG}x{CAO}+40+40")
    app.update()
    app.update_idletasks()
    cho_app_ve_xong(app, 1.2)
    t3 = time.perf_counter()

    n_widget = len(duvet(app))
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)

    print("=" * 78)
    print("CAMAI - DO LAN KEO DAU TIEN")
    print("=" * 78)
    print(f"  import gui          : {t_import:8.1f} ms")
    print(f"  CamAIGui()          : {(t2 - t1) * 1000.0:8.1f} ms")
    print(f"  update + cho 1,2 s  : {(t3 - t2) * 1000.0:8.1f} ms")
    print(f"  widget count        : {n_widget}")
    print("-" * 78)

    g = do_keo(app, hwnd)
    print(f"  LAN KEO DAU TIEN    : {tom_tat(g)}")
    lon = sorted((x for x in g if x > 30), reverse=True)[:8]
    print(f"  8 gap lon nhat (ms) : {[round(x) for x in lon]}")
    print("-" * 78)
    print(f"  MO APP (import+tao+update+1,2 s): {t_import + (t3 - t1) * 1000.0:8.1f} ms")
    print("=" * 78)

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
