"""Do CHI PHI 1 VONG _hut_hang_doi khi queue day - nap moi truoc moi vong."""
from __future__ import annotations

import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import customtkinter as ctk

from cam_ai_core import Progress
from gui import CamAIGui


def nap(app, n):
    for i in range(n):
        app.queue.put(("log", f"  frame {i}/2500 | Nguoi: 3 | Mat: 1 | Vao: 2 | Ra: 1"))


def do_pump(app, n_log, so_tick=5):
    mau = []
    for _ in range(so_tick):
        nap(app, n_log)
        t0 = time.perf_counter()
        app._hut_hang_doi()
        mau.append((time.perf_counter() - t0) * 1000.0)
    return {"TB": round(statistics.mean(mau), 2), "max": round(max(mau), 2)}


def do_pump_progress(app, so_tick=10):
    mau = []
    for i in range(so_tick):
        for k in range(50):
            app.queue.put(("progress", Progress(
                frame_index=i * 50 + k, total_frames=2500, so_nguoi=3, so_mat=1,
                vao=2, ra=1, trong_vung=1, vi_pham=1, canh_lau=0,
                nhan_dien="An")))
        t0 = time.perf_counter()
        app._hut_hang_doi()
        mau.append((time.perf_counter() - t0) * 1000.0)
    return {"TB": round(statistics.mean(mau), 2), "max": round(max(mau), 2)}


def main() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    print("=== CHI PHI 1 VONG _hut_hang_doi (chu ky PUMP_MS = 120ms) ===")
    for n in (300, 1000, 3000, 8000):
        print(f"  {n:>5} dong log  -> {do_pump(app, n)} ms")
    print(f"  50 su kien progress -> {do_pump_progress(app)} ms")
    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())