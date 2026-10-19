"""Do chi phi KEO khi pipeline dang chay (queue day log + progress).
KHONG sua gi trong gui.py."""
from __future__ import annotations

import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import customtkinter as ctk

from gui import CamAIGui


def dem_tong(w):
    return 1 + sum(dem_tong(c) for c in w.winfo_children())


def do_keo(app, nham=40, buoc=4):
    app.update()
    x, y, w, h = app.winfo_x(), app.winfo_y(), app.winfo_width(), app.winfo_height()
    mau = []
    for i in range(nham):
        t0 = time.perf_counter()
        app.geometry(f"{w}x{h}+{x + (i % 2) * buoc}+{y + i}")
        app.update_idletasks()
        mau.append((time.perf_counter() - t0) * 1000.0)
    mau.sort()
    return {"TB": round(statistics.mean(mau), 2), "median": round(statistics.median(mau), 2),
            "p90": round(mau[int(len(mau) * .9) - 1], 2), "max": round(mau[-1], 2)}


def do_1_tick_pump(app, so_tick=20):
    """Thoi gian thuc cua 1 vong _hut_hang_doi khi hang doi co tac nhan."""
    app.update()
    mau = []
    for _ in range(so_tick):
        t0 = time.perf_counter()
        app._hut_hang_doi()
        mau.append((time.perf_counter() - t0) * 1000.0)
    mau.sort()
    return {"TB": round(statistics.mean(mau), 2), "max": round(mau[-1], 2)}


def main() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    for _n, nhom in app.danh_sach_nhom():
        nhom.dat_mo(True)
    app.update_idletasks()
    print(f"widget tong = {dem_tong(app)}")
    print(f"\n[A] KEO khi IDLE (hang doi rong)")
    print("   ", do_keo(app))
    print(f"   1 tick pump rong : {do_1_tick_pump(app)}")

    # --- dap 2000 dong log nhu that khi chay video co thanh tien trinh ---
    for i in range(2000):
        app.queue.put(("log", f"  frame {i}/2500 | Nguoi: 3 | Mat: 1 | Vao: 2 | Ra: 1"))
    app.update()
    print(f"\n[B] KEO khi queue day 2000 dong log (chua xu ly)")
    print("   ", do_keo(app))

    print(f"\n[C] 1 vong _hut_hang_doi xu ly het 2000 dong log")
    print("   ", do_1_tick_pump(app, 3))

    # --- dap them progress nhu that ---
    for i in range(500):
        app.queue.put(("progress", None))
    print(f"\n[D] 1 vong _hut_hang_doi (chi progress rong)")
    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())