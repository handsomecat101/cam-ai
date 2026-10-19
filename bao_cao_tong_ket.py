#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CamAI - Bao cao tong ket (Excel + trang xem lai offline).

Doc file CSV do app.py xuat (<ten>_bao_cao.csv) va sinh ra 2 file:

  1. <ten>_tong_ket.xlsx  - Excel tong ket, mo ra la dep, khong phai sua gi.
  2. <ten>_xem_lai.html   - trang xem lai video, mo bang trinh duyet, KHONG can Internet.

Cach dung:
    .venv\\Scripts\\python.exe bao_cao_tong_ket.py --csv <duong_dan.csv> \\
        [--video <duong_dan_ket_qua.mp4] [--xuat <thu_muc>] [--nguong-dong N]

CSV can 10 cot: giay, so_nguoi, so_mat, nguoi_quen, nam, nu, tuoi_tb,
                trong_vung, vi_pham, canh_lau

Ghi chu ve y nghia so lieu:
  - vi_pham / canh_lau la CO HIEU 0 hoac 1 tren TUNG khung hinh.
    "So lan" trong bao cao = so LAN LIEN TIEP (mot lan vao vung la 1 lan,
    giu nguyen trong vung 5 giay van chi la 1 lan) - dung y nhu app.py.
  - Nguong "vuot nguoi trong vung" khong nam trong CSV. Mac dinh lay bang
    so nguoi nhieu nhat co trong vung. Muon dung nguong khac:
        --nguong-dong 5

Chi can openpyxl. Khong can matplotlib, khong can Internet.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.parse
from collections import Counter, OrderedDict

# openpyxl dung o tang duoi - import o cap module de moi ham deu dung duoc.
try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    CO_XLSX = True
except ImportError:                                   # thieu openpyxl
    CO_XLSX = False

# ----------------------------------------------------------------- hang so

PHIEN_BAN = "1.0"

# Cot bat buoc trong CSV. Cac cot khac thieu thi van chay duoc (lay = 0/rong).
COT_BAT_BUOC = ("giay", "so_nguoi")

# Day du 10 cot app.py xuat ra. Cot ngoai danh sach nay se bi bo qua.
COT_DAY_DU = (
    "giay", "so_nguoi", "so_mat", "nguoi_quen", "nam", "nu",
    "tuoi_tb", "trong_vung", "vi_pham", "canh_lau",
)

# Ten sheet trong Excel (tieng Viet khong dau de moi Windows/doc duoc)
SHEET_TONG_KET = "Tong ket"
SHEET_THEO_GIO = "Theo gio"
SHEET_CU_THEO_GIAY = "Cu theo giay"

# Do rong cot (ky tu) cho tung sheet - tranh o hien ####
RONG_TONG_KET = (26, 40, 24, 62)
RONG_THEO_GIO = (30, 14, 14, 14, 14, 18, 20)
RONG_CU_THEO_GIAY = (12, 14, 14, 14, 14, 18, 18, 18)

MAU_TIEU_DE = "1F4E79"      # xanh dam - nen dong tieu de
MAU_CHU_TIEU_DE = "FFFFFF"
MAU_MUC = "DDEBF7"          # xanh nhat - dong nhom muc
MAU_LE = "F2F7FC"           # xanh rat nhat - dong ghi chu
MAU_TIEU_DE_CHINH = "1F2937"

# Gioi han an toan (khong bao gio lam treo may chu nha)
TOI_DA_DONG_HTML = 400          # so su kien dua vao danh sach HTML
TOI_DA_GIAY_CHI_TIET = 20000   # so dong cua sheet "Cu theo giay"


class BaoCaoLoi(Exception):
    """Loi thuong, se in ra bang tieng Viet chu khong loay do (traceback)."""


# ----------------------------------------------------------------- tien ich

def _s(value, mac_dinh=0.0):
    """Chuyen chuoi CSV thanh so. Cell rong/sai -> mac dinh (khong crash)."""
    if value is None:
        return mac_dinh
    text = str(value).strip().replace(",", ".")
    if not text:
        return mac_dinh
    try:
        return float(text)
    except ValueError:
        return mac_dinh


def _i(value, mac_dinh=0):
    """Chuyen thanh so nguyen."""
    return int(round(_s(value, mac_dinh)))


def _hms(giay):
    """0.0 -> '00:00' | 75.86 -> '01:15' | 3725.0 -> '1:02:05'"""
    try:
        tong = int(round(float(giay)))
    except (TypeError, ValueError):
        return "--:--"
    if tong < 0:
        tong = 0
    gio, phut = divmod(tong // 60, 60)
    giay = tong % 60
    if gio:
        return "%d:%02d:%02d" % (gio, phut, giay)
    return "%02d:%02d" % (phut, giay)


def _loai_bo_gia(so, n=2):
    """Lam tron va bo dau thap phan thua: 3.0 -> '3' | 2.50 -> '2.5'"""
    try:
        x = round(float(so), n)
    except (TypeError, ValueError):
        return str(so)
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ("%." + str(n) + "f") % x


def _chuan_hoa_ten(goc, duoi):
    """'video_test_bao_cao' + '_bao_cao' -> 'video_test'."""
    ten = os.path.basename(goc)
    if ten.lower().endswith(duoi.lower()):
        ten = ten[: -len(duoi)]
    return ten or os.path.splitext(os.path.basename(goc))[0]


# ----------------------------------------------------------------- doc CSV

def doc_csv(duong_dan):
    """Doc CSV cua app.py. Tra ve (danh sach dong, danh sach canh bao).

    Moi dong la dict da ep kieu: giay/so_nguoi/... la number,
    nguoi_quen la danh sach ten da tach.
    """
    if not os.path.isfile(duong_dan):
        raise BaoCaoLoi("Khong tim thay file CSV: %s" % duong_dan)

    canh_bao = []
    try:
        with open(duong_dan, "r", encoding="utf-8-sig", newline="") as f:
            doc = csv.DictReader(f)
            if not doc.fieldnames:
                raise BaoCaoLoi(
                    "File CSV rong hoac khong co dong tieu de: %s" % duong_dan
                )
            ten_cot = [c.strip() for c in doc.fieldnames]
            thieu = [c for c in COT_BAT_BUOC if c not in ten_cot]
            if thieu:
                raise BaoCaoLoi(
                    "File CSV thieu cot bat buoc: %s.\nCac cot can co: %s.\nFile cu: %s"
                    % (", ".join(thieu), ", ".join(COT_BAT_BUOC), duong_dan)
                )
            la = [c for c in ten_cot if c not in COT_DAY_DU]
            if la:
                canh_bao.append("Bo qua cot khong dung de bao cao: " + ", ".join(la))
            thieu = [c for c in COT_DAY_DU if c not in ten_cot]
            if thieu:
                canh_bao.append(
                    "CSV khong co cot: %s - se coi nhu rong/0" % ", ".join(thieu)
                )

            dong = []
            so_dong_hong = 0
            for thu_tu, raw in enumerate(doc, start=2):
                gia_tri = {}
                for cot in ten_cot:
                    gia_tri[cot] = (raw.get(cot) or "").strip()

                o_giay = _s(gia_tri.get("giay"), -1.0)
                if o_giay < 0:
                    so_dong_hong += 1
                    continue
                if not gia_tri.get("so_nguoi", "").lstrip("-").isdigit():
                    # van chap nhan bang cach ep so, chi can bao dong khong doc duoc
                    so_dong_hong += 1

                quen = [
                    ten.strip()
                    for ten in gia_tri.get("nguoi_quen", "").replace(";", "|").split("|")
                    if ten.strip()
                ]
                tuoi = _s(gia_tri.get("tuoi_tb"), 0.0)

                dong.append({
                    "thu_tu": len(dong) + 1,
                    "giay": o_giay,
                    "so_nguoi": max(0, _i(gia_tri.get("so_nguoi"))),
                    "so_mat": max(0, _i(gia_tri.get("so_mat"))),
                    "nguoi_quen": quen,
                    "nam": max(0, _i(gia_tri.get("nam"))),
                    "nu": max(0, _i(gia_tri.get("nu"))),
                    "tuoi_tb": tuoi if tuoi > 0 else None,
                    "trong_vung": max(0, _i(gia_tri.get("trong_vung"))),
                    "vi_pham": 1 if _i(gia_tri.get("vi_pham")) > 0 else 0,
                    "canh_lau": 1 if _i(gia_tri.get("canh_lau")) > 0 else 0,
                })
    except UnicodeDecodeError:
        raise BaoCaoLoi(
            "File CSV khong doc duoc (khong phai ma hoa UTF-8): %s" % duong_dan
        )
    except csv.Error as loi:
        raise BaoCaoLoi("File CSV hong, khong doc duoc: %s" % loi)

    if not dong:
        raise BaoCaoLoi(
            "File CSV khong co duong du lieu nao (chi co tieu de hoac cot sai): %s"
            % duong_dan
        )
    if so_dong_hong:
        canh_bao.append("Bo qua %d dong khong doc duoc" % so_dong_hong)

    dong.sort(key=lambda r: r["giay"])
    for i, r in enumerate(dong, start=1):
        r["thu_tu"] = i
    return dong, canh_bao


# ----------------------------------------------------------------- tinh toan

def _cac_lan(dong, dieu_kien):
    """Dem so LAN LIEN TIEP thoa man dieu_kien.

    5 khung lien nhap co nguoi vao vung = 1 lan (khong phai 5 lan).
    """
    lan, dang_trong = [], False
    for r in dong:
        if dieu_kien(r):
            if not dang_trong:
                lan.append({"bat_dau": r, "ket_thuc": r, "khung": 1})
                dang_trong = True
            else:
                lan[-1]["ket_thuc"] = r
                lan[-1]["khung"] += 1
        else:
            dang_trong = False
    return lan


def _diem_dinh_ky(dong, khoa, lon_nhat=True):
    """Tra ve dong co gia tri lon/nho nhat cua khoa. Xu ly nhieu diem = lay lan dau."""
    tot = dong[0][khoa]
    for r in dong[1:]:
        if (r[khoa] > tot) if lon_nhat else (r[khoa] < tot):
            tot = r[khoa]
    for r in dong:
        if r[khoa] == tot:
            return r
    return dong[0]


def tong_ket(dong, nguong_dong=None):
    """Tinh toan tat ca con so tong hop tu CSV."""
    n = len(dong)
    dau, cuoi = dong[0], dong[-1]
    thoi_luong = cuoi["giay"] - dau["giay"]
    fps = (n / thoi_luong) if thoi_luong > 0 else 0.0

    so_nguoi = [r["so_nguoi"] for r in dong]
    trong_vung = [r["trong_vung"] for r in dong]

    dinh_ky = _diem_dinh_ky(dong, "so_nguoi", True)
    dinh_ky_vung = _diem_dinh_ky(dong, "trong_vung", True)

    if nguong_dong is None:
        nguong_dong = max(trong_vung) if trong_vung else 0
        nguong_tu_dong = True
    else:
        nguong_tu_dong = False

    lan_vao_vung = _cac_lan(dong, lambda r: r["trong_vung"] > 0)
    lan_dung_lau = _cac_lan(dong, lambda r: r["canh_lau"] > 0)
    lan_vuot = _cac_lan(dong, lambda r: r["trong_vung"] > nguong_dong)

    # ---- nguoi quen
    quen = OrderedDict()
    for r in dong:
        if not r["nguoi_quen"]:
            continue
        for ten in r["nguoi_quen"]:
            thong_tin = quen.setdefault(ten, {
                "ten": ten, "khung": 0, "tuoi": [], "nam": 0, "nu": 0,
                "dau": r["giay"], "cuoi": r["giay"],
            })
            thong_tin["khung"] += 1
            thong_tin["cuoi"] = r["giay"]
            if r["tuoi_tb"] is not None:
                thong_tin["tuoi"].append(r["tuoi_tb"])
            thong_tin["nam"] += r["nam"]
            thong_tin["nu"] += r["nu"]
    for thong_tin in quen.values():
        thong_tin["tuoi_tb"] = (
            sum(thong_tin["tuoi"]) / len(thong_tin["tuoi"]) if thong_tin["tuoi"] else None
        )

    return {
        "so_khung": n,
        "giay_dau": dau["giay"],
        "giay_cuoi": cuoi["giay"],
        "thoi_luong": thoi_luong,
        "fps": fps,
        "dinh_ky": dinh_ky,
        "dinh_ky_vung": dinh_ky_vung,
        "tb_nguoi": sum(so_nguoi) / n,
        "max_nguoi": max(so_nguoi),
        "min_nguoi": min(so_nguoi),
        "khung_co_nguoi": sum(1 for v in so_nguoi if v > 0),
        "khung_co_mat": sum(1 for r in dong if r["so_mat"] > 0),
        "nguoi_quen": list(quen.values()),
        "nguong_dong": nguong_dong,
        "nguong_tu_dong": nguong_tu_dong,
        "lan_vao_vung": lan_vao_vung,
        "lan_dung_lau": lan_dung_lau,
        "lan_vuot": lan_vuot,
        "khung_vi_pham": sum(1 for r in dong if r["vi_pham"]),
        "khung_canh_lau": sum(1 for r in dong if r["canh_lau"]),
        "max_trong_vung": max(trong_vung),
    }


def gom_nhom(dong, thoi_luong):
    """Chon cach gom hop ly: video ngan <= 1 gio -> theo PHUT, dai hon -> theo GIO."""
    theo_phut = thoi_luong <= 3600
    don_vi = 60 if theo_phut else 3600
    nhom = OrderedDict()
    for r in dong:
        so = int(r["giay"] // don_vi)
        nhom.setdefault(so, []).append(r)

    hang = []
    for so, cac_dong in nhom.items():
        if theo_phut:
            nhan = "Phut %d (%s-%s)" % (so + 1, _hms(so * 60), _hms((so + 1) * 60))
        else:
            nhan = "Gio %d (%s-%s)" % (
                so, _hms(so * 3600)[:-3], _hms((so + 1) * 3600)[:-3],
            )
        so_nguoi = [d["so_nguoi"] for d in cac_dong]
        hang.append({
            "nhan": nhan,
            "so_khung": len(cac_dong),
            "tb": sum(so_nguoi) / len(so_nguoi),
            "max": max(so_nguoi),
            "vi_pham": sum(1 for d in cac_dong if d["vi_pham"]),
            "dung_lau": sum(1 for d in cac_dong if d["canh_lau"]),
        })
    return hang, theo_phut


def gom_theo_giay(dong):
    """Gom du lieu theo giay nguyen de anh tu ve do thi."""
    nhom = OrderedDict()
    for r in dong:
        nhom.setdefault(int(r["giay"]), []).append(r)

    hang, buoc = [], 1
    if len(nhom) > TOI_DA_GIAY_CHI_TIET:
        buoc = int(math.ceil(len(nhom) / float(TOI_DA_GIAY_CHI_TIET)))

    for so, cac_dong in nhom.items():
        if buoc > 1 and (so % buoc) != 0:
            continue
        so_nguoi = [d["so_nguoi"] for d in cac_dong]
        hang.append({
            "giay": so,
            "khung": len(cac_dong),
            "tb": sum(so_nguoi) / len(so_nguoi),
            "max": max(so_nguoi),
            "tb_vung": sum(d["trong_vung"] for d in cac_dong) / len(cac_dong),
            "vi_pham": sum(1 for d in cac_dong if d["vi_pham"]),
            "dung_lau": sum(1 for d in cac_dong if d["canh_lau"]),
        })
    return hang, buoc


def su_kien(tk, dong):
    """Danh sach su kien dang chu y (dung cho HTML va bang 'Cu theo giay')."""
    muc = []
    for lan in tk["lan_vao_vung"]:
        d = lan["bat_dau"]
        muc.append({
            "giay": d["giay"], "thu_tu": d["thu_tu"], "loai": "vao_vung",
            "mau": "vang",
            "mo_ta": "Co nguoi vao vung canh (%d nguoi trong vung)" % d["trong_vung"],
        })
    for lan in tk["lan_vuot"]:
        d = lan["bat_dau"]
        muc.append({
            "giay": d["giay"], "thu_tu": d["thu_tu"], "loai": "vuot_nguong",
            "mau": "do",
            "mo_ta": "Vuot nguong %d nguoi trong vung (co %d nguoi)"
                     % (tk["nguong_dong"], d["trong_vung"]),
        })
    for lan in tk["lan_dung_lau"]:
        d = lan["bat_dau"]
        muc.append({
            "giay": d["giay"], "thu_tu": d["thu_tu"], "loai": "dung_lau",
            "mau": "cam",
            "mo_ta": "Co nguoi dung lau trong vung lan dau tien (gia tri canh_lau = 1)",
        })
    muc.sort(key=lambda e: (e["giay"], e["loai"]))
    return muc


# ----------------------------------------------------------------- Excel

def _viet_tieu_de(ws, hang, cot, rong):
    for i, (ten, r) in enumerate(zip(cot, rong), start=1):
        o = ws.cell(row=hang, column=i, value=ten)
        o.font = Font(bold=True, color=MAU_CHU_TIEU_DE, size=11)
        o.fill = PatternFill("solid", fgColor=MAU_TIEU_DE)
        o.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        o.border = Border(bottom=Side(style="medium", color="FFFFFF"))
        ws.column_dimensions[get_column_letter(i)].width = r
    ws.row_dimensions[hang].height = 30


def _canh_le(ws, so_dong, so_cot):
    """Dong du lieu: bo phan thap phan thua va canh phai."""
    for r in range(1, so_dong + 1):
        for c in range(1, so_cot + 1):
            o = ws.cell(row=r, column=c)
            if o.value is None:
                continue
            if isinstance(o.value, (int, float)) and not isinstance(o.value, bool):
                o.number_format = "0.00" if isinstance(o.value, float) else "0"
                o.alignment = Alignment(horizontal="center")
            else:
                o.alignment = Alignment(
                    horizontal="left", vertical="top", wrap_text=(c == so_cot),
                )


def tao_xlsx(tk, hang_gom, theo_phut, hang_giay, buoc, ten_file, duong_dan,
             thoi_dan_id=None):
    """Sinh file Excel tong ket."""
    if not CO_XLSX:
        raise BaoCaoLoi(
            "Thieu thu vien openpyxl de tao file Excel.\n"
            "Sua lai: .venv\\Scripts\\python.exe -m pip install openpyxl"
        )

    wb = openpyxl.Workbook()

    # ---------------------------------------------------- 1. Tong ket
    ws = wb.active
    ws.title = SHEET_TONG_KET
    ws["A1"] = "BAO CAO TONG KET - CAMAI"
    ws["A1"].font = Font(bold=True, size=15, color=MAU_TIEU_DE_CHINH)
    if thoi_dan_id:
        ws["A2"] = "Tao luc %s" % thoi_dan_id
        ws["A2"].font = Font(italic=True, size=9, color="6B7280")

    cot = ["Muc", "Chi so", "Gia tri", "Ghi chu"]
    hang_tieu_de = 4
    _viet_tieu_de(ws, hang_tieu_de, cot, RONG_TONG_KET)

    dinh_ky = tk["dinh_ky"]
    dv = tk["dinh_ky_vung"]
    nguong_txt = "%d nguoi" % tk["nguong_dong"]
    if tk["nguong_tu_dong"]:
        nguong_txt += " (tu dong)"
    if tk["nguong_dong"] <= 0:
        nguong_txt += " - video nay khong viet vung canh"

    du_lieu = [
        ("Tong quan", "Ten file CSV", str(ten_file),
         "Nguon du lieu cua bao cao nay"),
        ("Tong quan", "Tong so khung hinh da phan tich", tk["so_khung"],
         "Moi dong CSV = 1 khung hinh"),
        ("Tong quan", "Thoi luong video", _hms(tk["thoi_luong"]),
         "%.2f giay" % tk["thoi_luong"]),
        ("Tong quan", "So khung hinh / giay (FPS uoc tinh)",
         round(tk["fps"], 2) if tk["fps"] else 0, "Tuong doi, tinh tu CSV"),

        ("Diem dinh ky", "GIAY DONG NHAT (so nguoi nhieu nhat)", _hms(dinh_ky["giay"]),
         "%.2f giay - vao video o giay thu %d" % (dinh_ky["giay"], dinh_ky["thu_tu"])),
        ("Diem dinh ky", "So nguoi luc do", dinh_ky["so_nguoi"],
         "Dinh khung hinh thu %d trong video" % dinh_ky["thu_tu"]),
        ("Diem dinh ky", "So nguoi nhieu nhat trong VUNG CANH", dv["trong_vung"],
         "Luc %s - khung hinh thu %d" % (_hms(dv["giay"]), dv["thu_tu"])),

        ("So nguoi", "Trung binh so nguoi moi khung hinh",
         round(tk["tb_nguoi"], 2), ""),
        ("So nguoi", "Lon nhat", tk["max_nguoi"], ""),
        ("So nguoi", "Nho nhat", tk["min_nguoi"], ""),
        ("So nguoi", "So khung hinh co it nhat 1 nguoi", tk["khung_co_nguoi"],
         "%.1f%% cua video" % (100.0 * tk["khung_co_nguoi"] / tk["so_khung"])),

        ("Vung canh", "So LAN co nguoi vao vung", len(tk["lan_vao_vung"]),
         "Tinh theo lan lien tiep (vao 1 lan roi doi la 1 lan moi)"),
        ("Vung canh", "So khung hinh co nguoi trong vung", tk["khung_vi_pham"],
         "Tong so khung hinh, khong phai so lan"),
        ("Vung canh", "Nguong dong da dung de tinh", nguong_txt,
         "App khong luu nguong nay vao CSV. Dung --nguong-dong de chi dinh"
         if tk["nguong_tu_dong"] else "Do nguoi truyen --nguong-dong"),
        ("Vung canh", "So LAN vuot nguong dong", len(tk["lan_vuot"]),
         "So nguoi trong vung > %d" % tk["nguong_dong"]),
        ("Vung canh", "So LAN co nguoi dung lau", len(tk["lan_dung_lau"]),
         "Co nguoi o lai trong vung qua nguong canh"),
        ("Vung canh", "So khung hinh bi gan nho 'dung lau'", tk["khung_canh_lau"],
         "Tong so khung hinh, khong phai so lan"),
        ("Vung canh", "Thoi diem bi gan nho 'dung lau'",
         ", ".join(_hms(l["bat_dau"]["giay"]) for l in tk["lan_dung_lau"]) or "Khong co",
         "Bam vao de xem video o trang xem lai"),
    ]

    for q in tk["nguoi_quen"]:
        tuoi_txt = ("%.1f" % q["tuoi_tb"]) if q["tuoi_tb"] is not None else "Khong do duoc"
        tong_gt = q["nam"] + q["nu"]
        if tong_gt:
            if q["nam"] and q["nu"]:
                ty_le = "%d nam / %d nu" % (q["nam"], q["nu"])
            else:
                ty_le = ("Toan nam (%d)" % q["nam"]) if q["nam"] else ("Toan nu (%d)" % q["nu"])
        else:
            ty_le = "Khong do duoc"
        du_lieu.append((
            "Nguoi quen", q["ten"],
            "%d khung hinh" % q["khung"],
            "Xuat hien %s - %s | Tuoi TB %s | %s"
            % (_hms(q["dau"]), _hms(q["cuoi"]), tuoi_txt, ty_le),
        ))

    if not tk["nguoi_quen"]:
        du_lieu.append((
            "Nguoi quen", "Khong co nguoi quen nao",
            "0",
            "Video nay khong nhan dien duoc người quen. "
            "Neu can, them anh vao thu muc known_faces/<Ten>/ roi chay lai.",
        ))

    r = hang_tieu_de
    for muc, chi_so, gia_tri, ghi_chu in du_lieu:
        r += 1
        ws.cell(row=r, column=1, value=muc)
        ws.cell(row=r, column=2, value=chi_so)
        ws.cell(row=r, column=3, value=gia_tri)
        ws.cell(row=r, column=4, value=ghi_chu)
        for c in range(1, 5):
            o = ws.cell(row=r, column=c)
            o.border = Border(bottom=Side(style="hair", color="D0D7E2"))
        if muc and str(ws.cell(row=r, column=1).value) == muc:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=MAU_MUC)
            ws.cell(row=r, column=1).font = Font(bold=True, size=10)
        ws.cell(row=r, column=3).font = Font(bold=True, color="0F172A")

    _canh_le(ws, r, 4)
    for rr in range(hang_tieu_de + 1, r + 1):
        ws.cell(row=rr, column=1).alignment = Alignment(
            horizontal="center", vertical="top")
        ws.cell(row=rr, column=3).alignment = Alignment(
            horizontal="center", vertical="top")
    ws.freeze_panes = "A%d" % (hang_tieu_de + 1)
    ws.auto_filter.ref = "A%d:D%d" % (hang_tieu_de, r)
    ws.sheet_view.showGridLines = False

    # ---------------------------------------------------- 2. Theo gio
    ws2 = wb.create_sheet(SHEET_THEO_GIO)
    ws2["A1"] = "TONG HOP THEO %s" % ("PHUT" if theo_phut else "GIO")
    ws2["A1"].font = Font(bold=True, size=14, color=MAU_TIEU_DE_CHINH)
    if theo_phut:
        cach = ("Cach gom: theo PHUT (moi 60 giay) - video nay dai %.1f giay, "
                "chia theo phut cho de doc ro hon." % tk["thoi_luong"])
    else:
        cach = ("Cach gom: theo GIO (moi 3600 giay) - video nay dai %.1f giay "
                "(hon 1 gio), chia theo gio de dong bi lon." % tk["thoi_luong"])
    ws2["A2"] = cach
    ws2["A2"].font = Font(italic=True, size=9, color="6B7280")

    cot2 = ["Khoang thoi gian", "So khung hinh", "TB so nguoi", "Max so nguoi",
            "Tong so lan vi pham", "Tong so lan dung lau"]
    ht2 = 4
    _viet_tieu_de(ws2, ht2, cot2, RONG_THEO_GIO)
    for i, h in enumerate(hang_gom, start=1):
        ws2.cell(row=ht2 + i, column=1, value=h["nhan"])
        ws2.cell(row=ht2 + i, column=2, value=h["so_khung"])
        ws2.cell(row=ht2 + i, column=3, value=round(h["tb"], 2))
        ws2.cell(row=ht2 + i, column=4, value=h["max"])
        ws2.cell(row=ht2 + i, column=5, value=h["vi_pham"])
        ws2.cell(row=ht2 + i, column=6, value=h["dung_lau"])
    r2 = ht2 + len(hang_gom)
    _canh_le(ws2, r2, 6)
    for rr in range(ht2 + 1, r2 + 1):
        ws2.cell(row=rr, column=1).alignment = Alignment(horizontal="left")
    ws2.freeze_panes = "A%d" % (ht2 + 1)
    ws2.auto_filter.ref = "A%d:F%d" % (ht2, r2)
    ws2.sheet_view.showGridLines = False

    # ---------------------------------------------------- 3. Cu theo giay
    ws3 = wb.create_sheet(SHEET_CU_THEO_GIAY)
    ws3["A1"] = "SO LIEU TUNG GIAY (DE TU VE DO THI)"
    ws3["A1"].font = Font(bold=True, size=14, color=MAU_TIEU_DE_CHINH)
    ghi_chu3 = (
        "Moi dong la 1 giay cua video. Cot 'TB so nguoi' va 'Max so nguoi' "
        "la thong ke trong cac khung hinh cua giay do."
    )
    if buoc > 1:
        ghi_chu3 += (" | Video rat dai nen chi lay 1 giay moi %d giay de file "
                     "khong qua lon." % buoc)
    ws3["A2"] = ghi_chu3
    ws3["A2"].font = Font(italic=True, size=9, color="6B7280")

    cot3 = ["Giay thu", "Thoi diem (giay)", "So khung hinh", "TB so nguoi",
            "Max so nguoi", "TB nguoi trong vung", "So khung vi pham",
            "So khung dung lau"]
    ht3 = 4
    _viet_tieu_de(ws3, ht3, cot3, RONG_CU_THEO_GIAY)
    for i, h in enumerate(hang_giay, start=1):
        ws3.cell(row=ht3 + i, column=1, value=h["giay"] + 1)
        ws3.cell(row=ht3 + i, column=2, value=h["giay"])
        ws3.cell(row=ht3 + i, column=3, value=h["khung"])
        ws3.cell(row=ht3 + i, column=4, value=round(h["tb"], 2))
        ws3.cell(row=ht3 + i, column=5, value=h["max"])
        ws3.cell(row=ht3 + i, column=6, value=round(h["tb_vung"], 2))
        ws3.cell(row=ht3 + i, column=7, value=h["vi_pham"])
        ws3.cell(row=ht3 + i, column=8, value=h["dung_lau"])
    r3 = ht3 + len(hang_giay)
    _canh_le(ws3, r3, 8)
    ws3.freeze_panes = "A%d" % (ht3 + 1)
    ws3.auto_filter.ref = "A%d:H%d" % (ht3, r3)
    ws3.sheet_view.showGridLines = False

    try:
        wb.save(duong_dan)
    except PermissionError:
        raise BaoCaoLoi(
            "Khong ghi duoc file Excel (file dang duoc mo bang Excel?):\n  %s"
            % duong_dan
        )
    return duong_dan


# ----------------------------------------------------------------- HTML

MAU_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TIEU_DE__ - Xem lai video</title>
<style>
:root{
  --nen:#0b1220; --nen2:#111c30; --the:#18263f; --chu:#e8eefc; --chu-mo:#93a4c4;
  --vang:#f5b942; --do:#ff5a6a; --cam:#ff9f43; --xanh:#4cc9f0; --luc:#6ee7a8;
  --vien:#24324d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--nen);color:var(--chu);
 font-family:"Segoe UI",Tahoma,Verdana,sans-serif;font-size:15px;line-height:1.5}
header{padding:18px 22px 12px;background:var(--nen2);border-bottom:1px solid var(--vien)}
h1{margin:0 0 4px;font-size:21px}
.sub{color:var(--chu-mo);font-size:13px}
main{padding:18px 22px 40px;max-width:1500px;margin:0 auto}
.the{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin-bottom:20px}
.o{background:var(--the);border:1px solid var(--vien);border-radius:10px;padding:12px 14px}
.o .n{color:var(--chu-mo);font-size:12px;text-transform:uppercase;letter-spacing:.4px}
.o .v{font-size:24px;font-weight:700;margin-top:4px}
.o .d{color:var(--chu-mo);font-size:12px;margin-top:2px}
.v.vang{color:var(--vang)} .v.do{color:var(--do)} .v.cam{color:var(--cam)} .v.xanh{color:var(--xanh)}
.luoi{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:18px}
@media(max-width:1000px){.luoi{grid-template-columns:1fr}}
.khoi{background:var(--nen2);border:1px solid var(--vien);border-radius:12px;padding:14px}
.khoi h2{margin:0 0 10px;font-size:16px}
canvas{width:100%;height:340px;display:block;border-radius:8px;background:#0a1120;cursor:crosshair}
.chuc{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:12.5px;color:var(--chu-mo)}
.chuc i{display:inline-block;width:14px;height:4px;vertical-align:middle;margin-right:6px;border-radius:2px}
.chuc i.dot{width:9px;height:9px;border-radius:50%}
.hang Dieu{margin-top:14px}
.nut{background:var(--the);color:var(--chu);border:1px solid var(--vien);border-radius:10px;
 padding:11px 16px;font-size:14.5px;font-weight:600;cursor:pointer;font-family:inherit}
.nut:hover{border-color:var(--xanh);color:#fff}
.nut.lon{background:linear-gradient(135deg,#f5b942,#ff9f43);color:#1a1206;border:none;
 padding:14px 22px;font-size:16px;width:100%}
.nut:hover{filter:brightness(1.08)}
.nut.nho{padding:7px 12px;font-size:13px;font-weight:500}
#trangthai{color:var(--chu-mo);font-size:13.5px;margin-top:10px;min-height:20px}
video{width:100%;margin-top:14px;border-radius:10px;background:#000;max-height:44vh}
ul{list-style:none;margin:0;padding:0;max-height:520px;overflow:auto}
li{margin-bottom:8px}
li button{width:100%;text-align:left;background:var(--the);border:1px solid var(--vien);
 border-left:4px solid var(--vang);border-radius:8px;padding:9px 12px;cursor:pointer;
 color:var(--chu);font-family:inherit;font-size:13.5px}
li button:hover{background:#22334f}
li.vuot button{border-left-color:var(--do)}
li.lau button{border-left-color:var(--cam)}
.g{font-weight:700;color:var(--vang);font-variant-numeric:tabular-nums}
li.vuot .g{color:var(--do)} li.lau .g{color:var(--cam)}
.ghi{margin-top:12px;padding:10px 12px;background:#0f1a2c;border:1px dashed var(--vien);
 border-radius:8px;color:var(--chu-mo);font-size:12.5px}
</style>
</head>
<body>
<header>
  <h1>__TIEU_DE__ &mdash; Xem lai video</h1>
  <div class="sub">__TONG_DON__</div>
</header>
<main>
  <section class="the" id="the"></section>
  <div class="luoi">
    <div>
      <div class="khoi">
        <h2>So nguoi theo thoi gian</h2>
        <canvas id="bieu"></canvas>
        <div class="chuc">
          <span><i style="background:#4cc9f0"></i>So nguoi trong khung hinh</span>
          <span><i class="dot" style="background:#ff5a6a"></i>Vi pham (co nguoi trong vung)</span>
          <span><i class="dot" style="background:#ff9f43"></i>Dung lau</span>
          <span><i class="dot" style="background:#6ee7a8"></i>Dinh diem nhieu nhat nhat</span>
        </div>
        <div class="hang dieu">
          <button class="nut lon" id="btnDinhKy">&#9193; Nhay toi giay dong nhat</button>
        </div>
        <div class="hang dieu">
          <button class="nut nho" id="btnPhat">&#9654; Phat video</button>
          <button class="nut nho" id="btnVeDau">&#8676; Ve dau</button>
          <span style="flex:1"></span>
          <span style="color:var(--chu-mo);font-size:12.5px;align-self:center">
            Bam vao bieu do de nhay dung giay do</span>
        </div>
        <div id="trangthai"></div>
        <video id="video" controls preload="metadata" playsinline __SRC__></video>
        <div class="ghi" id="ghiChu"></div>
      </div>
    </div>
    <div class="khoi">
      <h2>Su kien dang chu y (<span id="soSuKien">0</span>)</h2>
      <ul id="dsSuKien"></ul>
      <div class="ghi">
        Bam vao mot su kien se dua video toi dung giay do.
        Chi so &ldquo;vi pham&rdquo; va &ldquo;dung lau&rdquo; lay tu file CSV cua CamAI.
      </div>
    </div>
  </div>
</main>
<script>
var D = __DU_LIEU__;
var cv = document.getElementById('bieu');
var ctx = cv.getContext('2d');
var vid = document.getElementById('video');
var P = {l:56, r:16, t:16, b:32};
var W = 0, H = 340, hover = -1, diemDinhKy = D.dinh_ky.thu_tu - 1;

function viSaoNhat(i){ return D.t[i]; }
function canBang(t){
  var a = D.t, lo = 0, hi = a.length - 1;
  if (hi <= 0) return 0;
  while (lo < hi){
    var giua = (lo + hi) >> 1;
    if (a[giua] < t) lo = giua + 1; else hi = giua;
  }
  if (lo > 0 && Math.abs(a[lo-1] - t) <= Math.abs(a[lo] - t)) lo = lo - 1;
  return lo;
}
function xSai(t){
  var a = D.t, d = (a[a.length-1] - a[0]) || 1;
  return P.l + (t - a[0]) / d * (W - P.l - P.r);
}
function ySai(v){
  var toi = Math.max(1, D.max_nguoi, D.max_vung);
  return (H - P.b) - v / (toi * 1.15) * (H - P.t - P.b);
}
function khuong(){
  ctx.strokeStyle = '#24324d'; ctx.lineWidth = 1;
  ctx.fillStyle = '#93a4c4'; ctx.font = '11px "Segoe UI",Tahoma,sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  var so = 6, a = D.t, dau = a[0], cuoi = a[a.length-1];
  for (var i = 0; i <= so; i++){
    var t = dau + (cuoi - dau) * i / so, x = Math.round(xSai(t)) + 0.5;
    ctx.beginPath(); ctx.moveTo(x, P.t); ctx.lineTo(x, H - P.b); ctx.stroke();
    ctx.fillText(D.hms ? hhmm(t) : t.toFixed(0), x, H - P.b + 6);
  }
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  var toi = Math.max(1, D.max_nguoi, D.max_vung);
  var buoc = toi <= 5 ? 1 : (toi <= 12 ? 2 : Math.ceil(toi / 5));
  for (var v = 0; v <= toi; v += buoc){
    var y = Math.round(ySai(v)) + 0.5;
    ctx.beginPath(); ctx.moveTo(P.l, y); ctx.lineTo(W - P.r, y); ctx.stroke();
    ctx.fillText(String(v), P.l - 8, y);
  }
}
function hhmm(t){
  var n = Math.round(t), g = Math.floor(n / 3600), p = Math.floor((n % 3600) / 60), s = n % 60;
  var p2 = (p < 10 ? '0' : '') + p, s2 = (s < 10 ? '0' : '') + s;
  return g ? (g + ':' + p2 + ':' + s2) : (p2 + ':' + s2);
}
function ve(){
  ctx.clearRect(0, 0, W, H);
  khuong();
  var n = D.t.length, buoc = Math.max(1, Math.ceil(n / 2200));
  // vung nen duoi duong so nguoi
  ctx.beginPath(); ctx.moveTo(xSai(D.t[0]), H - P.b);
  for (var i = 0; i < n; i += buoc) ctx.lineTo(xSai(D.t[i]), ySai(D.nguoi[i]));
  ctx.lineTo(xSai(D.t[n-1]), ySai(D.nguoi[n-1]));
  ctx.lineTo(xSai(D.t[n-1]), H - P.b); ctx.closePath();
  ctx.fillStyle = 'rgba(76,201,240,0.13)'; ctx.fill();
  ctx.beginPath();
  for (var j = 0; j < n; j += buoc){
    var x = xSai(D.t[j]), y = ySai(D.nguoi[j]);
    if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = '#4cc9f0'; ctx.lineWidth = 2; ctx.stroke();
  // vach vi pham (theo chieu rong cua video)
  ctx.fillStyle = 'rgba(255,90,106,0.62)';
  var w = Math.max(1, (W - P.l - P.r) / Math.max(1, n));
  for (var a2 = 0; a2 < n; a2++) if (D.vi[a2]) ctx.fillRect(xSai(D.t[a2]) - w/2, H - P.b - 4, Math.max(1, w), 4);
  // cham dung lau
  ctx.fillStyle = '#ff9f43';
  for (var b2 = 0; b2 < n; b2++) if (D.lau[b2]){
    ctx.beginPath(); ctx.arc(xSai(D.t[b2]), ySai(D.nguoi[b2]), 4, 0, 6.284); ctx.fill();
  }
  // dinh diem nhieu nhat nhat
  if (diemDinhKy >= 0 && diemDinhKy < n){
    var xd = xSai(D.t[diemDinhKy]), yd = ySai(D.nguoi[diemDinhKy]);
    ctx.strokeStyle = '#6ee7a8'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(xd, yd, 7, 0, 6.284); ctx.stroke();
    ctx.fillStyle = '#6ee7a8'; ctx.font = 'bold 12px "Segoe UI",Tahoma,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.fillText('Dinh ' + D.nguoi[diemDinhKy] + ' nguoi', xd, yd - 9);
  }
  if (hover >= 0 && hover < n){
    var xh = xSai(D.t[hover]);
    ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(xh, P.t); ctx.lineTo(xh, H - P.b); ctx.stroke();
    var txt = hhmm(D.t[hover]) + '  |  ' + D.nguoi[hover] + ' nguoi';
    ctx.font = '12px "Segoe UI",Tahoma,sans-serif';
    var wtxt = ctx.measureText(txt).width + 14;
    var bx = Math.min(Math.max(xh - wtxt/2, P.l), W - P.r - wtxt);
    ctx.fillStyle = 'rgba(20,30,50,0.95)';
    ctx.fillRect(bx, 2, wtxt, 20);
    ctx.fillStyle = '#e8eefc'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.fillText(txt, bx + 7, 12);
  }
}
function resize(){
  var dpr = window.devicePixelRatio || 1;
  W = Math.max(360, cv.parentElement.clientWidth - 28);
  H = 340;
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ve();
}
function nhay(i){
  if (i < 0 || i >= D.t.length) return;
  hover = i; ve();
  var giay = D.t[i];
  document.getElementById('trangthai').textContent =
    'Da chon giay ' + hhmm(giay) + ' (' + giay.toFixed(2) + 's) - khung hinh thu ' +
    (i + 1) + ' - ' + D.nguoi[i] + ' nguoi.';
  if (D.video){
    try { vid.currentTime = giay; } catch(e){}
  } else {
    document.getElementById('ghiChu').textContent =
      'Chua gan video nen chi chon duoc thoi diem, khong xem duoc. ' +
      'Chay lai voi --video <ten>_ket_qua.mp4 de xem video trong trang nay.';
  }
  vid.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
cv.addEventListener('mousemove', function(e){
  var r = cv.getBoundingClientRect();
  var x = e.clientX - r.left;
  if (x < P.l - 4 || x > W - P.r + 4){ if (hover !== -1){ hover = -1; ve(); } return; }
  var a = D.t, d = (a[a.length-1] - a[0]) || 1;
  var i = canBang(a[0] + (x - P.l) / (W - P.l - P.r) * d);
  if (i !== hover){ hover = i; ve(); }
});
cv.addEventListener('mouseleave', function(){ hover = -1; ve(); });
cv.addEventListener('click', function(){ nhay(hover < 0 ? diemDinhKy : hover); });
document.getElementById('btnDinhKy').addEventListener('click', function(){
  nhay(diemDinhKy);
});
document.getElementById('btnVeDau').addEventListener('click', function(){
  if (D.video){ try { vid.currentTime = 0; vid.play(); } catch(e){} }
});
document.getElementById('btnPhat').addEventListener('click', function(){
  if (!D.video) return;
  if (vid.paused){ vid.play(); } else { vid.pause(); }
});
document.getElementById('btnPhat').addEventListener('click', function(){
  this.innerHTML = vid.paused ? '&#9654; Phat video' : '&#10073;&#10073; Dung video';
});
vid.addEventListener('play', function(){ document.getElementById('btnPhat').innerHTML = '&#10073;&#10073; Dung video'; });
vid.addEventListener('pause', function(){ document.getElementById('btnPhat').innerHTML = '&#9654; Phat video'; });

(function(){
  var the = document.getElementById('the');
  D.the.forEach(function(o){
    var d = document.createElement('div'); d.className = 'o';
    d.innerHTML = '<div class="n"></div><div class="v"></div><div class="d"></div>';
    d.querySelector('.n').textContent = o.n;
    var v = d.querySelector('.v'); v.textContent = o.v;
    if (o.mau) v.classList.add(o.mau);
    d.querySelector('.d').textContent = o.d || '';
    the.appendChild(d);
  });
  var ds = document.getElementById('dsSuKien');
  document.getElementById('soSuKien').textContent = D.su_kien.length;
  if (!D.su_kien.length){
    var li = document.createElement('li');
    li.innerHTML = '<button type="button" disabled>Video nao khong co su kien dang chu y.</button>';
    ds.appendChild(li);
  }
  D.su_kien.forEach(function(s, k){
    var li = document.createElement('li');
    li.className = s.loai === 'vuot_nguong' ? 'vuot' : (s.loai === 'dung_lau' ? 'lau' : '');
    var b = document.createElement('button'); b.type = 'button';
    b.innerHTML = '<span class="g"></span> <span class="m"></span><br><span class="t"></span>';
    b.querySelector('.g').textContent = hhmm(s.giay);
    b.querySelector('.m').textContent = s.nhan;
    b.querySelector('.t').textContent = 'giay thu ' + s.thu_tu + ' - ' + s.mo_ta;
    b.addEventListener('click', function(){ nhay(s.thu_tu - 1); });
    li.appendChild(b); ds.appendChild(li);
  });
  document.getElementById('ghiChu').innerHTML = D.ghi_chu;
  window.addEventListener('resize', resize);
  resize();
})();
</script>
</body>
</html>
"""


def tao_html(tk, dong, su_kien_list, ten_file, duong_dan_html, duong_dan_video):
    """Sinh trang xem lai HTML tu chua (khong dung tai nguyen Internet nao)."""
    from datetime import datetime

    dinh_ky = tk["dinh_ky"]
    the = [
        {"n": "Khung hinh da phan tich", "v": "{:,}".format(tk["so_khung"]).replace(",", "."),
         "d": "video dai " + _hms(tk["thoi_luong"]), "mau": None},
        {"n": "Giay dong nhat", "v": _hms(dinh_ky["giay"]),
         "d": "%d nguoi - khung thu %d" % (dinh_ky["so_nguoi"], dinh_ky["thu_tu"]),
         "mau": "vang"},
        {"n": "TB so nguoi", "v": _loai_bo_gia(tk["tb_nguoi"]),
         "d": "max %d / min %d" % (tk["max_nguoi"], tk["min_nguoi"]), "mau": "xanh"},
        {"n": "So lan co nguoi vao vung", "v": str(len(tk["lan_vao_vung"])),
         "d": "%d khung hinh" % tk["khung_vi_pham"], "mau": "vang"},
        {"n": "Vuot nguong %d nguoi" % tk["nguong_dong"], "v": str(len(tk["lan_vuot"])),
         "d": "lan vuot nguong trong vung", "mau": "do"},
        {"n": "So lan dung lau", "v": str(len(tk["lan_dung_lau"])),
         "d": "co nguoi o lai lau trong vung", "mau": "cam"},
        {"n": "Nguoi quen", "v": str(len(tk["nguoi_quen"])),
         "d": ", ".join(q["ten"] for q in tk["nguoi_quen"]) or "khong co",
         "mau": None},
    ]

    co_video = bool(duong_dan_video and os.path.isfile(duong_dan_video))
    if co_video:
        try:
            tuong_doi = os.path.relpath(
                os.path.abspath(duong_dan_video),
                os.path.abspath(os.path.dirname(duong_dan_html)),
            )
        except ValueError:
            tuong_doi = None
        if tuong_doi:
            src_attr = 'src="%s"' % urllib.parse.quote(
                tuong_doi.replace("\\", "/"), safe="/.-_~()"
            )
        else:
            # khac o dia: dung duong dan tuyet doi co scheme tep
            src_attr = 'src="file:///%s"' % urllib.parse.quote(
                os.path.abspath(duong_dan_video).replace("\\", "/"), safe="/.-_~()"
            )
    else:
        src_attr = ""

    su_kien_htm = [{
        "giay": round(s["giay"], 2),
        "thu_tu": s["thu_tu"],
        "loai": s["loai"],
        "nhan": {"vao_vung": "Co nguoi vao vung canh",
                 "vuot_nguong": "Vuot nguong nguoi trong vung",
                 "dung_lau": "Co nguoi dung lau trong vung"}[s["loai"]],
        "mo_ta": s["mo_ta"],
    } for s in su_kien_list[:TOI_DA_DONG_HTML]]

    ghi_chu = (
        "Duong dan video: <b>%s</b>. File HTML nay tu chua hoan toan, khong can Internet. "
        "Nhan giu video lai cung thu muc voi file HTML nay de no mo duoc video."
        % os.path.basename(duong_dan_video) if co_video else
        "Ban chua truyen --video nen trang nay khong co player. "
        "Chay lai: python bao_cao_tong_ket.py --csv &lt;ten&gt;.csv "
        "--video &lt;ten&gt;_ket_qua.mp4 --xuat &lt;thu muc&gt;"
    )
    if tk["nguong_tu_dong"]:
        ghi_chu += (" | Nguong dong lay tu dong = %d nguoi (so nguoi nhieu nhat trong vung); "
                    "neu anh dat nguong khac khi chay CamAI, hay chay lai voi --nguong-dong."
                    % tk["nguong_dong"])

    du_lieu = {
        "video": co_video,
        "t": [round(r["giay"], 2) for r in dong],
        "nguoi": [r["so_nguoi"] for r in dong],
        "vi": [r["vi_pham"] for r in dong],
        "lau": [r["canh_lau"] for r in dong],
        "max_nguoi": tk["max_nguoi"],
        "max_vung": tk["max_trong_vung"],
        "dinh_ky": {"giay": round(dinh_ky["giay"], 2), "thu_tu": dinh_ky["thu_tu"],
                    "so_nguoi": dinh_ky["so_nguoi"]},
        "the": the,
        "su_kien": su_kien_htm,
        "ghi_chu": ghi_chu,
    }

    html = MAU_HTML
    html = html.replace("__TIEU_DE__", _chuan_hoa_ten(ten_file, "_bao_cao.csv"))
    html = html.replace("__TONG_DON__", (
        "%d khung hinh &middot; %s giay &middot; %d su kien dang chu y &middot; "
        "tao luc %s"
        % (tk["so_khung"], _hms(tk["thoi_luong"]), len(su_kien_htm),
           datetime.now().strftime("%d/%m/%Y %H:%M"))
    ))
    html = html.replace("__SRC__", src_attr)
    html = html.replace(
        "__DU_LIEU__",
        json.dumps(du_lieu, ensure_ascii=False).replace("</", "<\\/"),
    )

    try:
        with open(duong_dan_html, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
    except PermissionError:
        raise BaoCaoLoi(
            "Khong ghi duoc file HTML (file dang duoc mo?):\n  %s" % duong_dan_html
        )
    return duong_dan_html


# ----------------------------------------------------------------- console

def _in_tong_ket(tk, hang_gom, theo_phut):
    d = tk["dinh_ky"]
    print("")
    print("=" * 68)
    print("  TONG KET CAMAI")
    print("=" * 68)
    print("  Tong so khung hinh da phan tich : %s"
          % "{:,}".format(tk["so_khung"]).replace(",", "."))
    print("  Do dai video                    : %s (%.2f giay, ~%.1f fps)"
          % (_hms(tk["thoi_luong"]), tk["thoi_luong"], tk["fps"]))
    print("  GIAY DONG NHAT                  : %s - co %d nguoi (khung hinh thu %d)"
          % (_hms(d["giay"]), d["so_nguoi"], d["thu_tu"]))
    print("  So nguoi nhieu nhat trong vung  : %d nguoi (luc %s)"
          % (tk["max_trong_vung"], _hms(tk["dinh_ky_vung"]["giay"])))
    print("  TB / lon nhat / nho nhat nguoi  : %s / %d / %d"
          % (_loai_bo_gia(tk["tb_nguoi"]), tk["max_nguoi"], tk["min_nguoi"]))
    print("-" * 68)
    if tk["nguoi_quen"]:
        for q in tk["nguoi_quen"]:
            tuoi = "%.1f" % q["tuoi_tb"] if q["tuoi_tb"] is not None else "khong do duoc"
            print("  Nguoi quen: %-12s | xuat hien %d khung hinh | tuoi TB %s | %d nam / %d nu"
                  % (q["ten"], q["khung"], tuoi, q["nam"], q["nu"]))
    else:
        print("  Nguoi quen: khong co (video nay khong nhan dien duoc người quen)")
    print("-" * 68)
    print("  So LAN co nguoi vao vung canh    : %d lan (%d khung hinh)"
          % (len(tk["lan_vao_vung"]), tk["khung_vi_pham"]))
    nguong_txt = "%d nguoi" % tk["nguong_dong"]
    if tk["nguong_tu_dong"]:
        nguong_txt += " [tu dong]"
    print("  So LAN vuot nguong dong           : %d lan (nguong %s)"
          % (len(tk["lan_vuot"]), nguong_txt))
    print("  So LAN co nguoi dung lau         : %d lan (%d khung hinh)"
          % (len(tk["lan_dung_lau"]), tk["khung_canh_lau"]))
    if tk["lan_dung_lau"]:
        print("  Thoi diem bi gan nho 'dung lau'   : %s"
              % ", ".join(_hms(l["bat_dau"]["giay"]) for l in tk["lan_dung_lau"]))
    print("-" * 68)
    cach = "theo PHUT (60 giay)" if theo_phut else "theo GIO (3600 giay)"
    print("  Sheet '%s'       : %d nhom, gom %s"
          % (SHEET_THEO_GIO, len(hang_gom), cach))
    print("  Sheet '%s': tung giay, de anh tu ve do thi"
          % SHEET_CU_THEO_GIAY)
    print("=" * 68)


# ----------------------------------------------------------------- chay

def _chuan_hoa_console():
    """Windows console hay dung cp1252 -> hay ep UTF-8 de khong loi tieng Viet."""
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def chay(argv=None):
    _chuan_hoa_console()

    ctl = argparse.ArgumentParser(
        prog="bao_cao_tong_ket.py",
        description="Tao file Excel tong ket + trang xem lai HTML tu CSV cua CamAI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ctl.add_argument("--csv", required=True, metavar="DUONG_DAN",
                     help="File CSV do CamAI xuat (bat buoc).")
    ctl.add_argument("--video", default=None, metavar="DUONG_DAN",
                     help="File mp4 ket qua (tuong chon) - de xem lai trong HTML.")
    ctl.add_argument("--xuat", default=None, metavar="THU_MUC",
                     help="Thu muc ghi ket qua. Mac dinh: cung thu muc voi CSV.")
    ctl.add_argument("--nguong-dong", type=int, default=None, metavar="N",
                     help="Nguoi toi da trong vung. Mac dinh lay so nguoi nhieu nhat "
                          "quan sat duoc trong vung.")
    args = ctl.parse_args(argv)

    duong_csv = os.path.abspath(args.csv)
    if args.xuat:
        thu_muc = os.path.abspath(args.xuat)
    else:
        thu_muc = os.path.dirname(duong_csv) or "."

    if not os.path.isdir(thu_muc):
        try:
            os.makedirs(thu_muc, exist_ok=True)
        except OSError as loi:
            raise BaoCaoLoi("Khong tao duoc thu muc '%s': %s" % (thu_muc, loi))

    duong_video = None
    if args.video:
        duong_video = os.path.abspath(args.video)
        if not os.path.isfile(duong_video):
            print("CANH BAO: Khong tim thay file video: %s" % duong_video)
            print("         Trang HTML van duoc tao, nhung se khong co video.")
            duong_video = None

    dong, canh_bao = doc_csv(duong_csv)

    if args.nguong_dong is not None and args.nguong_dong < 0:
        raise BaoCaoLoi("Nguong dong khong duoc am. Nhap: --nguong-dong 5")

    tk = tong_ket(dong, args.nguong_dong)
    hang_gom, theo_phut = gom_nhom(dong, tk["thoi_luong"])
    hang_giay, buoc = gom_theo_giay(dong)
    su_kien_list = su_kien(tk, dong)

    ten = _chuan_hoa_ten(duong_csv, "_bao_cao.csv")
    duong_xlsx = os.path.join(thu_muc, "%s_tong_ket.xlsx" % ten)
    duong_html = os.path.join(thu_muc, "%s_xem_lai.html" % ten)

    from datetime import datetime
    tao_xlsx(tk, hang_gom, theo_phut, hang_giay, buoc, os.path.basename(duong_csv),
             duong_xlsx, thoi_dan_id=datetime.now().strftime("%d/%m/%Y %H:%M"))
    tao_html(tk, dong, su_kien_list, duong_csv, duong_html, duong_video)

    print("CamAI - Bao cao tong ket (phien ban %s)" % PHIEN_BAN)
    print("-" * 68)
    print("  File CSV da doc : %s" % duong_csv)
    print("  So dong du lieu : %d" % len(dong))
    for c in canh_bao:
        print("  Luu y          : %s" % c)
    print("")
    _in_tong_ket(tk, hang_gom, theo_phut)
    print("  DA TAO FILE EXCEL :")
    print("     %s" % duong_xlsx)
    print("     (%d sheet: %s)"
          % (3, ", ".join([SHEET_TONG_KET, SHEET_THEO_GIO, SHEET_CU_THEO_GIAY])))
    print("  DA TAO TRANG XEM LAI (mo bang trinh duyet):")
    print("     %s" % duong_html)
    if duong_video:
        print("     Video lay theo duong dan tuong doi: %s"
              % os.path.basename(duong_video))
    print("")
    return 0


def main(argv=None):
    try:
        return chay(argv)
    except BaoCaoLoi as loi:
        print("")
        print("=" * 68)
        print("  LOI: %s" % loi)
        print("=" * 68)
        return 1
    except KeyboardInterrupt:
        print("\nDa dung theo yeu cau nguoi dung.")
        return 130


if __name__ == "__main__":
    sys.exit(main())