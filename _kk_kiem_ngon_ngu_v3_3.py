# -*- coding: utf-8 -*-
"""Kiem chung chuoi tieng Anh cho 5 widget MOI cua ban 3.3.

Kiem 2 checkbox moi (Xem truc tiep / Xem khung hinh ket qua) + 3 nut moi
(Dang ky nguoi quen / Doc bien so thu / Ve vung ngay tai day).

Chay: .venv\\Scripts\\python.exe -W ignore _kk_kiem_ngon_ngu_v3_3.py
"""
from __future__ import annotations

import os
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import customtkinter as ctk  # noqa: E402

from gui import CamAIGui  # noqa: E402

APP_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NGON_NGU = os.path.join(APP_DIR, "gui_ngon_ngu.json")

# 5 chuoi moi cua ban 3.3: (ten, chuoi tieng Viet, tien to tieng Anh)
CHUOI_MOI = [
    ("chk_xem_video", "Xem trực tiếp", "Live view"),
    ("chk_xem_ket_qua", "Xem khung hình kết quả", "Show result frames"),
    ("nut_dang_ky", "Đăng ký người quen", "Register a known person"),
    ("nut_doc_bien_so_thu", "Đọc biển số thử", "Test plate reading"),
    ("nut_ve_vung_tai_day", "Vẽ vùng ngay tại đây", "Draw the zone right here"),
]

CHUOI_CO_DAU = "ăâđêôơưĂÂĐÊÔƠƯ"


def co_dau(chuoi: str) -> bool:
    """True neu chuoi co it nhat 1 dau tieng Viet.

    Dau tieng Viet trong Unicode hay duoc ghep san (vd 'ự' = U+1EE5, 'ộ' =
    U+1ED9) nen khong do duoc bang cach so sanh chuoi co dau co dinh.
    Cach dung: bat ky chu cai ASCII-pha tren 255 deu la chu Viet co dau.
    """
    for ch in chuoi:
        if ch in CHUOI_CO_DAU:
            return True
        if unicodedata.combining(ch):
            return True
        if ch.isalpha() and ord(ch) > 0xFF:
            return True
    return False


def duyet_nut(app):
    """Tra ve danh sach (text, widget) cua moi CTkButton trong cay widget."""
    ket = []

    def quet(wdg):
        if isinstance(wdg, ctk.CTkButton):
            try:
                ket.append((wdg.cget("text"), wdg))
            except Exception:                                 # noqa: BLE001
                pass
        for con in wdg.winfo_children():
            quet(con)

    quet(app)
    return ket


def tim_nut_theo_tien_doan(app, tien_doan):
    """Nut CTkButton nao co text CHUA tien doan. Tra ve danh sach text."""
    return [t for t, _ in duyet_nut(app)
            if isinstance(t, str) and tien_doan in t]


def main() -> int:
    # --- giu nguyen file lua ngon ngu (app se tu ghi khi doi ngon ngu) ---
    goc_file = None
    if os.path.isfile(FILE_NGON_NGU):
        with open(FILE_NGON_NGU, "rb") as f:
            goc_file = f.read()

    app = None
    loi = []
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        app = CamAIGui()
        app.update_idletasks()

        # --- buoc 1: chay o TIENG VIET ---
        if app.ngon_ngu != "vi":
            app.ngon_ngu = "vi"
            app._lam_moi_ngon_ngu()
            app.update_idletasks()

        print("=" * 70)
        print("TRUOC KHI DOI NGON NGU (tieng Viet)")
        print("=" * 70)
        print(f"  app.title()            = {app.title()!r}")
        print(f"  chk_xem_video          = {app.chk_xem_video.cget('text')!r}")
        print(f"  chk_xem_ket_qua        = {app.chk_xem_ket_qua.cget('text')!r}")
        for ten, chu_vi, _ in CHUOI_MOI[2:]:
            ds = tim_nut_theo_tien_doan(app, chu_vi)
            print(f"  nut[{ten}]        = {ds!r}")
            if len(ds) != 1:
                loi.append(f"VI: nut '{chu_vi}' tim thay {len(ds)} nut (can 1)")
        for ten, chu_vi, _ in CHUOI_MOI[:2]:
            txt = (app.chk_xem_video.cget("text") if ten == "chk_xem_video"
                   else app.chk_xem_ket_qua.cget("text"))
            if txt != chu_vi:
                loi.append(f"VI: {ten} = {txt!r} (mong doi {chu_vi!r})")
            if not co_dau(txt):
                loi.append(f"VI: {ten} = {txt!r} THIEU dau tieng Viet")
        chuoi_vi = [app.chk_xem_video.cget("text"),
                    app.chk_xem_ket_qua.cget("text")]
        for _, chu_vi_goc, _ in CHUOI_MOI[2:]:
            chuoi_vi += tim_nut_theo_tien_doan(app, chu_vi_goc)
        print(f"  tat ca chuoi tieng Viet co dau = "
              f"{all(co_dau(t) for t in chuoi_vi)}  ({len(chuoi_vi)} chuoi)")

        # --- buoc 2: DOI sang tieng Anh (dung ham co san trong gui.py) ---
        app._doi_ngon_ngu()
        app.update_idletasks()

        print()
        print("=" * 70)
        print("SAU KHI DOI NGON NGU (tieng Anh)")
        print("=" * 70)
        print(f"  app.ngon_ngu           = {app.ngon_ngu!r}")
        print(f"  app.title()            = {app.title()!r}")
        print(f"  chk_xem_video          = {app.chk_xem_video.cget('text')!r}")
        print(f"  chk_xem_ket_qua        = {app.chk_xem_ket_qua.cget('text')!r}")
        for ten, chu_vi, tien_en in CHUOI_MOI[2:]:
            ds = tim_nut_theo_tien_doan(app, tien_en)
            print(f"  nut[{ten}]        = {ds!r}")
            if len(ds) != 1:
                loi.append(f"EN: nut '{tien_en}' tim thay {len(ds)} nut (can 1)")
                # tra lai cac nut tieng Viet chua doi -> bao loi chi tiet
                ds_vi = tim_nut_theo_tien_doan(app, chu_vi)
                if ds_vi:
                    loi.append(f"EN: nut '{chu_vi}' VAN TIENG VIET: {ds_vi!r}")

        # --- buoc 3: kiem 5 chuoi moi co dung tieng Anh ---
        print()
        print("=" * 70)
        print("KET LUAN")
        print("=" * 70)
        bang = [
            ("chk_xem_video", app.chk_xem_video.cget("text")),
            ("chk_xem_ket_qua", app.chk_xem_ket_qua.cget("text")),
        ]
        for ten, chu_vi, tien_en in CHUOI_MOI[2:]:
            ds = tim_nut_theo_tien_doan(app, tien_en)
            bang.append((ten, ds[0] if ds else "<KHONG TIM THAY>"))

        for ten, txt in bang:
            mong = tien_en_of(ten)
            dung = isinstance(txt, str) and mong in txt
            trang = "PASS" if dung else "FAIL"
            print(f"  [{trang}] {ten:24s} = {txt!r}")
            if not dung:
                loi.append(f"EN: {ten} = {txt!r} (mong doi chua '{mong}')")

        # tieu de
        td = app.title()
        td_ok = "3.3" in td and "CamAI" in td
        print(f"  [{'PASS' if td_ok else 'FAIL'}] tieu de                 = {td!r}")
        if not td_ok:
            loi.append(f"EN: tieu de khong co phien ban 3.3: {td!r}")

        # --- buoc 4: doi NGUOC lai tieng Viet (kiem chu goc da ghi nhan dung) ---
        app._doi_ngon_ngu()
        app.update_idletasks()
        print()
        print("=" * 70)
        print("DOI NGUOC LAI TIENG VIET (kiem chu goc)")
        print("=" * 70)
        print(f"  app.ngon_ngu           = {app.ngon_ngu!r}")
        print(f"  app.title()            = {app.title()!r}")
        print(f"  chk_xem_video          = {app.chk_xem_video.cget('text')!r}")
        print(f"  chk_xem_ket_qua        = {app.chk_xem_ket_qua.cget('text')!r}")
        nguoc = [
            ("chk_xem_video", app.chk_xem_video.cget("text")),
            ("chk_xem_ket_qua", app.chk_xem_ket_qua.cget("text")),
        ]
        for ten, chu_vi, _ in CHUOI_MOI[2:]:
            ds = tim_nut_theo_tien_doan(app, chu_vi)
            nguoc.append((ten, ds[0] if ds else "<KHONG TIM THAY>"))
        for ten, txt in nguoc:
            mong = chu_vi_cua(ten)
            dung = isinstance(txt, str) and mong in txt
            print(f"  [{'PASS' if dung else 'FAIL'}] {ten:24s} = {txt!r}")
            if not dung:
                loi.append(f"VE: {ten} = {txt!r} (mong doi chua '{mong}')")

        print()
        if loi:
            print(f"KET QUA: FAIL ({len(loi)} loi)")
            for d in loi:
                print(f"  - {d}")
            return 1
        print("KET QUA: PASS - 5/5 chuoi moi da co ban dich tieng Anh, "
              "tieng Viet co du dau.")
        return 0
    finally:
        # tra lai file lua ngon ngu ve trang thai ban dau
        if goc_file is not None:
            try:
                with open(FILE_NGON_NGU, "wb") as f:
                    f.write(goc_file)
            except OSError:
                pass
        if app is not None:
            try:
                app.destroy()
            except Exception:                                 # noqa: BLE001
                pass


def tien_en_of(ten):
    """Chuoi tieng Anh mong doi cua 1 widget trong 5 chuoi moi."""
    for t, _, en in CHUOI_MOI:
        if t == ten:
            return en
    return ""


def chu_vi_cua(ten):
    """Chuoi tieng Viet GOC cua 1 widget trong 5 chuoi moi."""
    for t, vi, _ in CHUOI_MOI:
        if t == ten:
            return vi
    return ""


if __name__ == "__main__":
    sys.exit(main())
