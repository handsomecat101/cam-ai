# -*- coding: utf-8 -*-
"""
CamAI - DO THOI GIAN MO APP (coordinator).

Do 3 moc:
  1. import gui            (nap thu vien)
  2. CamAIGui()           (dung giao dien)
  3. update() + cho 1,2s  (ve xong)
Tong = thoi gian den khi cua so san sang.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_do_thoi_gian_mo_app.py
"""

from __future__ import annotations

import os
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


def chay() -> int:
    t0 = time.perf_counter()
    import gui  # noqa: F401
    t1 = time.perf_counter()
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = gui.CamAIGui()
    t2 = time.perf_counter()
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()
    t3 = time.perf_counter()

    print("=" * 70)
    print("CamAI - THOI GIAN MO APP")
    print("=" * 70)
    print(f"  import gui            : {(t1 - t0) * 1000:8.0f} ms")
    print(f"  CamAIGui()           : {(t2 - t1) * 1000:8.0f} ms")
    print(f"  update + cho 1,2 s   : {(t3 - t2) * 1000:8.0f} ms")
    print(f"  TONG den khi cua so   : {(t3 - t0) * 1000:8.0f} ms")
    print("=" * 70)
    try:
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(chay())
