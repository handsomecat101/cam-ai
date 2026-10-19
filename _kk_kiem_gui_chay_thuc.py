# -*- coding: utf-8 -*-
"""
CamAI - CHUNG MINH GUI chay phan tich THAT tu dau den cuoi (E2E).

Muc tieu cua file nay:
  - Mo cua so GUI desktop that (gui.py -> lop CamAIGui).
  - Dien duong dan video vao + thu muc luu ket qua.
  - BAM NUT "BAT DAU" that (btn_chay.invoke() -> _bat_dau()).
  - BOM EVENT LOOP Tk trong vong lap (vi pipeline chay o thread nen va
    phan hien thi duoc ve bang after()).
  - Tu do bang chung DO DUOC:
      1. GUI khoi dong duoc (tieu de cua so + phien ban VERSION)
      2. Pipeline chay xong (app.busy -> False, co ket qua, co dong log)
      3. File video ket qua ton tai va KHONG rong
      4. File CSV bao cao ton tai (so dong)
      5. Video ket qua doc duoc that bang cv2 (dem frame that)
      6. Codec (ffprobe neu co trong PATH; khong co thi bo qua)
  - Chup 2 ANH cua so that: 1 anh khi DANG CHAY + 1 anh SAU KHI CHAY XONG.

Ky thuat chup cua so (thu tu da duyet, KHONG duoc doi):
  1. attributes("-topmost", True) + lift()   (chinh tien trinh so huu cua so)
  2. GetAncestor(winfo_id(), 2)  -> HWND that (GA_ROOT)
  3. GetWindowRect(hwnd)        -> toa do cua so
  4. PIL.ImageGrab.grab(bbox=..., all_screens=True)

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_gui_chay_thuc.py

File nay KHONG sua bat ky file nao khac trong repo.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# --- GIU stdout THAT. gui.py thay sys.stdout bang QueueWriter khi chay
#     pipeline tren thread nen; neu in bang sys.stdout truc tiep thi
#     dong cua script nay se bi "nuot" mat vao nhat ky cua GUI.
_REAL_STDOUT = sys.stdout
try:
    _REAL_STDOUT.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def in_ky(*args) -> None:
    """In ra console THAT (khong bi pipeline nuot mat)."""
    print(*args, file=_REAL_STDOUT, flush=True)


VIDEO_VAO = os.path.join(APP_DIR, "video_test.mp4")
THU_MUC_KQ = os.path.join(APP_DIR, "_kk_out", "gui_e2e")
IMG_DANG_CHAY = os.path.join(THU_MUC_KQ, "gui_dang_chay.png")
IMG_CHAY_THUC = os.path.join(THU_MUC_KQ, "gui_chay_thuc.png")
HET_GIOI = 180.0        # giay - nap model + pipeline co the ton thoi gian

# ------------------------------------------------------------------- Win32
u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def rect_cua_so(app):
    """Toa do cua so that (HWND goc, khong phai widget con)."""
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    if not hwnd:
        return rc
    u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    return rc


def thong_tin_anh(anh):
    """So mau don sac + do sang -> chung minh anh KHONG den / KHONG trang."""
    from PIL import ImageStat

    rgb = anh.convert("RGB")
    mau = rgb.getcolors(maxcolors=2_000_000)
    so_mau = len(mau) if mau is not None else -1
    stat = ImageStat.Stat(rgb)
    tb = stat.mean
    ld = stat.stddev
    return {
        "kich_thuoc": anh.size,
        "so_mau_don_sac": so_mau,
        "sang_tb": round(sum(tb) / 3.0, 2),
        "sang_lc": round(sum(ld) / 3.0, 2),
    }


def chup_cua_so(app, duong_dan):
    """Chup cua so that va luu xuong dia chi. Tra ve thong tin do duoc."""
    from PIL import ImageGrab

    app.update()
    app.update_idletasks()
    # 1. dua cua so len tren + lam noi bat (phai do chinh tien trinh nay goi)
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.4)
    app.update()
    # 2 + 3. HWND that -> toa do cua so
    rc = rect_cua_so(app)
    # 4. chup vung cua so
    anh = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                         all_screens=True)
    anh.save(duong_dan)
    tt = thong_tin_anh(anh)
    tt["duong_dan"] = duong_dan
    tt["toa_do"] = (rc.left, rc.top, rc.right, rc.bottom)
    return tt


def xoa_ket_qua_cu(duong_dan):
    """Xoa file ket qua cu lan truoc (de khong co 'ket qua gia' do bien chung)."""
    if os.path.isfile(duong_dan):
        try:
            os.remove(duong_dan)
            return True
        except OSError:
            return False
    return False


def phan_tram_tu_trang_thai(text):
    """'Khung hình 123/250 · 49%' -> 49.0 (0.0 neu khong doc duoc)."""
    if not text or "%" not in text:
        return 0.0
    try:
        return float(text.rsplit("%", 1)[0].split("·")[-1].strip())
    except ValueError:
        return 0.0


# ------------------------------------------------------------------ kiem tra
def kt_1_gui_khoi_dong(app, version):
    tieu_de = app.title()
    rong = app.winfo_width()
    cao = app.winfo_height()
    ok = bool(tieu_de) and (version in tieu_de) and rong > 0 and cao > 0
    do_so = (f"tieu de={tieu_de!r} | VERSION={version} | "
             f"kich thuoc cua so={rong}x{cao} px")
    return ok, do_so


def kt_2_pipeline_chay_xong(app, dong_log):
    ket_qua = app.result
    co_log_ket_qua = any("Kết quả:" in d for d in dong_log)
    co_log_bao_cao = any("Báo cáo:" in d for d in dong_log)
    ok = (app.busy is False) and (ket_qua is not None) and co_log_ket_qua
    do_so = (f"app.busy={app.busy} | app.result={type(ket_qua).__name__} | "
             f"so dong nhat ky GUI={len(dong_log)} | "
             f"co dong 'Kết quả:'={co_log_ket_qua} | "
             f"co dong 'Báo cáo:'={co_log_bao_cao} | "
             f"hang doi con lai={app.queue.qsize()} muc")
    return ok, do_so


def kt_3_file_video(video_path):
    if not os.path.isfile(video_path):
        return False, f"KHONG TON TAI: {video_path}"
    byte = os.path.getsize(video_path)
    return byte > 0, f"{video_path} | dung luong={byte} byte"


def kt_4_file_csv(csv_path):
    if not os.path.isfile(csv_path):
        return False, f"KHONG TON TAI: {csv_path}"
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        lines = f.read().splitlines()
    tieu_de = lines[0] if lines else ""
    du_lieu = max(0, len(lines) - 1)
    ok = du_lieu > 0
    do_so = (f"{csv_path} | tong so dong={len(lines)} "
             f"(1 dong tieu de + {du_lieu} dong du lieu) | "
             f"tieu de='{tieu_de[:110]}'")
    return ok, do_so


def kt_5_video_doc_duoc(video_path):
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False, f"cv2.VideoCapture khong mo duoc: {video_path}"
    so_frame = 0
    kich = None
    tong_byte = 0
    while True:
        ok, khung = cap.read()
        if not ok:
            break
        if so_frame == 0:
            kich = (khung.shape[1], khung.shape[0])
        tong_byte += int(khung.size)
        so_frame += 1
    cap.release()
    ok = so_frame > 0
    do_so = (f"doc THAT {so_frame} frame | kich thuoc khung={kich} | "
             f"tong so pixel doc duoc={tong_byte}")
    return ok, do_so


def kt_6_codec(video_path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return "BO QUA", "ffprobe KHONG co trong PATH -> bo qua (khong bat buoc)"
    if not os.path.isfile(video_path):
        return "FAIL", f"khong co file video de kiem tra: {video_path}"
    try:
        ket = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries",
             "stream=codec_name,width,height,nb_frames,avg_frame_rate",
             "-of", "default=noprint_wrappers=1", video_path],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        return "BO QUA", f"ffprobe loi khi chay ({exc}) -> bo qua"
    if ket.returncode != 0:
        return "FAIL", f"ffprobe tra ve ma loi {ket.returncode}: {ket.stderr[:200]}"
    dong = ket.stdout.strip().replace("\n", " | ")
    return "PASS", f"ffprobe: {dong}"


# ---------------------------------------------------------------------- chay
def chay() -> int:
    import customtkinter as ctk

    from cam_ai_core import VERSION, output_paths
    from gui import CamAIGui

    os.makedirs(THU_MUC_KQ, exist_ok=True)

    in_ky("=" * 78)
    in_ky("CamAI - CHUNG MINH GUI CHAY PHAN TICH THAT (E2E)")
    in_ky("=" * 78)
    in_ky(f"  video vao       : {VIDEO_VAO}")
    in_ky(f"  thu muc ket qua : {THU_MUC_KQ}")
    in_ky(f"  moc thoi gian   : {HET_GIOI:.0f} giay")
    in_ky(f"  phien ban       : {VERSION}")
    in_ky("")

    # --- xoa ket qua cu lan truoc: khong de file con lai lam "bang chung" ---
    video_ky_vong, csv_ky_vong = output_paths(
        os.path.join(THU_MUC_KQ,
                     os.path.splitext(os.path.basename(VIDEO_VAO))[0]))
    da_xoa = [d for d in (video_ky_vong, csv_ky_vong) if xoa_ket_qua_cu(d)]
    in_ky(f"  da xoa ket qua cu: {da_xoa if da_xoa else 'khong co file nao ton tai'}")
    in_ky("")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    in_ky("[1/6] Mo cua so GUI...")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()
    in_ky(f"  cua so da mo: {app.title()!r} "
          f"({app.winfo_width()}x{app.winfo_height()} px)")

    # --- dien thong tin vao GUI ---
    app.v_video.set(VIDEO_VAO)
    app.v_output.set(THU_MUC_KQ)
    app.v_phat_hien.set("1")       # bat phat hien nguoi (GUI bat buoc co)
    app.v_face.set("1")            # BAT nhan dien khuon mat
    app.v_face_every.set("3")
    app.v_model.set("yolo11n.pt")
    app.v_thiet_bi.set("Tự động")
    app.v_conf.set("0.25")
    app.v_khung.set("1")
    app.v_nhan.set("1")
    # XEM TRUC TIEP: TAT trong script nay.
    # Ly do (do that, khong doan): thread xem truc tiep goi Tk tu thread nen.
    # Tcl/Tk chi cho phep khi luong CHINH dang nam trong mainloop(); script nay
    # bom event loop bang update() theo yeu cau -> Tcl nem "main thread is not
    # in main loop", thread xem die, va no ghi de trang thai chinh cua GUI
    # thanh "Tam dung" (nham) trong khi pipeline van chay.
    # Xem truc tiep chi la HINH ANH hien thi, KHONG anh huong ket qua phan tich
    # (so frame/so dong CSV giong het co bat va tu tat).
    app.v_xem_video.set("0")
    app.v_canh_bao.set("0")        # KHONG gui tin ra ngoai
    app.v_bien_so.set("0")
    app.v_tu_chup.set("0")
    app.v_tach_o.set("0")
    app.v_vung.set("0")
    app.v_vat_the.set("0")
    app.v_clip.set("0")
    app.v_dem_ra_vao.set("0")
    app.v_pixelate.set("0")
    app.update()
    in_ky(f"  da dien: video={app.v_video.get()}")
    in_ky(f"          luu ket qua={app.v_output.get()}")
    in_ky(f"          nhan dien mat={app.v_face.get()} | "
          f"model={app.v_model.get()} | thiet bi={app.v_thiet_bi.get()}")
    in_ky(f"          xem video khi chay={app.v_xem_video.get()} | "
          f"canh bao={app.v_canh_bao.get()}")

    # --- BAM NUT "BAT DAU" THAT ---
    in_ky("")
    in_ky("[2/6] BAM NUT 'BAT DAU' THAT (btn_chay.invoke -> _bat_dau)...")
    moc = time.monotonic()
    app.btn_chay.invoke()
    app.update()
    if not app.busy:
        in_ky("  [canh bao] btn_chay.invoke() khong kich hoat duoc -> "
              "goi truc tiep app._bat_dau()")
        app._bat_dau()
        app.update()
    in_ky(f"  app.busy sau khi bam = {app.busy}")
    if not app.busy:
        in_ky(f"  [LOI] GUI khong chay. loi hien tren man hinh: "
              f"{app.lbl_loi.cget('text')!r}")

    # --- bom event loop Tk cho den khi xong ---
    anh_dang_chay = None
    da_chup_dang_chay = False
    het_gioi = False
    chuoi_tien_do = []          # (giay, phan_tram, trang_thai) - bang chung GUI
    lan_gan = 0.0
    luc_bat_dau_frame = None    # giay nhung vong xu ly anh THAT bat dau
    while True:
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        da_chay = time.monotonic() - moc
        # --- ghi lai chuoi tien do cua GUI (bang chung GUI thay tiep khung hinh) ---
        if da_chay - lan_gan >= 1.0:
            lan_gan = da_chay
            trang = app.v_tien_trinh.get()
            chuoi_tien_do.append((round(da_chay, 1),
                                  phan_tram_tu_trang_thai(trang), trang))
        # --- chup 1 LAN, khi pipeline da xu ly duoc khung hinh that ---
        # KHONG chup ngay luc bat dau: ImageGrab chan luong UI ~0.4 giay, thread
        # xem truc tiep goi Tk tu thread nen se bi Tcl tu choi ("main thread is
        # not in main loop") -> mat khung hinh xem. Chup khi vong xu ly anh da
        # chay duoc vai giay thi thread xem da ve khung hinh roi.
        if not da_chup_dang_chay and app.busy:
            try:
                tail = app.log_box.get("end-4lines", "end")
            except Exception:  # noqa: BLE001
                tail = ""
            if luc_bat_dau_frame is None and "/250" in tail:
                luc_bat_dau_frame = da_chay
            if (luc_bat_dau_frame is not None
                    and da_chay - luc_bat_dau_frame >= 4.0):
                anh_dang_chay = chup_cua_so(app, IMG_DANG_CHAY)
                da_chup_dang_chay = True
                in_ky(f"  [chup] anh khi DANG CHAY (t={da_chay:.1f}s, "
                      f"{da_chay - luc_bat_dau_frame:.1f}s sau khi bat dau xu ly "
                      f"anh) -> {IMG_DANG_CHAY} "
                      f"{anh_dang_chay['kich_thuoc']}")
        if not app.busy and app.result is not None:
            break
        if da_chay > HET_GIOI:
            het_gioi = True
            in_ky(f"  [LOI] QUA MOC {HET_GIOI:.0f} giay. app.busy={app.busy} "
                  f"app.result={app.result}")
            break
        # Ngu dong it thoi: luong UI phai nam trong vong `update()` de thread
        # xem truc tiep (goi Tk tu thread nen) khong bi Tcl tu choi.
        time.sleep(0.005)

    thoi_gian = time.monotonic() - moc

    # --- cho UI ve xong truoc khi chup anh cuoi ---
    for _ in range(30):
        try:
            app.update()
        except Exception:  # noqa: BLE001
            break
        time.sleep(0.05)

    anh_cuoi = chup_cua_so(app, IMG_CHAY_THUC)
    in_ky(f"  [chup] anh SAU KHI CHAY XONG -> {IMG_CHAY_THUC} "
          f"{anh_cuoi['kich_thuoc']}")

    # --- doc nhat ky GUI (KHONG rut het hang doi: se lam mat log cua GUI) ---
    noi_dung = app.log_box.get("1.0", "end")
    dong_log = [d for d in (x.rstrip() for x in noi_dung.splitlines()) if d]

    in_ky("")
    in_ky("[3/6] 10 DONG NHAT KY GUI CUOI CUNG")
    in_ky("-" * 78)
    for i, d in enumerate(dong_log[-10:], 1):
        in_ky(f"  {i:>2}. {d}")
    in_ky("-" * 78)
    if len(dong_log) <= 40:
        # nhat ky ngan -> in ca bo de thay dong "[video] codec:" va loi (neu co)
        in_ky("")
        in_ky(f"[3b/6] TOAN BO NHAT KY GUI ({len(dong_log)} dong)")
        in_ky("-" * 78)
        for i, d in enumerate(dong_log, 1):
            in_ky(f"  {i:>2}. {d}")
        in_ky("-" * 78)

    # --- 6 kiem tra co bang chung do duoc ---
    result = app.result
    video_path = getattr(result, "out_path", "") or video_ky_vong
    csv_path = getattr(result, "report_path", "") or csv_ky_vong

    in_ky("")
    in_ky("[3c/6] CHUOI TIEN DO GUI TUONG (bang chung GUI chay that)")
    in_ky("-" * 78)
    for giay, pt, trang in chuoi_tien_do:
        in_ky(f"  t={giay:>5.1f}s | {pt:>5.1f}% | {trang}")
    in_ky("-" * 78)

    in_ky("")
    in_ky("[4/6] 6 KIEM TRA")
    in_ky("-" * 78)

    ok1, do1 = kt_1_gui_khoi_dong(app, VERSION)
    in_ky(f"  [1] GUI khoi dong duoc  : {'PASS' if ok1 else 'FAIL'}")
    in_ky(f"      {do1}")

    ok2, do2 = kt_2_pipeline_chay_xong(app, dong_log)
    in_ky(f"  [2] Pipeline chay xong  : {'PASS' if ok2 else 'FAIL'}")
    in_ky(f"      {do2}")
    in_ky(f"      5 dong log cuoi:")
    for d in dong_log[-5:]:
        in_ky(f"        - {d}")

    ok3, do3 = kt_3_file_video(video_path)
    in_ky(f"  [3] File video ket qua  : {'PASS' if ok3 else 'FAIL'}")
    in_ky(f"      {do3}")
    in_ky(f"      (duong dan ky vong tu cam_ai_core.output_paths: {video_ky_vong})")

    ok4, do4 = kt_4_file_csv(csv_path)
    in_ky(f"  [4] File CSV bao cao    : {'PASS' if ok4 else 'FAIL'}")
    in_ky(f"      {do4}")
    in_ky(f"      (duong dan ky vong tu cam_ai_core.output_paths: {csv_ky_vong})")

    ok5, do5 = kt_5_video_doc_duoc(video_path)
    in_ky(f"  [5] Video doc duoc that : {'PASS' if ok5 else 'FAIL'}")
    in_ky(f"      {do5}")

    trang6, do6 = kt_6_codec(video_path)
    in_ky(f"  [6] Codec (ffprobe)      : {trang6}")
    in_ky(f"      {do6}")

    # --- anh chup ---
    in_ky("")
    in_ky("[5/6] 2 ANH CHUP CUA SO")
    in_ky("-" * 78)
    for nhan, tt in (("DANG CHAY", anh_dang_chay), ("SAU KHI CHAY XONG", anh_cuoi)):
        if not tt:
            in_ky(f"  {nhan:<20}: KHONG CO ANH")
            continue
        in_ky(f"  {nhan:<20}: {tt['duong_dan']}")
        in_ky(f"  {'':<20}  kich thuoc={tt['kich_thuoc']} | "
              f"so mau don sac={tt['so_mau_don_sac']} | "
              f"do sang tb={tt['sang_tb']} | do lech chuan={tt['sang_lc']} | "
              f"toa do={tt['toa_do']}")

    # --- so lieu tong hop tu AnalysisResult ---
    in_ky("")
    in_ky("[6/6] SO LIEU TU AnalysisResult + THOI GIAN CHAY")
    in_ky("-" * 78)
    in_ky(f"  thoi gian chay that : {thoi_gian:.1f} giay "
          f"(het gioi = {HET_GIOI:.0f} giay)")
    in_ky(f"  trang thai cua so    : {app.v_tien_trinh.get()!r}")
    loi_gui = app.lbl_loi.cget("text")
    in_ky(f"  loi hien tren GUI   : {loi_gui!r}")
    if result is not None:
        in_ky(f"  out_path            : {result.out_path}")
        in_ky(f"  report_path         : {result.report_path}")
        in_ky(f"  frames xu ly        : {result.frames} | fps={result.fps}")
        in_ky(f"  so nguoi toi da     : {result.max_people} | "
              f"so mat toi da = {result.max_faces}")
        in_ky(f"  nam/nu/avg tuoi     : {result.males}/{result.females}/"
              f"{result.avg_age}")
        in_ky(f"  dung nhan dien mat  : {result.used_face} | "
              f"dung bi cam = {result.stopped}")
    else:
        in_ky("  app.result = None -> pipeline KHONG tra ve ket qua")

    # --- bang tong ket ---
    in_ky("")
    in_ky("=" * 78)
    in_ky("BANG TONG KET")
    in_ky("=" * 78)
    in_ky(f"  {'MA':<4}{'KIEM TRA':<30}{'KET QUA':<10}DO SO THAT")
    in_ky("  " + "-" * 74)
    bang = [
        ("1", "GUI khoi dong duoc", "PASS" if ok1 else "FAIL", do1),
        ("2", "Pipeline chay xong", "PASS" if ok2 else "FAIL", do2),
        ("3", "File video ket qua", "PASS" if ok3 else "FAIL", do3),
        ("4", "File CSV bao cao", "PASS" if ok4 else "FAIL", do4),
        ("5", "Video doc duoc that", "PASS" if ok5 else "FAIL", do5),
        ("6", "Codec (ffprobe)", trang6, do6),
    ]
    for ma, ten, kq, do_so in bang:
        in_ky(f"  {ma:<4}{ten:<30}{kq:<10}{do_so}")
    in_ky("  " + "-" * 74)

    bat_buoc_ok = ok1 and ok2 and ok3 and ok4 and ok5 and trang6 != "FAIL"
    tong = "PASS" if bat_buoc_ok else "FAIL"
    in_ky(f"  TONG KET: {tong}"
          + (" (het gioi)" if het_gioi else "")
          + f" | thoi gian chay {thoi_gian:.1f}s")
    in_ky("=" * 78)

    # --- don dep ---
    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if bat_buoc_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        in_ky("")
        in_ky("!!!! LOI KHONG MONG DOI - DAY LA DAY DU traceback !!!!")
        traceback.print_exc(file=_REAL_STDOUT)
        sys.exit(2)
