# -*- coding: utf-8 -*-
"""
CamAI - CHUNG MINH KHONG MAT TINH NANG sau khi bo cuc lai COT TRAI.

Cach dung:
  1) CHAY TRUOC KHI SUA (luu anh chup cua cau truc):
        .venv\\Scripts\\python.exe -W ignore _kk_kiem_khong_mat_tinh_nang.py --luu _kk_out\\truoc.json
  2) SUA `gui.py`
  3) CHAY LAI:
        .venv\\Scripts\\python.exe -W ignore _kk_kiem_khong_mat_tinh_nang.py --luu _kk_out\\sau.json
  4) SO SANH:
        .venv\\Scripts\\python.exe -W ignore _kk_kiem_khong_mat_tinh_nang.py --so _kk_out\\truoc.json _kk_out\\sau.json

Script thu thap:
  * MOI CHECKBOX: chu hien thi + ten bien (StringVar) + gia tri mac dinh
  * MOI NUT:      chu hien thi + lenh (ham) duoc gan
  * MOI NHOM TINH NANG (12 nhom con): ten hien thi + bien
  * MOI THE VIDEO MAU: ten + mo ta (bam vao de chon video)

Ket luan PASS/FAIL: 3 danh sach phai GIONG HET (thu tu duoc phep khac).
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_REAL_STDOUT = sys.stdout
try:
    _REAL_STDOUT.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def in_ky(*args) -> None:
    print(*args, file=_REAL_STDOUT, flush=True)


# ------------------------------------------------------------------ thu thap

def duyet(widget, ket=None):
    """Duyet TOAN BO cay widget (goi de quet cac frame CTk)."""
    if ket is None:
        ket = []
    ket.append(widget)
    for con in widget.winfo_children():
        duyet(con, ket)
    return ket


def ten_lenh(cmd) -> str:
    """Ten ham duoc gan cho nut (de so sanh doc lap cau truc)."""
    if cmd is None:
        return ""
    if isinstance(cmd, str):
        return "str:" + cmd
    return getattr(cmd, "__qualname__", None) or getattr(cmd, "__name__", None) \
        or type(cmd).__name__


def ban_do_bien(app) -> dict:
    """Bien tkinter -> ten thuoc tinh cua app (vd 'v_phat_hien').

    Dung de dinh danh 1 checkbox CHAC CHAN la bien nao, khong phu thuoc vao
    thu tu khai bao bien (PY_VAR0, PY_VAR1...).
    """
    out = {}
    for ten, gt in list(vars(app).items()):
        if hasattr(gt, "get") and hasattr(gt, "set") and hasattr(gt, "_name"):
            out[id(gt)] = ten
    return out


def thu_thap(app) -> dict:
    import customtkinter as ctk

    ban_bien = ban_do_bien(app)

    def khoa_bien(var) -> str:
        if var is None:
            return ""
        ten = ban_bien.get(id(var))
        if ten:
            return ten
        return "tk:" + str(var)

    def gia_tri(var) -> str:
        if var is None:
            return ""
        try:
            return str(var.get())
        except Exception:  # noqa: BLE001
            return ""

    checkboxes = []
    buttons = []
    chevrons = []
    the_video = []
    for w in duyet(app):
        if isinstance(w, ctk.CTkCheckBox):
            try:
                text = str(w.cget("text"))
            except Exception:  # noqa: BLE001
                text = ""
            var = getattr(w, "_variable", None)
            checkboxes.append({
                "text": text,
                "bien": khoa_bien(var),
                "gia_tri": gia_tri(var),
            })
        elif isinstance(w, ctk.CTkButton):
            try:
                text = str(w.cget("text"))
            except Exception:  # noqa: BLE001
                text = ""
            cmd = getattr(w, "_command", None)
            lenh = ten_lenh(cmd)
            if lenh.endswith("_doi_trang_thai"):
                # Nut MUI TEN bat / dong (cau truc) - tach rieng de khong
                # goi vao "mat tinh nang". Chuoi ky tu se doi theo trang thai
                # mo / dong nen chi ghi lai LOAI CHEVRON.
                chevrons.append({
                    "chu_roi": lenh.split(".")[0],
                    "la_chevron": text in ("\ue76c", "\ue70d", "\ue70e"),
                })
            else:
                buttons.append({"text": text, "lenh": lenh})
        elif type(w).__name__ == "TheVideoMau":
            ten = getattr(w, "_ten", "")
            mo_ta = getattr(w, "_mo_ta", "")
            the_video.append({"ten": ten, "mo_ta": mo_ta,
                              "co_lenh": getattr(w, "_command", None) is not None})

    # 12 nhom tinh nang con (ten hien thi + bien) - giu qua `danh_sach_nhom`.
    nhom = []
    try:
        for ten_hien, nhom_obj in app.danh_sach_nhom():
            var = getattr(nhom_obj, "var", None)
            nhom.append({"text": ten_hien, "bien": khoa_bien(var),
                         "gia_tri": gia_tri(var)})
    except Exception:  # noqa: BLE001
        pass

    return {"checkboxes": checkboxes, "buttons": buttons,
            "chevrons": chevrons, "nhom": nhom, "the_video_mau": the_video}


# ------------------------------------------------------------------ so sanh

# v3.6: 3 NUT CHON NGUON moi (anh / camera / danh sach camera).
# Day la TINH NANG MOI (khong mat gi) - danh sach khoa "lenh" cua nut.
NUT_MOI_CHO_PHEP = {
    "CamAIGui._chon_anh",
    "CamAIGui._chon_camera",
    "CamAIGui._xem_danh_sach_camera",
}

# v3.6: doi CHU HIEN THI cua 1 nut (ket qua co the la video HOAC anh).
# lenh -> (chu cu, chu moi)
NHAN_DOI_CHO_PHEP = {
    "CamAIGui._mo_video_ket_qua": ("Mở video kết quả", "Mở kết quả"),
}


def khoa_dong(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def chuan_hoa_nhom(ds: list) -> list:
    """`tk:PY_VAR51` -> `tk:auto` (so bien tao truc tiep khong phu thuoc thu tu)."""
    out = []
    for x in ds:
        x = dict(x)
        if str(x.get("bien", "")).startswith("tk:PY_VAR"):
            x["bien"] = "tk:auto"
        out.append(x)
    return sorted(out, key=khoa_dong)


def so_sanh(a: dict, b: dict) -> tuple[bool, list[str]]:
    dong = []
    ok = True
    for khoa, nhan in (("checkboxes", "CHECKBOX"),
                       ("nhom", "NHOM TINH NANG"),
                       ("the_video_mau", "THE VIDEO MAU")):
        ds_a = sorted(a.get(khoa, []), key=khoa_dong)
        ds_b = sorted(b.get(khoa, []), key=khoa_dong)
        if khoa == "nhom":
            ds_a, ds_b = chuan_hoa_nhom(ds_a), chuan_hoa_nhom(ds_b)
        if ds_a == ds_b:
            dong.append(f"  [{'OK  '}] {nhan:20s} {len(ds_a):3d} muc - GIONG HET")
        else:
            ok = False
            only_a = [x for x in ds_a if x not in ds_b]
            only_b = [x for x in ds_b if x not in ds_a]
            dong.append(f"  [SAI ] {nhan:20s} truoc {len(ds_a)} / sau {len(ds_b)}"
                        f" - THIEU {len(only_a)} / THUA {len(only_b)}")
            for x in only_a[:20]:
                dong.append(f"          - chi co TRUOC: {x}")
            for x in only_b[:20]:
                dong.append(f"          - chi co SAU : {x}")

    # --- NUT (chuc nang): so theo LENH (ham), KHONG theo chu hien thi ---
    # Doi chu hien thi (vd "Mo video ket qua" -> "Mo ket qua") KHONG phai
    # mat tinh nang - nen so theo lenh. Nut BI MAT (co lenh, khong con) =
    # FAIL that. Nut MOI = chi duoc phep khi co trong danh sach cho phep.
    def theo_lenh(ds):
        out: dict = {}
        for x in ds:
            out.setdefault(x.get("lenh", ""), []).append(x.get("text", ""))
        return out

    nut_a = theo_lenh(a.get("buttons", []))
    nut_b = theo_lenh(b.get("buttons", []))
    lenh_a = {k for k in nut_a if k}
    lenh_b = {k for k in nut_b if k}

    mat = sorted(lenh_a - lenh_b)
    if mat:
        ok = False
        dong.append(f"  [SAI ] NUT (chuc nang)      MAT {len(mat)} nut")
        for lh in mat:
            dong.append(f"          - khong con nut: {lh} {nut_a[lh]}")
    else:
        dong.append(f"  [OK  ] NUT (chuc nang)      {len(lenh_a):3d} lenh - KHONG MAT NUT NAO")

    moi = sorted(lenh_b - lenh_a)
    cho_phep = [lh for lh in moi if lh in NUT_MOI_CHO_PHEP]
    khong_cho_phep = [lh for lh in moi if lh not in NUT_MOI_CHO_PHEP]
    if khong_cho_phep:
        ok = False
        dong.append(f"  [SAI ] NUT (chuc nang)      {len(khong_cho_phep)} nut MOI "
                    f"KHONG nam trong danh sach cho phep")
        for lh in khong_cho_phep:
            dong.append(f"          - nut moi khong cho phep: {lh} {nut_b[lh]}")
    if cho_phep:
        dong.append(f"  [MOI ] NUT (chuc nang)      {len(cho_phep)} nut MOI (cho phep)")
        for lh in cho_phep:
            dong.append(f"          - nut moi: {lh} {nut_b[lh]}")

    doi_nhan = []
    for lh in sorted(lenh_a & lenh_b):
        if sorted(nut_a[lh]) != sorted(nut_b[lh]):
            doi_nhan.append((lh, nut_a[lh], nut_b[lh]))
    cho_phep_nhan = [x for x in doi_nhan if x[0] in NHAN_DOI_CHO_PHEP]
    khong_cho_phep_nhan = [x for x in doi_nhan if x[0] not in NHAN_DOI_CHO_PHEP]
    for lh, cu, moi_cu in khong_cho_phep_nhan:
        ok = False
        dong.append(f"  [SAI ] NUT (chuc nang)      doi nhan khong cho phep: "
                    f"{lh} {cu} -> {moi_cu}")
    if cho_phep_nhan:
        dong.append(f"  [MOI ] NUT (chuc nang)      {len(cho_phep_nhan)} nut DOI NHAN "
                    f"(cho phep)")
        for lh, cu, moi_cu in cho_phep_nhan:
            dong.append(f"          - doi nhan: {lh} {cu} -> {moi_cu}")

    # --- NUT MUI TEN (bat / dong) ---
    # Nut MUI TEN la CAU TRUC, khong phai tinh nang: so sanh theo LOAI.
    # `NhomTinhNang` = 12 nut muc con (phai giu nguyen 12).
    # `NhomLon`      = 4 nut muc lon (MOI - them moi, khong mat gi).
    def dem_chevron(du_lieu, lop):
        return len([c for c in du_lieu.get("chevrons", [])
                    if c["chu_roi"] == lop])

    for lop, so_toi_da in (("NhomTinhNang", 12), ("NhomLon", 0)):
        sa = dem_chevron(a, lop)
        sb = dem_chevron(b, lop)
        if lop == "NhomTinhNang":
            if sa == sb:
                dong.append(f"  [{'OK  '}] NUT MUI TEN {lop:14s} {sa:3d} nut - GIONG HET")
            else:
                ok = False
                dong.append(f"  [SAI ] NUT MUI TEN {lop:14s} truoc {sa} / sau {sb}")
        else:
            dong.append(f"  [MOI ] NUT MUI TEN {lop:14s} truoc {sa} / sau {sb}"
                        f" - them moi de mo/dong 4 muc lon (khong mat gi)")

    # Moi nut mui ten phai la CHEVRON that (glyph Segoe MDL2, khong emoji).
    for du_lieu, nhan in ((a, "TRUOC"), (b, "SAU  ")):
        sai = [c for c in du_lieu.get("chevrons", []) if not c["la_chevron"]]
        if sai:
            ok = False
            dong.append(f"  [SAI ] nut mui ten khong phai CHEVRON ({nhan}): {sai}")
    return ok, dong


def in_bang(du_lieu: dict) -> None:
    in_ky("-" * 78)
    in_ky(f"  CHECKBOX ({len(du_lieu['checkboxes'])}):")
    for c in du_lieu["checkboxes"]:
        in_ky(f"      {c['text']!r:52s} bien={c['bien']:22s} mac_dinh={c['gia_tri']!r}")
    in_ky(f"  NUT CHUC NANG ({len(du_lieu['buttons'])}):")
    for c in du_lieu["buttons"]:
        in_ky(f"      {c['text']!r:52s} lenh={c['lenh']}")
    in_ky(f"  NUT MUI TEN ({len(du_lieu.get('chevrons', []))}):")
    for c in du_lieu.get("chevrons", []):
        in_ky(f"      chu_roi={c['chu_roi']:16s} la_chevron={c['la_chevron']}")
    in_ky(f"  NHOM TINH NANG ({len(du_lieu['nhom'])}):")
    for c in du_lieu["nhom"]:
        in_ky(f"      {c['text']!r:52s} bien={c['bien']:22s} mac_dinh={c['gia_tri']!r}")
    in_ky(f"  THE VIDEO MAU ({len(du_lieu['the_video_mau'])}):")
    for c in du_lieu["the_video_mau"]:
        in_ky(f"      {c['ten']!r:24s} mo_ta={c['mo_ta']!r:34s} co_lenh={c['co_lenh']}")
    in_ky("-" * 78)


# ------------------------------------------------------------------- chay

def luu(duong_dan: str) -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.6)
    app.update()

    du_lieu = thu_thap(app)
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    with open(duong_dan, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=1)

    in_ky("=" * 78)
    in_ky(f"DA THU THAP CAU TRUC GUI -> {duong_dan}")
    in_ky("=" * 78)
    in_bang(du_lieu)

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


def so(a: str, b: str) -> int:
    with open(a, "r", encoding="utf-8") as f:
        du_a = json.load(f)
    with open(b, "r", encoding="utf-8") as f:
        du_b = json.load(f)

    in_ky("=" * 78)
    in_ky("SO SANH CAU TRUC GUI TRUOC / SAU KHI BO CUC LAI COT TRAI")
    in_ky("=" * 78)
    in_ky(f"  TRUOC: {a}")
    in_ky(f"  SAU  : {b}")
    in_ky("")
    ok, dong = so_sanh(du_a, du_b)
    for d in dong:
        in_ky(d)
    in_ky("")
    in_ky("  TONG KET: " + ("PASS - KHONG MAT TINH NANG NAO" if ok
                            else "FAIL - CO TINH NANG BI MAT / DOI"))
    in_ky("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        args = sys.argv[1:]
        if len(args) >= 3 and args[0] == "--so":
            sys.exit(so(args[1], args[2]))
        if len(args) >= 2 and args[0] == "--luu":
            sys.exit(luu(args[1]))
        in_ky("Dung:")
        in_ky("  python _kk_kiem_khong_mat_tinh_nang.py --luu <file.json>")
        in_ky("  python _kk_kiem_khong_mat_tinh_nang.py --so <a.json> <b.json>")
        sys.exit(2)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
