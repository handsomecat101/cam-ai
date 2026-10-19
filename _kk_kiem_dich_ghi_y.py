# -*- coding: utf-8 -*-
"""Coordinator: kiem moi chuoi `_ghi_y(...)` co ban dich Anh khop.

Dung AST de lay nguyen van ban chuoi trong moi lenh `self._ghi_y(...)`,
roi doi tung chuoi qua ham dich cua gui.py. Chuoi nao khong doi (van la
tieng Viet) thi bi bao loi.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_kiem_dich_ghi_y.py
"""
from __future__ import annotations

import ast
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import gui  # noqa: E402

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DUONG = os.path.join(APP_DIR, "gui.py")


def chuoi_tu_bien_thuc(node):
    """Gop cac string literal lien tiep thanh 1 chuoi."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for p in node.values:
            if isinstance(p, ast.Constant) and isinstance(p.value, str):
                out.append(p.value)
            else:
                return None
        return "".join(out)
    return None


def lay_chuoi_ghi_y():
    with open(DUONG, "r", encoding="utf-8") as f:
        cay = ast.parse(f.read(), filename=DUONG)
    ket = []
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Call):
            continue
        ten = ""
        if isinstance(nut.func, ast.Attribute):
            ten = nut.func.attr
        elif isinstance(nut.func, ast.Name):
            ten = nut.func.id
        if ten != "_ghi_y" or len(nut.args) < 2:
            continue
        s = chuoi_tu_bien_thuc(nut.args[1])
        if s is None:
            continue
        ket.append((nut.lineno, s))
    return sorted(ket)


def main() -> int:
    ds = lay_chuoi_ghi_y()
    loi = []
    for dong, s in ds:
        d = gui.dich(s, "en")
        if d is None:
            loi.append((dong, s, "khong co ham dich"))
            continue
        if d == s:
            loi.append((dong, s, "CHUA CO BAN DICH ANH"))
    print(f"so chuoi _ghi_y   = {len(ds)}")
    print(f"chuoi chua dich   = {len(loi)}")
    for dong, s, nguyennhan in loi:
        print(f"  [LOI] dong {dong}: {nguyennhan}")
        print(f"         {s[:100]}")
    # Kiem tra nguoc: khoa trong DICH_VI_EN khong dung o dau
    dung = {s for _, s in ds}
    thua = [k for k in gui.DICH_VI_EN if k not in dung]
    print(f"\nkhoa DICH_VI_EN khong khop voi _ghi_y nao = {len(thua)}")
    for k in thua:
        print(f"  - {k[:90]}")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
