"""Do chi phi keo cua so + dem widget. KHONG sua gi trong gui.py."""
from __future__ import annotations

import sys, time, statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import customtkinter as ctk
import gui
from gui import CamAIGui, dem_widget_hien_thi


def dem_tong(wdg):
    tong = 1
    for con in wdg.winfo_children():
        tong += dem_tong(con)
    return tong


def do_keo(app, nham=40, buoc=4):
    """Mo phong keo: doi geometry + update_idletasks (dien bien khi Windows
    gui <Configure> xuong cay widget trong luc keo)."""
    app.update()
    x, y = app.winfo_x(), app.winfo_y()
    w, h = app.winfo_width(), app.winfo_height()
    mau = []
    for i in range(nham):
        t0 = time.perf_counter()
        app.geometry(f"{w}x{h}+{x + (i % 2) * buoc}+{y + i}")
        app.update_idletasks()
        mau.append((time.perf_counter() - t0) * 1000.0)
    mau.sort()
    return {
        "n": len(mau),
        "trung_binh_ms": round(statistics.mean(mau), 2),
        "median_ms": round(statistics.median(mau), 2),
        "p90_ms": round(mau[int(len(mau) * 0.9) - 1], 2),
        "max_ms": round(mau[-1], 2),
    }


def do_pump(app, so_tick=30):
    """Do chi phi 1 tick cua _hut_hang_doi (chu ky PUMP_MS)."""
    app.update()
    mau = []
    for _ in range(so_tick):
        t0 = time.perf_counter()
        app._hut_hang_doi.__wrapped__() if hasattr(app._hut_hang_doi, "__wrapped__") else None
        app.after_cancel(app._id_dem) if hasattr(app, "_id_dem") else None
        mau.append((time.perf_counter() - t0) * 1000.0)
    return round(statistics.mean(mau), 3) if mau else 0


def main() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()

    tong = dem_tong(app)
    hien = dem_widget_hien_thi(app)
    print("=== SO LUONG ===")
    print(f"  widget TONG (ke ca an)      : {tong}")
    print(f"  widget DANG HIEN THI        : {hien}")
    print(f"  so nhom tinh nang           : {len(app.danh_sach_nhom())}")
    print(f"  cua so                      : {app.winfo_width()}x{app.winfo_height()}")

    # --- khi THU GON (trang thai mac dinh khi mo phan mem) ---
    print("\n=== KHI THU GON (mac dinh) ===")
    r1 = do_keo(app)
    print(f"  {r1}")

    # --- khi MO HET 8 nhom (truong hop nguoi dung dang cau hinh) ---
    for ten, nhom in app.danh_sach_nhom():
        nhom.dat_mo(True)
    app.update_idletasks()
    print("\n=== KHI MO HET 8 NHOM ===")
    tong2 = dem_tong(app)
    hien2 = dem_widget_hien_thi(app)
    print(f"  widget TONG : {tong2}   DANG HIEN THI : {hien2}")
    r2 = do_keo(app)
    print(f"  {r2}")

    # --- do them: 1 tick pump rong ---
    t0 = time.perf_counter()
    for _ in range(50):
        try:
            app.queue.get_nowait()
        except Exception:
            pass
    rong = (time.perf_counter() - t0) * 1000.0 / 50
    print(f"\n=== PUMP ===")
    print(f"  1 tick _hut_hang_doi khi hang doi RONG : {rong:.3f} ms")
    print(f"  chu ky PUMP_MS                          : {gui.PUMP_MS} ms")
    print(f"  => so lan tick/giay khi rong            : {1000 / gui.PUMP_MS:.1f}")

    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())