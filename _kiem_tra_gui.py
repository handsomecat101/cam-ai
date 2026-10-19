"""
CamAI - kiem chung bo cuc "gập mở" cua gui.py (khong can bam chuot that).

Chay:
    .venv\\Scripts\\python.exe _kiem_tra_gui.py

Lam gi:
    1. Dung cua so that trong chinh tien trinh nay, khong dung mainloop.
    2. Kiem tra MAC DINH THU GON HET: khong tinh nang nao dang mo luc moi mo.
    3. Bam gia lap vao tung tieu de, kiem tra so widget cau hinh THAT SU
       xuat hien (winfo_manager + winfo_viewable), roi bam lai de an.
    4. Bat/tat checkbox xem co tu bung / tu thu gon + khoi phuc mac dinh khong.
    5. Mo cua so con "Thong tin mo hinh AI", kiem tra du 4 model.

Khong sua gi ca trong gui.py - file nay chi doc.
"""

from __future__ import annotations

import sys
import traceback

import customtkinter as ctk

import gui
from gui import CamAIGui, dem_widget_hien_thi

TEN_COT = 60


def in_ky(dong: str) -> None:
    print(dong)


def kiem_tra_mac_dinh(app: CamAIGui) -> bool:
    in_ky("\n=== 1. MAC DINH: phai THU GON HET ===")
    ok = True
    for ten, nhom in app.danh_sach_nhom():
        trang_thai = nhom.trang_thai()
        so = nhom.dem_widget_hien_thi()
        dung = (nhom.khung.winfo_manager() == "" and not nhom.dang_mo and so == 0)
        ok = ok and dung
        in_ky(f"  [{'OK ' if dung else 'LOI'}] {ten:<26} {trang_thai}")
    return ok


def kiem_tra_bam_tieu_de(app: CamAIGui) -> bool:
    in_ky("\n=== 2. BAM TIEU DE: phai MO / DONG that su ===")
    ok = True
    for ten, nhom in app.danh_sach_nhom():
        # --- bam 1 lan: phai mo ---
        nhom.btn_mo.invoke()
        app.update()
        mo = nhom.khung.winfo_manager()
        xunghinh = nhom.khung.winfo_viewable()
        so_mo = dem_widget_hien_thi(nhom.khung)
        mo_dung = mo == "grid" and xunghinh == 1 and so_mo > 0 and nhom.dang_mo
        # --- bam them 1 lan: phai dong ---
        nhom.btn_mo.invoke()
        app.update()
        dong = nhom.khung.winfo_manager()
        xunghinh2 = nhom.khung.winfo_viewable()
        so_dong = dem_widget_hien_thi(nhom.khung)
        dong_dung = dong == "" and xunghinh2 == 0 and so_dong == 0 and not nhom.dang_mo
        ok = ok and mo_dung and dong_dung
        in_ky(f"  [{'OK ' if mo_dung and dong_dung else 'LOI'}] {ten}")
        in_ky(f"        sau 1 lan bam : manager={mo!r} viewable={xunghinh} "
               f"so_widget={so_mo}")
        in_ky(f"        sau 2 lan bam : manager={dong!r} viewable={xunghinh2} "
               f"so_widget={so_dong}")
    return ok


def kiem_tra_checkbox(app: CamAIGui) -> bool:
    in_ky("\n=== 3. BAT / TAT CHECKBOX: tu bung, tu thu gon, khoi phuc mac dinh ===")
    ok = True
    for ten, nhom in app.danh_sach_nhom():
        if not nhom.co_checkbox:
            in_ky(f"  [--- ] {ten:<26} (khong co checkbox - nut mo cua so con)")
            continue
        bien = nhom.var
        dang_bat = bien.get() == "1"

        # --- tat -> phai thu gon + khoi phuc mac dinh ---
        bien.set("0")
        nhom._doi_checkbox()
        app.update()
        if dang_bat:
            nhom._mac_dinh and [v.set(g) for v, g in nhom._mac_dinh]
        thu_gon = nhom.khung.winfo_manager() == "" and dem_widget_hien_thi(nhom.khung) == 0
        khoi_phuc = all(v.get() == g for v, g in nhom._mac_dinh)

        # --- bat -> phai bung ra ---
        bien.set("1")
        nhom._doi_checkbox()
        app.update()
        bung = nhom.khung.winfo_manager() == "grid" and dem_widget_hien_thi(nhom.khung) > 0

        # --- tra ve trang thai ban dau ---
        bien.set("1" if dang_bat else "0")
        nhom._doi_checkbox()
        app.update()

        dung = thu_gon and khoi_phuc and bung
        ok = ok and dung
        in_ky(f"  [{'OK ' if dung else 'LOI'}] {ten:<26} "
               f"mac_dinh_ban_dau={'BAT' if dang_bat else 'TAT'} | "
               f"tat->thu_gon={thu_gon} khoi_phuc_mac_dinh={khoi_phuc} bat->bung={bung}")
    return ok


def kiem_tra_cua_so_model(app: CamAIGui) -> bool:
    in_ky("\n=== 4. CUA SO CON 'Thong tin mo hinh AI' ===")
    app._mo_thong_tin_model()
    app.update()
    win = app.cua_so_model
    if win is None or not win.winfo_exists():
        in_ky("  [LOI] khong mo duoc cua so con")
        return False
    ten_cua_so = win.title()
    in_ky(f"  tieu de cua so con : {ten_cua_so!r}")

    chu = []
    def quet(w):
        try:
            gia_tri = w.cget("text")
            if gia_tri:
                chu.append(str(gia_tri))
        except Exception:                                   # noqa: BLE001
            pass
        for con in w.winfo_children():
            quet(con)
    quet(win)

    from model_info import ALL_MODELS
    thieu = [m.ten for m in ALL_MODELS
             if not any(m.ten in c for c in chu)]
    in_ky(f"  so nhan thu ky thuat thu thay : {len(chu)}")
    for m in ALL_MODELS:
        co = any(m.ten in c for c in chu)
        in_ky(f"    [{'OK ' if co else 'LOI'}] {m.ten:<26} ({m.model_id})")
    in_ky(f"  co khoi 'Vai tro tung mo hinh'  : "
          f"{any('Vai trò' in c for c in chu)}")
    in_ky(f"  co khoi 'Thong so ky thuat'     : "
          f"{any('Thông số kỹ thuật' in c for c in chu)}")
    in_ky(f"  co dong phien ban + GPU          : "
          f"{any('GPU' in c for c in chu)}")

    win.destroy()
    app.update()
    dong_duoc = not win.winfo_exists()
    in_ky(f"  dong duoc khong treo           : {dong_duoc}")
    return not thieu and dong_duoc and ten_cua_so == "Thông tin mô hình AI đang dùng"


def chay() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()

    in_ky("CamAI - kiem chung bo cuc gui.py")
    in_ky(f"  cua so   : {app.winfo_width()}x{app.winfo_height()}")
    in_ky(f"  tieu de  : {app.title()!r}")

    ket_qua = {
        "mac dinh thu gon het": kiem_tra_mac_dinh(app),
        "bam tieu de mo/dong": kiem_tra_bam_tieu_de(app),
        "checkbox tu bung/thu gon": kiem_tra_checkbox(app),
        "cua so con thong tin model": kiem_tra_cua_so_model(app),
    }

    in_ky("\n=== KET QUA ===")
    for ten, ok in ket_qua.items():
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}")

    app.destroy()
    return 0 if all(ket_qua.values()) else 1


if __name__ == "__main__":
    # Console Windows mac dinh la cp1252 -> in tieng Viet co dau se ra chu loi.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    try:
        sys.exit(chay())
    except Exception:                                       # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)