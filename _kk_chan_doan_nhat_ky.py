# -*- coding: utf-8 -*-
"""
CamAI - CHAN DOAN LOI: nhat ky GUI thieu dong "Ket qua:" / "Bao cao:".

Chay pipeline that trong GUI, roi IN TOAN BO nhat ky + bat loi callback Tk.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_chan_doan_nhat_ky.py
"""

from __future__ import annotations

import os
import sys
import time
import traceback

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


VIDEO_VAO = os.path.join(APP_DIR, "video_test.mp4")
THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "chan_doan")
os.makedirs(THU_MUC_KQ, exist_ok=True)


def chay():
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()

    app.v_video.set(VIDEO_VAO)
    app.v_output.set(THU_MUC_KQ)
    app.v_phat_hien.set("1")
    app.v_face.set("1")
    app.v_face_every.set("3")
    app.v_model.set("yolo11n.pt")
    app.v_thiet_bi.set("Tự động")
    app.update()

    app.btn_chay.invoke()
    app.update()
    in_ky(f"  busy sau khi bam = {app.busy}")

    moc = time.monotonic()
    while time.monotonic() - moc < 180:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            in_ky("LOI khi bom event loop:")
            in_ky(traceback.format_exc())
            break
        if not app.busy and app.result is not None:
            break
        time.sleep(0.05)
    time.sleep(1.5)
    app.update()

    in_ky("")
    in_ky("=" * 78)
    in_ky("TOAN BO NHAT KY GUI")
    in_ky("=" * 78)
    for i, dong in enumerate(app.log_box.get("1.0", "end").splitlines()):
        in_ky(f"  {i + 1:>3}| {dong}")
    in_ky("=" * 78)
    in_ky(f"  app.busy  = {app.busy}")
    in_ky(f"  app.result = {type(app.result).__name__}")
    in_ky(f"  co dong 'Ket qua:' = "
          f"{'Kết quả:' in app.log_box.get('1.0', 'end')}")
    in_ky(f"  co dong 'Bao cao:' = "
          f"{'Báo cáo:' in app.log_box.get('1.0', 'end')}")
    in_ky(f"  hang doi con lai = {app.queue.qsize()}")
    in_ky("=" * 78)

    try:
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(chay())
