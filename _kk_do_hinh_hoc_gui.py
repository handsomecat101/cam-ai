"""Do hinh hoc that cua khung ben trai: nhom 'Chay bang gi' co
nam ngoai vung nhin duoc khong?"""

import traceback

import customtkinter as ctk
from gui import CamAIGui


def main() -> int:
    app = CamAIGui()
    app.geometry("1610x980+0+0")
    app.update()

    # tim khong chua cac nhom
    khung = None
    for ten_attr in dir(app):
        if ten_attr.startswith("nhom_"):
            doi = getattr(app, ten_attr)
            if isinstance(doi, ctk.CTkFrame):
                khung = doi.master
                break

    print("=== KHUNG CHUA NHOM ===")
    print(f"  {type(khung).__name__}  {khung.winfo_width()}x{khung.winfo_height()}"
          f"  y={khung.winfo_rooty()}")

    # dong het, do chi cao moi nhom
    danh_sach = [(t, getattr(app, t)) for t in dir(app)
                 if t.startswith("nhom_") and hasattr(getattr(app, t), "dat_mo")]
    for _, n in danh_sach:
        n.dat_mo(False)
    app.update_idletasks()

    tong = 0
    for ten, n in danh_sach:
        h = n.winfo_height()
        tong += h
        print(f"  {ten:22s} y={n.winfo_rooty():<6} h={h}")
    print(f"  TONG chieu cao 10 nhom khi thu gon = {tong} px")
    print(f"  Chieu cao khung chua = {khung.winfo_height()} px")
    print(f"  => {'VUA khop' if tong <= khung.winfo_height() else 'TRAN doan chua noi dung'}")

    # mo nhom thiet bi, do phan bi cat
    app.nhom_thiet_bi.dat_mo(True)
    app.update_idletasks()

    nut = app.nhom_thiet_bi.nut_tieu_de
    y_nut = nut.winfo_rooty()
    print("\n=== KHI MO NHOM 'MAY NAY CHAY BANG GI' ===")
    print(f"  nut tieu de : y={y_nut}  h={nut.winfo_height()}")
    print(f"  kiem noi cua khung noi = {y_nut + khung.winfo_height()}")

    # tim widget con dau tien co text de xac nhan dropdown bi cat
    k = app.nhom_thiet_bi.khung
    print(f"  khung noi: y={k.winfo_rooty()} h={k.winfo_height()}")
    for tre in k.winfo_children():
        try:
            y = tre.winfo_rooty()
            h = tre.winfo_height()
        except Exception:
            continue
        vi_tri = "TRONG man hinh" if y + h <= y_nut + khung.winfo_height() else ">>> BI CAT <<<"
        print(f"    - {type(tre).__name__:<18} y={y:<6} h={h:<5} {vi_tri}")
        for chau in tre.winfo_children():
            try:
                y2 = chau.winfo_rooty()
                h2 = chau.winfo_height()
            except Exception:
                continue
            v2 = "TRONG" if y2 + h2 <= y_nut + khung.winfo_height() else ">>> BI CAT <<<"
            print(f"        . {type(chau).__name__:<16} y={y2:<6} h={h2:<5} "
                  f"text={getattr(chau, 'text', '')!r} {v2}")

    app.destroy()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)