# -*- coding: utf-8 -*-
r"""
CamAI - IN STACK PYTHON TRONG LUC APP "GIAT" (lan keo dau tien).

Dung faulthandler.dump_traceback_later de in stack cua tat ca thread khi
app dang tre -> biet chinh xac khoi ma nao lam tre UI thread.

Chay:
    .venv\Scripts\python.exe -W ignore _kk_do_giat_stack.py
"""

from __future__ import annotations

import ctypes
import faulthandler
import os
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

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.MoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                           ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
u32.MoveWindow.restype = ctypes.c_int
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int

THU_MUC = os.path.join(APP_DIR, "_kk_out", "agent_fix_giat")
os.makedirs(THU_MUC, exist_ok=True)
FILE_STACK = os.path.join(THU_MUC, "stack_khi_giat.txt")


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


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

    print("bat faulthandler, keo lan 1 ...")
    with open(FILE_STACK, "w", encoding="utf-8", newline="\n") as f:
        faulthandler.dump_traceback_later(0.20, repeat=True, file=f)
        g = do_keo(app, hwnd, rong, cao)
        faulthandler.cancel_dump_traceback_later()

    lon = sorted((x for x in g if x > 30), reverse=True)
    print(f"  gap > 30ms: {len(lon)} | lon nhat = {[round(x) for x in lon[:10]]}")
    print(f"  stack ghi tai: {FILE_STACK}")
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
