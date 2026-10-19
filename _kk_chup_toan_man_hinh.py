#!/usr/bin/env python
# Chup TOAN man hinh de xac dinh vi tri that cua cua so.
import os
import sys

import ctypes
import ctypes.wintypes as wt

ct = ctypes
u32 = ctypes.windll.user32
u32.SetProcessDPIAware()

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_kiem_chung")
os.makedirs(OUT_DIR, exist_ok=True)
ten = sys.argv[1] if len(sys.argv) > 1 else "man_hinh_day_du.png"


class RECT(ctypes.Structure):
    _fields_ = [("left", ct.c_long), ("top", ct.c_long),
                ("right", ct.c_long), ("bottom", ct.c_long)]


def tim_cua_so(tu_khoa):
    ket_qua = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def dong(u, p):
        if not u32.IsWindowVisible(u):
            return True
        n = u32.GetWindowTextLengthW(u)
        if n <= 0:
            return True
        buf = ct.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(u, buf, n + 1)
        if tu_khoa.lower() in buf.value.lower():
            ket_qua.append((u, buf.value))
        return True

    u32.EnumWindows(dong, 0)
    return ket_qua


wa = RECT()
u32.SystemParametersInfoW(0x0030, 0, ct.byref(wa), 0)
print("Vung lam viec: x={} y={} rong={} cao={}".format(
    wa.left, wa.top, wa.right - wa.left, wa.bottom - wa.top))

for hwnd, ten_cua in tim_cua_so("camai"):
    r = RECT()
    u32.GetWindowRect(hwnd, ct.byref(r))
    print("Cua so '{}': x={} y={} rong={} cao={} | duoi_vung_lam_viec={}".format(
        ten_cua, r.left, r.top, r.right - r.left, r.bottom - r.top,
        r.bottom > wa.bottom))

from PIL import ImageGrab

anh = ImageGrab.grab(all_screens=True)
duong_dan = os.path.join(OUT_DIR, ten)
anh.save(duong_dan)
print("Da luu {} ({}x{})".format(duong_dan, anh.width, anh.height))