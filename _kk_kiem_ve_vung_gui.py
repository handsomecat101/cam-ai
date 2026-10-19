"""Kiem chung tu dong cho ve_vung_gui.ve_vung_trong_gui.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_ve_vung_gui.py

Cac phase:
P1  Gia lap chuot that tren Canvas -> bam "Luu vung" -> toa do khop vung keo.
P2  Keo vung -> bam "Bo" -> ham tra ve None.
P3  Keo vung -> bam "Chon lai" -> nut bi khoa + nhan ve "Chua co vung",
    keo lai -> bam "Luu vung" -> toa do van dung.
P4  Anh rong/None -> ham tra ve None + ghi log loi (khong mo cua so).

Tieu chi: ket qua P1/P3 phai la 1 tuple 4 float trong [0,1] va khop vung da
gia lap (sai so cho phep ~0.02 do lam tron / thu nho).
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes

import customtkinter as ctk
import numpy as np
from PIL import ImageGrab

ROOT = r"H:\AI Project\cam-ai"
OUT_DIR = os.path.join(ROOT, "_kk_out", "agent_b")
SHOT = os.path.join(OUT_DIR, "ve_vung_gui.png")
SHOT_FULL = os.path.join(OUT_DIR, "ve_vung_gui_full.png")

# Vung gia lap tren canvas (pixel) - se duoc doi sang toa do tuong doi.
X1, Y1, X2, Y2 = 100, 80, 300, 240
SAI_SO_CHO_PHEP = 0.02

os.makedirs(OUT_DIR, exist_ok=True)


def tim_theo_ten(w, ten):
    """Tim widget theo ten (name=) trong cay widget, khong phu thuoc thu tu."""
    for c in w.winfo_children():
        try:
            if c.winfo_name() == ten:
                return c
        except Exception:
            pass
        r = tim_theo_ten(c, ten)
        if r is not None:
            return r
    return None


def tim_nut(w, chu):
    """Tim CTkButton theo chu hien thi (CTkButton khong cho dat ten)."""
    for c in w.winfo_children():
        if isinstance(c, ctk.CTkButton):
            try:
                if str(c.cget("text")) == chu:
                    return c
            except Exception:
                pass
        r = tim_nut(c, chu)
        if r is not None:
            return r
    return None


def an_ascii(s):
    """Chuoi an toan ASCII de in ra console Windows (console khong ho tro tieng Viet)."""
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def tim_nhan(w):
    """Tra ve danh sach text cua moi CTkLabel trong cay widget."""
    ket = []
    for c in w.winfo_children():
        if isinstance(c, ctk.CTkLabel):
            try:
                ket.append(str(c.cget("text")))
            except Exception:
                pass
        ket.extend(tim_nhan(c))
    return ket


def tim_toplevel(root):
    for c in root.winfo_children():
        if isinstance(c, ctk.CTkToplevel):
            return c
    return None


def chup_cua_so(win, duong_dan, duong_dan_full=None):
    """Chup vung cua so that cua hop thoai (dung HWND that)."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetAncestor(win.winfo_id(), 2)   # 2 = GA_ROOT
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return None
    if duong_dan_full:
        try:
            ImageGrab.grab(all_screens=True).save(duong_dan_full)
        except Exception as exc:
            print("[WARN] khong chup duoc toan man hinh:", exc)
    anh = ImageGrab.grab(bbox=bbox, all_screens=True)
    anh.save(duong_dan)
    return bbox, anh.size


def tao_anh_gi():
    """Anh BGR gia 640x480, nen xam + vai hinh vuon mau."""
    anh = np.full((480, 640, 3), 110, dtype=np.uint8)
    anh[40:200, 60:240] = (30, 190, 240)
    anh[220:400, 300:520] = (220, 90, 40)
    anh[300:440, 60:200] = (90, 220, 90)
    return anh


def keo_chuot(canvas, x1=X1, y1=Y1, x2=X2, y2=Y2):
    """Gia lap keo chuot tren canvas bang event_generate."""
    loi = []
    for ten_event, x, y in (("<ButtonPress-1>", x1, y1),
                            ("<B1-Motion>", (x1 + x2) // 2, (y1 + y2) // 2),
                            ("<Motion>", (x1 + x2) // 2, (y1 + y2) // 2),
                            ("<B1-Motion>", x2, y2),
                            ("<Motion>", x2, y2),
                            ("<ButtonRelease-1>", x2, y2)):
        try:
            canvas.event_generate(ten_event, x=x, y=y)
        except Exception as exc:
            loi.append(f"{ten_event}: {exc}")
    return loi


def mo_hop_thoai(root, anh, nguon, ghi_log, hanh_dong, tre=700):
    """Mo hop thoai (modal) va chay `hanh_dong(win, ...)` sau khi cua so len."""
    trang_thai = {}

    def cb():
        win = tim_toplevel(root)
        if win is None:
            trang_thai["loi"] = "khong tim thay Toplevel"
            return
        try:
            win.update()
        except Exception:
            pass
        canvas = tim_theo_ten(win, "ve_vung_canvas")
        nut_luu = tim_nut(win, "Lưu vùng")
        nut_chon_lai = tim_nut(win, "Chọn lại")
        nut_bo = tim_nut(win, "Bỏ")
        if canvas is None or nut_luu is None:
            trang_thai["loi"] = "khong tim thay canvas / nut"
            return
        trang_thai["win"] = win
        trang_thai["canvas"] = canvas
        trang_thai["nut_luu"] = nut_luu
        trang_thai["nut_chon_lai"] = nut_chon_lai
        trang_thai["nut_bo"] = nut_bo
        try:
            hanh_dong(trang_thai)
        except Exception as exc:
            trang_thai["loi"] = f"hanh_dong that bai: {exc}"

    root.after(tre, cb)
    ket_qua = ve_vung_trong_gui(root, anh, nguon=nguon, log=ghi_log)
    return ket_qua, trang_thai


def chay():
    anh = tao_anh_gi()
    h, w = anh.shape[:2]
    print(f"[anh] {w}x{h} (BGR gia)")

    root = ctk.CTk()
    root.geometry("900x600+0+0")
    root.title("KK - nen de mo hop thoai ve vung")

    nhat_ky = []

    def ghi_log(s):
        nhat_ky.append(s)
        print("[log]", an_ascii(s))

    ket_qua = {}
    ok_chung = True

    # ---------------------------------------------------------------- P1
    print("=" * 60)
    print("P1: gia lap chuot that -> bam 'Luu vung'")

    def p1(ts):
        canvas = ts["canvas"]
        loi = keo_chuot(canvas)
        ts["win"].update()
        if loi:
            print("[WARN] event_generate loi:", "; ".join(loi))
        print(f"[P1] nut_luu_state sau khi keo = {ts['nut_luu'].cget('state')}")
        print("[P1] nhan gui: " + " | ".join(an_ascii(t) for t in tim_nhan(ts["win"])))
        if str(ts["nut_luu"].cget("state")) != "normal":
            raise RuntimeError("nut Luu vung khong bat duoc sau khi gia lap keo")
        # chup man hinh (co hinh chu nhat da ve) TRUOC khi bam Luu
        try:
            ts["win"].attributes("-topmost", True)
            ts["win"].lift()
            ts["win"].update()
            time.sleep(0.4)
            ts["win"].update()
            kq = chup_cua_so(ts["win"], SHOT, SHOT_FULL)
            if kq:
                print(f"[P1] screenshot {SHOT} bbox={kq[0]} size={kq[1]}")
            else:
                print("[WARN] khong chup duoc cua so")
        except Exception as exc:
            print("[WARN] chup anh that bai:", exc)
        ts["nut_luu"].invoke()

    ket_qua["P1"], ts1 = mo_hop_thoai(root, anh, "kiem chung", ghi_log, p1)
    print("[P1] ket_qua =", ket_qua["P1"])
    if ts1.get("loi"):
        print("[P1] LOI:", ts1["loi"])
        ok_chung = False
    if not isinstance(ket_qua["P1"], tuple) or len(ket_qua["P1"]) != 4:
        print("P1: FAIL - khong tra ve tuple 4 so")
        ok_chung = False
    else:
        v = [float(x) for x in ket_qua["P1"]]
        exp = (X1 / w, Y1 / h, X2 / w, Y2 / h)
        lech = [abs(a - b) for a, b in zip(v, exp)]
        print("P1: toa_do = " + " ".join(f"{x:.4f}" for x in v))
        print("P1: ky_vong = " + " ".join(f"{x:.4f}" for x in exp))
        print("P1: sai_so  = " + " ".join(f"{x:.4f}" for x in lech))
        if not all(0.0 <= x <= 1.0 for x in v) or max(lech) > SAI_SO_CHO_PHEP:
            print("P1: FAIL - toa do sai")
            ok_chung = False

    # ---------------------------------------------------------------- P2
    print("=" * 60)
    print("P2: keo vung -> bam 'Bo' -> phai tra ve None")

    def p2(ts):
        keo_chuot(ts["canvas"])
        ts["win"].update()
        ts["nut_bo"].invoke()

    ket_qua["P2"], ts2 = mo_hop_thoai(root, anh, "kiem chung", ghi_log, p2)
    print("[P2] ket_qua =", ket_qua["P2"])
    if ket_qua["P2"] is not None:
        print("P2: FAIL - phai tra ve None")
        ok_chung = False

    # ---------------------------------------------------------------- P3
    print("=" * 60)
    print("P3: keo -> 'Chon lai' -> keo lai -> 'Luu vung'")

    def p3(ts):
        keo_chuot(ts["canvas"])
        ts["win"].update()
        ts["nut_chon_lai"].invoke()
        ts["win"].update()
        print(f"[P3] sau 'Chon lai': nut_luu_state={ts['nut_luu'].cget('state')}")
        print("[P3] nhan gui: " + " | ".join(an_ascii(t) for t in tim_nhan(ts["win"])))
        if str(ts["nut_luu"].cget("state")) != "disabled":
            raise RuntimeError("nut Luu vung van bat sau khi Chon lai")
        keo_chuot(ts["canvas"])
        ts["win"].update()
        print(f"[P3] sau khi keo lai: nut_luu_state={ts['nut_luu'].cget('state')}")
        ts["nut_luu"].invoke()

    ket_qua["P3"], ts3 = mo_hop_thoai(root, anh, "kiem chung", ghi_log, p3)
    print("[P3] ket_qua =", ket_qua["P3"])
    if not isinstance(ket_qua["P3"], tuple) or len(ket_qua["P3"]) != 4:
        print("P3: FAIL - khong tra ve tuple 4 so")
        ok_chung = False
    else:
        v = [float(x) for x in ket_qua["P3"]]
        exp = (X1 / w, Y1 / h, X2 / w, Y2 / h)
        lech = [abs(a - b) for a, b in zip(v, exp)]
        print("P3: toa_do = " + " ".join(f"{x:.4f}" for x in v))
        print("P3: sai_so  = " + " ".join(f"{x:.4f}" for x in lech))
        if max(lech) > SAI_SO_CHO_PHEP:
            print("P3: FAIL - toa do sai")
            ok_chung = False

    # ---------------------------------------------------------------- P4
    print("=" * 60)
    print("P4: anh None -> phai tra ve None + ghi log loi")
    truoc = len(nhat_ky)
    ket_qua["P4"] = ve_vung_trong_gui(root, None, nguon="kiem chung", log=ghi_log)
    print("[P4] ket_qua =", ket_qua["P4"])
    if ket_qua["P4"] is not None:
        print("P4: FAIL - phai tra ve None")
        ok_chung = False
    if len(nhat_ky) <= truoc:
        print("P4: FAIL - khong ghi log loi")
        ok_chung = False

    # ---------------------------------------------------------------- tong ket
    print("=" * 60)
    print("so_dong_nhat_ky_log =", len(nhat_ky))
    for i, dong in enumerate(nhat_ky, 1):
        print(f"  log[{i}] = {an_ascii(dong)}")
    print("KET QUA: " + ("PASS" if ok_chung else "FAIL"))

    try:
        root.destroy()
    except Exception:
        pass
    sys.stdout.flush()
    os._exit(0 if ok_chung else 1)


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    from ve_vung_gui import ve_vung_trong_gui
    chay()
