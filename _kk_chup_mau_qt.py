# -*- coding: utf-8 -*-
"""Chup anh mau giao dien Qt theo mau BAT BUOC cua du an.

attributes('-topmost', True) -> lift() -> GetAncestor(id, 2)
-> GetWindowRect -> ImageGrab.grab(bbox, all_screens=True)

Sinh 4 anh trong _kk_out\\mau_qt\\:
    mau_qt_full.png        - toan cua so
    mau_qt_cot_trai_3x.png  - phong to 3x cot trai
    mau_qt_the_so_3x.png    - phong to 3x hang 6 the so
    mau_qt_dau_3x.png       - phong to 3x khung video + thanh dau
"""

from __future__ import annotations

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
MAU_GUI = os.path.join(APP, "mau_gui_qt.py")
OUT = os.path.join(APP, "_kk_out", "mau_qt")

FULL = os.path.join(OUT, "mau_qt_full.png")
COT_TRAI = os.path.join(OUT, "mau_qt_cot_trai_3x.png")
THE_SO = os.path.join(OUT, "mau_qt_the_so_3x.png")
DAU = os.path.join(OUT, "mau_qt_dau_3x.png")

TEN_CUA_SO = "Mau giao dien Qt"


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


def cat_phong_to(anh, vung, goc, dich, xem=3):
    """Cat vung theo toa do GLOBAL roi phong to x3 bang PIL (khong dung cv2)."""
    x, y, w, h = vung
    x = int(x) - int(goc[0])
    y = int(y) - int(goc[1])
    crop = anh.crop((x, y, x + int(w), y + int(h)))
    cw, ch = crop.size
    crop = crop.resize((cw * xem, ch * xem), Image.LANCZOS)
    crop.save(dich)
    print(f"  {os.path.basename(dich)}  vung=({x},{y},{w},{h})  phong to {xem}x -> {crop.size}")
    return crop


def main():
    os.makedirs(OUT, exist_ok=True)
    duong_dan_vung = os.path.join(OUT, "_vung.json")
    if os.path.isfile(duong_dan_vung):
        os.remove(duong_dan_vung)

    print("Mo mau giao dien Qt ...")
    tien_trinh = subprocess.Popen(
        [PY, MAU_GUI, "--topmost"],
        cwd=APP,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    hwnd = None
    tieu_de = ""
    het = time.time() + 45
    while time.time() < het:
        if tien_trinh.poll() is not None:
            out = tien_trinh.stdout.read() if tien_trinh.stdout else ""
            print("APP THOAT SOM. Output:\n", out)
            return 1
        tim = tim_cua_so()
        if tim:
            hwnd, tieu_de = tim[0]
            break
        time.sleep(0.4)

    if not hwnd:
        tien_trinh.kill()
        print("KHONG tim thay cua so mau giao dien")
        return 2

    print("Cua so tim thay:", tieu_de)

    # --- mau bat buoc: topmost -> lift -> GetAncestor(id, 2) -> GetWindowRect
    try:
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
    except Exception as e:                                    # noqa: BLE001
        print("topmost loi (bo qua):", e)

    try:
        win32gui.ShowWindow(hwnd, 9)      # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:                                    # noqa: BLE001
        print("focus loi (bo qua):", e)

    time.sleep(1.6)

    goc = win32gui.GetAncestor(hwnd, 2)     # GA_ROOT - cua so cap cao
    if not goc:
        goc = hwnd
    left, top, right, bottom = win32gui.GetWindowRect(goc)
    print("GetAncestor(id, 2) =", goc, " GetWindowRect =", (left, top, right, bottom))

    bbox = (left, top, right, bottom)
    anh = ImageGrab.grab(bbox=bbox, all_screens=True)
    anh.save(FULL)
    print(f"Da luu: {FULL}  {anh.size}")

    # --- cat + phong to 3x
    if not os.path.isfile(duong_dan_vung):
        time.sleep(1.0)
    with open(duong_dan_vung, "r", encoding="utf-8") as f:
        vung = json.load(f)
    goc = (left, top)      # goc cua anh chup = goc GetWindowRect

    cat_phong_to(anh, vung["cot_trai"], goc, COT_TRAI)
    cat_phong_to(anh, vung["the_so"], goc, THE_SO)
    cat_phong_to(anh, vung["dau_video"], goc, DAU)

    print("KICH THUOC CUA SO (client):", vung.get("size_cua_so"))
    print("KICH THUOC ANH FULL:", anh.size)

    tien_trinh.terminate()
    try:
        tien_trinh.wait(timeout=5)
    except Exception:                                         # noqa: BLE001
        tien_trinh.kill()

    print("HOAN TAT")
    for p in (FULL, COT_TRAI, THE_SO, DAU):
        print("  ", p, os.path.getsize(p), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
