"""
Do GIL starvation: 1 thread nap cam_ai_core (torch) trong khi thread khac
giai mao "vong lap UI" va do tre lon nhat cua no.

Day la mo phong trinh tuong trung app_qt.py: uvicorn chay o thread daemon,
vong lap Qt chay o thread chinh => ca hai can GIL. Neu thread nap model giu
GIL lau, thread UI bi treo => cua so "khong phan hoi".

Chay:
    .venv\\Scripts\\python.exe _kk_do_gil.py
"""

from __future__ import annotations

import os
import sys
import threading
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)


def main() -> int:
    tre = []
    dung = threading.Event()
    buoi = [0.0]

    def vong_lap_ui() -> None:
        """Giong vong lap Qt: lien tuc lam viec nhe, do gap giua 2 lan."""
        lan_cuoi = time.perf_counter()
        while not dung.is_set():
            buoi[0] += 1
            time.sleep(0.005)                 # 200 lan/s
            luc = time.perf_counter()
            tre.append(luc - lan_cuoi)
            lan_cuoi = luc

    def nap_model() -> None:
        t0 = time.perf_counter()
        import cam_ai_core  # noqa: F401
        print("[nap] import cam_ai_core xong sau %.2f s" % (time.perf_counter() - t0))

    t_ui = threading.Thread(target=vong_lap_ui, daemon=True)
    t_ui.start()
    time.sleep(1.0)                          # 1s baseline

    tre_baseline = list(tre)
    tre.clear()

    t0 = time.perf_counter()
    t_model = threading.Thread(target=nap_model, daemon=True)
    t_model.start()
    t_model.join()
    nap_lau = time.perf_counter() - t0

    time.sleep(0.5)
    dung.set()
    t_ui.join(timeout=2)

    tre_nap = sorted(tre)
    print("")
    print("=" * 72)
    print("KET QUA DO GIL")
    print("=" * 72)
    print("Baseline (khong nap model):")
    print("  so vong lap           : %d" % len(tre_baseline))
    print("  tre lon nhat          : %.3f s" % max(tre_baseline))
    print("Nap model (%.2f s):" % nap_lau)
    print("  so vong lap           : %d" % len(tre_nap))
    if tre_nap:
        print("  tre lon nhat          : %.3f s   <-- UI TREO BAO LAU" % tre_nap[-1])
        print("  tre p95               : %.3f s" % tre_nap[int(len(tre_nap) * 0.95)])
        print("  so lan tre > 0.5s     : %d" % len([t for t in tre_nap if t > 0.5]))
        print("  so lan tre > 2.0s     : %d" % len([t for t in tre_nap if t > 2.0]))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
