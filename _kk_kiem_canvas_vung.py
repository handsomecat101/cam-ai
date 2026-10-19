# -*- coding: utf-8 -*-
"""
CamAI - KIEM CHUNG DOC LAP module ve_vung_gui (coordinator tu chay).

Muc tieu: chung minh ham `ve_vung_trong_gui` THAT SU ve duoc vung bang chuot
trong mot cua so con, va tra ve toa do TUONG DOI 0..1 dung voi vung da keo.

Ky thuat:
  - Ham la MODAL (wait_window) -> goi tren UI thread.
  - Gia lap chuot bang `event_generate` tren widget Canvas (neu tim thay).
  - Neu gia lap chuot that KHONG duoc (vi du CustomTkinter bo qua su kien toa do),
    thu tiep tiep bang cach goi truc tiep cac callback noi bo ma module da
    dang ky (bien PUBLIC_TEST_CALLBACKS neu module co) -> phai bao cao
    trung thuc kieu kiem chung nao that, kieu nao qua noi bo.
  - Ket qua: toa do 4 so float trong 0..1, khop vung da keo (sai so <= 0.03).

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_canvas_vung.py

File nay KHONG sua file nao khac trong repo.
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


THU_MUC_ANH = os.path.join(APP_DIR, "_kk_out", "kiem_canvas")
ANH_KET_QUA = os.path.join(THU_MUC_ANH, "canvas_vung.png")


def tao_anh_gia():
    """Anh gia 640x480 co vai hinh vuon de kéo vung (chi de kiem chung UI)."""
    import numpy as np

    anh = np.full((480, 640, 3), 60, dtype=np.uint8)
    anh[100:200, 150:330] = (40, 200, 240)      # vung xanh
    anh[300:380, 420:560] = (200, 80, 40)      # vung cam
    return anh


def tim_canvas(widget, ket_qua=None):
    """Tim widget Canvas (tkinter) trong cay widget."""
    import tkinter

    if ket_qua is None:
        ket_qua = []
    for con in widget.winfo_children():
        if isinstance(con, tkinter.Canvas):
            ket_qua.append(con)
        tim_canvas(con, ket_qua)
    return ket_qua


def tim_nut_theo_text(widget, chu_can_tim, ket_qua=None):
    """Tim CTkButton co text chua `chu_can_tim`."""
    import customtkinter as ctk

    if ket_qua is None:
        ket_qua = []
    for con in widget.winfo_children():
        if isinstance(con, ctk.CTkButton):
            try:
                if chu_can_tim.lower() in str(con.cget("text")).lower():
                    ket_qua.append(con)
            except Exception:  # noqa: BLE001
                pass
        tim_nut_theo_text(con, chu_can_tim, ket_qua)
    return ket_qua


def chup_toan_man_hinh(duong_dan):
    from PIL import ImageGrab

    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    anh = ImageGrab.grab(all_screens=True)
    anh.save(duong_dan)
    return anh.size


def chup_cua_so_con(win, duong_dan):
    """Chup DUNG cua so con (theo HWND that), khong phai ca man hinh.

    Phai dua cua so len tren truoc, neu no bi cua so khac che (da xay ra 1 lan:
    grab ca man hinh ra anh trinh duyet, khong thay hop thoai).
    """
    import ctypes

    from PIL import ImageGrab

    u32 = ctypes.windll.user32
    u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    u32.GetAncestor.restype = ctypes.c_void_p
    u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    u32.GetWindowRect.restype = ctypes.c_int

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    try:
        win.attributes("-topmost", True)
        win.lift()
        win.focus_force()
        win.update()
        time.sleep(0.4)
        win.update()
    except Exception:  # noqa: BLE001
        pass
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(win.winfo_id())), 2)
    if not hwnd:
        raise RuntimeError("khong lay duoc HWND cua so con")
    u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    anh = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                          all_screens=True)
    anh.save(duong_dan)
    return anh.size, (rc.left, rc.top, rc.right, rc.bottom)


def chay() -> int:
    import customtkinter as ctk

    from ve_vung_gui import ve_vung_trong_gui

    os.makedirs(THU_MUC_ANH, exist_ok=True)

    in_ky("=" * 78)
    in_ky("CamAI - KIEM CHUNG DOC LAP module ve_vung_gui")
    in_ky("=" * 78)
    in_ky(f"  module ve_vung_gui: {ve_vung_trong_gui.__module__}")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Kiem chung canvas ve vung")
    root.geometry("900x650+40+40")
    root.update()

    anh = tao_anh_gia()
    # Vung se gia lap keo: pixel (120, 90) -> (330, 210) tren canvas.
    X1, Y1, X2, Y2 = 120, 90, 330, 210
    trang_thai = {"rect": None, "cua_so": None, "da_chup": False,
                  "rong_canvas": 0, "cao_canvas": 0}

    def bam_vao_canvas():
        """Chay sau 400ms: tim cua so con, gia lap keo chuot, bam nut Luu."""
        try:
            tops = [w for w in root.winfo_children()
                    if w.winfo_class() in ("Toplevel", "CTkToplevel")]
            if not tops:
                in_ky("  [LOI] khong tim thay cua so con (Toplevel)")
                root.destroy()
                return
            win = tops[0]
            trang_thai["cua_so"] = win
            win.update()
            in_ky(f"  tim thay cua so con: {win.title()!r} "
                  f"({win.winfo_width()}x{win.winfo_height()} px)")

            # 2. gia lap keo chuot tren Canvas
            canvases = tim_canvas(win)
            in_ky(f"  so Canvas trong cua so con: {len(canvases)}")
            if canvases:
                cv = canvases[0]
                cv.update_idletasks()
                trang_thai["rong_canvas"] = int(cv.winfo_width())
                trang_thai["cao_canvas"] = int(cv.winfo_height())
                in_ky(f"  kich thuoc Canvas: "
                      f"{trang_thai['rong_canvas']}x{trang_thai['cao_canvas']} px")
                cv.event_generate("<ButtonPress-1>", x=X1, y=Y1)
                cv.event_generate("<B1-Motion>", x=(X1 + X2) // 2, y=(Y1 + Y2) // 2)
                cv.event_generate("<B1-Motion>", x=X2, y=Y2)
                cv.event_generate("<ButtonRelease-1>", x=X2, y=Y2)
                win.update()
                in_ky(f"  da gia lap keo chuot tren Canvas "
                      f"({X1},{Y1}) -> ({X2},{Y2})")

            # 3. chup anh SAU KHI KEO (phai thay hinh chu nhat + dong toa do)
            if not trang_thai["da_chup"]:
                try:
                    kich, toa_do = chup_cua_so_con(win, ANH_KET_QUA)
                    in_ky(f"  [chup] anh cua so ve vung (SAU KHI KEO) -> "
                          f"{ANH_KET_QUA} {kich} toa_do={toa_do}")
                except Exception as exc:  # noqa: BLE001
                    in_ky(f"  [canh bao] chup anh loi: {exc}")
                trang_thai["da_chup"] = True

            # 4. bam nut "Luu vung"
            nut = tim_nut_theo_text(win, "lưu") or tim_nut_theo_text(win, "luu")
            if not nut:
                in_ky("  [LOI] khong tim thay nut 'Luu vung'")
                root.destroy()
                return
            in_ky(f"  bam nut: {nut[0].cget('text')!r} "
                  f"(state={nut[0].cget('state')})")
            try:
                nut[0].invoke()
            except Exception:  # noqa: BLE001
                nut[0].event_generate("<Button-1>")
            win.update()
        except Exception:  # noqa: BLE001
            in_ky("  [LOI] trong bam_vao_canvas:")
            in_ky(traceback.format_exc())
            try:
                root.destroy()
            except Exception:  # noqa: BLE001
                pass

    root.after(500, bam_vao_canvas)

    # Gọi ham MODAL (chan cho tien trinh chinh) - sau khi ket qua se tra ve.
    rect = ve_vung_trong_gui(root, anh, nguon="kiem chung",
                             log=lambda d: in_ky(f"  [module] {d}"))

    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA KIEM CHUNG")
    in_ky("=" * 78)
    in_ky(f"  ket qua ham ve_vung_trong_gui = {rect!r}")

    ok = False
    do_so = ""
    if rect is None:
        do_so = "ham tra None (KHONG ve duoc vung)"
    elif not (isinstance(rect, tuple) and len(rect) == 4):
        do_so = f"ket qua khong phai tuple 4 so: {rect!r}"
    else:
        vals = [float(v) for v in rect]
        trong = all(0.0 <= v <= 1.0 for v in vals)
        x1, y1, x2, y2 = vals
        do_so = (f"toa do tuong doi = ({x1:.4f}, {y1:.4f}, {x2:.4f}, {y2:.4f}) "
                 f"| trong khoang 0..1 = {trong}")
        # Toa do tuong doi tren canvas LUON bang toa do tuong doi tren anh goc
        # (module chia pixel canvas cho ty_le roi chia cho kich thuoc anh goc),
        # nen ky_vong = pixel canvas / kich thuoc canvas THAT.
        rong_cv = trang_thai.get("rong_canvas") or 640
        cao_cv = trang_thai.get("cao_canvas") or 480
        ky_vong = (X1 / rong_cv, Y1 / cao_cv, X2 / rong_cv, Y2 / cao_cv)
        lech = max(abs(a - b) for a, b in zip(vals, ky_vong))
        do_so += (f" | ky vong (theo canvas that {rong_cv}x{cao_cv}) = "
                  f"({ky_vong[0]:.4f}, {ky_vong[1]:.4f}, "
                  f"{ky_vong[2]:.4f}, {ky_vong[3]:.4f}) "
                  f"| lech = {lech:.4f} (cho phep <= 0.03)")
        ok = trong and lech <= 0.03

    in_ky(f"  KET QUA: {'PASS' if ok else 'FAIL'} - {do_so}")
    in_ky(f"  anh chup: {ANH_KET_QUA} "
          f"(co = {os.path.isfile(ANH_KET_QUA)})")
    in_ky("=" * 78)

    try:
        root.destroy()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.2)
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    try:
        chay()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        in_ky("LOI KHONG DO DUOC:")
        in_ky(traceback.format_exc())
        os._exit(2)
