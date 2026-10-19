# -*- coding: utf-8 -*-
"""
CamAI v3.3 - KIEM CHUNG DOC LAP 3 TINH NANG MOI TRONG GUI (coordinator tu chay).

Kiem chung 3 nhom tinh nang agent A vua them vao `gui.py`:
  [1] TACH 2 O XEM VIDEO: "Xem truc tiep" + "Xem khung hinh ket qua"
  [2] NUT "DANG KY NGUOI QUEN" - chay THAT tren 1 anh co mat
  [3] NUT "DOC BIEN SO THU" - chay THAT tren 1 anh bien so gia
  [4] NUT "VE VUNG NGAY TAI DAY" - module canvas -> ghi file vung.txt

Nguyen tac: KHONG tin bao cao cua agent. Moi muc deu:
  - chay code THAT cua GUI (patch hoi thoai file / ten nguoi de khong can
    nguoi dung bam tay),
  - kiem tra FILE/SO DO doc duoc tu dia,
  - chup anh va TOI TU XEM bang mat.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_gui_b3.py

File nay KHONG sua file nao khac trong repo (chi tao file trong _kk_out/).
"""

from __future__ import annotations

import ctypes
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


THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "kiem_gui_b3")
IMG_FULL = os.path.join(THU_MUC_KQ, "b3_full.png")
IMG_HANG = os.path.join(THU_MUC_KQ, "b3_hang_2_o_xem.png")
VIDEO_VAO = os.path.join(APP_DIR, "video_test.mp4")
ANH_MAT = os.path.join(APP_DIR, "known_faces", "An", "01.jpg")
ANH_BIEN_SO = os.path.join(APP_DIR, "_kiem_chung", "plate_gia",
                           "vn_2hang_30A_12345.png")
HET_GIOI_MOI = 120.0

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def rect_cua_so(app):
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    if hwnd:
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    return rc


def do_anh(anh):
    from PIL import ImageStat

    rgb = anh.convert("RGB")
    mau = rgb.getcolors(maxcolors=2_000_000)
    stat = ImageStat.Stat(rgb)
    return {
        "kich_thuoc": anh.size,
        "so_mau": len(mau) if mau is not None else -1,
        "sang_tb": round(sum(stat.mean) / 3.0, 2),
        "max": max(rgb.getextrema()[i][1] for i in range(3)),
        "min": min(rgb.getextrema()[i][0] for i in range(3)),
    }


def chup(app, duong_dan):
    from PIL import ImageGrab

    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    app.update()
    app.update_idletasks()
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.4)
    app.update()
    rc = rect_cua_so(app)
    anh = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                         all_screens=True)
    anh.save(duong_dan)
    return anh, rc


def cat_vung(app, anh, rc, widget, duong_dan):
    """Cat dung vung widget trong anh chup cua so -> luu + do."""
    x0 = widget.winfo_rootx() - rc.left
    y0 = widget.winfo_rooty() - rc.top
    w = widget.winfo_width()
    h = widget.winfo_height()
    if w <= 1 or h <= 1:
        return None
    cat = anh.crop((x0, y0, x0 + w, y0 + h))
    cat.save(duong_dan)
    return do_anh(cat)


def bom_app(app, giay):
    """BOM EVENT LOOP TK trong `giay` giay (xử lý hàng đợi + after())."""
    moc = time.monotonic()
    while time.monotonic() - moc < giay:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        time.sleep(0.01)


def cho_den(app, tu_khoa, giay=HET_GIOI_MOI):
    """Bơm event loop cho tới khi nhật ky GUI chua tu khoa (hoac het gioi)."""
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
    return [d.rstrip() for d in app.log_box.get("1.0", "end").splitlines() if d.strip()]


def chay() -> int:
    import customtkinter as ctk

    import gui as gui_module
    from gui import CamAIGui

    os.makedirs(THU_MUC_KQ, exist_ok=True)
    # Thu muc tam cho kiem chung (khong lam doi du lieu that cua anh)
    faces_dir = os.path.join(THU_MUC_KQ, "known_faces_test")
    bien_so_dir = os.path.join(THU_MUC_KQ, "anh_bien_so")
    vung_file = os.path.join(THU_MUC_KQ, "vung_test.txt")
    os.makedirs(faces_dir, exist_ok=True)
    os.makedirs(bien_so_dir, exist_ok=True)

    in_ky("=" * 78)
    in_ky("CamAI v3.3 - KIEM CHUNG DOC LAP 3 TINH NANG MOI TRONG GUI")
    in_ky("=" * 78)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()
    in_ky(f"  cua so: {app.title()!r} ({app.winfo_width()}x{app.winfo_height()})")

    ket_qua = []

    # ===================================================== [1] 2 O XEM VIDEO
    in_ky("")
    in_ky("[1] TACH 2 O XEM VIDEO")
    text1 = str(app.chk_xem_video.cget("text"))
    text2 = str(app.chk_xem_ket_qua.cget("text"))
    mac_dinh1 = app.v_xem_video.get()
    mac_dinh2 = app.v_xem_ket_qua.get()
    in_ky(f"  chk_xem_video     : {text1!r} (mac dinh v_xem_video={mac_dinh1!r})")
    in_ky(f"  chk_xem_ket_qua   : {text2!r} (mac dinh v_xem_ket_qua={mac_dinh2!r})")
    ok1 = (text1 == "Xem trực tiếp"
           and text2 == "Xem khung hình kết quả"
           and mac_dinh1 == "1" and mac_dinh2 == "1")
    in_ky(f"  -> {'PASS' if ok1 else 'FAIL'}")

    anh, rc = chup(app, IMG_FULL)
    tt = cat_vung(app, anh, rc, app.chk_xem_video, IMG_HANG)
    in_ky(f"  [chup] cua so -> {IMG_FULL} {do_anh(anh)['kich_thuoc']}")
    if tt:
        in_ky(f"  [chup] vung 2 o xem -> {IMG_HANG} | mau={tt['so_mau']} | "
              f"sang tb={tt['sang_tb']} | max={tt['max']} min={tt['min']}")
    ket_qua.append(("2 o xem video", ok1))

    # ============================================ [2] DANG KY NGUOI QUEN
    in_ky("")
    in_ky("[2] NUT 'DANG KY NGUOI QUEN' - chay THAT tren anh co mat")
    app.v_faces_dir.set(faces_dir)
    ten_nguoi = "KiemThuV33"
    thu_muc_nguoi = os.path.join(faces_dir, ten_nguoi)
    if os.path.isdir(thu_muc_nguoi):
        shutil.rmtree(thu_muc_nguoi)

    goc_ask = gui_module.filedialog.askopenfilename
    goc_hoi_ten = CamAIGui._hoi_ten_nguoi_quen
    goc_yesno = gui_module.messagebox.askyesno
    try:
        gui_module.filedialog.askopenfilename = lambda *a, **k: ANH_MAT
        gui_module.messagebox.askyesno = lambda *a, **k: True
        CamAIGui._hoi_ten_nguoi_quen = lambda self: ten_nguoi
        app._mo_dang_ky_nguoi_quen()
        co, giay = cho_den(app, "Số ảnh đã lưu")
        bom_app(app, 1.0)
    finally:
        gui_module.filedialog.askopenfilename = goc_ask
        gui_module.messagebox.askyesno = goc_yesno
        CamAIGui._hoi_ten_nguoi_quen = goc_hoi_ten

    anh_trong_thu_muc = []
    if os.path.isdir(thu_muc_nguoi):
        anh_trong_thu_muc = [f for f in os.listdir(thu_muc_nguoi)
                             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    in_ky(f"  thu muc tao ra   : {thu_muc_nguoi} "
          f"| so anh = {len(anh_trong_thu_muc)} -> {anh_trong_thu_muc}")
    dong = dong_log(app)
    in_ky("  6 dong nhat ky cuoi:")
    for d in dong[-6:]:
        in_ky(f"      {d}")
    ok2 = len(anh_trong_thu_muc) > 0
    in_ky(f"  -> {'PASS' if ok2 else 'FAIL'} "
          f"(co thu muc va anh that: {ok2})")
    ket_qua.append(("dang ky nguoi quen", ok2))

    # ============================================= [3] DOC BIEN SO THU
    in_ky("")
    in_ky("[3] NUT 'DOC BIEN SO THU' - chay THAT tren anh bien so gia")
    app.v_bien_so_dir.set(bien_so_dir)
    app.v_bien_so_vung.set("")
    try:
        gui_module.filedialog.askopenfilename = lambda *a, **k: ANH_BIEN_SO
        app._mo_doc_bien_so_thu()
        bom_app(app, 1.0)
        co, giay = cho_den(app, "biển số:")
        bom_app(app, 1.0)
    finally:
        gui_module.filedialog.askopenfilename = goc_ask

    dong = dong_log(app)
    dong_bien_so = [d for d in dong if "biển số:" in d.lower()]
    in_ky(f"  anh bien so       : {ANH_BIEN_SO}")
    for d in dong[-6:]:
        in_ky(f"      {d}")
    anh_crop = [f for f in os.listdir(bien_so_dir)] if os.path.isdir(bien_so_dir) else []
    in_ky(f"  anh crop da luu   : {anh_crop}")
    ok3 = len(dong_bien_so) > 0
    in_ky(f"  -> {'PASS' if ok3 else 'FAIL'} "
          f"(nhat ky co dong ket qua bien so: {ok3})")
    ket_qua.append(("doc bien so thu", ok3))

    # ============================================ [4] VE VUNG TRONG GUI
    in_ky("")
    in_ky("[4] NUT 'VE VUNG NGAY TAI DAY' -> ghi file vung.txt")
    app.v_video.set(VIDEO_VAO)
    app.v_vung_file.set(vung_file)
    if os.path.isfile(vung_file):
        os.remove(vung_file)
    import ve_vung_gui

    goc_canvas = ve_vung_gui.ve_vung_trong_gui
    try:
        ve_vung_gui.ve_vung_trong_gui = (
            lambda master, anh_bgr, nguon="", log=None: (0.2, 0.15, 0.8, 0.95))
        app._ve_vung_ngay_tai_day()
        co, giay = cho_den(app, "Đã lưu vùng")
        bom_app(app, 1.0)
    finally:
        ve_vung_gui.ve_vung_trong_gui = goc_canvas

    noi_dung_vung = ""
    if os.path.isfile(vung_file):
        with open(vung_file, "r", encoding="utf-8") as f:
            noi_dung_vung = f.read()
    in_ky(f"  file vung ghi ra  : {vung_file} | ton tai = "
          f"{os.path.isfile(vung_file)}")
    in_ky("  noi dung file:")
    for d in noi_dung_vung.splitlines():
        in_ky(f"      {d}")
    dong = dong_log(app)
    for d in dong[-3:]:
        in_ky(f"      {d}")
    ok4 = ("0.2000 0.1500 0.8000 0.9500" in noi_dung_vung)
    in_ky(f"  -> {'PASS' if ok4 else 'FAIL'} (file vung co toa do tuong doi dung)")
    ket_qua.append(("ve vung trong GUI", ok4))

    # ------------------------------------------------------------------ tong
    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA KIEM CHUNG 3 TINH NANG MOI")
    in_ky("=" * 78)
    for ten, ok in ket_qua:
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}")
    tong = all(ok for _, ok in ket_qua)
    in_ky(f"  TONG KET: {'PASS' if tong else 'FAIL'}")
    in_ky(f"  anh chup cua so : {IMG_FULL}")
    in_ky(f"  anh vung 2 o xem: {IMG_HANG}")
    in_ky("=" * 78)

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if tong else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
