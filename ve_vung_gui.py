"""
Ve vung canh ngay trong GUI CustomTkinter (ban thay the cho ve_vung.py CLI).

Ham public duy nhat:
    ve_vung_trong_gui(master, anh_bgr, nguon="", log=None) -> tuple | None

Ve vung bang chuot TRONG MAN HINH GUI (khong mo cua so OpenCV rieng), tra ve
toa do TUONG DOI 0.0 - 1.0 cua vung da khoanh: (x1, y1, x2, y2).
Tra ve None neu nguoi dung huy.

Quy tac tep:
- File nay LUON luu o dang UTF-8 KHONG BOM, xuong dong LF thuan.
- Comment / docstring trong code: tieng Viet KHONG dau.
- Chuoi hien thi len cua so: tieng Viet CO dau.
- Khong dung print() lam kenh chinh (GUI chinh bat stdout rieng).
"""

from __future__ import annotations

import tkinter as tk

import cv2
import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk

__all__ = ["ve_vung_trong_gui"]

# --- hang so giao dien ---
TIEU_DE = "Vẽ vùng canh — kéo chuột rồi bấm Lưu"
MAU_VUNG = "#00E5FF"
KICH_THUOC_CUA_SO_TOI_DA = (1200, 800)   # (rong, cao) toi da cua hop thoai
CHIEU_DAI_VUNG_TOI_THIEU = 5               # vung phai it nhat 5 x 5 px moi luu duoc
KHOANG_TRONG = 10                          # khoang cach doc giua khung anh va cua so
CHIEU_CAO_HANG_DIEU_KHIEN = 132            # khoang cho hang toa do + hang nut bam
DO_RONG_HANG_NUT = 130


# ---------------------------------------------------------------- tien ich

def _ghi_log(log, chuoi: str) -> None:
    """Ghi 1 dong thong bao qua callback `log` (neu co). Khong bao gio lam vo."""
    if log is None:
        return
    try:
        log(chuoi)
    except Exception:
        pass


def _chuan_hoa_anh(anh_bgr):
    """Chuyen input thanh anh BGR uint8 3 kenh. Tra None neu khong dung duoc."""
    if anh_bgr is None:
        return None
    try:
        anh = np.asarray(anh_bgr)
    except Exception:
        return None
    if anh.size == 0 or anh.ndim < 2:
        return None
    if anh.ndim == 2:
        anh = cv2.cvtColor(anh.astype(np.uint8), cv2.COLOR_GRAY2BGR)
    elif anh.shape[2] == 4:
        anh = cv2.cvtColor(anh.astype(np.uint8), cv2.COLOR_BGRA2BGR)
    elif anh.shape[2] != 3:
        return None
    if anh.dtype != np.uint8:
        anh = np.clip(anh, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(anh)


def _canh_giua(win, rong: int, cao: int) -> None:
    """Canh cua so o giua man hinh theo kich thuoc yeu cau."""
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
    except Exception:
        sw, sh = 1920, 1080
    x = max(0, (sw - rong) // 2)
    y = max(0, (sh - cao) // 3)
    try:
        win.geometry(f"{rong}x{cao}+{x}+{y}")
    except Exception:
        pass


# ---------------------------------------------------------------- ham chinh

def ve_vung_trong_gui(master, anh_bgr, nguon: str = "", log=None) -> tuple | None:
    """Mo hop thoai ve vung bang chuot NGAY TRONG GUI.

    Tra ve (x1, y1, x2, y2) - TOA DO TUONG DOI 0.0 - 1.0 (float), theo thu tu
    x truoc, y sau. Tra ve None neu nguoi dung huy.
    PHAI goi tren UI THREAD (Toplevel trong Tk khong tao duoc o thread khac).
    """
    anh = _chuan_hoa_anh(anh_bgr)
    if anh is None:
        _ghi_log(log, "Lỗi: không có ảnh hợp lệ để vẽ vùng.")
        return None

    if master is None:
        try:
            master = ctk.CTk()
        except Exception:
            _ghi_log(log, "Lỗi: chưa có cửa sổ chính, không mở được hộp thoại vẽ vùng.")
            return None

    try:
        win = ctk.CTkToplevel(master)
    except Exception as exc:
        _ghi_log(log, f"Lỗi: không mở được hộp thoại vẽ vùng ({exc}).")
        return None

    # --- kich thuoc anh goc va anh thu nho cho vua khung ---
    chieu_cao_goc, chieu_rong_goc = int(anh.shape[0]), int(anh.shape[1])
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
    except Exception:
        sw, sh = 1920, 1080
    rong_toi_da = min(KICH_THUOC_CUA_SO_TOI_DA[0], sw - 60)
    cao_toi_da = min(KICH_THUOC_CUA_SO_TOI_DA[1], sh - 100)
    cho_phep_rong = max(120, rong_toi_da - 2 * KHOANG_TRONG)
    cho_phep_cao = max(90, cao_toi_da - CHIEU_CAO_HANG_DIEU_KHIEN)
    ty_le = min(cho_phep_rong / chieu_rong_goc, cho_phep_cao / chieu_cao_goc, 1.0)
    if ty_le <= 0:
        ty_le = 1.0
    anh_hien = cv2.resize(anh, (max(1, int(chieu_rong_goc * ty_le)),
                                 max(1, int(chieu_cao_goc * ty_le))),
                          interpolation=cv2.INTER_AREA)
    rong_hien, cao_hien = anh_hien.shape[1], anh_hien.shape[0]

    # --- trang thai vung (don vi: pixel tren canvas) ---
    sel = {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "keo": False,
           "x_keo": 0, "y_keo": 0, "hinh": None, "hop_le": False}
    ket_qua = {"value": None}
    da_dong = False

    win.title(TIEU_DE)
    try:
        win.transient(master)
    except Exception:
        pass
    win.grid_columnconfigure(0, weight=1)
    win.grid_rowconfigure(0, weight=1)

    khung_anh = ctk.CTkFrame(win, fg_color="transparent")
    khung_anh.grid(row=0, column=0, sticky="nsew", padx=KHOANG_TRONG, pady=(KHOANG_TRONG, 0))

    canvas = tk.Canvas(khung_anh, width=rong_hien, height=cao_hien,
                       bg="#1b1b1b", highlightthickness=0, bd=0,
                       name="ve_vung_canvas")
    canvas.grid(row=0, column=0)

    # --- hang thong tin ---
    khung_info = ctk.CTkFrame(win, fg_color="transparent")
    khung_info.grid(row=1, column=0, sticky="ew", padx=KHOANG_TRONG, pady=(4, 0))
    khung_info.grid_columnconfigure(0, weight=1)

    lbl_toa_do = ctk.CTkLabel(khung_info, text="Chưa có vùng",
                              font=("Consolas", 14, "bold"),
                              anchor="w", justify="left")
    lbl_toa_do.grid(row=0, column=0, sticky="w")

    lbl_goi_y = ctk.CTkLabel(
        khung_info,
        text="Kéo chuột trái trên ảnh để khoanh vùng. Kéo từ góc trên-trái "
             "đến góc dưới-phải.",
        font=("Segoe UI", 12), anchor="w", justify="left", text_color="#a8a8a8")
    lbl_goi_y.grid(row=1, column=0, sticky="w", pady=(2, 0))

    dong_nguon = f"Nguồn: {nguon}" if nguon else ""
    lbl_nguon = ctk.CTkLabel(khung_info, text=dong_nguon,
                             font=("Segoe UI", 11), anchor="w",
                             justify="left", text_color="#8a8a8a")
    lbl_nguon.grid(row=2, column=0, sticky="w", pady=(2, 0))

    # --- hang nut bam ---
    khung_nut = ctk.CTkFrame(win, fg_color="transparent")
    khung_nut.grid(row=2, column=0, sticky="ew", padx=KHOANG_TRONG, pady=(8, KHOANG_TRONG))
    khung_nut.grid_columnconfigure(2, weight=1)

    nut_luu = ctk.CTkButton(khung_nut, text="Lưu vùng", width=DO_RONG_HANG_NUT,
                             state="disabled")
    nut_luu.grid(row=0, column=0, padx=(0, 8))

    nut_chon_lai = ctk.CTkButton(khung_nut, text="Chọn lại", width=DO_RONG_HANG_NUT)
    nut_chon_lai.grid(row=0, column=1, padx=(0, 8))

    nut_bo = ctk.CTkButton(khung_nut, text="Bỏ", width=DO_RONG_HANG_NUT,
                            fg_color="#8a1f1f", hover_color="#a52626")
    nut_bo.grid(row=0, column=3, sticky="e")

    # --- anh nen (giu tham chieu de khong bi thu hoi boi bo dem) ---
    try:
        anh_pil = Image.fromarray(cv2.cvtColor(anh_hien, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(anh_pil)
        canvas.create_image(0, 0, anchor="nw", image=photo)
    except Exception as exc:
        _ghi_log(log, f"Lỗi: không hiển thị được ảnh ({exc}).")
        photo = None
        try:
            win.destroy()
        except Exception:
            pass
        return None

    # ---------------------------------------------------------- ham noi bo

    def _toa_do_tuong_doi():
        """Doi toa do pixel tren canvas thanh toa do tuong doi cua ANH GOC."""
        goc_x = sel["x1"] / ty_le
        goc_y = sel["y1"] / ty_le
        cuoi_x = sel["x2"] / ty_le
        cuoi_y = sel["y2"] / ty_le
        rx1 = max(0.0, min(1.0, goc_x / chieu_rong_goc))
        ry1 = max(0.0, min(1.0, goc_y / chieu_cao_goc))
        rx2 = max(0.0, min(1.0, cuoi_x / chieu_rong_goc))
        ry2 = max(0.0, min(1.0, cuoi_y / chieu_cao_goc))
        if rx1 > rx2:
            rx1, rx2 = rx2, rx1
        if ry1 > ry2:
            ry1, ry2 = ry2, ry1
        return (round(rx1, 6), round(ry1, 6), round(rx2, 6), round(ry2, 6))

    def _cap_nhat_nhan_ky():
        """Cap nhat dong toa do tuong doi + trang thai nut Luu."""
        if not sel["hop_le"]:
            lbl_toa_do.configure(text="Chưa có vùng")
            return
        rx1, ry1, rx2, ry2 = _toa_do_tuong_doi()
        lbl_toa_do.configure(text=f"{rx1:.4f} {ry1:.4f} {rx2:.4f} {ry2:.4f}")
        nut_luu.configure(state="normal")

    def _ve_hinh_chu_nhat(x1, y1, x2, y2):
        """Ve hoac cap nhat hinh chu nhat tren canvas."""
        if sel["hinh"] is None:
            sel["hinh"] = canvas.create_rectangle(x1, y1, x2, y2,
                                                  outline=MAU_VUNG, width=2)
        else:
            canvas.coords(sel["hinh"], x1, y1, x2, y2)

    def _bam_chuot(event):
        sel["keo"] = True
        sel["x_keo"], sel["y_keo"] = event.x, event.y
        sel["x1"], sel["y1"] = event.x, event.y
        sel["x2"], sel["y2"] = event.x, event.y
        sel["hop_le"] = False
        _ve_hinh_chu_nhat(event.x, event.y, event.x, event.y)

    def _keo_chuot(event):
        if not sel["keo"]:
            return
        sel["x2"], sel["y2"] = event.x, event.y
        sel["x1"] = min(sel["x_keo"], event.x)
        sel["y1"] = min(sel["y_keo"], event.y)
        sel["x2"] = max(sel["x_keo"], event.x)
        sel["y2"] = max(sel["y_keo"], event.y)
        sel["hop_le"] = False
        _ve_hinh_chu_nhat(sel["x1"], sel["y1"], sel["x2"], sel["y2"])
        # hien thi toa do khi keo (chua chot) de nguoi dung kiem
        if sel["x2"] > sel["x1"] and sel["y2"] > sel["y1"]:
            rx1, ry1, rx2, ry2 = _toa_do_tuong_doi()
            lbl_toa_do.configure(text=f"{rx1:.4f} {ry1:.4f} {rx2:.4f} {ry2:.4f}")
        else:
            lbl_toa_do.configure(text="Chưa có vùng")

    def _tha_chuot(event):
        if not sel["keo"]:
            return
        sel["keo"] = False
        sel["x1"] = min(sel["x_keo"], event.x)
        sel["y1"] = min(sel["y_keo"], event.y)
        sel["x2"] = max(sel["x_keo"], event.x)
        sel["y2"] = max(sel["y_keo"], event.y)
        rong = sel["x2"] - sel["x1"]
        cao = sel["y2"] - sel["y1"]
        rong_goc = rong / ty_le
        cao_goc = cao / ty_le
        sel["hop_le"] = (rong >= CHIEU_DAI_VUNG_TOI_THIEU
                         and cao >= CHIEU_DAI_VUNG_TOI_THIEU
                         and rong_goc >= CHIEU_DAI_VUNG_TOI_THIEU
                         and cao_goc >= CHIEU_DAI_VUNG_TOI_THIEU)
        _ve_hinh_chu_nhat(sel["x1"], sel["y1"], sel["x2"], sel["y2"])
        if sel["hop_le"]:
            _cap_nhat_nhan_ky()
        else:
            lbl_toa_do.configure(text="Chưa có vùng")
            nut_luu.configure(state="disabled")

    def _chon_lai():
        sel.update({"x1": 0, "y1": 0, "x2": 0, "y2": 0, "keo": False,
                    "x_keo": 0, "y_keo": 0, "hop_le": False})
        if sel["hinh"] is not None:
            canvas.delete(sel["hinh"])
            sel["hinh"] = None
        lbl_toa_do.configure(text="Chưa có vùng")
        nut_luu.configure(state="disabled")

    def _dong():
        """Dong cua so - chi goi destroy DUNG 1 LAN."""
        nonlocal da_dong
        if da_dong:
            return
        da_dong = True
        try:
            win.grab_release()
        except Exception:
            pass
        try:
            win.destroy()
        except Exception:
            pass

    def _luu_vung():
        if not sel["hop_le"]:
            return
        ket_qua["value"] = _toa_do_tuong_doi()
        _dong()

    def _huy():
        ket_qua["value"] = None
        _dong()

    # ---------------------------------------------------------- ket noi su kien

    canvas.bind("<ButtonPress-1>", _bam_chuot)
    canvas.bind("<B1-Motion>", _keo_chuot)
    canvas.bind("<Motion>", _keo_chuot)
    canvas.bind("<ButtonRelease-1>", _tha_chuot)
    nut_luu.configure(command=_luu_vung)
    nut_chon_lai.configure(command=_chon_lai)
    nut_bo.configure(command=_huy)
    win.protocol("WM_DELETE_WINDOW", _huy)
    win.bind("<Escape>", lambda _e: _huy())

    # ---------------------------------------------------------- mo cua so

    try:
        _canh_giua(win, rong_hien + 2 * KHOANG_TRONG,
                   cao_hien + CHIEU_CAO_HANG_DIEU_KHIEN)
    except Exception:
        pass
    try:
        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_force()
    except Exception:
        pass
    try:
        win.grab_set()
    except Exception:
        pass

    try:
        win.wait_window(win)
    except Exception:
        pass
    finally:
        _dong()

    gia_tri = ket_qua["value"]
    if gia_tri is None:
        _ghi_log(log, "Đã hủy vẽ vùng.")
        return None
    _ghi_log(log, f"Đã chọn vùng: {gia_tri[0]:.4f} {gia_tri[1]:.4f} "
                  f"{gia_tri[2]:.4f} {gia_tri[3]:.4f}")
    return gia_tri
