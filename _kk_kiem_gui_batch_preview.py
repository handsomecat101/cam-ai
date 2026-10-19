# -*- coding: utf-8 -*-
"""
Kiem chung doc lap: GUI o che do PHAN TICH THEO LO (batch) co hien khung hinh
hay khong (bug "khung Xem video den").

Khac voi _kk_kiem_gui_chay_thuc.py:
  - thu muc ket qua rieng (_kk_out/pc_audit/V5_batch_preview) -> khong dung
  - dem SO LAN khung hinh thuc su duoc hien (bom _hien_khung_hinh)
  - do pixel VUNG KHUNG HINH trong anh chup (crop theo toa do widget) de
    chung minh panel KHONG DEN
  - luu 3 anh chup: luc moi bat dau, luc dang chay, luc xong

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_gui_batch_preview.py
"""
from __future__ import annotations

import ctypes
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
THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "pc_audit", "V5_batch_preview")
IMG_DAU = os.path.join(THU_MUC_KQ, "v5_moi_bat_dau.png")
IMG_CHAY = os.path.join(THU_MUC_KQ, "v5_dang_chay.png")
IMG_CUOI = os.path.join(THU_MUC_KQ, "v5_xong.png")
HET_GIOI = 180.0

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
        "sang_lc": round(sum(stat.stddev) / 3.0, 2),
        "max": max(rgb.getextrema()[i][1] for i in range(3)),
        "min": min(rgb.getextrema()[i][0] for i in range(3)),
    }


def chup(app, duong_dan, tieu_de):
    from PIL import ImageGrab
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
    tt = do_anh(anh)
    tt["duong_dan"] = duong_dan
    tt["toa_do"] = (rc.left, rc.top, rc.right, rc.bottom)
    in_ky(f"  [chup] {tieu_de} -> {os.path.basename(duong_dan)} | "
          f"{tt['kich_thuoc']} | mau={tt['so_mau']} | "
          f"sang tb={tt['sang_tb']} | max={tt['max']} min={tt['min']}")
    return tt, anh, rc


def do_vung_khung_hinh(anh, rc, app):
    """Cat dung vung widget 'Xem video' trong anh chup cua so.

    winfo_rootx/rooty cho toa do MAN HINH cua widget -> chuyen sang toa do
    trong anh chup bang cach tru di canh cua so.
    """
    o = app.o_hinh
    x0 = o.winfo_rootx() - rc.left
    y0 = o.winfo_rooty() - rc.top
    w = o.winfo_width()
    h = o.winfo_height()
    if w <= 1 or h <= 1:
        return None, {"loi": "widget khong co kich thuoc"}
    vung = anh.crop((x0, y0, x0 + w, y0 + h))
    tt = do_anh(vung)
    tt["vung"] = (x0, y0, w, h)
    return vung, tt


def main() -> int:
    import customtkinter as ctk

    from cam_ai_core import VERSION, output_paths
    from gui import CamAIGui

    os.makedirs(THU_MUC_KQ, exist_ok=True)
    in_ky("=" * 78)
    in_ky("CamAI v3.2 - KIEM CHUNG KHUNG 'XEM VIDEO' KHI CHAY THEO LO")
    in_ky("=" * 78)
    in_ky(f"  video vao     : {VIDEO_VAO}")
    in_ky(f"  thu muc ket qua: {THU_MUC_KQ}")
    in_ky(f"  phien ban     : {VERSION}")
    in_ky("")

    video_ky_vong, csv_ky_vong = output_paths(
        os.path.join(THU_MUC_KQ,
                     os.path.splitext(os.path.basename(VIDEO_VAO))[0]))
    for d in (video_ky_vong, csv_ky_vong):
        if os.path.isfile(d):
            os.remove(d)
    in_ky(f"  da xoa ket qua cu (de khong co bang chung gia)")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()
    in_ky(f"  cua so: {app.title()!r} ({app.winfo_width()}x{app.winfo_height()})")

    # --- dem so khung hinh thuc su duoc hien len panel ---
    dem = {"so_lan": 0, "byte_gan_nhat": 0}
    ham_goc = app._hien_khung_hinh

    def ham_boc(jpeg):
        dem["so_lan"] += 1
        dem["byte_gan_nhat"] = len(jpeg) if jpeg else 0
        return ham_goc(jpeg)

    app._hien_khung_hinh = ham_boc

    app.v_video.set(VIDEO_VAO)
    app.v_output.set(THU_MUC_KQ)
    app.v_phat_hien.set("1")
    app.v_face.set("1")
    app.v_face_every.set("3")
    app.v_model.set("yolo11n.pt")
    app.v_thiet_bi.set("Tự động")
    app.v_conf.set("0.25")
    app.v_khung.set("1")
    app.v_nhan.set("1")
    app.v_xem_video.set("0")     # BAT -> phan tich theo lo (che do canh chong)
    app.v_canh_bao.set("0")
    app.v_bien_so.set("0")
    app.v_tu_chup.set("0")
    app.v_tach_o.set("0")
    app.v_vung.set("0")
    app.v_vat_the.set("0")
    app.v_clip.set("0")
    app.v_dem_ra_vao.set("0")
    app.v_pixelate.set("0")
    app.update()
    in_ky(f"  xem video khi chay = {app.v_xem_video.get()} (0 = che do theo lo)")

    tt_dau, _, _ = chup(app, IMG_DAU, "MOI BAT DAU")
    in_ky("")

    moc = time.monotonic()
    app.btn_chay.invoke()
    app.update()
    if not app.busy:
        in_ky("  [canh bao] invoke() khong kich hoat -> goi truc tiep _bat_dau()")
        app._bat_dau()
        app.update()
    in_ky(f"  app.busy = {app.busy}")

    anh_chay = None
    tt_chay = None
    tt_vung = None
    da_chup = False
    het_gioi = False
    while True:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        da_chay = time.monotonic() - moc
        if not da_chup and da_chay > 6.0 and dem["so_lan"] > 0:
            tt_chay, anh_chay, rc_chay = chup(app, IMG_CHAY, "DANG CHAY")
            vung, tt_vung = do_vung_khung_hinh(anh_chay, rc_chay, app)
            if vung is not None:
                vung.save(os.path.join(THU_MUC_KQ, "v5_vung_khung_hinh.png"))
                in_ky(f"  [vung khung hinh] {tt_vung['vung']} | "
                      f"mau={tt_vung['so_mau']} | sang tb={tt_vung['sang_tb']} | "
                      f"max={tt_vung['max']} min={tt_vung['min']}")
            in_ky(f"  [dem] khung hinh da hien len panel = {dem['so_lan']} lan")
            da_chup = True
        if not app.busy and app.result is not None:
            break
        if da_chay > HET_GIOI:
            het_gioi = True
            break
        time.sleep(0.005)

    thoi_gian = time.monotonic() - moc
    for _ in range(30):
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        time.sleep(0.05)

    tt_cuoi, anh_cuoi, rc_cuoi = chup(app, IMG_CUOI, "SAU KHI XONG")
    vung_cuoi, tt_vung_cuoi = do_vung_khung_hinh(anh_cuoi, rc_cuoi, app)
    if vung_cuoi is not None:
        vung_cuoi.save(os.path.join(THU_MUC_KQ, "v5_vung_khung_hinh_cuoi.png"))
        in_ky(f"  [vung khung hinh - cuoi] {tt_vung_cuoi['vung']} | "
              f"mau={tt_vung_cuoi['so_mau']} | sang tb={tt_vung_cuoi['sang_tb']} | "
              f"max={tt_vung_cuoi['max']} min={tt_vung_cuoi['min']}")

    res = app.result
    video_path = getattr(res, "out_path", "") or video_ky_vong
    csv_path = getattr(res, "report_path", "") or csv_ky_vong

    in_ky("")
    in_ky("[KET QUA]")
    in_ky("-" * 78)
    in_ky(f"  thoi gian chay        : {thoi_gian:.1f} s "
          f"(het gioi = {HET_GIOI:.0f} s)")
    in_ky(f"  khung hinh hien panel : {dem['so_lan']} lan | "
          f"jpeg gan nhat = {dem['byte_gan_nhat']} byte")
    in_ky(f"  video ket qua         : {video_path} | "
          f"{os.path.getsize(video_path) if os.path.isfile(video_path) else 'KHONG CO'}")
    in_ky(f"  csv bao cao           : {csv_path} | "
          f"{os.path.getsize(csv_path) if os.path.isfile(csv_path) else 'KHONG CO'}")
    if res is not None:
        in_ky(f"  frames / fps          : {res.frames} / {res.fps}")
        in_ky(f"  max nguoi / max mat   : {res.max_people} / {res.max_faces}")
    dong_log = [d for d in (x.rstrip() for x in
                            app.log_box.get("1.0", "end").splitlines()) if d]
    in_ky(f"  dong nhat ky cuoi     :")
    for d in dong_log[-8:]:
        in_ky(f"      {d}")

    # ket luan
    vung_den = bool(tt_vung) and tt_vung["so_mau"] <= 4 and tt_vung["max"] <= 8
    ok_hien = dem["so_lan"] > 0 and not vung_den
    ok_file = os.path.isfile(video_path) and os.path.getsize(video_path) > 0
    in_ky("")
    in_ky(f"  [A] Khung hinh da hien len panel : {'PASS' if dem['so_lan'] > 0 else 'FAIL'}"
          f" ({dem['so_lan']} lan)")
    in_ky(f"  [B] Vung 'Xem video' KHONG den    : {'FAIL' if vung_den else 'PASS'}"
          + (f" | mau={tt_vung['so_mau']} max={tt_vung['max']} min={tt_vung['min']}"
             if tt_vung else ""))
    in_ky(f"  [C] Video + CSV ket qua          : {'PASS' if ok_file else 'FAIL'}")
    tong = "PASS" if (ok_hien and ok_file and not vung_den) else "FAIL"
    in_ky(f"  TONG KET: {tong}")

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if tong == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
