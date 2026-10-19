"""
Canh bao cho CamAI - gui tin nhan Telegram + chuong / hop thoai tren may tinh.

Hai kenh canh bao (khong gui hinh anh, khong gui video - chi gui chu):
    1. Kenh chinh: tin nhan Telegram len dien thoai chu nha (can Internet).
    2. Kenh phu  : chuong + hop thoai ngay tren may tinh (khong can Internet).

Dung nhu lenh:
    .venv\\Scripts\\python.exe canh_bao.py --help
    .venv\\Scripts\\python.exe canh_bao.py --kiem-tra

Dung nhu module (phan mem chinh goi):
    from canh_bao import CanhBao

    canh_bao = CanhBao()
    canh_bao.guii("co_nguoi_vao_vung", {"video": "cua.mp4", "so_nguoi": 3})
    ...
    print(canh_bao.tong_ket())
    canh_bao.tat()

Cau hinh (KHONG ghi token truc tiep vao ma):
    - tham so lenh      : --token / --chat-id
    - bien moi truong   : CAMAI_TELEGRAM_TOKEN / CAMAI_TELEGRAM_CHAT_ID
    - file canh hinh    : canh_bao.ini
    Thu tu do ve truoc (CLI > bien moi truong > file canh hinh).

Luu y ky thuat:
    - MessageBoxW KHONG co co so "timeout". Gia tri 0x40 la MB_ICONASTERISK
      (icon), khong phai MB_TIMEOUT. Vi vay hop thoai duoc mo trong MOT LUONG RIENG
      (daemon) va mot luong gac se tu dong dong hop thoai sau `--het-hop-thoai` giay,
      nen tien trinh chinh khong bao gio bi treo.
    - Moi lan gui deu co timeout mac dinh 10 giay: mat mang khong lam treo phan mem.
"""

from __future__ import annotations

import argparse
import configparser
import ctypes
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque

__all__ = ["CanhBao", "chuan_hoa_console", "tao_canh_bao", "main"]

# ----------------------------------------------------------------- hang so

TEN_FILE_CAU_HINH = "canh_bao.ini"
TEN_MUC_TELEGRAM = "telegram"

TOKEN_MOI_TRUONG = "CAMAI_TELEGRAM_TOKEN"
CHAT_ID_MOI_TRUONG = "CAMAI_TELEGRAM_CHAT_ID"

MOI_TELEGRAM = "https://api.telegram.org"

GIOI_HAN_MOI_PHUT = 60  # don vi gioi han: so tin / 60 giay
GIOI_HAN_MAC_DINH = 5
GO_MAC_DINH = 60
THOI_GIAN_CHO_MAC_DINH = 10
DONG_HOP_THOAI_MAC_DINH = 60
SO_LAN_CHUONG_MAC_DINH = 2
SO_KY_TU_TOI_DA_TELEGRAM = 4096

# Co so: MB_OK | MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST
MB_OK = 0x00000000
MB_ICONWARNING = 0x00000030
MB_SETFOREGROUND = 0x00010000
MB_TOPMOST = 0x00040000
WM_CLOSE = 0x0010
LOP_HOP_THOAI = "#32770"

# Loai su kien (ma ngan) -> cau tieng Viet gui ra ngoai.
# Da them san ca cac ma LY_DO_* cua cam_ai_core.py nen goi su_kien[0] cung duoc.
# Muon them loai rieng: sua o day, hoac truyen cau san vao .guii().
NHAN_SU_KIEN = {
    # --- ma cua cam_ai_core.py (LY_DO_*) ---
    "vao_vung": "Có người vào vùng canh",
    "vuot_nguong_dong": "Vượt quá số người cho phép trong vùng canh",
    "dung_lau": "Có người đứng lâu bất thường trong vùng canh",
    "nguoi_quen": "Có người quen trong vùng canh",
    "co_nguoi": "Có người trong khung hình",
    # --- ma trai nghiem ---
    "co_nguoi_vao_vung": "Có người vào vùng canh",
    "nhiem_viet": "Người lạ xuất hiện trong vùng canh",
    "ra_khoi_vung": "Người đã rời vùng canh",
    "chuyen_dong": "Phát hiện chuyển động trong vùng canh",
    "canh_bao_he_thong": "Cảnh báo hệ thống CamAI",
}


# ------------------------------------------------------------- tien ich

def chuan_hoa_console():
    """Sua stdout/ststderr de khong bao gio vong khi in tieng Viet co dau.

    Console cu cua Windows (cp1252/cp437) khong in duoc 'đ' hay emoji.
    O day: doi sang UTF-8 neu can, va luon bat loi 'replace'.
    """
    for ten in ("stdout", "stderr"):
        luong = getattr(sys, ten, None)
        if luong is None:
            continue
        ma_hoa = (getattr(luong, "encoding", "") or "").lower()
        if ma_hoa and ma_hoa != "utf-8":
            try:
                "đ".encode(ma_hoa)
            except Exception:
                try:
                    luong.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        try:
            luong.reconfigure(errors="replace")
        except Exception:
            pass


def _in(dong, xuong_dong=0):
    """In an toan: co loi thi rut gon lai thay vi lam chet chuong trinh."""
    try:
        print(dong, file=sys.stdout)
    except UnicodeEncodeError:
        ma_hoa = (getattr(sys.stdout, "encoding", "") or "utf-8")
        try:
            print(dong.encode(ma_hoa, "replace").decode(ma_hoa, "replace"))
        except Exception:
            pass
    except Exception:
        pass


def _che_token(token):
    """Che token khi in ra man hinh/nhat ky (chi lo 4 dau + 4 cuoi)."""
    if not token:
        return "(chua co)"
    token = str(token)
    if len(token) <= 12:
        return "*" * len(token)
    return f"{token[:6]}...{token[-4:]} (an {len(token)} ky tu)"


def _dung_console_co_tieng_viet():
    try:
        return "đ".encode(sys.stdout.encoding or "utf-8") is not None
    except Exception:
        return False


# ---------------------------------------------------------------- CanhBao

class CanhBao:
    """Gui canh bao: Telegram (chu) + chuong / hop thoai tren may tinh.

    Tham so:
        telegram_token  token bot (None = lay tu bien moi truong / canh_bao.ini)
        chat_id         id cua chat nhan tin (None = tu bien moi truong / file)
        gioi_han        toi da so tin trong 1 phut (mac dinh 5)
        go              gop tin trung trong bao nhieu giay (mac dinh 60)
        bat_telegram    False = khong dung Telegram
        bat_chuong      False = khong phat chuong
        hien_hop_thoai  False = khong mo hop thoai
        timeout         cho toi da giay moi lan gui (mac dinh 10)
        dong_hop_thoai  tu dong dong hop thoai sau bao nhieu giay (mac dinh 60)
        tep_cau_hinh    duong dan file .ini (mac dinh canh_bao.ini)
        in_thong_bao    False = khong in dong trạng thái ra man hinh
        mo_phong        True = chi mo phong, KHONG gui gi ra ngoai
    """

    def __init__(self, telegram_token=None, chat_id=None, gioi_han=5, go=60,
                 bat_telegram=True, bat_chuong=True, hien_hop_thoai=True,
                 timeout=THOI_GIAN_CHO_MAC_DINH,
                 dong_hop_thoai=DONG_HOP_THOAI_MAC_DINH,
                 tep_cau_hinh=None, in_thong_bao=True, mo_phong=False):
        self.khoa = threading.RLock()
        self.dong = False

        self.gioi_han = max(1, int(gioi_han))
        self.go = max(0.0, float(go))
        self.bat_telegram = bool(bat_telegram)
        self.bat_chuong = bool(bat_chuong)
        self.bat_hop_thoai = bool(hien_hop_thoai)
        self.timeout = max(0.1, float(timeout))
        self.dong_hop_thoai = max(0.0, float(dong_hop_thoai))
        self.in_thong_bao = bool(in_thong_bao)
        self.mo_phong = bool(mo_phong)

        self.tep_cau_hinh = tep_cau_hinh or TEN_FILE_CAU_HINH
        cau_hinh = self._doc_file_cau_hinh(self.tep_cau_hinh)

        self.telegram_token, self.nguon_token = self._chon_phan(
            telegram_token, os.environ.get(TOKEN_MOI_TRUONG),
            self._gia_tri(cau_hinh, "token"), "tham so", TOKEN_MOI_TRUONG,
            f"{self.tep_cau_hinh} [telegram] token")
        self.chat_id, self.nguon_chat_id = self._chon_phan(
            chat_id, os.environ.get(CHAT_ID_MOI_TRUONG),
            self._gia_tri(cau_hinh, "chat_id"), "tham so", CHAT_ID_MOI_TRUONG,
            f"{self.tep_cau_hinh} [telegram] chat_id")

        self.lich_gui = deque()          # moc thoi gian cac lan gui gan nhat
        self.tan_da_gui = {}            # loai su kien -> (thoi gian, so lan)
        self.hop_thoai_dang_mo = 0
        self.hoa_don_hop_thoai = 0

        self.dem = {
            "so_su_kien": 0,
            "guii_thanh_cong": 0,
            "guii_that_bai": 0,
            "da_gop": 0,
            "bi_chan_gioi_han": 0,
            "hop_thoai": 0,
            "chuong": 0,
        }
        self.loi_gan_nhat = ""
        # ket qua cua lan goi .guii() gan nhat (de tien xem ly do bi bo qua)
        self.ket_qua_gan_nhat = {}

        if self.in_thong_bao:
            self.in_cau_hinh()

    # ---------------------------------------------------------- cau hinh

    @staticmethod
    def _doc_file_cau_hinh(duong_dan):
        """Doc file .ini. Thieu/cham -> tra None, khong bao loi."""
        if not duong_dan or not os.path.isfile(duong_dan):
            return None
        cau_hinh = configparser.ConfigParser(interpolation=None)
        try:
            # utf-8-sig: chay duoc ca khi anh luu file bang Notepad co BOM.
            cau_hinh.read(duong_dan, encoding="utf-8-sig")
        except Exception:
            return None
        return cau_hinh if cau_hinh.sections() else None

    @staticmethod
    def _gia_tri(cau_hinh, khoa):
        """Lay gia tri tu muc [telegram], neu khong co thi o muc mac dinh."""
        if cau_hinh is None:
            return None
        for muc in (TEN_MUC_TELEGRAM, cau_hinh.default_section):
            try:
                gia_tri = cau_hinh.get(muc, khoa, fallback="").strip()
            except Exception:
                gia_tri = ""
            if gia_tri:
                return gia_tri
        return None

    @staticmethod
    def _chon_phan(goi_truc_tiep, bien_moi_truong, tu_file, nhan_goi, nhan_moi_truong, nhan_file):
        """Uu tien: tham so > bien moi truong > file cau hinh. Tra (gia_tri, nguon)."""
        if goi_truc_tiep:
            return str(goi_truc_tiep).strip(), nhan_goi
        if bien_moi_truong and bien_moi_truong.strip():
            return bien_moi_truong.strip(), nhan_moi_truong
        if tu_file:
            return str(tu_file).strip(), nhan_file
        return None, "chua co"

    def telegram_san_sang(self):
        """True neu moi co du token + chat_id va dang bat Telegram."""
        return bool(self.bat_telegram and self.telegram_token and self.chat_id)

    def in_cau_hinh(self):
        _in("--- CANH BAO: cau hinh ---")
        _in(f"  Telegram       : {'bat' if self.bat_telegram else 'TAT'}"
            f"{' (san sang gui)' if self.telegram_san_sang() else ''}")
        _in(f"  Token          : {_che_token(self.telegram_token)}  <- {self.nguon_token}")
        _in(f"  Chat ID        : {self.chat_id if self.chat_id else '(chua co)'}  <- {self.nguon_chat_id}")
        _in(f"  Chuong         : {'bat' if self.bat_chuong else 'TAT'}")
        _in(f"  Hop thoai      : {'bat' if self.bat_hop_thoai else 'TAT'}")
        _in(f"  Chong spam     : toi da {self.gioi_han} tin / {GIOI_HAN_MOI_PHUT}s, gop trong {self.go:g}s")
        _in(f"  Timeout        : {self.timeout:g}s / lan gui")
        if not self.telegram_san_sang() and self.bat_telegram:
            _in("  [!] Chua du token/chat_id -> chi chay duoc kenh chuong + hop thoai.")
            _in("      Xem HUONG_DAN_CANH_BAO.md de them token.")

    # -------------------------------------------------------------- gui

    def guii(self, loai_su_kien, chi_tiet=None):
        """Goi 1 canh bao.

        loai_su_kien : chuoi ngan ("co_nguoi_vao_vung") hoac cau tieng Viet san.
        chi_tiet     : dict, nhan cac khoa
                       video, so_nguoi, mo_ta, duong_dan_xem, gio.
        Tra True neu it nhat 1 kenh bao thanh cong.
        Ly do bi bo qua (gop / chan / loi) nam o self.ket_qua_gan_nhat.
        """
        if self.dong:
            self.ket_qua_gan_nhat = {"hanh_dong": "da_tat", "chi_tiet": "CanhBao da .tat()"}
            return False

        chi_tiet = dict(chi_tiet or {})
        bay_gi = time.monotonic()
        tieu_de = NHAN_SU_KIEN.get(loai_su_kien, str(loai_su_kien))
        so_lan_gop_truoc = 0

        with self.khoa:
            self.dem["so_su_kien"] += 1
            # 1) Gop tin trung: cung loai su kien trong `go` giay -> chi gui 1 lan.
            truoc = self.tan_da_gui.get(loai_su_kien)
            if truoc is not None and self.go > 0 and (bay_gi - truoc[0]) < self.go:
                so_lan = truoc[1] + 1
                self.tan_da_gui[loai_su_kien] = (bay_gi, so_lan)
                self.dem["da_gop"] += 1
                self.ket_qua_gan_nhat = {
                    "hanh_dong": "gop",
                    "so_lan": so_lan,
                    "chi_tiet": f"trung '{tieu_de}' - da go lan {so_lan} trong {self.go:g}s",
                }
                if self.in_thong_bao:
                    _in(f"  [gop] {tieu_de} (lan {so_lan}, gop trong {self.go:g}s) -> khong gui lai")
                return False

            # 2) Gioi han so tin / 1 phut.
            while self.lich_gui and (bay_gi - self.lich_gui[0]) >= GIOI_HAN_MOI_PHUT:
                self.lich_gui.popleft()
            if len(self.lich_gui) >= self.gioi_han:
                self.dem["bi_chan_gioi_han"] += 1
                self.ket_qua_gan_nhat = {
                    "hanh_dong": "chan_gioi_han",
                    "chi_tiet": f"da gui {self.gioi_han} tin trong {GIOI_HAN_MOI_PHUT}s",
                }
                if self.in_thong_bao:
                    _in(f"  [chan] {tieu_de} -> da du {self.gioi_han} tin/phut, bo qua")
                return False

            self.lich_gui.append(bay_gi)
            if truoc is not None:
                so_lan_gop_truoc = max(0, truoc[1] - 1)
            self.tan_da_gui[loai_su_kien] = (bay_gi, 1)

        # --- Phan gui (KHONG giu khoa: len mang co the lai toi 10 giay) ---
        noi_dung = self._tao_noi_dung(tieu_de, chi_tiet, so_lan_gop_truoc)

        # Chi "that su gui" khi bat Telegram + co du token/chat_id.
        # Neu bat co y tat hoac chua cau hinh -> khong coi la loi.
        se_gui = self.telegram_san_sang() and not self.mo_phong
        chuong_ok = hop_thoai_ok = False
        if self.mo_phong:
            gui_ok, loi = True, ""
        else:
            gui_ok, loi = self._gui_telegram(noi_dung) if se_gui else (False, "")
            if self.bat_chuong:
                chuong_ok = self._phat_chuong()
                if chuong_ok:
                    self.dem["chuong"] += 1
            if self.bat_hop_thoai:
                hop_thoai_ok = self._mo_hop_thoai(noi_dung)

        thanh_cong = bool(gui_ok or chuong_ok or hop_thoai_ok or self.mo_phong)
        with self.khoa:
            if thanh_cong:
                self.dem["guii_thanh_cong"] += 1
            if se_gui and not gui_ok:
                # Da thu gui that su ma hong -> tinh vao so tin gui that bai.
                self.dem["guii_that_bai"] += 1
                self.loi_gan_nhat = loi
            self.ket_qua_gan_nhat = {
                "hanh_dong": "gui_ok" if thanh_cong else ("gui_loi" if se_gui else "khong_kenh"),
                "noi_dung": noi_dung,
                "loi": loi,
            }

        if self.in_thong_bao:
            if self.mo_phong:
                _in(f"  [mo phong] {tieu_de} -> se gui 1 tin")
            elif gui_ok:
                _in(f"  [gui OK] Telegram: {tieu_de}")
            elif se_gui:
                _in(f"  [loi] Telegram KHONG gui: {loi}")
            else:
                _in(f"  [canh bao] {tieu_de} -> chuong: "
                    f"{'co' if chuong_ok else 'khong'}, hop thoai: "
                    f"{'co' if hop_thoai_ok else 'khong'}")

        return thanh_cong

    def _tao_noi_dung(self, tieu_de, chi_tiet, so_lan_gop_truoc=0):
        """Lam noi dung tin nhan (chi chu, khong hinh anh/video)."""
        gio = str(chi_tiet.get("gio") or time.strftime("%H:%M:%S"))
        dong = ["\u26a0\ufe0f C\u1ea2NH B\u00c1O CAMAI", f"{gio} \u2014 {tieu_de}"]
        if chi_tiet.get("video"):
            dong.append(f"Video: {chi_tiet['video']}")
        if chi_tiet.get("so_nguoi") is not None:
            dong.append(f"Trong v\u00f9ng l\u00fac \u0111\u00f3: {chi_tiet['so_nguoi']} ng\u01b0\u1eddi")
        if chi_tiet.get("mo_ta"):
            dong.append(f"Chi ti\u1ebft: {chi_tiet['mo_ta']}")
        if so_lan_gop_truoc > 0:
            dong.append(f"Tr\u01b0\u1edbc \u0111\u00f3 \u0111\u00e3 g\u1ed9p th\u00eam {so_lan_gop_truoc} l\u1ea7n.")
        duong_dan = chi_tiet.get("duong_dan_xem")
        if duong_dan:
            if str(duong_dan).lower().startswith(("http://", "https://")):
                dong.append(f"M\u1edf video: {duong_dan}")
            else:
                dong.append(f"Video tr\u00ean m\u00e1y: {duong_dan}")
        return "\n".join(dong)

    # --------------------------------------------------------- Telegram

    def _gui_telegram(self, noi_dung):
        """Gui 1 tin nhan. Tra (thanh_cong, loi). Khong bao gio nem loi ra ngoai."""
        if not self.bat_telegram:
            return False, "Telegram dang tat (bat_telegram=False)"
        if not self.telegram_token or not self.chat_id:
            return False, "Chua co token / chat_id (xem HUONG_DAN_CANH_BAO.md)"

        du_lieu = json.dumps(
            {"chat_id": self.chat_id, "text": noi_dung[:SO_KY_TU_TOI_DA_TELEGRAM]},
            ensure_ascii=False,
        ).encode("utf-8")
        yeu_cau = urllib.request.Request(
            f"{MOI_TELEGRAM}/bot{self.telegram_token}/sendMessage",
            data=du_lieu,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(yeu_cau, timeout=self.timeout) as phan_hoi:
                ket_qua = json.loads(phan_hoi.read().decode("utf-8"))
        except urllib.error.HTTPError as loi:
            return False, f"HTTP {loi.code}: {self._doc_loi(loi)}"
        except Exception as loi:  # mat mang, sai token, het gio...
            return False, f"{type(loi).__name__}: {loi}"
        if not ket_qua.get("ok"):
            return False, f"Telegram bao loi: {ket_qua.get('description', 'khong ro')}"
        return True, ""

    @staticmethod
    def _doc_loi(loi):
        try:
            return loi.read().decode("utf-8", "replace")[:200]
        except Exception:
            return ""

    # ------------------------------------------- chuong + hop thoai (may tinh)

    def _phat_chuong(self):
        """Phat tieng chuong tren may tinh. Tra True neu phat duoc."""
        try:
            import winsound
        except Exception:
            return False
        try:
            for so_lan in range(max(1, SO_LAN_CHUONG_MAC_DINH)):
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                if so_lan:
                    time.sleep(0.25)
            return True
        except Exception:
            return False

    def _mo_hop_thoai(self, noi_dung):
        """Mo hop thoai canh bao o LUONG RIENG (daemon) - khong treo tien trinh."""
        if not self.bat_hop_thoai or not hasattr(ctypes, "windll"):
            return False
        with self.khoa:
            if self.hop_thoai_dang_mo >= 1:
                # Con hop thoai cu chua dong -> khong cho chong them.
                if self.in_thong_bao:
                    _in("  [hop thoai] da co 1 hop thoai mo, bo qua lan nay")
                return False
            self.hop_thoai_dang_mo += 1
            self.hoa_don_hop_thoai += 1
            self.dem["hop_thoai"] += 1
            tieu_de = f"CamAI - Canh bao #{self.hoa_don_hop_thoai}"
        luong = threading.Thread(target=self._chay_hop_thoai,
                                 args=(tieu_de, noi_dung), daemon=True)
        luong.start()
        return True

    def _chay_hop_thoai(self, tieu_de, noi_dung):
        flags = MB_OK | MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST
        try:
            if self.dong_hop_thoai > 0:
                luong_gac = threading.Thread(target=self._dong_hop_thoai_sau,
                                             args=(tieu_de, self.dong_hop_thoai),
                                             daemon=True)
                luong_gac.start()
            ctypes.windll.user32.MessageBoxW(None, noi_dung, tieu_de, flags)
        except Exception:
            pass
        finally:
            with self.khoa:
                self.hop_thoai_dang_mo = max(0, self.hop_thoai_dang_mo - 1)
            if self.in_thong_bao:
                _in(f"  [hop thoai] '{tieu_de}' da dong")

    def _dong_hop_thoai_sau(self, tieu_de, giay):
        """Tu dong dong hop thoai sau `giay` giay (MessageBoxW khong co co timeout)."""
        try:
            het = time.monotonic() + float(giay)
            while time.monotonic() < het:
                hwnd = ctypes.windll.user32.FindWindowW(LOP_HOP_THOAI, tieu_de)
                if hwnd:
                    time.sleep(0.3)  # cho no kip hien roi moi dong
                    if ctypes.windll.user32.IsWindow(hwnd):
                        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                        if self.in_thong_bao:
                            _in(f"  [hop thoai] '{tieu_de}' tu dong dong sau {giay:g}s")
                    return
                time.sleep(0.2)
        except Exception:
            pass

    # ------------------------------------------------------------ tong ket

    def tong_ket(self):
        """Tra dict so lieu de in cuoi buoi (van con cua ca chuong trinh)."""
        with self.khoa:
            ket_qua = dict(self.dem)
            ket_qua["telegram_san_sang"] = self.telegram_san_sang()
            ket_qua["token_co"] = bool(self.telegram_token)
            ket_qua["chat_id_co"] = bool(self.chat_id)
            ket_qua["nguon_token"] = self.nguon_token
            ket_qua["nguon_chat_id"] = self.nguon_chat_id
            ket_qua["loi_gan_nhat"] = self.loi_gan_nhat
            ket_qua["gioi_han"] = self.gioi_han
            ket_qua["go"] = self.go
            return ket_qua

    def in_tong_ket(self):
        so_lieu = self.tong_ket()
        _in("--- TONG KET CANH BAO ---")
        _in(f"  Su kien canh bao       : {so_lieu['so_su_kien']}")
        _in(f"  Tin gui thanh cong     : {so_lieu['guii_thanh_cong']}")
        _in(f"  Tin gui that bai       : {so_lieu['guii_that_bai']}")
        _in(f"  Tin bi gop (trung)     : {so_lieu['da_gop']}")
        _in(f"  Tin bi chan (gioi han) : {so_lieu['bi_chan_gioi_han']}")
        _in(f"  Hop thoai da mo        : {so_lieu['hop_thoai']}")
        _in(f"  Chuong da phat         : {so_lieu['chuong']}")
        _in(f"  Telegram               : {'san sang' if so_lieu['telegram_san_sang'] else 'CHUA san sang'}")
        if so_lieu["guii_that_bai"]:
            _in(f"  Loi gan nhat           : {so_lieu['loi_gan_nhat']}")
        return so_lieu

    def tat(self, in_tong_ket=True):
        """Dong tinh, in bang tong ket (truoc do da dung gui moi thao tac)."""
        with self.khoa:
            self.dong = True
        if in_tong_ket:
            self.in_tong_ket()
        return self.tong_ket()


# ------------------------------------------------------------------- CLI

def tao_canh_bao(args):
    """Tao CanhBao tu tham so lenh (da dung chung ca khi goi tu module khac)."""
    return CanhBao(
        telegram_token=args.token,
        chat_id=args.chat_id,
        gioi_han=args.gioi_han,
        go=args.go,
        bat_telegram=not args.khong_telegram,
        bat_chuong=not args.khong_chuong,
        hien_hop_thoai=not args.khong_hien_hop_thoai,
        timeout=args.timeout,
        dong_hop_thoai=args.het_hop_thoai,
        tep_cau_hinh=args.tep_cau_hinh,
        mo_phong=args.mo_phong,
        in_thong_bao=not args.kiem_tra,  # kiem tra tu in cau hinh o buoc 2
    )


def _huong_dan_ngan():
    _in("")
    _in("CamAI - canh bao. Cac buoc thi dung:")
    _in("  1. Tao bot Telegram + lay token + chat_id   -> xem HUONG_DAN_CANH_BAO.md")
    _in("  2. Luu vao file canh_bao.ini (mau co san trong file huong dan)")
    _in("  3. Kiem tra da dung chua:")
    _in("     .venv\\Scripts\\python.exe canh_bao.py --kiem-tra")
    _in("")
    _in("Neu chua co token, kenh chuong + hop thoai tren may tinh van chay.")


def _buoc(so, tong, tieu_de):
    _in("")
    _in(f"[{so}/{tong}] {tieu_de}")


def kiem_tra(can_bao, args):
    """Tu kiem tra buoc mot. Luon chay duoc, khong bao loi, khong treo."""
    tong = 6
    _in("=" * 64)
    _in("KIEM TRA CANH BAO CAMAI")
    _in("=" * 64)

    _buoc(1, tong, "Moi truong")
    try:
        _in(f"  Python   : {sys.version.split()[0]}  ({sys.executable})")
        _in(f"  He dieu hanh: {sys.platform}")
        _in(f"  Console  : {sys.stdout.encoding} - "
            f"{'in duoc tieng Viet' if _dung_console_co_tieng_viet() else 'DA CHUYEN SANG UTF-8'}")
        _in(f"  Gio      : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as loi:
        _in(f"  [loi] khong doc duoc thong tin moi truong: {loi}")

    _buoc(2, tong, "Cau hinh Telegram")
    try:
        can_bao.in_cau_hinh()
        _in(f"  File cau hinh: {can_bao.tep_cau_hinh} "
            f"({'co' if os.path.isfile(can_bao.tep_cau_hinh) else 'CHUA co - khong sao'})")
    except Exception as loi:
        _in(f"  [loi] khong doc duoc cau hinh: {loi}")

    _buoc(3, tong, "Chuong tren may tinh")
    if args.khong_chuong or can_bao.mo_phong:
        _in("  [bo qua] dang tat theo tham so.")
    else:
        _in("  Dang phat chuong...")
        try:
            if can_bao._phat_chuong():
                can_bao.dem["chuong"] += 1
                _in("  [OK] Da phat chuong. Khong nghe -> may tinh dang im (Settings > Sounds).")
            else:
                _in("  [!] Khong phat duoc chuong (may tinh co the dang im).")
        except Exception as loi:
            _in(f"  [loi] khong phat duoc chuong: {loi}")

    _buoc(4, tong, "Hop thoai canh bao")
    if args.khong_hien_hop_thoai or can_bao.mo_phong:
        _in("  [bo qua] dang tat theo tham so.")
    else:
        _in(f"  Se mo hop thoai, tu dong dong sau {can_bao.dong_hop_thoai:g}s (luong rieng, khong treo).")
        try:
            if can_bao._mo_hop_thoai("CamAI - Canh bao (kiem tra)\n\nDay la tin nhan thu.\nBam OK de dong."):
                _in("  [OK] Da mo hop thoai o luong rieng. Tien trinh van chay binh thuong.")
            else:
                _in("  [!] Khong mo duoc hop thoai (co the dang co hop thoai khac mo).")
        except Exception as loi:
            _in(f"  [loi] khong mo duoc hop thoai: {loi}")

    _buoc(5, tong, "Gui tin nhan Telegram")
    if can_bao.mo_phong or args.khong_telegram:
        _in("  [bo qua] dang tat theo tham so.")
    elif not can_bao.telegram_san_sang():
        _in("  [chua can] Chua co token / chat_id -> BO QUA buoc nay, KHONG co loi.")
        _in("")
        _in("  ==> De canh bao len dien thoai, lam theo 4 buoc sau:")
        _in("      1) Mo Telegram, tim @BotFather, go /newbot, dat ten bot,")
        _in("         chon username, bot tra ve token dang 123456:AAxxxxxx")
        _in("      2) Mo chat voi bot do, bam Start (hoac go chu bat dau)")
        _in("      3) Mo trinh duyet vao: https://api.telegram.org/bot<TOKEN>/getUpdates")
        _in("         doi MOT LAN, tim dong \"chat\":{\"id\": ...} -> so do la chat_id")
        _in("      4) Tao file canh_bao.ini cung thu muc canh_bao.py:")
        _in("             [telegram]")
        _in("             token = 123456:AAxxxxxx")
        _in("             chat_id = 987654321")
        _in("         roi chay lai: .venv\\Scripts\\python.exe canh_bao.py --kiem-tra")
        _in("")
        _in("  Chi tiet de hieu hon: HUONG_DAN_CANH_BAO.md")
        _in("  => Kenh chuong + hop thoai tren may tinh VAN DUNG binh thuong.")
    else:
        _in("  Token/chat_id da co. Dang gui 1 tin nhan thu...")
        try:
            noi_dung = can_bao._tao_noi_dung("Tin nhan thu kiem tra", {
                "mo_ta": "Ban vua chay: python canh_bao.py --kiem-tra",
                "gio": time.strftime("%H:%M:%S"),
            })
            ok, loi = can_bao._gui_telegram(noi_dung)
            if ok:
                can_bao.dem["guii_thanh_cong"] += 1
                _in(f"  [OK] Da gui thanh cong. Mo dien thoai de kiem tra (co the cham vai giay).")
            else:
                can_bao.dem["guii_that_bai"] += 1
                can_bao.loi_gan_nhat = loi
                _in(f"  [LOI] khong gui duoc: {loi}")
                _in("       - Kiem tra token/chat_id co dung khong?")
                _in("       - Ban da mo chat voi bot va bam Start chua?")
                _in("       - May tinh co Internet khong?")
        except Exception as loi:
            _in(f"  [loi] khong gui duoc tin thu: {loi}")

    _buoc(6, tong, "Tu kiem tra chong spam (mo phong, KHONG gui gi ra ngoai)")
    try:
        kiem_tra_chong_spam(args)
    except Exception as loi:
        _in(f"  [loi] khong chay duoc tu kiem tra: {loi}")

    _in("")
    _in("=" * 64)
    _in("HOAN TAT KIEM TRA - KHONG CO LOI FAT NAO CAU HINH PHAI SU VAO")
    _in("=" * 64)
    can_bao.in_tong_ket()
    return 0


def kiem_tra_chong_spam(args):
    """Mo phong 2 lan gop tin + vuot gioi han, in ra so lieu de anh doi chieu."""
    gioi_han = args.gioi_han
    _in(f"  4a) Go tin trung: goi 5 lan cung 1 su kien trong <1s (go = {args.go:g}s)")
    thu = CanhBao(gioi_han=100, go=args.go, bat_telegram=False, bat_chuong=False,
                  hien_hop_thoai=False, in_thong_bao=False, mo_phong=True)
    for lan in range(1, 6):
        thu.guii("co_nguoi_vao_vung", {"video": "test.mp4", "so_nguoi": 3})
    so_lieu = thu.tong_ket()
    _in(f"      -> gui thanh cong: {so_lieu['guii_thanh_cong']} (mong doi: 1), "
        f"bi gop: {so_lieu['da_gop']} (mong doi: 4)")

    _in(f"  4b) Vuot gioi han: goi 10 su kien KHAC NHAU (gioi han = {gioi_han} tin/phut)")
    thu2 = CanhBao(gioi_han=gioi_han, go=0, bat_telegram=False, bat_chuong=False,
                   hien_hop_thoai=False, in_thong_bao=False, mo_phong=True)
    for lan in range(1, 11):
        thu2.guii(f"su_kien_so_{lan}", {"video": "test.mp4"})
    so_lieu2 = thu2.tong_ket()
    _in(f"      -> gui thanh cong: {so_lieu2['guii_thanh_cong']} (mong doi: {min(gioi_han, 10)}), "
        f"bi chan: {so_lieu2['bi_chan_gioi_han']} (mong doi: {max(0, 10 - gioi_han)})")
    thu.tat(in_tong_ket=False)
    thu2.tat(in_tong_ket=False)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="canh_bao.py",
        description="CamAI - canh bao qua Telegram + chuong/hop thoai may tinh (chi gui chu).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Vi du:\n"
            "  python canh_bao.py --kiem-tra\n"
            "  python canh_bao.py --token 123456:AAxxx --chat-id 987654321\n"
            "  python canh_bao.py --kiem-tra --khong-hien-hop-thoai --het-hop-thoai 5\n"
            "\n"
            "Cau hinh: --token/--chat-id > bien moi truong CAMAI_TELEGRAM_TOKEN/\n"
            "          CAMAI_TELEGRAM_CHAT_ID > file canh_bao.ini\n"
            "\n"
            "Chi gui CHU. Khong bao gio gui hinh anh hay video.\n"
        ),
    )
    parser.add_argument("--kiem-tra", action="store_true",
                        help="tu kiem tra buoc mot va in ket qua (an toan, khong treo)")
    parser.add_argument("--token", default=None, help="token bot Telegram (uu tien cao nhat)")
    parser.add_argument("--chat-id", default=None, help="id chat nhan tin, vd 987654321")
    parser.add_argument("--gioi-han", type=int, default=GIOI_HAN_MAC_DINH,
                        help="toi da bao nhieu tin trong 1 phut (mac dinh: 5)")
    parser.add_argument("--go", type=float, default=GO_MAC_DINH,
                        help="gop tin trung trong bao nhieu giay (mac dinh: 60)")
    parser.add_argument("--timeout", type=float, default=THOI_GIAN_CHO_MAC_DINH,
                        help="cho toi da giay moi lan gui (mac dinh: 10)")
    parser.add_argument("--het-hop-thoai", type=float, default=DONG_HOP_THOAI_MAC_DINH,
                        help="tu dong dong hop thoai sau bao nhieu giay (mac dinh: 60)")
    parser.add_argument("--tep-cau-hinh", default=TEN_FILE_CAU_HINH,
                        help="duong dan file cau hinh .ini (mac dinh: canh_bao.ini)")
    parser.add_argument("--khong-telegram", action="store_true",
                        help="tat kenh Telegram (chi dung chuong + hop thoai)")
    parser.add_argument("--khong-chuong", action="store_true", help="khong phat chuong")
    parser.add_argument("--khong-hien-hop-thoai", action="store_true",
                        help="khong mo hop thoai (dung khi chay nien)")
    parser.add_argument("--mo-phong", action="store_true",
                        help="chi mo phong: khong gui gi ra ngoai, dung de thu chong spam")
    return parser.parse_args(argv)


def main(argv=None):
    chuan_hoa_console()
    args = parse_args(argv)
    can_bao = tao_canh_bao(args)
    if args.kiem_tra:
        return kiem_tra(can_bao, args)
    _huong_dan_ngan()
    can_bao.tat(in_tong_ket=False)
    return 0


# Tu chuan hoa ngay khi import de moi noi dung tieng Viet in ra deu khong vong.
chuan_hoa_console()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _in("\nDa dung theo yeu cau (Ctrl+C).")
        sys.exit(0)