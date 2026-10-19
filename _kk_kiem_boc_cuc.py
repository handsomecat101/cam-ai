r"""MUC TIEU 3: bo cuc + nhan tran.

A) BO CUC: video chiem >=70% be ngang (video + cot su kien).
   Do truc tiep tren widget GUI dang chay (winfo_width), o 3 kich thuoc cua so.
B) NHAN TRAN: 0 nhan ve ra ngoai khung video.
   B1 - widget: do anh (o_hinh) co lot ra ngoai khung_den khong.
   B2 - pixel : ve that su bang ham `ve_nguoi` tren anh da RESIZE DUNG kich
        thuoc o_hinh, roi dem nhan co toa ra ngoai bien anh khong.

Khong do tren anh -> do tren widget va tren ham ve that cua san pham.
"""

from __future__ import annotations

import os
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

VIDEO = os.path.join(APP_DIR, "video_mau", "moi", "nguoi-dung-cho.mp4")
KT = os.path.join(APP_DIR, "_kiem_chung")

KICH_THUOC = [(1610, 980), (1400, 900), (1900, 1040)]
NGUONG = 70.0

dong: list[str] = []
ket_luan = {"boc_cuc": False, "khong_tran": False}


def _ghi(s: str) -> None:
    dong.append(s)
    print(s, flush=True)


def _do_boc_cuc(app, w, h):
    app.update_idletasks()
    app.update()
    app.geometry(f"{w}x{h}")
    for _ in range(15):                      # cho Tk chot lai bo cuc
        app.update_idletasks()
        app.update()
        time.sleep(0.08)

    kd = app.khung_den
    ps = app.panel_su_kien
    wv, we = kd.winfo_width(), ps.winfo_width()
    tong = wv + we
    ty_le = (wv / tong * 100) if tong else 0.0

    # --- widget anh co lot ra ngoai khung video khong? ---
    oh = app.o_hinh
    xa = oh.winfo_rootx() - kd.winfo_rootx()
    ya = oh.winfo_rooty() - kd.winfo_rooty()
    aw, ah = oh.winfo_width(), oh.winfo_height()
    tran = (max(0, -xa) + max(0, -ya)
            + max(0, (xa + aw) - kd.winfo_width())
            + max(0, (ya + ah) - kd.winfo_height()))

    _ghi(f"  cua so {w}x{h}: video={wv}px  su kien={we}px  tong={tong}px"
         f"  ->  {ty_le:.1f}%  {'DAT' if ty_le >= NGUONG else 'KHONG DAT'}")
    _ghi(f"              o hinh {aw}x{ah} tai ({xa},{ya}) trong khung {kd.winfo_width()}x"
         f"{kd.winfo_height()}  -> tran {tran}px")
    return ty_le, tran, (aw, ah)


def _do_nhan_tran(app, kich_thuoc_anh):
    """Ve nhan that len DUNG anh co kich thuoc cua widget o_hinh roi dem tran."""
    import numpy as np
    from PIL import Image

    import gui_khung as GK

    aw, ah = kich_thuoc_anh
    aw, ah = max(16, aw), max(16, ah)
    goc = getattr(app, "_anh_gu", None)
    if goc is None:
        return None, "khong co khung hinh nao trong bo dem"

    cao_h, rong_h = goc.shape[:2]
    ty_le = min(aw / float(rong_h), ah / float(cao_h))
    rong_moi = max(1, min(aw, int(round(rong_h * ty_le))))
    cao_moi = max(1, min(ah, int(round(cao_h * ty_le))))

    import cv2

    nho = cv2.resize(goc, (rong_moi, cao_moi), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(cv2.cvtColor(nho, cv2.COLOR_BGR2RGB))

    import numpy as _np

    boxes, nhan, mau, uu = [], [], [], []
    ten = ["An", "Binh", "Chi", "Duc"]
    ds_live = getattr(app, "_ds_nguoi_live", None) or []
    for j, b in enumerate(ds_live):
        boxes.append(b)
        if j % 3 == 0:
            nhan.append(f"{ten[(j // 3) % len(ten)]} · {30 + j % 40} · Nam")
            uu.append(0.9)
        else:
            nhan.append(f"Người {j + 1}")
            uu.append(0.4)
        mau.append("#22C55E")
    if not boxes:
        # khong co san danh sach san -> dung YOLO tren chinh anh nay
        from ultralytics import YOLO

        det = YOLO("yolo11n.pt")
        r = det(nho, verbose=False, conf=0.25)[0]
        if r.boxes is not None:
            for j, b in enumerate(r.boxes.xyxy.tolist()):
                if int(r.boxes.cls[j]) != 0:
                    continue
                boxes.append(b)
                nhan.append(f"Người {j + 1}")
                mau.append("#22C55E")
                uu.append(0.4)

    rects = GK.ve_nguoi(img, boxes, nhan, mau, 15, 2, uu_tien=uu) if boxes else []
    tran = [r for r in rects
            if not (0 <= r[0] and 0 <= r[1]
                    and r[2] <= img.width and r[3] <= img.height)]

    _ghi(f"  anh tren man hinh {aw}x{ah} -> anh resize {img.width}x{img.height}"
         f"  (guoc {rong_h}x{cao_h})")
    _ghi(f"  nguoi tren anh: {len(boxes)}   nhan ve duoc: {len(rects)}"
         f"   nhan TRAN ra ngoai anh: {len(tran)}")
    for r in tran:
        _ghi(f"    TRAN: {r}")
    return (len(tran) == 0), f"nhan={len(rects)} tran={len(tran)}"


def _chup(app, ten):
    """Chup anh cua so CamAI tren man hinh that (de coordinator tu nhin).

    Luu y quan trong: phai EP CUA SO LEN TRUOC khi chup. Neu chi chup theo
    toa do cua Tk, cua so bi cua so khac (Chrome...) che la hinh thu ra
    khong phai ung dung - em da chup nham mot lan va phai hieu lai.
    `SetForegroundWindow` tu PowerShell/ nen bi Windows tu choi, nhung
    `attributes('-topmost')` do chinh tiend trinh so huu cua so thi luon duoc.
    """
    try:
        import ctypes
        import ctypes.wintypes as wt
        import time as _t

        from PIL import ImageGrab

        u32 = ctypes.windll.user32
        u32.SetProcessDPIAware()
        app.attributes("-topmost", True)
        app.lift()
        app.focus_force()
        app.update()
        _t.sleep(1.5)

        hwnd = u32.GetAncestor(app.winfo_id(), 2)      # GA_ROOT = 2
        r = wt.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        x, y = r.left, r.top
        w, h = r.right - r.left, r.bottom - r.top

        duong = os.path.join(KT, ten)
        anh = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        anh.save(duong)

        duong_full = os.path.join(KT, "kk_36_toan_man_hinh.png")
        ImageGrab.grab(all_screens=True).save(duong_full)

        app.attributes("-topmost", False)
        _ghi(f"  chup cua so that: {anh.width}x{anh.height} tai ({x},{y})")
        return duong
    except Exception as exc:                       # noqa: BLE001
        _ghi(f"  (khong chup duoc: {exc})")
        return None


def main() -> int:
    os.makedirs(KT, exist_ok=True)
    import customtkinter as ctk

    import gui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = gui.CamAIGui()
    app.v_video.set(VIDEO)
    app.v_output.set(APP_DIR)
    app.v_face.set("0")
    app.v_vung.set("0")
    app.v_clip.set("0")

    anh = {}
    _bat_dau_luoi = {"t": 0.0}

    def _bat_dau():
        import time as _t
        _bat_dau_luoi["t"] = _t.time()
        try:
            app._bat_dau()
        except Exception:                          # noqa: BLE001
            _ghi("LOI khi bat dau:")
            _ghi(traceback.format_exc())
            anh["loi"] = True
            return
        app.after(600, _cho_khung_hinh)

    def _cho_khung_hinh():
        """Nap model mat ~7s nen PHAI cho co khung hinh truoc khi do."""
        import time as _t
        if getattr(app, "_anh_gu", None) is not None:
            app.after(1200, _do_luu)                # de it nhat 1 khung o o hinh
            return
        if _t.time() - _bat_dau_luoi["t"] > 90:
            _ghi("LOI: 90s van khong co khung hinh nao ve len o hinh")
            loi = ""
            try:
                loi = app.lbl_loi.cget("text")
            except Exception:                      # noqa: BLE001
                pass
            _ghi(f"  lbl_loi = {loi!r}")
            _ghi(f"  _xem_dang_chay = {getattr(app, '_xem_dang_chay', None)}"
                 f"  busy = {getattr(app, 'busy', None)}")
            anh["loi"] = True
            app.after(200, _ket_thuc)
            return
        app.after(300, _cho_khung_hinh)

    def _do_luu():
        _ghi("=== A) BO CUC: video / (video + cot su kien) ===")
        ty_le_list, tran_widget, kich = [], 0, None
        for w, h in KICH_THUOC:
            t, tr, kc = _do_boc_cuc(app, w, h)
            ty_le_list.append(t)
            tran_widget += tr
            kich = kc

        _ghi("")
        _ghi("=== B) NHAN TRAN ===")
        _ghi("-- B1 widget: anh lot ra ngoai khung video --")
        _ghi(f"  TONG SO PX TRAN WIDGET: {tran_widget}")
        ket_luan["khong_tran"] = (tran_widget == 0)

        _ghi("-- B2 pixel: ve nhan that tren anh da resize --")
        ok2, chi_tiet = _do_nhan_tran(app, kich)
        _ghi(f"  ket qua B2: {chi_tiet}")
        ket_luan["khong_tran"] = ket_luan["khong_tran"] and bool(ok2)

        ket_luan["boc_cuc"] = min(ty_le_list) >= NGUONG

        _ghi("")
        _ghi(f"nguong yeu cau bo cuc: >= {NGUONG:.0f}%")
        _ghi(f"nho nhat tren 3 kich thuoc: {min(ty_le_list):.1f}%")
        _ghi("")
        _ghi(f"KET LUAN BO CUC  : {'DAT' if ket_luan['boc_cuc'] else 'KHONG DAT'}")
        _ghi(f"KET LUAN NHAN TRAN: {'DAT' if ket_luan['khong_tran'] else 'KHONG DAT'}")

        duong = _chup(app, "kk_36_boc_cuc.png")
        if duong:
            _ghi(f"anh chup man hinh that: {duong}")
        app.after(200, _ket_thuc)

    def _ket_thuc():
        bao = "\n".join(dong)
        duong_txt = os.path.join(KT, "kk_36_boc_cuc.txt")
        with open(duong_txt, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(bao + "\n")
        print(f"\nghi ra: {duong_txt}", flush=True)
        try:
            app.stop_flag.set()
            app._ket_thuc_xem.set()
            app.quit()
            app.destroy()
        except Exception:                          # noqa: BLE001
            pass

    app.after(700, _bat_dau)
    app.mainloop()

    if "loi" in anh:
        return 2
    return 0 if (ket_luan["boc_cuc"] and ket_luan["khong_tran"]) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:                           # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(3)