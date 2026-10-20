# -*- coding: utf-8 -*-
r"""
CamAI - CHUNG MINH TOOLTIP VAN HOAT DONG SAU KHI SUA GIA KHI KEO CUA SO.

Kiem tra 4 dieu:
  [1] `_vao()` KHONG hien ngay - phai doi 450 ms (do tre Windows).
  [2] Sau 700 ms: cua so tooltip DANG HIEN (state != withdrawn, mapped).
  [3] `_ra()`: cua so tooltip AN (khong bi destroy) - van dung lai duoc.
  [4] `_vao()` lan 2: tooltip HIEN LAI bang DUNG CUA SO cu (tai su dung).

Chay:
    .venv\Scripts\python.exe -W ignore _kk_kiem_tooltip_giat.py
"""

from __future__ import annotations

import ctypes
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

THU_MUC = os.path.join(APP_DIR, "_kk_out", "agent_fix_giat")
os.makedirs(THU_MUC, exist_ok=True)

u32 = ctypes.windll.user32


def bom(app, giay=0.0) -> None:
    """Pum (chay) vong su kien cua Tk trong `giay` giay."""
    cuoi = time.perf_counter() + giay
    while True:
        app.update()
        if time.perf_counter() >= cuoi:
            return
        time.sleep(0.01)


def trang_thai(hd) -> str:
    if hd.cua_so is None:
        return "CHUA TAO CUA SO"
    try:
        st = hd.cua_so.state()
    except Exception:  # noqa: BLE001
        return "LOI KHI DOC state()"
    try:
        mapped = bool(hd.cua_so.winfo_ismapped())
    except Exception:  # noqa: BLE001
        mapped = False
    return f"state={st} mapped={mapped}"


def hien(hd) -> bool:
    if hd.cua_so is None:
        return False
    try:
        if hd.cua_so.state() == "withdrawn":
            return False
        return bool(hd.cua_so.winfo_ismapped())
    except Exception:  # noqa: BLE001
        return False


def chay() -> int:
    import customtkinter as ctk

    from gui import CamAIGui, HuongDan

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.geometry("1400x900+60+60")
    app.update()
    app.update_idletasks()
    time.sleep(1.0)
    app.update()

    print("=" * 74)
    print("KIEM TRA TOOLTIP SAU KHI SUA GIA KHI KEO CUA SO")
    print("=" * 74)
    print(f"  so HuongDan da tao = {len(HuongDan._danh_sach)}")
    if not HuongDan._danh_sach:
        print("  FAIL: khong tim thay tooltip nao trong app")
        return 1

    # Chon 1 tooltip co noi dung khong rong (de tooltip that su hien).
    hd = None
    for h in HuongDan._danh_sach:
        if h._noi_dung_hien_tai():
            hd = h
            break
    if hd is None:
        print("  FAIL: moi tooltip deu rong noi dung")
        return 1

    print(f"  tooltip mau: noi dung = {hd._noi_dung_hien_tai()!r}")
    print(f"  nhan = {type(hd.widget).__name__}  "
          f"THOI_GIAN_HIEN = {HuongDan.THOI_GIAN_HIEN} ms")

    # --- dua con tro chuot vao o de tooltip hien dung choi (anh chup dep) ---
    try:
        x = hd.dich.winfo_rootx() + 20
        y = hd.dich.winfo_rooty() + 10
        u32.SetCursorPos(int(x), int(y))
        app.update()
    except Exception:  # noqa: BLE001
        pass

    ok = []
    # ------------------------------------------------------------ [1] tre
    hd._vao()
    app.update()
    s0 = trang_thai(hd)
    print(f"\n  [1] ngay sau _vao(): {s0}")
    ok.append(("hien ngay", hien(hd) is False, s0))

    # [1b] sau 250 ms van chua hien
    bom(app, 0.25)
    s250 = trang_thai(hd)
    print(f"  [1b] sau 250 ms: {s250}")
    ok.append(("tre 450 ms", hien(hd) is False, s250))

    # ------------------------------------------------------------ [2] hien
    bom(app, 0.55)
    s700 = trang_thai(hd)
    print(f"  [2] sau 700 ms: {s700}")
    ok.append(("hien sau 450 ms", hien(hd) is True, s700))
    cua_so_1 = hd.cua_so
    chieu_rong = cua_so_1.winfo_reqwidth() if cua_so_1 is not None else 0

    # ------------------------------------------------------------ [3] an
    hd._ra()
    bom(app, 0.15)
    s_an = trang_thai(hd)
    con_song = False
    try:
        con_song = bool(cua_so_1.winfo_exists())
    except Exception:  # noqa: BLE001
        con_song = False
    print(f"  [3] sau _ra(): {s_an} | cua so con ton tai = {con_song} "
          f"| da bi destroy = {not con_song}")
    ok.append(("an khong destroy", (hien(hd) is False) and con_song, s_an))

    # ------------------------------------------------------------ [4] dung lai
    hd._vao()
    bom(app, 0.75)
    s_lai = trang_thai(hd)
    cung_cua_so = (hd.cua_so is cua_so_1)
    print(f"  [4] _vao() lan 2 sau 750 ms: {s_lai} | "
          f"dung cua so cu = {cung_cua_so}")
    ok.append(("hien lai bang cua so cu", (hien(hd) is True) and cung_cua_so,
               s_lai))

    # ------------------------------------------------------------ chup anh
    duong_dan = os.path.join(THU_MUC, "tooltip.png")
    duong_dan_hwnd = os.path.join(THU_MUC, "tooltip_cua_so.png")
    ok_chup = False
    if hd.cua_so is not None:
        try:
            from PIL import ImageGrab

            x = hd.cua_so.winfo_rootx()
            y = hd.cua_so.winfo_rooty()
            w = hd.cua_so.winfo_width()
            h = hd.cua_so.winfo_height()
            if w <= 1:
                w = chieu_rong
            if h <= 1:
                h = hd.cua_so.winfo_reqheight()
            bien = 40
            bbox = (max(0, x - bien), max(0, y - bien),
                    x + w + bien, y + h + bien)
            anh = ImageGrab.grab(bbox=bbox)
            anh.save(duong_dan)
            ok_chup = True
            print(f"\n  [CHUP] anh man hinh (vung tooltip): {duong_dan} "
                  f"{anh.size}")
        except Exception as e:  # noqa: BLE001
            print(f"\n  [CHUP] ImageGrab that bai: {e}")

        try:
            import _kk_chup_cua_so

            hwnd = u32.GetAncestor(ctypes.c_void_p(int(hd.cua_so.winfo_id())), 2)
            kq = _kk_chup_cua_so.chup(hwnd, duong_dan_hwnd)
            print(f"  [CHUP] anh cua so tooltip: {duong_dan_hwnd} {kq}")
        except Exception as e:  # noqa: BLE001
            print(f"  [CHUP] PrintWindow that bai: {e}")

    # ------------------------------------------------------------ don dep
    try:
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    con_mo_coi = 0
    for h in HuongDan._danh_sach:
        if h.cua_so is not None:
            try:
                if h.cua_so.winfo_exists():
                    con_mo_coi += 1
            except Exception:  # noqa: BLE001
                pass
    print(f"  [DONG APP] so cua so tooltip con mo coi = {con_mo_coi}")
    ok.append(("dong app khong de cua so mo coi", con_mo_coi == 0,
               f"con_mo_coi={con_mo_coi}"))

    # ------------------------------------------------------------ ket qua
    print("-" * 74)
    all_ok = True
    for ten, trong, chi_tiet in ok:
        all_ok = all_ok and trong
        print(f"  [{'PASS' if trong else 'FAIL'}] {ten}  ({chi_tiet})")
    if ok_chup:
        print(f"  [PASS] da chup anh tooltip")
    else:
        all_ok = False
        print("  [FAIL] khong chup duoc anh tooltip")
    print("=" * 74)
    print(f"  KET QUA: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        sys.exit(2)
