#!/usr/bin/env python
# Bam nut "BAT DAU" trong cua so CamAI roi chup lai.
# Vong trong: tim cua so -> dua len truoc -> SetCursorPos + mouse_event.
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

ct = ctypes
u32 = ct.windll.user32
u32.SetProcessDPIAware()

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_kiem_chung")
os.makedirs(OUT_DIR, exist_ok=True)

# Ty le toa do nut BAT DAU trong cua so (do bang mat, tu anh chup That)
TY_LE_X = 0.077
TY_LE_Y = 0.703


class RECT(ctypes.Structure):
    _fields_ = [("left", ct.c_long), ("top", ct.c_long),
                ("right", ct.c_long), ("bottom", ct.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ct.c_long), ("y", ct.c_long)]


def tim_cua_so(tu_khoa):
    ket_qua = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def dong(h, p):
        if not u32.IsWindowVisible(h):
            return True
        n = u32.GetWindowTextLengthW(h)
        if n <= 0:
            return True
        buf = ct.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(h, buf, n + 1)
        if tu_khoa.lower() in buf.value.lower():
            ket_qua.append((h, buf.value))
        return True

    u32.EnumWindows(dong, 0)
    return ket_qua


def click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.2)
    u32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
    time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP


def main():
    ds = tim_cua_so("camai v")
    if not ds:
        print("KHONG_TIM_THAY_CUA_SO")
        return
    hwnd, ten = ds[0]
    u32.ShowWindow(hwnd, 9)          # SW_RESTORE
    u32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

    r = RECT()
    u32.GetWindowRect(hwnd, ct.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    print("Cua so: x={} y={} rong={} cao={}".format(r.left, r.top, w, h))

    cx = r.left + int(w * TY_LE_X)
    cy = r.top + int(h * TY_LE_Y)
    print("Bam tai {}, {}".format(cx, cy))
    click(cx, cy)

    # Cho video chay toi khung co nguoi quen roi chup
    time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 14)

    from PIL import ImageGrab
    ten_anh = sys.argv[2] if len(sys.argv) > 2 else "v24_ui_dang_chay.png"
    duong_dan = os.path.join(OUT_DIR, ten_anh)
    ImageGrab.grab(all_screens=True).save(duong_dan)
    print("Da luu " + duong_dan)


if __name__ == "__main__":
    main()