"""
Kiem chung rieng cho gui.py v2 (video mau + 2 ngon ngu + thu muc ket qua).

Chay:
    .venv\\Scripts\\python.exe _kk_ngon_ngu.py

Kiem tra 5 dung:
    1. Doi ngon ngu qua lai: nhom dang MO van mo, nhom dang DONG van dong.
    2. Bang dich co khoa cho MOI nhan hien thi (in ra danh sach thieu - can rong).
    3. Nut "Dung video mau nay" dien dung duong dan tuyet doi, ton tai tren dia
       cho ca 7 video (o ca 2 ngon ngu).
    4. O "Luu ket qua" mac dinh la THU MUC (khong phai file video).
    5. Chu trang thai "Chua chay" dung 1 khoang trang va co ban dich.

File nay chi DOC gui.py, khong sua gi.
"""

from __future__ import annotations

import os
import sys
import traceback

import customtkinter as ctk

import gui
from cam_ai_core import output_paths
from gui import (DICH_VI_EN, NGON_NGU_FILE, VIDEO_MAU, _KHOA_DICH_TIEU,
                 CamAIGui, dem_widget_hien_thi)

AN = "  "


def in_ky(dong: str) -> None:
    print(dong)


def co_khoa_dich(chu: str) -> bool:
    if not chu:
        return True
    if chu in DICH_VI_EN:
        return True
    return any(chu.startswith(k) for k in _KHOA_DICH_TIEU)


def quet_chu(wdg, ket_qua: list[str]) -> None:
    chu = getattr(wdg, "_chu_vi", None)
    if chu is not None and not co_khoa_dich(chu):
        ket_qua.append(chu)
    for con in wdg.winfo_children():
        quet_chu(con, ket_qua)


# ------------------------------------------------------------------ 1

def kiem_tra_doi_ngon_ngu(app: CamAIGui) -> bool:
    in_ky("\n=== 1. DOI NGON NGU QUA LAI: nhom MO/DONG phai giu nguyen ===")
    nhom = app.danh_sach_nhom()

    # Mo 3 nhom, de lai 5 nhom dong.
    for idx in (0, 3, 7):
        nhom[idx][1].dat_mo(True)
    app.update()
    truoc = [(ten, n.dang_mo, n.khung.winfo_manager(),
              dem_widget_hien_thi(n.khung)) for ten, n in nhom]

    ok = True
    for lan in (1, 2):
        app._doi_ngon_ngu()
        app.update()
        sau = [(ten, n.dang_mo, n.khung.winfo_manager(),
                dem_widget_hien_thi(n.khung)) for ten, n in nhom]
        giong = truoc == sau
        ok = ok and giong
        in_ky(f"  lan {lan} (ngon ngu = {app.ngon_ngu}) | "
              f"tieu de cua so = {app.title()!r}")
        in_ky(f"    nut doi ngon ngu = {app.btn_ngon_ngu.cget('text')!r}")
        for (ten, mo, manager, so), (t2, mo2, m2, so2) in zip(truoc, sau):
            in_ky(f"    [{'OK ' if (mo, manager, so) == (mo2, m2, so2) else 'LOI'}] "
                  f"{ten:<42} mo={mo2} manager={m2!r} so_widget={so2}")
        in_ky(f"    -> trang thai giu nguyen: {giong}")

    # Tra ve tieng Viet (de _kiem_tra_gui.py van 4/4 PASS).
    while app.ngon_ngu != "vi":
        app._doi_ngon_ngu()
        app.update()
    in_ky(f"  da tra ve tieng Viet | tieu de = {app.title()!r} | "
          f"nut = {app.btn_ngon_ngu.cget('text')!r}")
    in_ky(f"  file luu ngon ngu: {NGON_NGU_FILE} -> "
          f"{'co' if os.path.isfile(NGON_NGU_FILE) else 'khong'}")
    return ok


# ------------------------------------------------------------------ 2

def kiem_tra_bang_dich(app: CamAIGui) -> bool:
    in_ky("\n=== 2. BANG DICH PHAI CO KHOA CHO MOI NHAN HIEN THI ===")
    thieu: list[str] = []
    quet_chu(app, thieu)

    # Nhan trong cua so con "Thong tin mo hinh AI".
    app._mo_thong_tin_model()
    app.update()
    quet_chu(app.cua_so_model, thieu)
    # Tieu de cua so con cung phai co khoa.
    if not co_khoa_dich("Thông tin mô hình AI đang dùng"):
        thieu.append("Thông tin mô hình AI đang dùng")
    # Chu trang thai ben canh thanh tien trinh.
    for mau in gui.TRANG_THAI_TIEN_TRINH.values():
        if not co_khoa_dich(mau):
            thieu.append(mau)

    app.cua_so_model.destroy()
    app.update()

    thieu = sorted(set(thieu))
    in_ky(f"  so khoa trong bang dich : {len(DICH_VI_EN)}")
    in_ky(f"  danh sach khoa THIEU     : {thieu}")
    return not thieu


# ------------------------------------------------------------------ 3

def kiem_tra_video_mau(app: CamAIGui) -> bool:
    in_ky("\n=== 3. NUT 'DUNG VIDEO MAU NAY' -> 7 video ===")
    ok = True
    for ngon_ngu in ("vi", "en"):
        if app.ngon_ngu != ngon_ngu:
            while app.ngon_ngu != ngon_ngu:
                app._doi_ngon_ngu()
            app.update()
        in_ky(f"  --- ngon ngu = {ngon_ngu} ---")
        for nhan_vi, ten_file, dung_luong in VIDEO_MAU:
            hien_thi = app.dich(nhan_vi)
            app.v_video_mau.set(hien_thi)
            app.v_output.set(app.v_output.get())      # giu nguyen
            truoc = app.v_output.get()
            app._dung_video_mau()
            app.update()
            nhan_dung = app.v_video.get()
            mong_doi = os.path.join(
                os.path.dirname(os.path.abspath(gui.__file__)),
                "video_mau", ten_file,
            )
            co_that = os.path.isfile(nhan_dung)
            dung = nhan_dung == mong_doi and co_that
            ok = ok and dung
            in_ky(f"    [{'OK ' if dung else 'LOI'}] {hien_thi}")
            in_ky(f"          -> {nhan_dung}")
            in_ky(f"          ton tai tren dia = {co_that} | "
                  f"dung luong ghi trong bang = {dung_luong} | "
                  f"thu muc 'Luu ket qua' khong doi = {truoc == app.v_output.get()}")
    while app.ngon_ngu != "vi":
        app._doi_ngon_ngu()
    app.update()
    return ok


# ------------------------------------------------------------------ 4

def kiem_tra_thu_muc_ket_qua(app: CamAIGui) -> bool:
    in_ky("\n=== 4. O 'LUU KET QUA' MAC DINH LA THU MUC ===")
    gia_tri = app.v_output.get()
    la_thu_muc = os.path.isdir(gia_tri)
    la_file_video = gia_tri.lower().endswith((".mp4", ".avi", ".mkv", ".mov"))
    in_ky(f"  gia tri mac dinh : {gia_tri}")
    in_ky(f"  la thu muc       : {la_thu_muc}")
    in_ky(f"  ket thuc bang file video : {la_file_video} (phai la False)")

    # Kiem tra khi chay that: output cuoi cung phai NAM TRONG thu muc do.
    app.v_video.set(os.path.join(gui.APP_DIR, "video_test.mp4"))
    cfg = app._tao_cau_hinh()
    out_path, report_path = output_paths(cfg.output)
    trong_thu_muc = os.path.dirname(out_path) == os.path.abspath(gia_tri)
    in_ky(f"  video ket qua se ghi vao : {out_path}")
    in_ky(f"  bao cao CSV se ghi vao   : {report_path}")
    in_ky(f"  nam DUNG trong thu muc da chon : {trong_thu_muc}")

    # Thu muc khong ton tai -> bao loi tieng Viet co dau, khong crash.
    app.v_output.set(os.path.join(gui.APP_DIR, "thu_muc_khong_ton_tai_xyz"))
    try:
        app._tao_cau_hinh()
        bao_dung = False
    except ValueError as exc:
        bao_dung = "Thư mục lưu kết quả không có trên máy" in str(exc)
    in_ky(f"  thu muc khong ton tai -> bao loi dung : {bao_dung}")
    app.v_output.set(gia_tri)
    return la_thu_muc and not la_file_video and trong_thu_muc and bao_dung


# ------------------------------------------------------------------ 5

def kiem_tra_chu_trang_thai(app: CamAIGui) -> bool:
    in_ky("\n=== 5. CHU TRANG THAI BEN CANH THANH TIEN TRINH ===")
    app._set_trang_thai("chua_chay")
    app.update()
    tieng_viet = app.v_tien_trinh.get()
    in_ky(f"  tieng Viet : {tieng_viet!r}")
    dung_khoang = tieng_viet == "Chưa chạy"
    in_ky(f"  dung 1 khoang trang (khong phai 2) : {dung_khoang}")

    while app.ngon_ngu != "en":
        app._doi_ngon_ngu()
    app.update()
    tieng_anh = app.v_tien_trinh.get()
    in_ky(f"  tieng Anh  : {tieng_anh!r}")
    dung_dich = tieng_anh == "Not run yet"
    in_ky(f"  doi sang tieng Anh dung : {dung_dich}")

    while app.ngon_ngu != "vi":
        app._doi_ngon_ngu()
    app.update()
    in_ky(f"  quay lai tieng Viet : {app.v_tien_trinh.get()!r}")
    return dung_khoang and dung_dich


# ------------------------------------------------------------------ chay

def chay() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()

    in_ky("CamAI - kiem chung rieng: video mau + ngon ngu + thu muc ket qua")
    in_ky(f"  cua so  : {app.winfo_width()}x{app.winfo_height()}")
    in_ky(f"  tieu de : {app.title()!r}")
    in_ky(f"  VIDEO_MAU co {len(VIDEO_MAU)} muc")

    ket_qua = {
        "doi ngon ngu giu trang thai mo/dong": kiem_tra_doi_ngon_ngu(app),
        "bang dich du khoa cho moi nhan": kiem_tra_bang_dich(app),
        "nut dung video mau": kiem_tra_video_mau(app),
        "o luu ket qua la thu muc": kiem_tra_thu_muc_ket_qua(app),
        "chu trang thai 'Chua chay'": kiem_tra_chu_trang_thai(app),
    }

    in_ky("\n=== KET QUA ===")
    for ten, ok in ket_qua.items():
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}")

    app.destroy()
    return 0 if all(ket_qua.values()) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    try:
        sys.exit(chay())
    except Exception:                                       # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)