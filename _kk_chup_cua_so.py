r"""Chup dung CUA SO cua CamAI bang PrintWindow (khong can cua so nam tren cung).

Dung khi cac cach dua cua so len truoc bi Windows chan (foreground lock).

Cu phap:
    .venv\Scripts\python.exe _kk_chup_cua_so.py <ten_file.png>
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

SRCCOPY = 0x00CC0020
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def tim_cua_so(tieu_de_chua: str) -> int:
    """HWND cua cua so dang mo co tieu de chua `tieu_de_chua` (do doc, khong doi app)."""
    ket_qua = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        do_dai = user32.GetWindowTextLengthW(hwnd)
        if do_dai <= 0:
            return True
        dem = ctypes.create_unicode_buffer(do_dai + 1)
        user32.GetWindowTextW(hwnd, dem, do_dai + 1)
        if tieu_de_chua in dem.value:
            ket_qua.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return ket_qua[0] if ket_qua else 0


def chup(hwnd: int, duong_dan: str) -> tuple[int, int]:
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect that bai")
    rong = rect.right - rect.left
    cao = rect.bottom - rect.top
    if rong <= 0 or cao <= 0:
        raise RuntimeError(f"Kich thuoc khong hop le: {rong}x{cao}")

    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbm = gdi32.CreateCompatibleBitmap(hdc_window, rong, cao)
    gdi32.SelectObject(hdc_mem, hbm)
    try:
        ok = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
        if not ok:
            # Cu so so / phong toi: thu ve client area bang BitBlt.
            gdi32.BitBlt(hdc_mem, 0, 0, rong, cao, hdc_window, 0, 0, SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = rong
        bmi.bmiHeader.biHeight = -cao          # am -> hang tren xuong duoi
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        so_byte = rong * cao * 4
        buffer = ctypes.create_string_buffer(so_byte)
        dong = gdi32.GetDIBits(hdc_mem, hbm, 0, cao, buffer, ctypes.byref(bmi),
                               DIB_RGB_COLORS)
        if dong == 0:
            raise RuntimeError("GetDIBits tra ve 0 dong")
        anh = Image.frombuffer("RGB", (rong, cao), buffer, "raw", "BGRX", 0, 1)
        anh.save(duong_dan)
        return rong, cao
    finally:
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)


def main() -> int:
    if len(sys.argv) < 2:
        print("Thieu ten file. Dung: _kk_chup_cua_so.py <ten.png>")
        return 2
    duong_dan = sys.argv[1]
    hwnd = tim_cua_so("CamAI")
    if not hwnd:
        print("KHONG TIM THAY CUA SO CamAI")
        return 1
    rong, cao = chup(hwnd, duong_dan)
    print(f"HWND={hwnd}  {rong}x{cao}")
    print(f"Da luu {duong_dan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())