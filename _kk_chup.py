#!/usr/bin/env python
# Chup anh cua so theo tieu de, luu vao _kiem_chung.
import ctypes
import os
import sys

import ctypes.wintypes as wt

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_kiem_chung")
os.makedirs(OUT_DIR, exist_ok=True)

u32 = ctypes.windll.user32
u32.SetProcessDPIAware()

title_khong = sys.argv[1] if len(sys.argv) > 1 else "CamAI"
ten_file = sys.argv[2] if len(sys.argv) > 2 else "gui_chup.png"


def tim_cua_so(tu_khoa):
    ket_qua = []
    dem = u32.GetDesktopWindow()

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def dong(u, p):
        if not u32.IsWindowVisible(u):
            return True
        n = u32.GetWindowTextLengthW(u)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(u, buf, n + 1)
        if tu_khoa.lower() in buf.value.lower():
            ket_qua.append((u, buf.value))
        return True

    u32.EnumWindows(dong, 0)
    return ket_qua


def vung_cua_so(hwnd):
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def chup(hwnd, duong_dan):
    import numpy as np
    from PIL import ImageGrab

    x, y, w, h = vung_cua_so(hwnd)
    if w <= 0 or h <= 0:
        raise SystemExit("Cua so co kich thuoc khong hop le")
    u32.SetForegroundWindow(hwnd)
    import time

    time.sleep(1.2)
    anh = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    anh.save(duong_dan)
    print("Da luu {}  ({}x{})".format(duong_dan, anh.width, anh.height))


danh_sach = tim_cua_so(title_khong)
if not danh_sach:
    raise SystemExit("Khong tim thay cua so chua '{}'".format(title_khong))
for hwnd, ten in danh_sach:
    print("Tim thay: {} @ {}".format(ten, hwnd))

hwnd = danh_sach[-1][0]
chup(hwnd, os.path.join(OUT_DIR, ten_file))