# -*- coding: utf-8 -*-
"""Coordinator: chup TOAN BO cua so GUI de TOI MAT kiem 2 nhom moi v3.0.

Chup bang HWND that (GetAncestor -> GetWindowRect -> ImageGrab all_screens)
de khong chup nham cua so khac.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_chup_gui_v3_0_full.py
"""
from __future__ import annotations

import ctypes
import os
import sys
import time

import customtkinter as ctk
from PIL import ImageGrab

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from gui import CamAIGui  # noqa: E402

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(APP_DIR, "_kk_out")
u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def rect_cua_so(app):
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(app.winfo_id()), 2)
    u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    return rc


def chup(app, ten):
    rc = rect_cua_so(app)
    img = ImageGrab.grab(bbox=(rc.left, rc.top, rc.right, rc.bottom),
                         all_screens=True)
    duong = os.path.join(OUT, f"{ten}.png")
    img.save(duong)
    print(f"  [chup] {ten}: {img.size} -> {duong}", flush=True)


def tim_scroll(app):
    w = app.nhom_phat_hien
    while w is not None and not hasattr(w, "_parent_canvas"):
        w = w.master
    return w


def cuon_den(app, widget, viet=0.05):
    canvas = tim_scroll(app)._parent_canvas
    for _ in range(14):
        app.update_idletasks()
        cao = canvas.winfo_height()
        lech = (widget.winfo_rooty() - canvas.winfo_rooty()) - viet * cao
        if abs(lech) < 10:
            break
        bbox = canvas.bbox("all")
        total = (bbox[3] if bbox else cao)
        f = canvas.yview()[0]
        canvas.yview_moveto(max(0.0, min(1.0, f + lech / max(1, total - cao))))
        app.update()
        app.update_idletasks()
        time.sleep(0.15)
    app.update()
    time.sleep(0.3)
    app.update()


def chay():
    os.makedirs(OUT, exist_ok=True)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.8)
    app.update()
    app.attributes("-topmost", True)
    app.lift()

    def buoc_0():
        app.nhom_bien_so.dat_mo(True)
        app.after(900, buoc_1)

    def buoc_1():
        cuon_den(app, app.nhom_bien_so.chk, viet=0.06)
        app.after(400, buoc_2)

    def buoc_2():
        app.update()
        time.sleep(0.4)
        app.update()
        chup(app, "v3_40_gui_nhom_bien_so")
        app.after(300, buoc_3)

    def buoc_3():
        app.nhom_tu_chup.dat_mo(True)
        app.after(900, buoc_4)

    def buoc_4():
        cuon_den(app, app.nhom_tu_chup.chk, viet=0.06)
        app.after(400, buoc_5)

    def buoc_5():
        app.update()
        time.sleep(0.4)
        app.update()
        chup(app, "v3_41_gui_nhom_tu_chup")
        app.after(300, buoc_6)

    def buoc_6():
        app.destroy()

    app.after(1000, buoc_0)
    app.mainloop()


if __name__ == "__main__":
    chay()
