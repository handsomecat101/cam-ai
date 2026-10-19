"""
CamAI - tu chup anh khi co su kien (vuot nguong dong / thay nguoi quen / vuot vung).

KHONG gui gi ra ngoai. Anh chi ghi xuong dia may.

Dung truc tiep:
    from tu_chup import TuChupAnh

    chup = TuChupAnh("anh_su_kien", nhoan_lai_giay=10.0)
    if chup.co_the_chup("vuot_nguong_dong"):
        duong = chup.chup(anh_bgr, "vuot_nguong_dong", so_nguoi=12)
    chup.dong()      # ghi CSV bang ke + dong file

Dieu kien chup (trong cam_ai_core.run_analysis):
- co nguoi vuot nguong dong trong vung canh   -> LY_DO_VUOT_DONG
- phat hien nguoi quen trong khung hinh     -> LY_DO_NGUOI_QUEN
- co nguoi vao vung canh                     -> LY_DO_VAO_VUNG
- co nguoi dung lau trong vung              -> LY_DO_DUNG_LAU

CHONG SPAM: moi loai su kien chi chup 1 lan trong `nhoan_lai_giay`
(mac dinh 10 giay). Khong chup lai lien tuc trong cung 1 su kien.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Callable

import cv2
import numpy as np

__all__ = ["TuChupAnh", "LOAI_SU_KIEN", "CSV_BANG_KE", "NHAN_LAI_MAC_DINH_GIAY"]

NHAN_LAI_MAC_DINH_GIAY = 10.0

# Chuoi su kien (trung voi LY_DO_* cua cam_ai_core.py) -> nhan tieng Viet de hien
# thi. Ma goc van duoc ghi vao CSV de doi chieu.
LOAI_SU_KIEN = {
    "vuot_nguong_dong": "Vượt ngưỡng đông",
    "nguoi_quen": "Phát hiện người quen",
    "vao_vung": "Có người vào vùng canh",
    "dung_lau": "Có người đứng lâu",
    "co_nguoi": "Có người trong khung hình",
    "bien_so": "Phát hiện biển số",
}

# Cot CSV bang ke (thu muc cua file CSV cung la thu muc luu anh)
CSV_BANG_KE = ["duong_dan", "thoi_diem", "loai_su_kien", "ten_hien_thi",
               "so_nguoi", "giay_trong_video"]


class TuChupAnh:
    """Tu chup 1 khung hinh khi co su kien, chong spam bang lich tuyet doi.

    Ten file: su_kien_<yyyyMMdd_HHMMSS>_<loai>_<so nguoi>.jpg
    Bang ke CSV: <thu muc>/_bang_ke_chup.csv (ghi khi dong() hoac dung gi).
    """

    def __init__(
        self,
        thu_muc: str,
        nhoan_lai_giay: float = NHAN_LAI_MAC_DINH_GIAY,
        chat_luong_jpg: int = 92,
        log: Callable[[str], None] | None = None,
        ghi_bang_ke: bool = True,
    ):
        self.thu_muc = thu_muc or ""
        self.nhoan_lai_giay = max(0.0, float(nhoan_lai_giay))
        self.chat_luong_jpg = int(chat_luong_jpg)
        self.log = log or (lambda _dong: None)
        self.ghi_bang_ke = bool(ghi_bang_ke)
        self.lan_cuoi: dict[str, float] = {}      # loai su kien -> giay vua chup
        self.ket_qua: list[dict] = []             # mot dong moi lan chup
        self.duong_dan_csv = ""

    # ------------------------------------------------------------------ chot
    def co_the_chup(self, loai_su_kien: str) -> bool:
        """True neu duoc phep chup su kien nay (khong trong thoi gian nhoan lai)."""
        if not self.thu_muc:
            return False
        import time

        lan_cuoi = self.lan_cuoi.get(loai_su_kien)
        if lan_cuoi is None:
            return True
        return (time.monotonic() - lan_cuoi) >= self.nhoan_lai_giay

    def chup(
        self,
        anh_bgr,
        loai_su_kien: str,
        so_nguoi: int = 0,
        giay_trong_video: float = 0.0,
    ) -> str | None:
        """Chup 1 khung hinh. Tra duong dan file da luu, None neu khong chup."""
        if not self.co_the_chup(loai_su_kien):
            return None
        if anh_bgr is None or not hasattr(anh_bgr, "shape") or anh_bgr.size == 0:
            return None
        import time

        now_wall = datetime.now()
        nhan = now_wall.strftime("%Y%m%d_%H%M%S")
        ten = f"su_kien_{nhan}_{loai_su_kien}_nguoi{so_nguoi}.jpg"
        try:
            os.makedirs(self.thu_muc, exist_ok=True)
            duong = os.path.join(self.thu_muc, ten)
            if os.path.exists(duong):            # trung 1 giay -> them _1, _2
                k = 1
                while os.path.exists(os.path.join(
                        self.thu_muc, f"su_kien_{nhan}_{loai_su_kien}_nguoi{so_nguoi}_{k}.jpg")):
                    k += 1
                duong = os.path.join(
                    self.thu_muc, f"su_kien_{nhan}_{loai_su_kien}_nguoi{so_nguoi}_{k}.jpg")
            if not cv2.imwrite(duong, anh_bgr,
                               [int(cv2.IMWRITE_JPEG_QUALITY), self.chat_luong_jpg]):
                return None
        except Exception as exc:                            # noqa: BLE001
            self.log(f"[tu chup] KHONG ghi duoc anh ({type(exc).__name__}: {exc})")
            return None

        self.lan_cuoi[loai_su_kien] = time.monotonic()
        dong = {
            "duong_dan": duong,
            "thoi_diem": now_wall.strftime("%Y-%m-%d %H:%M:%S"),
            "loai_su_kien": loai_su_kien,
            "ten_hien_thi": LOAI_SU_KIEN.get(loai_su_kien, loai_su_kien),
            "so_nguoi": int(so_nguoi),
            "giay_trong_video": round(float(giay_trong_video), 2),
        }
        self.ket_qua.append(dong)
        return duong

    # -------------------------------------------------------------- bang ke
    def ghi_csv(self) -> str:
        """Ghi CSV bang ke cac lan chup. Tra duong dan file (rong = khong co)."""
        if not self.ghi_bang_ke or not self.thu_muc:
            return ""
        try:
            os.makedirs(self.thu_muc, exist_ok=True)
            duong = os.path.join(self.thu_muc, "_bang_ke_chup.csv")
            co_moi = os.path.exists(duong)
            with open(duong, "a", newline="", encoding="utf-8-sig") as f:
                ghi = csv.DictWriter(f, fieldnames=CSV_BANG_KE)
                if not co_moi:
                    ghi.writeheader()
                ghi.writerows(self.ket_qua)
            self.duong_dan_csv = duong
            return duong
        except Exception as exc:                            # noqa: BLE001
            self.log(f"[tu chup] KHONG ghi duoc CSV bang ke ({type(exc).__name__}: {exc})")
            return ""

    def dong(self) -> None:
        """Ket thuc: ghi CSV bang ke (goi khi chay xong video hoac dung)."""
        if self.ket_qua:
            duong = self.ghi_csv()
            if duong:
                self.log(
                    f"[tu chup] Da chup {len(self.ket_qua)} anh | bang ke: {duong}"
                )