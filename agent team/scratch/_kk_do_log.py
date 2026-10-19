"""Phan tich chi tiet: dong nao trong _ghi_log / _hut_hang_doi gay tre."""
from __future__ import annotations

import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import customtkinter as ctk

from gui import CamAIGui


def nap(app, n):
    for i in range(n):
        app.queue.put(("log", f"  frame {i}/2500 | Nguoi: 3 | Mat: 1 | Vao: 2 | Ra: 1"))


def main() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()

    print("=== 1. Tung 1 dong log le (do tung lenh) ===")
    for lan in range(3):
        nap(app, 1)
        t0 = time.perf_counter()
        app._hut_hang_doi()
        print(f"  tick {lan+1} (1 dong log)      : {(time.perf_counter()-t0)*1000:.3f} ms")

    print("\n=== 2. Tung N dong log, do tung tick ===")
    for n in (50, 300, 1000):
        mau = []
        for lan in range(4):
            nap(app, n)
            t0 = time.perf_counter()
            app._hut_hang_doi()
            mau.append(round((time.perf_counter() - t0) * 1000, 2))
        print(f"  {n:>5} dong -> tung tick: {mau}")

    print("\n=== 3. Do tung lenh trong _ghi_log (n = 300 dong) ===")
    nap(app, 300)
    hang_doi = list(app.queue.queue)
    app.queue.queue.clear()
    tong = 0.0
    for _k, _p in hang_doi:
        text = app.dich(_p)
        t0 = time.perf_counter()
        app.log_box.configure(state="normal")
        app.log_box.insert("end", text + "\n")
        t1 = time.perf_counter()
        app.log_lines += 1
        if app.log_lines > 200:
            drop = app.log_lines // 2
            app.log_box.delete("1.0", f"{drop}.0")
            app.log_lines -= drop
        t2 = time.perf_counter()
        app.log_box.see("end")
        t3 = time.perf_counter()
        app.log_box.configure(state="disabled")
        t4 = time.perf_counter()
        tong += (t4 - t0) * 1000
    print(f"  tong 300 dong        : {tong:.1f} ms")
    print(f"    configure(state)   : {(t1-t0)*300*1000:.1f} ms")
    print(f"    insert             : {(t2-t1)*300*1000:.1f} ms")
    print(f"    delete (dong>200)  : {(t3-t2)*300*1000:.1f} ms")
    print(f"    see('end')         : {(t4-t3)*300*1000:.1f} ms")

    print("\n=== 4. update_idletasks sau khi chen log ===")
    t0 = time.perf_counter()
    app.update_idletasks()
    print(f"  update_idletasks 1 lan : {(time.perf_counter()-t0)*1000:.2f} ms")
    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())