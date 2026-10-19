# -*- coding: utf-8 -*-
"""
CamAI - KIEM CHUNG LOI "main thread is not in main loop" khi DANG KY NGUOI QUEN.

Kich ban (giong het coordinator da tai bien):
  1. Dung `CamAIGui` that.
  2. Patch `gui.filedialog.askopenfilename` -> tra ve anh co mat that.
  3. Patch `CamAIGui._hoi_ten_nguoi_quen` -> tra ve ten thu.
  4. `app.v_faces_dir` -> thu muc TAM trong `_kk_out/` (khong dung
     `known_faces` that cua anh).
  5. Bam `app._mo_dang_ky_nguoi_quen()`, BOM EVENT LOOP bang `app.update()`
     (KHONG dung `mainloop()`) cho toi khi nhat ky co dong "Đã học được:".
     -> Voi `update()`, moi loi goi Tk tu thread nen deu nem
        "main thread is not in main loop" -> script nay bat duoc loi that.

DIEU KIEN PASS:
  - nhat ky CO dong "> Đã học được:",
  - nhat ky KHONG co dong nao chua "main thread is not in main loop",
  - thu muc nguoi moi co it nhat 1 file .jpg.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_dang_ky_nguoi_quen_fix.py

File nay KHONG sua file nao khac trong repo (chi tao file trong _kk_out/).
"""

from __future__ import annotations

import os
import shutil
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


THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "dang_ky_fix")
FACES_DIR = os.path.join(THU_MUC_KQ, "known_faces_test")
ANH_MAT = os.path.join(APP_DIR, "known_faces", "An", "01.jpg")
TEN_NGUOI = "KiemThuFix"
HET_GIOI = 120.0
CHUOI_LOI = "main thread is not in main loop"


def bom_app(app, giay: float) -> None:
    """BOM EVENT LOOP TK trong `giay` giay (xử lý hàng đợi + after())."""
    moc = time.monotonic()
    while time.monotonic() - moc < giay:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        time.sleep(0.02)


def cho_den(app, tu_khoa: str, giay: float = HET_GIOI):
    """Bơm event loop cho tới khi nhat ky GUI chua tu khoa (hoac het gioi)."""
    moc = time.monotonic()
    while time.monotonic() - moc < giay:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        noi_dung = app.log_box.get("1.0", "end")
        if tu_khoa.lower() in noi_dung.lower():
            return True, time.monotonic() - moc
        time.sleep(0.02)
    return False, time.monotonic() - moc


def dong_log(app):
    return [d.rstrip() for d in app.log_box.get("1.0", "end").splitlines()
            if d.strip()]


def chay() -> int:
    import customtkinter as ctk

    import gui as gui_module
    from gui import CamAIGui

    os.makedirs(FACES_DIR, exist_ok=True)
    thu_muc_nguoi = os.path.join(FACES_DIR, TEN_NGUOI)
    if os.path.isdir(thu_muc_nguoi):
        shutil.rmtree(thu_muc_nguoi)

    in_ky("=" * 78)
    in_ky("CamAI - KIEM CHUNG: dang ky nguoi quen (thread nen -> luong UI)")
    in_ky("=" * 78)
    in_ky(f"  anh vao      : {ANH_MAT} (ton tai = {os.path.isfile(ANH_MAT)})")
    in_ky(f"  faces_dir    : {FACES_DIR}")
    in_ky(f"  ten nguoi    : {TEN_NGUOI}")
    in_ky(f"  thu muc ngm  : {thu_muc_nguoi}")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.5)
    app.update()

    # --- chuan bi: tro thu muc tam + patch hoi thoai ------------------------
    app.v_faces_dir.set(FACES_DIR)

    goc_ask = gui_module.filedialog.askopenfilename
    goc_yesno = gui_module.messagebox.askyesno
    goc_hoi_ten = CamAIGui._hoi_ten_nguoi_quen
    try:
        gui_module.filedialog.askopenfilename = lambda *a, **k: ANH_MAT
        gui_module.messagebox.askyesno = lambda *a, **k: True
        CamAIGui._hoi_ten_nguoi_quen = lambda self: TEN_NGUOI

        in_ky("")
        in_ky("--- BAM 'DANG KY NGUOI QUEN' (bom app.update(), KHONG mainloop) ---")
        app._mo_dang_ky_nguoi_quen()
        co, giay = cho_den(app, "Đã học được:")
        in_ky(f"  cho 'Đã học được:' -> co={co} sau {giay:.1f}s")
        # them thoi gian de thread nap lai danh sach (neu co) ghi xong
        bom_app(app, 3.0)
    finally:
        gui_module.filedialog.askopenfilename = goc_ask
        gui_module.messagebox.askyesno = goc_yesno
        CamAIGui._hoi_ten_nguoi_quen = goc_hoi_ten

    # --- kiem tra file that trong thu muc nguoi ----------------------------
    anh_trong_thu_muc = []
    if os.path.isdir(thu_muc_nguoi):
        anh_trong_thu_muc = [f for f in os.listdir(thu_muc_nguoi)
                             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    in_ky("")
    in_ky(f"  thu muc tao ra   : {thu_muc_nguoi}")
    in_ky(f"  so anh trong do  : {len(anh_trong_thu_muc)} -> {anh_trong_thu_muc}")

    dong = dong_log(app)
    in_ky("")
    in_ky("--- 10 DONG NHAT KY CUOI ---")
    for d in dong[-10:]:
        in_ky(f"      {d}")
    in_ky("--- HET NHAT KY ---")

    # --- ket luan ----------------------------------------------------------
    dong_hoc = [d for d in dong if "Đã học được:" in d]
    dong_loi = [d for d in dong if CHUOI_LOI in d]

    ok_hoc = len(dong_hoc) > 0
    ok_khong_loi = len(dong_loi) == 0
    ok_anh = len(anh_trong_thu_muc) > 0
    ok = ok_hoc and ok_khong_loi and ok_anh

    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA")
    in_ky("=" * 78)
    in_ky(f"  [{'PASS' if ok_hoc else 'FAIL'}] nhat ky co dong '> Đã học được:'")
    in_ky(f"  [{'PASS' if ok_khong_loi else 'FAIL'}] nhat ky KHONG co "
          f"'{CHUOI_LOI}'")
    in_ky(f"  [{'PASS' if ok_anh else 'FAIL'}] thu muc nguoi moi co anh that")
    if dong_hoc:
        in_ky(f"      -> {dong_hoc[-1]}")
    if dong_loi:
        in_ky(f"      -> {dong_loi[-1]}")
    in_ky(f"  TONG KET: {'PASS' if ok else 'FAIL'}")
    in_ky("=" * 78)

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
