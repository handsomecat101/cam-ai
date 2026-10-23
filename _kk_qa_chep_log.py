# -*- coding: utf-8 -*-
"""Tao ban tho gop cho _kk_out/qa/ tu cac log trong %TEMP%/camai_qa.

Che MAT KHAU (chuoi sinh ngau nhien cua app) de khong lam sai script
_kk_kiem_app_qt.py (script do quet thu muc du an tim mat khau).

Chay:
    .venv\\Scripts\\python.exe _kk_qa_chep_log.py
"""

from __future__ import annotations

import os
import re

TMP = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "camai_qa")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_kk_out", "qa")

# Cac mau can che: mat khau tu sinh, dong "MAT-KHAU-TU-SINH: xxx",
# va khoa truy cap (?k=...).
MAU = [
    (re.compile(r"(MAT-KHAU-TU-SINH:\s*)(\S+)"), r"\1<MAT-KHAU-DA-CHE>"),
    (re.compile(r"(CAMAI_PASSWORD trong moi truong:\s*)(\S+)"),
     r"\1<MAT-KHAU-DA-CHE>"),
    (re.compile(r"(\?k=)([A-Za-z0-9_\-]{16,})"), r"\1<KHOA-DA-CHE>"),
    (re.compile(r"(camai_phien=)([A-Za-z0-9_\-]{16,})"), r"\1<PHIEN-DA-CHE>"),
]

# Cac file log can gop lai.
TEN = [
    ("qa_3_yeu_cau.log", "qa_3_yeu_cau.log"),
    ("qa_worker.log", "qa_worker_favicon.log"),
    ("qa_badge.log", "qa_badge_chap.log"),
    ("khong_mat.log", "qa_khong_mat_tinh_nang.log"),
    ("bit_exact_2.log", "qa_bit_exact_200_200.log"),
    ("app_qt_clean.log", "qa_app_qt_clean.log"),
    ("web_server_final.log", "qa_web_server_chay_lai_cuoi.log"),
    ("ui_web_final.log", "qa_ui_web_chay_lai_cuoi.log"),
]

# Log cu (da nam trong thu muc du an) -> che tai cho tai.
CHEP_TAI = [
    (os.path.join(OUT, "bo_kiem_chay_1.log"), "bo_kiem_chay_1.log"),
]


def _che_mat_khau_dung_mot_dong(noi_dung: str) -> str:
    """App in mat khau o dang 2 dong:

        [app]   CAMAI: mat khau TAM SINH cho lan chay nay:
        [app]       8%WtQg5?Dr

    => dong thu 2 (chi toan ky tu) duoc che lai.
    """
    dong = noi_dung.split("\n")
    for i, d in enumerate(dong):
        if ("mat khau TAM SINH" in d or "MAT-KHAU-TU-SINH" in d
                or "mat khau TAM SINH cho lan chay nay" in d.lower()):
            if i + 1 < len(dong):
                # Dong tiep theo dang "   [app]       <mat-khau>" -> che token
                # CUOI cùng (mat khau), giu lai tien to "[app]".
                dong[i + 1] = re.sub(r"(\S+)(\s*)$",
                                      lambda m: "<MAT-KHAU-DA-CHE>" + m.group(2),
                                      dong[i + 1])
    return "\n".join(dong)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for nguon, dich in TEN:
        duong_nguon = os.path.join(TMP, nguon)
        if not os.path.isfile(duong_nguon):
            print("BO QUA (khong co): %s" % nguon)
            continue
        with open(duong_nguon, "r", encoding="utf-8", errors="replace") as f:
            noi_dung = f.read()
        for mau, thay in MAU:
            noi_dung = mau.sub(thay, noi_dung)
        noi_dung = _che_mat_khau_dung_mot_dong(noi_dung)
        duong_dich = os.path.join(OUT, dich)
        with open(duong_dich, "w", encoding="utf-8", newline="\n") as f:
            f.write(noi_dung)
        print("DA CHE: %s -> %s (%d byte)" % (nguon, dich,
                                              os.path.getsize(duong_dich)))
    for duong_nguon, dich in CHEP_TAI:
        if not os.path.isfile(duong_nguon):
            print("BO QUA (khong co): %s" % duong_nguon)
            continue
        with open(duong_nguon, "r", encoding="utf-8", errors="replace") as f:
            noi_dung = f.read()
        for mau, thay in MAU:
            noi_dung = mau.sub(thay, noi_dung)
        noi_dung = _che_mat_khau_dung_mot_dong(noi_dung)
        with open(duong_nguon, "w", encoding="utf-8", newline="\n") as f:
            f.write(noi_dung)
        print("DA CHE TAI CHO: %s (%d byte)" % (duong_nguon,
                                                os.path.getsize(duong_nguon)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
