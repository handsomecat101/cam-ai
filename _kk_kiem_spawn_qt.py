"""
Kiem tra process con (multiprocessing spawn) khoi dong duoc khi app chay
trong vo PySide6 (app_qt.py).

LY DO CAN KIEM: kieu "spawn" luon CHAY LAI file main trong process con.
Khi app chay bang app_qt.py, main la app_qt.py => child se import lai
app_qt.py (co PySide6). Script nay mo phong dung tinh huong do:
  - file main nay import app_qt.py (nhu app that)
  - goi web_server._lay_worker() de tao process con
  - chay 1 lan phan tich that qua process con
  - kiem tra ket qua ve duoc (tieng do co "Xong")

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_spawn_qt.py
"""

from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# --- Giong app that: app chay trong vo PySide6 ---------------------------
import app_qt  # noqa: E402,F401  (import lai trong child se chay lai app_qt.py)

import web_server  # noqa: E402

VIDEO = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")


def main() -> int:
    print("=" * 70)
    print("KIEM TRA SPAWN TRONG VO PySide6 (app_qt.py)")
    print("=" * 70)
    ok = web_server._lay_worker()
    print("Tao process con: %s" % ("OK" if ok else "THAT BAI"))
    if not ok:
        return 1

    proc = web_server._WORKER.get("proc")
    print("Process con pid=%s alive=%s" % (proc.pid, proc.is_alive()))

    # Chay 1 lan phan tich that qua process con.
    thu_muc = os.path.join(web_server.THU_MUC_KET_QUA, "kk_spawn_qt")
    os.makedirs(thu_muc, exist_ok=True)
    web_server.TT.reset(os.path.basename(VIDEO), thu_muc)
    threading = __import__("threading")
    t = threading.Thread(
        target=web_server._chay_phan_tich,
        args=(VIDEO, thu_muc, {"input": VIDEO, "conf": 0.25}),
        daemon=True,
    )
    t.start()

    het = time.time() + 180
    giai_doan = []
    while time.time() < het:
        trang = web_server.TT.ban_trang_thai()
        gd = trang.get("giai_doan")
        if gd and (not giai_doan or giai_doan[-1] != gd):
            giai_doan.append(gd)
        if trang.get("xong") or trang.get("loi"):
            break
        time.sleep(0.5)

    trang = web_server.TT.ban_trang_thai()
    print("Giai doan: %s" % " -> ".join(giai_doan))
    print("Xong=%s  Loi=%r" % (trang.get("xong"), trang.get("loi")))
    co_ket_qua = bool(trang.get("ket_qua"))
    print("Co ket qua: %s" % co_ket_qua)
    ok_het = bool(co_ket_qua and not trang.get("loi"))
    print("KET QUA: %s" % ("PASS" if ok_het else "FAIL"))
    return 0 if ok_het else 1


if __name__ == "__main__":
    sys.exit(main())
