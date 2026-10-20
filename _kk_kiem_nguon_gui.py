# -*- coding: utf-8 -*-
"""CamAI - KIEM CHUNG GUI chon nguon (v3.6): video / anh / camera may / camera IP.

Kiem 7 muc:
  [1] gui.py import duoc (compile + import khong loi)
  [2] NHAN trang thai o "Nguon" doi dung theo loai nguon
      (video / anh tinh / camera may / camera IP) + tu cap nhat khi go tay
  [3] run_analysis voi ANH -> EXIT=0, co file .jpg ket qua + file CSV
  [4] run_analysis voi CAMERA KHONG MO DUOC -> loi RO RANG, khong treo (<20s)
  [5] nut DUNG dung duoc vong lap LIVE (bo qua neu may khong co camera)
  [6] quet camera trong hop thoai khong treo (thread + hang doi)
  [7] chup anh GUI (co san de coordinator tu xem)

Chay:
  .venv\\Scripts\\python.exe -W ignore _kk_kiem_nguon_gui.py
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
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

THU_MUC_OUT = os.path.join(APP_DIR, "_kk_out", "agent_a_nguon")
ANH_MAU = os.path.join(APP_DIR, "sample_bus.jpg")
VIDEO_MAU = os.path.join(APP_DIR, "video_mau", "one-by-one-person-detection.mp4")

LOI = []      # danh sach loi (nen rong = PASS)
KET = []      # bang ket luan


def in_ky(*args) -> None:
    print(*args, file=_REAL_STDOUT, flush=True)


def bao(ten: str, ok: bool, ghi_chu: str = "") -> None:
    KET.append((ten, ok, ghi_chu))
    in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}"
          + (f"  ({ghi_chu})" if ghi_chu else ""))
    if not ok:
        LOI.append(ten)


def tao_thu_muc() -> str:
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    return THU_MUC_OUT


# --------------------------------------------------------------- [1] import

def kiem_import() -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[1] IMPORT gui.py")
    in_ky("=" * 78)
    import py_compile
    try:
        py_compile.compile(os.path.join(APP_DIR, "gui.py"), doraise=True)
        bao("gui.py compile", True)
    except Exception as exc:                          # noqa: BLE001
        bao("gui.py compile", False, str(exc))
        return
    try:
        import gui  # noqa: F401
        import cam_ai_core
        bao("gui.py import", True,
            f"cam_ai_core VERSION={cam_ai_core.VERSION}")
    except Exception as exc:                          # noqa: BLE001
        bao("gui.py import", False, f"{exc.__class__.__name__}: {exc}")
        traceback.print_exc()


# ------------------------------------------------- [2] nhan loai nguon GUI

def kiem_nhan_nguon(app) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[2] NHAN TRANG THAI O 'NGUON' THEO LOAI NGUON")
    in_ky("=" * 78)
    truoc = app.v_video.get()
    truong_hop = [
        (ANH_MAU, "Ảnh tĩnh", "duong dan ANH jpg"),
        (VIDEO_MAU, "Video", "duong dan VIDEO"),
        ("0", "Camera máy", "index camera may"),
        ("rtsp://192.168.1.10:554/stream", "Camera IP", "dia chi camera IP"),
        ("", "Chưa chọn", "de trong"),
    ]
    for gia_tri, can_co, mo_ta in truong_hop:
        app.v_video.set(gia_tri)
        app.update_idletasks()
        nhan = str(app.lbl_nguon.cget("text"))
        ok = can_co in nhan
        bao(f"nhan nguon [{mo_ta}]", ok, f"= {nhan!r}")
    app.v_video.set(truoc)
    app.update_idletasks()

    # Tu cap nhat khi nguoi dung GO TAY vao o (trace_add cua StringVar).
    app.v_video.set("")
    app.update_idletasks()
    app.v_video.set("0")
    app.update_idletasks()
    nhan = str(app.lbl_nguon.cget("text"))
    bao("nhan nguon tu cap nhat khi go tay", "Camera máy" in nhan, f"= {nhan!r}")
    app.v_video.set(truoc)
    app.update_idletasks()


# --------------------------------------------- [3] run_analysis voi ANH

def kiem_anh() -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[3] run_analysis voi ANH TINH")
    in_ky("=" * 78)
    from cam_ai_core import AnalysisConfig, run_analysis

    if not os.path.isfile(ANH_MAU):
        bao("co anh mau de test", False, f"khong tim thay {ANH_MAU}")
        return
    thu_muc = tao_thu_muc()
    cfg = AnalysisConfig(
        input=ANH_MAU,
        output=os.path.join(thu_muc, "sample_bus"),
        no_face=True,
        model="yolo11n.pt",
    )
    dong_log = []
    t0 = time.monotonic()
    try:
        res = run_analysis(cfg, log=lambda t: dong_log.append(t))
    except Exception as exc:                          # noqa: BLE001
        bao("run_analysis(anh) khong loi", False,
            f"{exc.__class__.__name__}: {exc}")
        return
    t_gay = time.monotonic() - t0
    bao("run_analysis(anh) khong loi", True, f"{t_gay:.1f}s")

    out_path = res.out_path or ""
    bao("ket qua la file ANH (.jpg)", out_path.lower().endswith(".jpg"),
        f"out_path={out_path}")
    bao("file ket qua .jpg ton tai", bool(out_path)
        and os.path.isfile(out_path))
    bao("file CSV bao cao ton tai",
        bool(res.report_path) and os.path.isfile(res.report_path),
        f"report_path={res.report_path}")
    if res.report_path and os.path.isfile(res.report_path):
        with open(res.report_path, "r", encoding="utf-8", errors="replace") as f:
            so_dong = len(f.read().splitlines())
        bao("CSV co du lieu (>= 2 dong)", so_dong >= 2, f"{so_dong} dong")
    else:
        bao("CSV co du lieu (>= 2 dong)", False, "khong doc duoc CSV")
    in_ky(f"  -> out_path   = {out_path}")
    in_ky(f"  -> report_path= {res.report_path}")


# ---------------------------------- [4] camera KHONG MO DUOC -> loi ro rang

def kiem_camera_loi() -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[4] CAMERA KHONG MO DUOC -> LOI RO RANG, KHONG TREO (< 20s)")
    in_ky("=" * 78)
    from cam_ai_core import AnalysisConfig, CamAIError, run_analysis

    thu_muc = tao_thu_muc()

    # 4a. webcam may ("0") - may co camera hay khong deu co kich ban.
    cfg = AnalysisConfig(
        input="0",
        output=os.path.join(thu_muc, "camera_0"),
        no_face=True,
        model="yolo11n.pt",
    )
    ket = {}

    def worker():
        try:
            res = run_analysis(
                cfg,
                # Dung ngay sau khung hinh dau (tranh chay vo han).
                progress_cb=lambda p: False,
                log=lambda t: None,
            )
            ket["ok"] = res
        except Exception as exc:                      # noqa: BLE001
            ket["loi"] = exc

    t0 = time.monotonic()
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=25)
    t_gay = time.monotonic() - t0
    if th.is_alive():
        bao("camera may (0) khong treo", False,
            f"van chay sau {t_gay:.1f}s (may co camera that)")
    elif "loi" in ket:
        loi = ket["loi"]
        la_cam = isinstance(loi, CamAIError) and "camera" in str(loi).lower()
        bao("camera may (0) bao loi ro rang", la_cam,
            f"{t_gay:.1f}s | {str(loi)[:120]}")
    else:
        bao("camera may (0) bao loi ro rang", False,
            "may co camera -> pipeline chay duoc (khong phai loi)")
        in_ky("      (may nay CO camera -> khong co loi de kiem)")

    # 4b. camera IP khong ket noi duoc (dia chi khong ton tai).
    cfg_ip = AnalysisConfig(
        input="rtsp://127.0.0.1:1/khong-ton-tai",
        output=os.path.join(thu_muc, "camera_ip"),
        no_face=True,
        model="yolo11n.pt",
    )
    ket2 = {}

    def worker2():
        try:
            ket2["ok"] = run_analysis(cfg_ip, log=lambda t: None)
        except Exception as exc:                      # noqa: BLE001
            ket2["loi"] = exc

    t0 = time.monotonic()
    th2 = threading.Thread(target=worker2, daemon=True)
    th2.start()
    th2.join(timeout=25)
    t_gay2 = time.monotonic() - t0
    if th2.is_alive():
        bao("camera IP khong ket noi -> loi, khong treo", False,
            f"van chay sau {t_gay2:.1f}s")
    elif "loi" in ket2:
        loi = ket2["loi"]
        la_cam = isinstance(loi, CamAIError)
        bao("camera IP khong ket noi -> loi ro rang", la_cam and t_gay2 < 20,
            f"{t_gay2:.1f}s | {str(loi)[:120]}")
    else:
        bao("camera IP khong ket noi -> loi ro rang", False,
            "khong loi (khong mong doi)")


# ---------------------------------------- [5] nut DUNG dung vong lap LIVE

def kiem_dung_live(app, co_camera: bool) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[5] NUT DUNG DUNG DUOC VONG LAP LIVE")
    in_ky("=" * 78)
    from cam_ai_core import Progress

    # 5a. Co so: callback cua GUI tra False khi co lenh DUNG.
    app.stop_flag.set()
    p = Progress(frame_index=1, total_frames=0, so_nguoi=0, so_mat=0, vao=0,
                 ra=0, trong_vung=0, vi_pham=0, canh_lau=0, nhan_dien="")
    ket = app._tien_trinh_cb(p)
    bao("callback tien trinh tra False khi co lenh DUNG", ket is False,
        f"= {ket!r}")
    app.stop_flag.clear()

    if not co_camera:
        bao("vong lap live dung bang nut DUNG", True,
            "KHONG KIEM CHUNG DUOC do may nay khong co camera")
        return

    # 5b. E2E: bat dau phan tich camera -> bam DUNG -> phai dung.
    app.v_video.set("0")
    app.update_idletasks()
    app._bat_dau()
    time.sleep(6)
    app._dung()
    for _ in range(60):
        app.update()
        time.sleep(0.2)
        if not app.busy:
            break
    res = getattr(app, "result", None)
    da_dung = bool(res is not None and getattr(res, "stopped", False))
    bao("vong lap live dung bang nut DUNG", da_dung,
        f"busy={app.busy} stopped={getattr(res, 'stopped', None)}")
    app.v_video.set(os.path.join(APP_DIR, "video_test.mp4"))
    app.update_idletasks()


# --------------------------------------- [6] quet camera khong treo

def kiem_quet_camera(app) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[6] QUET CAMERA TRONG HOP THOAI (thread + hang doi)")
    in_ky("=" * 78)
    from cam_ai_core import quet_camera

    # 6a. Ham cua core chay duoc va tra ve danh sach.
    t0 = time.monotonic()
    try:
        ds = quet_camera()
    except Exception as exc:                          # noqa: BLE001
        bao("quet_camera() khong loi", False, str(exc))
        ds = []
    t_gay = time.monotonic() - t0
    bao("quet_camera() khong loi va khong treo", t_gay < 25,
        f"{t_gay:.1f}s | {len(ds)} muc")
    mo_duoc = [c for c in ds if c.get("mo_duoc")]
    in_ky(f"  -> camera mo duoc: {len(mo_duoc)}/{len(ds)}")
    for c in ds:
        in_ky(f"     index {c.get('index')}: mo_duoc={c.get('mo_duoc')} "
              f"ten={c.get('ten')!r} {c.get('width')}x{c.get('height')}")

    # 6b. Hop thoai trong GUI: mo, quet, va dong - phai khong treo.
    try:
        app._xem_danh_sach_camera()
        app.update()
        dong = []
        for _ in range(150):                 # <= 30 giay
            app.update()
            time.sleep(0.2)
            if getattr(app, "lbl_trang_thai_camera", None) is None:
                break
            chu = str(app.lbl_trang_thai_camera.cget("text"))
            dong.append(chu)
            if chu and ("tìm thấy" in chu or "không có camera" in chu
                        or "Chưa quét" in chu):
                break
        chu = dong[-1] if dong else ""
        bao("hop thoai quet camera khong treo", bool(chu),
            f"trang thai cuoi = {chu!r}")
        app._dong_hop_thoai_camera()
        app.update()
    except Exception as exc:                          # noqa: BLE001
        bao("hop thoai quet camera khong treo", False,
            f"{exc.__class__.__name__}: {exc}")


# ------------------------------- [8] che do song ngu (tieng Anh) cho
#                                        cac CHUOI MOI

def kiem_tieng_anh(app) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[8] CHE DO TIENG ANH CHO CAC CHUOI MOI (nguon / camera)")
    in_ky("=" * 78)
    import gui as gui_mod

    ngon_ngu_cu = app.ngon_ngu
    app.ngon_ngu = "en"
    app._lam_moi_ngon_ngu()
    app.update_idletasks()

    # 8a. Nhan trang thai nguon -> phai la tieng Anh.
    app.v_video.set(ANH_MAU)
    app.update_idletasks()
    nhan = str(app.lbl_nguon.cget("text"))
    bao("EN: nhan loai nguon (anh)", "Still image" in nhan, f"= {nhan!r}")
    app.v_video.set("0")
    app.update_idletasks()
    nhan = str(app.lbl_nguon.cget("text"))
    bao("EN: nhan loai nguon (camera may)", "Built-in camera" in nhan,
        f"= {nhan!r}")
    app.v_video.set("rtsp://1.2.3.4:554/s")
    app.update_idletasks()
    nhan = str(app.lbl_nguon.cget("text"))
    bao("EN: nhan loai nguon (camera IP)", "IP camera" in nhan, f"= {nhan!r}")
    app.v_video.set(os.path.join(APP_DIR, "video_test.mp4"))
    app.update_idletasks()
    nhan = str(app.lbl_nguon.cget("text"))
    bao("EN: nhan loai nguon (video)", "Video" in nhan, f"= {nhan!r}")

    # 8b. Moi chuoi hien thi MOI phai co ban dich tieng Anh.
    chuoi_moi = [
        "Nguồn", "Chọn ảnh…", "Chọn camera…", "Danh sách camera",
        "Quét camera", "Huỷ", "Đóng", "Địa chỉ camera IP",
        "Dùng địa chỉ này", "Mở kết quả", "Camera",
        "Loại nguồn: ", "Ảnh tĩnh", "Camera máy", "Camera IP",
        "Chưa chọn", "Số camera tìm thấy: ",
    ]
    thieu = [c for c in chuoi_moi if c not in gui_mod.DICH_VI_EN]
    bao("EN: moi chuoi moi deu co ban dich", not thieu,
        f"thieu: {thieu}" if thieu else f"{len(chuoi_moi)} chuoi")

    # 8c. Cac chuoi hien thi cu cua app van dich duoc (khong lam hong).
    for c in ("Chọn video…", "Mở thư mục clip", "Lưu kết quả", "Chọn…"):
        bao(f"EN: chuoi cu van dich duoc ({c!r})", c in gui_mod.DICH_VI_EN)

    app.ngon_ngu = ngon_ngu_cu
    app._lam_moi_ngon_ngu()
    app.update_idletasks()


# ------------------- [9] thanh tien trinh: indeterminate cho nguon LIVE

def kiem_tien_trinh_live(app) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[9] THANH TIEN TRINH INDETERMINATE (nguon live) + KET QUA ANH")
    in_ky("=" * 78)
    from cam_ai_core import Progress

    app._bat_tien_trinh_live()
    app.update_idletasks()
    ok_mode = str(app.bar.cget("mode")) == "indeterminate"
    bao("bar chuyen sang mode indeterminate", ok_mode,
        f"mode={app.bar.cget('mode')!r}")
    bao("co co danh bao indeterminate", getattr(app, "_bar_indeterminate", False))

    # Cap nhat tien trinh khi dang indeterminate -> KHONG set() (khong lam
    # vong chay nguoc lai thanh "chay vui").
    p = Progress(frame_index=5, total_frames=0, so_nguoi=2, so_mat=1, vao=0,
                 ra=0, trong_vung=0, vi_pham=0, canh_lau=0, nhan_dien="")
    app._hien_tien_trinh(p)
    app.update_idletasks()
    bao("cap nhat tien trinh khi indeterminate khong loi", True,
        f"bar.get()={app.bar.get():.3f}")

    app._ket_tuc_tien_trinh()
    app.update_idletasks()
    bao("bar tra ve mode determinate",
        str(app.bar.cget("mode")) == "determinate",
        f"mode={app.bar.cget('mode')!r}")

    # Ket qua nguon ANH: file .jpg -> `_hien_ket_qua` phai chay duoc.
    from cam_ai_core import AnalysisResult
    anh_kq = os.path.join(THU_MUC_OUT, "sample_bus_ket_qua.jpg")
    res = AnalysisResult(out_path=anh_kq,
                         report_path=os.path.join(THU_MUC_OUT,
                                                 "sample_bus_bao_cao.csv"))
    try:
        app._hien_ket_qua(res)
        app.update_idletasks()
        bao("_hien_ket_qua voi ket qua ANH (.jpg)", True,
            f"bar.get()={app.bar.get():.2f}")
    except Exception as exc:                          # noqa: BLE001
        bao("_hien_ket_qua voi ket qua ANH (.jpg)", False,
            f"{exc.__class__.__name__}: {exc}")


# ------------------- [10] nut DUNG dung duoc 1 lan chay that (video)

def kiem_dung_that(app) -> None:
    in_ky("")
    in_ky("=" * 78)
    in_ky("[10] NUT DUNG DUNG DUOC 1 LAN CHAY THAT (video dai)")
    in_ky("=" * 78)
    video = os.path.join(APP_DIR, "video_mau", "one-by-one-person-detection.mp4")
    if not os.path.isfile(video):
        bao("co video mau de test", False, f"khong tim thay {video}")
        return
    app.v_video.set(video)
    app.update_idletasks()
    # Luu ket qua VAO THU MUC TEST (khong ghi de file goc cua du an).
    app.v_output.set(THU_MUC_OUT)
    app.update_idletasks()
    app._bat_dau()
    time.sleep(8)
    da_chay = app.busy
    app._dung()
    for _ in range(120):
        app.update()
        time.sleep(0.2)
        if not app.busy:
            break
    res = getattr(app, "result", None)
    bao("nut DUNG dung duoc pipeline", (not app.busy) and da_chay,
        f"busy luc dau={da_chay} | busy cuoi={app.busy}")
    bao("ket qua bi gan co 'stopped'",
        res is not None and bool(getattr(res, "stopped", False)),
        f"stopped={getattr(res, 'stopped', None)}")


# ------------------------------------------------------------- [7] chup anh

def chup(win, duong_dan: str) -> None:
    """Chup cua so theo mau bat buoc cua du an."""
    import ctypes.wintypes
    from PIL import ImageGrab

    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    win.update()
    win.update_idletasks()
    win.attributes("-topmost", True)
    win.lift()
    win.update()
    time.sleep(0.5)
    win.update()
    u32 = ctypes.windll.user32
    rc = ctypes.wintypes.RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(win.winfo_id())), 2)
    if hwnd:
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    anh = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                          all_screens=True)
    anh.save(duong_dan)
    in_ky(f"  -> anh cua so: {duong_dan} {anh.size}")


# ------------------------------------------------------------------- chay

def main() -> int:
    in_ky("=" * 78)
    in_ky("CamAI - KIEM CHUNG GUI CHON NGUON (video / anh / camera)")
    in_ky("=" * 78)

    kiem_import()
    if LOI:
        in_ky("")
        in_ky("KET QUA: FAIL - import loi, dung tai day.")
        return 1

    import customtkinter as ctk
    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()

    try:
        kiem_nhan_nguon(app)

        # Co camera tren may hay khong? (quet 1 lan, dung ham cua core)
        co_camera = False
        try:
            from cam_ai_core import quet_camera
            co_camera = any(c.get("mo_duoc") for c in quet_camera())
        except Exception:                             # noqa: BLE001
            pass
        in_ky(f"  (may nay co camera: {co_camera})")

        kiem_anh()
        kiem_camera_loi()
        kiem_dung_live(app, co_camera)
        kiem_quet_camera(app)
        kiem_tien_trinh_live(app)
        kiem_tieng_anh(app)
        kiem_dung_that(app)

        in_ky("")
        in_ky("[7] CHUP ANH GUI")
        chup(app, os.path.join(THU_MUC_OUT, "gui_nguon.png"))
        # Chup them 1 anh hop thoai chon camera.
        try:
            app._chon_camera()
            app.update()
            time.sleep(0.5)
            app.update()
            win_camera = getattr(app, "_cua_so_camera", None)
            if win_camera is not None:
                chup(win_camera, os.path.join(THU_MUC_OUT, "hop_thoai_camera.png"))
            app._dong_hop_thoai_camera()
            app.update()
        except Exception as exc:                      # noqa: BLE001
            in_ky(f"  (khong chup duoc hop thoai camera: {exc})")
    finally:
        try:
            app.stop_flag.set()
            app.destroy()
        except Exception:                             # noqa: BLE001
            pass

    in_ky("")
    in_ky("=" * 78)
    in_ky("KET LUA")
    in_ky("=" * 78)
    for ten, ok, ghi in KET:
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}"
              + (f"  ({ghi})" if ghi else ""))
    tong = len([1 for _, ok, _ in KET if ok])
    in_ky("")
    if LOI:
        in_ky(f"KET QUA: FAIL ({len(LOI)}/{len(KET)} muc that bai)")
        for d in LOI:
            in_ky(f"  - {d}")
        return 1
    in_ky(f"KET QUA: PASS - {tong}/{len(KET)} muc")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
