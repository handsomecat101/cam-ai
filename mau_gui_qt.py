# -*- coding: utf-8 -*-
"""Mau giao dien moi CamAI bang PySide6 - BAN MAU TINH de anh duyet.

Muc dich: anh chu du an XEM TRUOC bo cuc + dien mao de duyet huong thiet ke.
KHONG noi vao pipeline CV, KHONG detect, KHONG chay model. Chi la mau tinh.

Chay:
    .venv\\Scripts\\python.exe mau_gui_qt.py
Chay kem topmost (cho chup anh):
    .venv\\Scripts\\python.exe mau_gui_qt.py --topmost
"""

from __future__ import annotations

import json
import os
import sys

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ----------------------------------------------------------------- MAU SAC
#
# 1 dict MAU la nguon su that cho toan bo mau trong file nay.
MAU = {
    "nen": "#16181D",       # nen cua so
    "panel": "#1E2128",    # the / panel
    "panel_2": "#252932",  # o nhap, hang the
    "vien": "#31353F",     # vien 1px
    "chinh": "#E9EAEE",    # chu chinh
    "phu": "#9AA0AC",      # chu phu
    "accent": "#4C8DFF",   # nut chinh, so lon
    "accent_2": "#2A3A55", # nen nut accent phu
    "ok": "#3FB950",       # trang thai tot
    "canh": "#E3B341",     # canh bao
    "loi": "#F85149",      # loi
    "nen_video": "#0E1014",  # nen khung video
}

# ------------------------------------------------------------------- FONT
#
# Chi dung font co san tren Windows (app chay 100% offline).
FONT_CHU = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"
FONT_MONO = "Cascadia Mono"
FONT_KY_TU = "Segoe UI Symbol"      # cho chevron

# Icon nut (play / pause) KHONG ve bang emoji - ve bang QPainter trong file.
# Xem ham `_bieu_pixmap`.

# --------------------------------------------------------------- KHOANG CACH
#
# Luoi 8 / 12 / 16 / 24 - moi vai tro LUON dung dung mot gia tri.
C_8, C_12, C_16, C_24 = 8, 12, 16, 24
COT_TRAI = 300
COT_PHAI = 300
CAO_DAU = 60
CAO_THE_SO = 92
CAO_NHAT_KY = 180


def _qss() -> str:
    """Tra ve stylesheet cua toan bo app (khong dung style mac dinh cua Qt)."""
    return """
QWidget {
    color: %(chinh)s;
}

QWidget#nenChinh {
    background: %(nen)s;
}

QFrame#thanhDau {
    background: %(panel)s;
    border: none;
    border-bottom: 1px solid %(vien)s;
}

QLabel#tenApp {
    font-family: "%(semi)s";
    font-size: 20px;
    color: %(chinh)s;
}
QLabel#tenNhom {
    font-family: "%(semi)s";
    font-size: 13px;
    color: %(chinh)s;
}
QLabel#moTa {
    font-size: 11px;
    color: %(phu)s;
}
QLabel#chevron {
    font-family: "%(ky_tu)s";
    font-size: 13px;
    color: %(phu)s;
}
QLabel#nhanChung {
    font-size: 12px;
    color: %(phu)s;
}
QLabel#soLon {
    font-family: "%(chu)s";
    font-size: 26px;
    font-weight: 700;
}
QLabel#nhanSo {
    font-size: 11px;
    color: %(phu)s;
}
QLabel#tieuDeKhung {
    font-family: "%(semi)s";
    font-size: 13px;
    color: %(chinh)s;
}
QLabel#chuVideo {
    font-size: 13px;
    color: %(phu)s;
}
QLabel#eventTime {
    font-family: "%(mono)s";
    font-size: 11px;
    color: %(phu)s;
}
QLabel#eventDesc {
    font-size: 12px;
    color: %(chinh)s;
}
QLabel#logLine {
    font-family: "%(mono)s";
    font-size: 11px;
    color: %(phu)s;
}

QLabel#chip {
    background: %(panel_2)s;
    color: %(phu)s;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 11px;
}
QLabel#chipNho {
    background: %(panel_2)s;
    color: %(phu)s;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
}
QLabel#chipTrangThai {
    background: %(panel_2)s;
    color: %(ok)s;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}
QLabel#chipOk {
    background: rgba(63, 185, 80, 0.16);
    border: 1px solid rgba(63, 185, 80, 0.45);
    color: %(ok)s;
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
}

QPushButton {
    background: %(panel_2)s;
    color: %(chinh)s;
    border: 1px solid %(vien)s;
    border-radius: 8px;
    padding: 9px 14px;
    font-family: "%(semi)s";
    font-size: 13px;
}
QPushButton:hover {
    background: #2E3340;
    border-color: #454B58;
}
QPushButton:pressed {
    background: #20242C;
}
QPushButton#nutChinh {
    background: %(accent)s;
    color: #0B1220;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-family: "%(semi)s";
    font-size: 13px;
}
QPushButton#nutChinh:hover {
    background: #6BA1FF;
}
QPushButton#nutChinh:pressed {
    background: #3B7BEA;
}
QPushButton#nutNho {
    font-family: "%(chu)s";
    font-size: 12px;
    font-weight: 400;
    padding: 9px 10px;
}

QFrame#theAccordion {
    background: %(panel)s;
    border: 1px solid %(vien)s;
    border-radius: 10px;
}
QFrame#theSo {
    background: %(panel)s;
    border: 1px solid %(vien)s;
    border-radius: 10px;
}
QFrame#khungVideo {
    background: %(nen_video)s;
    border: 1px solid %(vien)s;
    border-radius: 10px;
}
QFrame#khungPanel {
    background: %(panel)s;
    border: 1px solid %(vien)s;
    border-radius: 10px;
}

QLineEdit {
    background: %(panel_2)s;
    border: 1px solid %(vien)s;
    border-radius: 8px;
    padding: 9px 11px;
    color: %(phu)s;
    font-size: 12px;
    selection-background-color: %(accent)s;
}
QLineEdit:focus {
    border-color: %(accent)s;
}

QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: %(vien)s;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #454B58;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    width: 0;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
""" % {
        "chinh": MAU["chinh"],
        "phu": MAU["phu"],
        "nen": MAU["nen"],
        "panel": MAU["panel"],
        "panel_2": MAU["panel_2"],
        "vien": MAU["vien"],
        "accent": MAU["accent"],
        "ok": MAU["ok"],
        "nen_video": MAU["nen_video"],
        "chu": FONT_CHU,
        "semi": FONT_SEMI,
        "mono": FONT_MONO,
        "ky_tu": FONT_KY_TU,
    }


def _bieu_pixmap(loai: str, mau_hex: str, co: int = 14) -> QPixmap:
    """Ve icon bang QPainter (KHONG dung emoji, KHONG phu thuoc font bieu tuong).

    `loai` = "phat" (tam giac) | "tam_dung" (hai thanh dung).
    """
    pm = QPixmap(co, co)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(mau_hex))
    if loai == "phat":
        w = co * 0.46
        h = co * 0.60
        x = (co - w) / 2 + w * 0.22
        y = (co - h) / 2
        p.drawPolygon(QPolygonF([
            QPointF(x, y),
            QPointF(x + w, y + h / 2),
            QPointF(x, y + h),
        ]))
    else:
        w = max(2, co * 0.15)
        h = co * 0.60
        y = (co - h) / 2
        x = (co - (w * 2 + w * 0.7)) / 2
        p.drawRoundedRect(QRectF(x, y, w, h), 1, 1)
        p.drawRoundedRect(QRectF(x + w * 1.7, y, w, h), 1, 1)
    p.end()
    return pm


# ------------------------------------------------------------------- WIDGET


class LogoTro(QWidget):
    """Logo tròn 30px ve bang QPainter (khop mau accent, khong phai anh PNG)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)

    def paintEvent(self, ev):                       # noqa: N802 - ten cua Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        g = QLinearGradient(0, 0, 30, 30)
        g.setColorAt(0.0, QColor("#6BA1FF"))
        g.setColorAt(1.0, QColor("#2A6BE0"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QRectF(1, 1, 28, 28))
        # vong kinh + dia cham = cam
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(1.6)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(7.5, 7.5, 15, 15))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(12.5, 12.5, 5, 5))
        p.end()


class CardAccordion(QFrame):
    """The accordion: tieu de + chevron + 1 dong mo ta + khoi noi dung (an/mo)."""

    def __init__(self, ten: str, mo_ta: str, mo: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("theAccordion")
        self._mo = bool(mo)

        v = QVBoxLayout(self)
        v.setContentsMargins(C_16, 14, C_16, C_16)
        v.setSpacing(6)

        self.chevron = QLabel("▾" if mo else "▸")
        self.chevron.setObjectName("chevron")
        self.chevron.setFixedWidth(14)
        self.chevron.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.tieude = QLabel(ten)
        self.tieude.setObjectName("tenNhom")

        tieu_de = QHBoxLayout()
        tieu_de.setContentsMargins(0, 0, 0, 0)
        tieu_de.setSpacing(6)
        tieu_de.addWidget(self.chevron)
        tieu_de.addWidget(self.tieude)
        tieu_de.addStretch(1)
        v.addLayout(tieu_de)

        self.mo_ta = QLabel(mo_ta)
        self.mo_ta.setObjectName("moTa")
        self.mo_ta.setContentsMargins(20, 0, 0, 0)
        self.mo_ta.setWordWrap(True)
        v.addWidget(self.mo_ta)

        self.noi_dung = QWidget()
        self.v_noi_dung = QVBoxLayout(self.noi_dung)
        self.v_noi_dung.setContentsMargins(0, C_8, 0, 0)
        self.v_noi_dung.setSpacing(C_8)
        v.addWidget(self.noi_dung)

        self._dat_mo(self._mo)

    def _dat_mo(self, mo: bool) -> None:
        self._mo = mo
        self.chevron.setText("▾" if mo else "▸")
        self.noi_dung.setVisible(mo)

    def doi_trang_thai(self) -> None:
        self._dat_mo(not self._mo)


class KhungVideo(QFrame):
    """Khung video ti le 16:9, bo goc 10px, vien 1px."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # QVBoxLayout chi dung heightForWidth khi size policy bat co flag nay.
        p = self.sizePolicy()
        p.setHeightForWidth(True)
        p.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(p)

    def hasHeightForWidth(self):                    # noqa: N802 - ten cua Qt
        return True

    def heightForWidth(self, w):                    # noqa: N802 - ten cua Qt
        return int(w * 9 / 16)

    def canh_chieu_cao_16x9(self) -> None:
        """Ep chieu cao theo ti le 16:9.

        PHAI goi ra ngoai vong layout (qua QTimer) - neu doi kich thuoc
        trong resizeEvent thi layout lam widget con bi ep ve 0 pixel.
        """
        w = self.width()
        if w > 0:
            self.setFixedHeight(int(w * 9 / 16))


class ChamDo(QWidget):
    """Cham mau nho (trang thai su kien)."""

    def __init__(self, mau_hex: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(9, 9)
        # QWidget mac dinh KHONG ve nen cua stylesheet - phai bat co nay.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background: {mau_hex}; border-radius: 4px;")


# ---------------------------------------------------------------- CUA SO


class CamAIMau(QMainWindow):
    """Cua so mau giao dien CamAI (tinh, khong chay pipeline)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CamAI - Mau giao dien Qt v3.8")
        self.setMinimumSize(1200, 760)
        self.resize(1440, 900)

        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "camai.png")
        if os.path.isfile(icon):
            self.setWindowIcon(QPixmap(icon))

        self._tao_thanh_dau()
        self._tao_than_bo()
        self._tao_noi_dung_cot_trai()

    def _tao_khung_goc(self) -> None:
        """Tao 1 widget goc + layout doc dung 1 lan (1 widget chi co 1 layout)."""
        nen = QWidget()
        nen.setObjectName("nenChinh")
        self.setCentralWidget(nen)
        self.v_nen = QVBoxLayout(nen)
        self.v_nen.setContentsMargins(0, 0, 0, 0)
        self.v_nen.setSpacing(0)

    # ------------------------------------------------------------ thanh dau
    def _tao_thanh_dau(self) -> None:
        self._tao_khung_goc()
        f = QFrame()
        f.setObjectName("thanhDau")
        f.setFixedHeight(CAO_DAU)

        h = QHBoxLayout(f)
        h.setContentsMargins(C_16, 0, C_16, 0)
        h.setSpacing(C_12)

        # --- trai: logo + ten + phien ban
        self.thanh_dau = f
        h.addWidget(LogoTro())

        ten = QLabel("CamAI")
        ten.setObjectName("tenApp")
        h.addWidget(ten)

        ban = QLabel("v3.8")
        ban.setObjectName("chipNho")
        h.addWidget(ban)

        h.addStretch(1)

        # --- giua: chip trang thai
        trang_thai = QLabel("●  Sẵn sàng")
        trang_thai.setObjectName("chipTrangThai")
        h.addWidget(trang_thai)

        h.addStretch(1)

        # --- phai: chip GPU + 2 nut
        gpu = QLabel("GPU RTX 3090")
        gpu.setObjectName("chip")
        h.addWidget(gpu)

        nut_dung = QPushButton("DỪNG")
        nut_dung.setObjectName("nutPhu")
        nut_dung.setIcon(_bieu_pixmap("tam_dung", MAU["chinh"], 14))
        nut_dung.setIconSize(QSize(14, 14))
        h.addWidget(nut_dung)

        nut_chay = QPushButton("BẮT ĐẦU")
        nut_chay.setObjectName("nutChinh")
        nut_chay.setIcon(_bieu_pixmap("phat", "#0B1220", 14))
        nut_chay.setIconSize(QSize(14, 14))
        h.addWidget(nut_chay)

        self.nut_dung = nut_dung
        self.nut_chay = nut_chay

        self.v_nen.addWidget(f)

    # -------------------------------------------------------------- than bo
    def _tao_than_bo(self) -> None:
        w = QWidget()
        w.setObjectName("nenChinh")
        self.v_nen.addWidget(w)
        h = QHBoxLayout(w)
        h.setContentsMargins(C_16, C_16, C_16, C_16)
        h.setSpacing(C_16)

        # cot trai
        self.cot_trai = QWidget()
        self.cot_trai.setFixedWidth(COT_TRAI)
        h.addWidget(self.cot_trai)

        # vung phai: cot chinh + cot phai
        self.vung_phai = QWidget()
        hp = QHBoxLayout(self.vung_phai)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.setSpacing(C_16)
        h.addWidget(self.vung_phai, 1)

        self._tao_cot_chinh(hp)
        self._tao_cot_phai(hp)

    # ----------------------------------------------------------- cot chinh
    def _tao_cot_chinh(self, hp: QHBoxLayout) -> None:
        self.cot_chinh = QWidget()
        v = QVBoxLayout(self.cot_chinh)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(C_12)
        hp.addWidget(self.cot_chinh, 1)

        # --- hang "nguon" nam tren khung video
        hang_nguon = QHBoxLayout()
        hang_nguon.setContentsMargins(0, 0, 0, 0)
        hang_nguon.setSpacing(C_8)
        nhan = QLabel("Loại nguồn:")
        nhan.setObjectName("nhanChung")
        hang_nguon.addWidget(nhan)
        chip = QLabel("Video")
        chip.setObjectName("chipOk")
        hang_nguon.addWidget(chip)
        hang_nguon.addStretch(1)
        v.addLayout(hang_nguon)

        # --- khung video 16:9
        self.khung_video = KhungVideo()
        self.khung_video.setObjectName("khungVideo")
        vh = QVBoxLayout(self.khung_video)
        vh.setContentsMargins(0, 0, 0, 0)
        vh.addStretch(1)
        chu = QLabel("Chưa có nguồn — chọn video, ảnh hoặc camera")
        chu.setObjectName("chuVideo")
        chu.setAlignment(Qt.AlignCenter)
        vh.addWidget(chu)
        vh.addStretch(1)
        v.addWidget(self.khung_video)

        # --- 6 the so
        self.hang_the_so = QWidget()
        hs = QHBoxLayout(self.hang_the_so)
        hs.setContentsMargins(0, 0, 0, 0)
        hs.setSpacing(C_12)

        the_so = [
            ("Người", "12", MAU["accent"]),
            ("Mặt", "5", MAU["accent"]),
            ("Người quen", "3", MAU["accent"]),
            ("Vào", "8", MAU["accent"]),
            ("Ra", "9", MAU["accent"]),
            ("Trong vùng", "2", MAU["canh"]),
        ]
        for ten, so, mau in the_so:
            the = QFrame()
            the.setObjectName("theSo")
            the.setFixedHeight(CAO_THE_SO)
            vt = QVBoxLayout(the)
            vt.setContentsMargins(8, 8, 8, 8)
            vt.setSpacing(2)
            vt.addStretch(1)
            lb_so = QLabel(so)
            lb_so.setObjectName("soLon")
            lb_so.setStyleSheet(f"color: {mau};")
            lb_so.setAlignment(Qt.AlignCenter)
            vt.addWidget(lb_so)
            lb_ten = QLabel(ten)
            lb_ten.setObjectName("nhanSo")
            lb_ten.setAlignment(Qt.AlignCenter)
            vt.addWidget(lb_ten)
            vt.addStretch(1)
            hs.addWidget(the, 1)

        v.addWidget(self.hang_the_so)
        v.addStretch(1)

    # ------------------------------------------------------------ cot phai
    def _tao_cot_phai(self, hp: QHBoxLayout) -> None:
        self.cot_phai = QWidget()
        self.cot_phai.setFixedWidth(COT_PHAI)
        v = QVBoxLayout(self.cot_phai)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(C_12)
        hp.addWidget(self.cot_phai)

        # --- khung danh sach su kien
        khung = QFrame()
        khung.setObjectName("khungPanel")
        v.addWidget(khung, 1)
        kv = QVBoxLayout(khung)
        kv.setContentsMargins(C_16, 14, C_16, 14)
        kv.setSpacing(C_8)

        td = QLabel("Danh sách sự kiện")
        td.setObjectName("tieuDeKhung")
        kv.addWidget(td)

        su_kien = [
            ("14:02:11", "Người lạ vào khu vực", MAU["accent"]),
            ("14:02:14", "Phát hiện 3 khuôn mặt", MAU["ok"]),
            ("14:02:19", "Xe máy rời khỏi vùng", MAU["ok"]),
            ("14:02:23", "Đọc biển số 30A-12345", MAU["ok"]),
            ("14:02:28", "Cảnh báo: người vượt vùng", MAU["canh"]),
            ("14:02:33", "Người quen: Trần Minh", MAU["ok"]),
            ("14:02:40", "Phát hiện vật thể lạ", MAU["canh"]),
            ("14:02:47", "Vùng không còn người", MAU["accent"]),
        ]
        for gio, mo_ta, mau in su_kien:
            dong = QWidget()
            dh = QHBoxLayout(dong)
            dh.setContentsMargins(0, 0, 0, 0)
            dh.setSpacing(C_8)
            lb_gio = QLabel(gio)
            lb_gio.setObjectName("eventTime")
            lb_gio.setFixedWidth(58)
            dh.addWidget(lb_gio)
            lb_mo = QLabel(mo_ta)
            lb_mo.setObjectName("eventDesc")
            dh.addWidget(lb_mo, 1)
            dh.addWidget(ChamDo(mau))
            kv.addWidget(dong, 1)

        # --- khung nhat ky
        khung_log = QFrame()
        khung_log.setObjectName("khungPanel")
        khung_log.setFixedHeight(CAO_NHAT_KY)
        v.addWidget(khung_log)
        kl = QVBoxLayout(khung_log)
        kl.setContentsMargins(C_16, 14, C_16, 14)
        kl.setSpacing(6)

        td_log = QLabel("Nhật ký")
        td_log.setObjectName("tieuDeKhung")
        kl.addWidget(td_log)

        dong_log = [
            "[14:02:10] INFO  Tai video mau",
            "[14:02:11] INFO  Nap model YOLO11n",
            "[14:02:12] WARN  CUDA khong dung",
            "[14:02:14] INFO  12 nguoi, 5 mat",
            "[14:02:19] INFO  Bien so 30A-12345",
            "[14:02:21] OK    Hoan tat xu ly",
        ]
        for dong in dong_log:
            lb = QLabel(dong)
            lb.setObjectName("logLine")
            kl.addWidget(lb)
        kl.addStretch(1)

    # ----------------------------------------------------------- cot trai
    def _tao_noi_dung_cot_trai(self) -> None:
        v = QVBoxLayout(self.cot_trai)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        v.addWidget(scroll)

        trong = QWidget()
        trong.setFixedWidth(COT_TRAI - 8)          # tru 8px cho thanh cuon
        scroll.setWidget(trong)

        vt = QVBoxLayout(trong)
        vt.setContentsMargins(0, 0, 8, 0)
        vt.setSpacing(C_8)

        # --- 4 muc lon dang accordion card
        c1 = CardAccordion("NGUỒN", "Chọn video, ảnh hoặc camera", True)
        vt.addWidget(c1)

        vt.addWidget(CardAccordion("PHÂN TÍCH", "Người, mặt, ra vào, vùng, vật thể", False))
        vt.addWidget(CardAccordion("BIỂN SỐ & ẢNH", "Đọc biển số, tự chụp ảnh sự kiện", False))
        vt.addWidget(CardAccordion("CẢNH BÁO & MÔ HÌNH", "Cảnh báo, thông tin model", False))
        vt.addStretch(1)

        # --- noi dung cua muc NGUON (chi card nay mo san)
        nhan = QLabel("Nguồn")
        nhan.setObjectName("nhanChung")
        c1.v_noi_dung.addWidget(nhan)

        o = QLineEdit(r"H:\AI Project\cam-ai\video_mau\car.mp4")
        o.setReadOnly(True)
        o.setCursorPosition(0)
        c1.v_noi_dung.addWidget(o)

        luoi = QGridLayout()
        luoi.setContentsMargins(0, 0, 0, 0)
        luoi.setSpacing(C_8)
        nut_nho = [
            ("Chọn video…", 0, 0),
            ("Chọn ảnh…", 0, 1),
            ("Chọn camera…", 1, 0),
            ("Danh sách camera", 1, 1),
        ]
        for chu, hang, cot in nut_nho:
            b = QPushButton(chu)
            b.setObjectName("nutNho")
            luoi.addWidget(b, hang, cot)
        c1.v_noi_dung.addLayout(luoi)

        self.cot_trai_scroll = scroll

    # -------------------------------------------------------------- du lieu
    def resizeEvent(self, e):                       # noqa: N802 - ten cua Qt
        super().resizeEvent(e)
        # Layout da chay xong roi moi ep chieu cao video 16:9.
        QTimer.singleShot(0, self.khung_video.canh_chieu_cao_16x9)

    def _rect_global(self, w: QWidget) -> list:
        """Tra ve [x, y, w, h] cua widget trong toa do man hinh (global)."""
        g = w.geometry()
        p = w.mapToGlobal(QPoint(0, 0))
        return [int(p.x()), int(p.y()), int(g.width()), int(g.height())]

    def dump_vung(self, path: str) -> None:
        """Ghi toa do cac vung de script chup anh cat dung cho.

        Toa do luon la GLOBAL (man hinh) - script chup anh tru `top` cua
        GetWindowRect de ra dung vung, khong doan offset khung cua so.
        """
        video = self._rect_global(self.khung_video)
        dau = self._rect_global(self.thanh_dau)
        cot_trai = self._rect_global(self.cot_trai)
        the_so = self._rect_global(self.hang_the_so)
        vung = {
            "size_cua_so": [self.width(), self.height()],
            "client": self._rect_global(self),
            "cot_trai": cot_trai,
            "the_so": the_so,
            "video": video,
            "dau": dau,
            "dau_video": [
                min(dau[0], video[0]),
                min(dau[1], video[1]),
                max(dau[0] + dau[2], video[0] + video[2]) - min(dau[0], video[0]),
                max(dau[1] + dau[3], video[1] + video[3]) - min(dau[1], video[1]),
            ],
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(vung, f, ensure_ascii=False, indent=2)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_CHU, 9))
    app.setStyleSheet(_qss())

    win = CamAIMau()
    win.show()
    # Layout chay xong -> ep chieu cao video 16:9 truoc khi chup anh.
    QTimer.singleShot(250, win.khung_video.canh_chieu_cao_16x9)

    topmost = "--topmost" in sys.argv
    if topmost:
        from PySide6.QtCore import Qt as _Qt
        win.setWindowFlag(_Qt.WindowStaysOnTopHint, True)
        win.show()
        win.raise_()
        win.activateWindow()

    thu_muc = os.path.dirname(os.path.abspath(__file__))
    duong_dan_vung = os.path.join(thu_muc, "_kk_out", "mau_qt", "_vung.json")

    def _dump():
        win.dump_vung(duong_dan_vung)
        print("KICH THUOC CUA SO:", win.width(), "x", win.height())
        print("FILE VUNG:", duong_dan_vung)
        sys.stdout.flush()

    QTimer.singleShot(1500, _dump)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
