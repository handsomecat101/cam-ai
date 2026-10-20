# -*- coding: utf-8 -*-
"""Chup man hinh cua so CamAI theo mau bat buoc cua du an.

attributes('-topmost', True) -> lift() -> GetAncestor(id, 2)
-> GetWindowRect -> ImageGrab.grab(bbox, all_screens=True)
"""
import os
import sys
import time

import win32con
import win32gui
from PIL import ImageGrab

TEN = "CamAI"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"H:\AI Project\cam-ai\_kk_out\app_dang_mo.png"


def tim_cua_so():
    ket_qua = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = win32gui.GetWindowText(hwnd)
        if TEN.lower() in t.lower():
            ket_qua.append((hwnd, t))
    win32gui.EnumWindows(callback, None)
    return ket_qua


found = tim_cua_so()
print("Cua so tim thay:", found)
if not found:
    sys.exit("KHONG tim thay cua so CamAI")

hwnd, tieu_de = found[0]
print("Chon:", tieu_de)

try:
    # HWND_TOPMOST: cua so luon tren cac cua so khac khi chup.
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
    )
except Exception as e:  # noqa: BLE001
    print("topmost loi (bo qua):", e)

try:
    win32gui.ShowWindow(hwnd, 9)   # SW_RESTORE
    win32gui.SetForegroundWindow(hwnd)
except Exception as e:  # noqa: BLE001
    print("focus loi (bo qua):", e)

time.sleep(1.0)

left, top, right, bottom = win32gui.GetWindowRect(hwnd)
print("GetWindowRect =", (left, top, right, bottom))
bbox = (left, top, right, bottom)
anh = ImageGrab.grab(bbox=bbox, all_screens=True)
anh.save(OUT)
print("Da luu:", OUT, anh.size)
