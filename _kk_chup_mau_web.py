# -*- coding: utf-8 -*-
r"""Chup anh mau giao dien webview CamAI theo mau BAT BUOC cua du an.

SetWindowPos TOPMOST -> ShowWindow(SW_RESTORE)/SetForegroundWindow
-> GetAncestor(id, 2) -> GetWindowRect -> ImageGrab.grab(bbox, all_screens=True)

Sinh trong _kk_out\mau_web\:
    mau_web_full.png            - toan cua so Qt (webview ben trong)
    mau_web_cot_trai_3x.png     - phong to 3x cot trai
    mau_web_the_so_3x.png       - phong to 3x hang 6 the so
    mau_web_dau_3x.png          - phong to 3x thanh dau + khung video
    mau_web_trinh_duyet.png     - chup trong trinh duyet (Edge headless) 1440x900
    mau_web_mobile_390.png      - cua so 390x844 (dien thoai doc)
    mau_web_mobile_820.png      - cua so 820x1180 (tablet)
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time

import win32con
import win32gui
from PIL import Image, ImageGrab

APP = r"H:\AI Project\cam-ai"
PY = os.path.join(APP, ".venv", "Scripts", "python.exe")
MAU_GUI = os.path.join(APP, "mau_gui_web.py")
HTML = os.path.join(APP, "mau_gui_web", "index.html")
OUT = os.path.join(APP, "_kk_out", "mau_web")

FULL = os.path.join(OUT, "mau_web_full.png")
COT_TRAI = os.path.join(OUT, "mau_web_cot_trai_3x.png")
THE_SO = os.path.join(OUT, "mau_web_the_so_3x.png")
DAU = os.path.join(OUT, "mau_web_dau_3x.png")
TRINH_DUYET = os.path.join(OUT, "mau_web_trinh_duyet.png")
TRINH_DUYET_1920 = os.path.join(OUT, "mau_web_trinh_duyet_1920.png")
TRINH_DUYET_390 = os.path.join(OUT, "mau_web_trinh_duyet_390.png")
MOBILE_390 = os.path.join(OUT, "mau_web_mobile_390.png")
MOBILE_820 = os.path.join(OUT, "mau_web_mobile_820.png")

TEN_CUA_SO = "CamAI - Phan tich video giam sat"

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


# ------------------------------------------------------------------ TIM CUA SO
def tim_cua_so():
    ket_qua = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = win32gui.GetWindowText(hwnd)
        if TEN_CUA_SO.lower() in t.lower():
            ket_qua.append((hwnd, t))

    win32gui.EnumWindows(callback, None)
    return ket_qua


# ------------------------------------------------------------------ CAT + ZOOM
def cat_phong_to(anh, vung, goc, dich, xem=3):
    """Cat vung theo toa do GLOBAL roi phong to x3 bang PIL (khong dung cv2)."""
    if not vung:
        print("  BO QUA (khong co toa do): %s" % os.path.basename(dich))
        return None
    x, y, w, h = vung
    x = int(x) - int(goc[0])
    y = int(y) - int(goc[1])
    crop = anh.crop((x, y, x + int(w), y + int(h)))
    cw, ch = crop.size
    crop = crop.resize((cw * xem, ch * xem), Image.LANCZOS)
    crop.save(dich)
    print("  %-28s vung=(%s,%s,%s,%s)  x%d -> %s" % (
        os.path.basename(dich), x, y, w, h, xem, crop.size))
    return crop


# ------------------------------------------------------------------ CHUP 1 CUA SO
def chay_app(args_extra, ten_dump, cho_file_dump=True, cho_giay=40):
    """Mo app, cho cua so xuat hien, tra ve (tien_trinh, hwnd)."""
    args = [PY, MAU_GUI, "--topmost", "--dump", ten_dump] + args_extra
    print("  lenh:", " ".join(args))
    tien_trinh = subprocess.Popen(
        args, cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )

    hwnd = None
    tieu_de = ""
    het = time.time() + 45
    while time.time() < het:
        if tien_trinh.poll() is not None:
            out = tien_trinh.stdout.read() if tien_trinh.stdout else ""
            print("  APP THOAT SOM. Output:\n", out)
            return None, None
        tim = tim_cua_so()
        if tim:
            hwnd, tieu_de = tim[0]
            break
        time.sleep(0.4)

    if not hwnd:
        tien_trinh.kill()
        print("  KHONG tim thay cua so mau giao dien")
        return None, None

    print("  cua so tim thay:", tieu_de)
    return tien_trinh, hwnd


def chup_cua_so(tien_trinh, hwnd, duong_dan_anh):
    """MAU BAT BUOC: topmost -> restore -> foreground -> GetAncestor(2) -> GetWindowRect."""
    try:
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
    except Exception as e:  # noqa: BLE001
        print("  topmost loi (bo qua):", e)

    try:
        win32gui.ShowWindow(hwnd, 9)      # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:  # noqa: BLE001
        print("  focus loi (bo qua):", e)

    time.sleep(1.8)

    goc = win32gui.GetAncestor(hwnd, 2)     # GA_ROOT - cua so cap cao
    if not goc:
        goc = hwnd
    left, top, right, bottom = win32gui.GetWindowRect(goc)
    print("  GetAncestor(id,2) =", goc, " GetWindowRect =", (left, top, right, bottom))

    # Dua cua so vao trong man hinh (neu no bi lech ra ngoai) de khong bi den
    kich_thuoc_man = ImageGrab.grab(all_screens=True).size
    rong = right - left
    cao = bottom - top
    if rong <= kich_thuoc_man[0] and cao <= kich_thuoc_man[1]:
        x = max(0, min(left, kich_thuoc_man[0] - rong))
        y = max(0, min(top, kich_thuoc_man[1] - cao))
        if (x, y) != (left, top):
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, x, y, 0, 0, win32con.SWP_NOSIZE)
            time.sleep(0.7)
            left, top, right, bottom = win32gui.GetWindowRect(goc)
            print("  da dua cua so vao man hinh -> GetWindowRect =",
                  (left, top, right, bottom))

    bbox = (left, top, right, bottom)
    anh = ImageGrab.grab(bbox=bbox, all_screens=True)
    anh.save(duong_dan_anh)
    print("  Da luu: %s  %s" % (duong_dan_anh, anh.size))

    # Man hinh thuc te nho hon cua so -> vung duoi bi den.
    # Giai phap: chup 2 lat (dich cua so) va noi lai thanh 1 anh dung kich thuoc.
    cao_man_hinh = ImageGrab.grab(all_screens=True).size[1]
    chieu_cao = bottom - top
    if chieu_cao > cao_man_hinh:
        print("  cua so cao hon man hinh (%d > %d) -> chup 2 lat va noi lai"
              % (chieu_cao, cao_man_hinh))
        rong = right - left

        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, left, 0, 0, 0, win32con.SWP_NOSIZE)
        time.sleep(0.9)
        lat_a = ImageGrab.grab(bbox=(left, 0, right, cao_man_hinh), all_screens=True)

        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, left, -(chieu_cao - cao_man_hinh), 0, 0,
            win32con.SWP_NOSIZE)
        time.sleep(0.9)
        lat_b = ImageGrab.grab(bbox=(left, 0, right, cao_man_hinh), all_screens=True)

        ghep = Image.new("RGB", (rong, chieu_cao))
        ghep.paste(lat_a.crop((0, 0, rong, chieu_cao - cao_man_hinh)), (0, 0))
        ghep.paste(lat_b, (0, chieu_cao - cao_man_hinh))
        ghep.save(duong_dan_anh)
        anh = ghep
        print("  Da luu (2 lat noi lai): %s  %s" % (duong_dan_anh, anh.size))

    return anh, (left, top)


def chup_trinh_duyet_dien_thoai():
    """Chup index.html o viewport 390 CSS px THAT trong trinh duyet.

    Edge/Chrome headless tren Windows co be rong cua so toi thieu (~500px) ->
    khong render duoc 390 CSS px truc tiep. Giai phap: mot trang wrapper chua
    <iframe width=390> -> media queries trong iframe tra loi dung be rong 390.
    """
    if not os.path.isfile(EDGE):
        return None

    duong_dan_url = "file:///" + HTML.replace("\\", "/").replace(" ", "%20")
    wrapper = os.path.join(OUT, "_wrapper_390.html")
    with open(wrapper, "w", encoding="utf-8") as f:
        f.write(
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<style>html,body{margin:0;padding:0;background:#16181D;overflow:hidden}'
            'iframe{width:390px;height:844px;border:0;display:block}</style>'
            '</head><body><iframe src="%s"></iframe></body></html>' % duong_dan_url
        )

    cmd = [
        EDGE,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--window-size=390,844",
        "--screenshot=" + TRINH_DUYET_390,
        "file:///" + wrapper.replace("\\", "/").replace(" ", "%20"),
    ]
    print("  lenh edge: headless=cu --window-size=390x844 (iframe 390 CSS px)")
    try:
        subprocess.run(
            cmd, cwd=APP, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90,
        )
    except Exception as e:  # noqa: BLE001
        print("  Edge that bai:", e)
        return None

    if os.path.isfile(TRINH_DUYET_390):
        img = Image.open(TRINH_DUYET_390)
        print("  Da luu: %s  %s" % (TRINH_DUYET_390, img.size))
        return TRINH_DUYET_390
    return None


def dung_app(tien_trinh):
    if tien_trinh is None:
        return
    try:
        tien_trinh.terminate()
        tien_trinh.wait(timeout=5)
    except Exception:  # noqa: BLE001
        tien_trinh.kill()


# ------------------------------------------------------------------ EDGE HEADLESS
def chup_trinh_duyet(kich_thuoc=(1440, 900), dich=None, headless="new"):
    """Chup index.html trong trinh duyet Edge headless de so sanh cung 1 bo HTML.

    Windows co be rong cua so toi thieu (~500px) o headless MOI -> khong render
    duoc viewport 390 CSS px. Headless CU co the render duoc 390x844 that.
    """
    if not os.path.isfile(EDGE):
        print("  KHONG tim thay Edge:", EDGE)
        return None

    dich = dich or TRINH_DUYET
    duong_dan_url = "file:///" + HTML.replace("\\", "/").replace(" ", "%20")
    cmd = [
        EDGE,
        "--headless" if headless == "cu" else "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--window-size=%d,%d" % (kich_thuoc[0], kich_thuoc[1]),
        "--screenshot=" + dich,
        duong_dan_url,
    ]
    print("  lenh edge: headless=%s --window-size=%dx%d" % (
        headless, kich_thuoc[0], kich_thuoc[1]))
    try:
        ket_qua = subprocess.run(
            cmd, cwd=APP, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90,
        )
    except Exception as e:  # noqa: BLE001
        print("  Edge that bai:", e)
        return None

    if os.path.isfile(dich):
        img = Image.open(dich)
        print("  Da luu: %s  %s" % (dich, img.size))
        return dich
    print("  Edge khong tao duoc anh. stderr:", (ket_qua.stderr or "")[:400])
    return None


# ------------------------------------------------------------------ MAIN
def main():
    os.makedirs(OUT, exist_ok=True)
    duong_dan_vung = os.path.join(OUT, "_vung_desktop.json")
    duong_dan_vung_m = os.path.join(OUT, "_vung_mobile_390.json")
    duong_dan_vung_t = os.path.join(OUT, "_vung_mobile_820.json")

    for duong_dan in (duong_dan_vung, duong_dan_vung_m, duong_dan_vung_t):
        if os.path.isfile(duong_dan):
            os.remove(duong_dan)

    # ---------------------------------------------------------- 1) DESKTOP
    print("\n=== 1/4 CUa so desktop 1440x900 ===")
    tien_trinh, hwnd = chay_app(
        ["--size", "1440x900", "--min-size", "1200x760"], duong_dan_vung)
    if tien_trinh is None:
        return 1

    # cho app ghi file vung xong
    het = time.time() + 20
    while time.time() < het and not os.path.isfile(duong_dan_vung):
        time.sleep(0.3)
    time.sleep(0.6)

    anh, goc = chup_cua_so(tien_trinh, hwnd, FULL)

    if os.path.isfile(duong_dan_vung):
        with open(duong_dan_vung, "r", encoding="utf-8") as f:
            vung = json.load(f)
        print("  KICH THUOC CUA SO (client):", vung.get("size_cua_so"))
        print("  VIEWPORT HTML:", vung.get("inner_width"), "x", vung.get("inner_height"))
        print("  DO RONG:", json.dumps(vung.get("do_rong"), ensure_ascii=False))
        cat_phong_to(anh, vung.get("cot_trai"), goc, COT_TRAI)
        cat_phong_to(anh, vung.get("the_so"), goc, THE_SO)
        cat_phong_to(anh, vung.get("dau_video"), goc, DAU)
    else:
        print("  KHONG co file vung:", duong_dan_vung)

    dung_app(tien_trinh)
    time.sleep(1.0)

    # ---------------------------------------------------------- 2) TRINH DUYET
    print("\n=== 2/5 Trinh duyet (Edge headless) ===")
    chup_trinh_duyet((1440, 900), TRINH_DUYET)
    chup_trinh_duyet((1920, 1080), TRINH_DUYET_1920)
    chup_trinh_duyet_dien_thoai()

    # ---------------------------------------------------------- 3) DIEN THOAI 390
    print("\n=== 3/4 Dien thoai 390x844 ===")
    tien_trinh, hwnd = chay_app(
        ["--size", "390x844", "--min-size", "360x600"], duong_dan_vung_m)
    if tien_trinh is not None:
        het = time.time() + 20
        while time.time() < het and not os.path.isfile(duong_dan_vung_m):
            time.sleep(0.3)
        time.sleep(0.6)
        chup_cua_so(tien_trinh, hwnd, MOBILE_390)
        if os.path.isfile(duong_dan_vung_m):
            with open(duong_dan_vung_m, "r", encoding="utf-8") as f:
                vm = json.load(f)
            print("  VIEWPORT HTML:", vm.get("inner_width"), "x", vm.get("inner_height"))
            print("  DO RONG:", json.dumps(vm.get("do_rong"), ensure_ascii=False))
        dung_app(tien_trinh)
    time.sleep(1.0)

    # ---------------------------------------------------------- 4) TABLET 820
    print("\n=== 4/4 Tablet 820x1180 ===")
    tien_trinh, hwnd = chay_app(
        ["--size", "820x1180", "--min-size", "600x700"], duong_dan_vung_t)
    if tien_trinh is not None:
        het = time.time() + 20
        while time.time() < het and not os.path.isfile(duong_dan_vung_t):
            time.sleep(0.3)
        time.sleep(0.6)
        chup_cua_so(tien_trinh, hwnd, MOBILE_820)
        if os.path.isfile(duong_dan_vung_t):
            with open(duong_dan_vung_t, "r", encoding="utf-8") as f:
                vt = json.load(f)
            print("  VIEWPORT HTML:", vt.get("inner_width"), "x", vt.get("inner_height"))
            print("  DO RONG:", json.dumps(vt.get("do_rong"), ensure_ascii=False))
        dung_app(tien_trinh)

    print("\nHOAN TAT")
    for p in (FULL, COT_TRAI, THE_SO, DAU, TRINH_DUYET, MOBILE_390, MOBILE_820):
        if os.path.isfile(p):
            print("   %-52s %8d bytes" % (p, os.path.getsize(p)))
        else:
            print("   %-52s THIEU" % p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
