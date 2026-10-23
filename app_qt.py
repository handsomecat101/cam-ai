# -*- coding: utf-8 -*-
"""
CamAI - vo desktop (PySide6 + QWebEngineView) boc giao dien web FastAPI.

Chay:
    .venv\\Scripts\\python.exe app_qt.py

Kien truc:
    1. Server FastAPI (web_server.py) chay trong 1 THREAD DAEMON (uvicorn.Server).
       Khong dung subprocess => dong cua so la tat sach, khong con process treo.
    2. QWebEngineView tro toi http://127.0.0.1:<port> => dung UI ma dien thoai cung thay.
    3. Thanh trang thai duoi cung + hop thoai "Mo tren dien thoai"
       (URL LAN SAN DUNG co ma truy cap + nut "Sao chep").

Mat khau (double-click la chay, khong can cau hinh bien moi truong):
    - Co CAMAI_PASSWORD trong moi truong -> dung nguyen, khong doi.
    - Khong co -> TU SINH mat khau ngau nhien moi lan khoi dong (secrets),
      gan vao os.environ TRUOC khi nap web_server.py
      (server doc bien nay luc khoi tao _Phien).
    - Mat khau khong bao gio ghi ra file, khong ghi ra log file.
      Chi in ra console (chay bang python.exe moi co console).

KHOA TRUY CAP SAN DUNG (v3.9):
    - web_server sinh 1 khoa ngau nhien (KHOA_TRUY_CAP) moi lan khoi dong.
    - Hop thoai "Mo tren dien thoai" hien URL SAN DUNG co khoa:
      http://<IP-LAN>:<port>/?k=<khoa> => dien thoai mo la VAO THANG,
      KHONG co form mat khau.
    - Nguoi la trong LAN khong co URL => khong vao duoc.

Dang nhap:
    - Desktop TU DANG NHAP HOP (fetch trong trang -> luu token vao localStorage).
    - Dien thoai mo bang DUONG DAN CO MA (server cap phien ngay).
    - Auto-dang nhap chi chay tren webview cuc bo (127.0.0.1) cua may nay.

Nguyen tac:
    - Desktop va dien thoai dung CHUNG 1 server => cung trang thai, khong ton 2 ban.
    - CHI DOC web_server.py. Khong sua file nao khac.
    - Server bind 0.0.0.0 de dien thoai cung LAN vao duoc.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

# Chromium hay bao loi khoi tao QWebEngine tren may nay.
# Bien moi truong phai duoc dat TRUOC khi import PySide6.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

# True neu chay bang python.exe (co console). Chay pythonw.exe -> stdout = None -> False.
CO_CONSOLE = sys.stdout is not None

# Khi chay bang pythonw.exe thi sys.stdout la None => print() se nem loi.
# Gan sang devnull de moi thu vien trong project (web_server.py) in thoai duoc.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TIEU_DE_CUA_SO = "CamAI — Phân tích video giám sát"
MAU_NEN = "#16181D"
MAU_THE = "#1B2336"
MAU_CHU = "#F8FAFC"
MAU_CHU_PHU = "#94A3B8"
MAU_VIEN = "#2A3550"
MAU_XANH = "#22C55E"

HOST_MAY_CHU = "0.0.0.0"          # 0.0.0.0 de dien thoai cung LAN vao duoc
PORT_MAC_DINH = 8765
SO_PORT_THU = 40
THOI_GIAN_CHO_SERVER = 20.0
THOI_GIAN_DONG_SERVER = 5.0
TEN_BIEN_MAT_KHAU = "CAMAI_PASSWORD"
DO_DAI_MAT_KHAU_TOI_THIEU = 8
DO_DAI_MAT_KHAU_SINH = 10

# Chu cho mat khau tu sinh: chu (hoa + thuong) + so + ky tu an toan.
# Khong dung ky tu la `, \, " , ' de khong vuot khi in ra console hay nhung JSON.
CHU_MAT_KHAU = (
    "abcdefghijkmnopqrstuvwxyz"
    "ABCDEFGHJKLMNPQRSTUVWXYZ"
    "23456789"
    "#!@%*?-_"
)

# ------------------------------------------------------------------ import PySide6
_LOI_PY = ""
try:
    from PySide6.QtCore import QObject, QTimer, QUrl, Qt, Signal, Slot
    from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QShortcut
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception as _loi:  # noqa: BLE001 - giu lai de import app_qt khong chet
    _LOI_PY = "%s: %s" % (type(_loi).__name__, _loi)


# ------------------------------------------------------------------ tien ich
def _in(text: str) -> None:
    """In ra console. Khong bao gio nem loi (chay pythonw cung duoc)."""
    try:
        print(text, flush=True)
    except Exception:  # noqa: BLE001
        pass


def _ip_lan() -> str:
    """IP cua may trong mang noi bo (dien thoai cung Wi-Fi vao duoc)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except Exception:  # noqa: BLE001
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:  # noqa: BLE001
            return "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


def _cong_trong(cong: int) -> bool:
    """True neu cong chưa ai dùng."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((HOST_MAY_CHU, cong))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


def _chon_cong(cong_mac_dinh: int = PORT_MAC_DINH, so_thu: int = SO_PORT_THU) -> int:
    """Dùng port cố định; nếu bận thì tự dòng port trống kế bên."""
    if _cong_trong(cong_mac_dinh):
        return cong_mac_dinh
    for i in range(1, so_thu + 1):
        cong = cong_mac_dinh + i
        if _cong_trong(cong):
            return cong
    return cong_mac_dinh


def _sinh_mat_khau(do_dai: int = DO_DAI_MAT_KHAU_SINH) -> str:
    """Sinh mat khau ngau nhien bang secrets (khong dung random).

    Moi lan khoi dong lai mot mat khau khac => an toan hon mat khau co dinh.
    """
    return "".join(secrets.choice(CHU_MAT_KHAU) for _ in range(do_dai))


def _lay_hoac_sinh_mat_khau() -> tuple[str, bool]:
    """Lay mat khau cho app.

    Tra ve (mat_khau, tu_sinh):
      - neu CAMAI_PASSWORD da co trong moi truong -> dung nguyen, khong doi gi.
      - neu chua co -> tu sinh mat khau ngau nhien VA gan vao os.environ
        (phai gan TRUOC khi nap web_server.py, vi server doc bien nay
        luc khoi tao _Phien).

    KHONG ghi mat khau ra file, KHONG ghi ra stderr.
    """
    co_san = os.environ.get(TEN_BIEN_MAT_KHAU, "").strip()
    if co_san:
        return co_san, False
    mat_khau = _sinh_mat_khau()
    os.environ[TEN_BIEN_MAT_KHAU] = mat_khau
    return mat_khau, True


def _nap_web_server():
    """Nạp web_server.py. Trả về (module, chuỗi lỗi)."""
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    try:
        import web_server  # noqa: PLC0415 - nap dong de khong chet luc import
    except Exception as loi:  # noqa: BLE001
        return None, "%s: %s" % (type(loi).__name__, loi)
    return web_server, ""


def _cho_server_san_sang(cong: int, tong: float = THOI_GIAN_CHO_SERVER):
    """Chờ server trả lời. Trả về (sẵn sàng, mã HTTP)."""
    het = time.time() + tong
    url = "http://127.0.0.1:%d/" % cong
    # Không dùng proxy của máy cho request nội bộ.
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.time() < het:
        try:
            with mo.open(url, timeout=2) as resp:
                if resp.status < 500:
                    return True, resp.status
        except urllib.error.HTTPError as e:
            return True, e.code
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False, 0


def _dang_nhap_http(url_may: str, mat_khau: str) -> tuple[bool, str]:
    """Đăng nhập từ Python (dùng làm đường dự phòng cho auto-login trên desktop).

    Trả về (đăng nhập được, token). Không ghi token ra file.
    """
    du_lieu = json.dumps({"mat_khauu": str(mat_khau)}).encode("utf-8")
    yeu_cau = urllib.request.Request(
        url_may.rstrip("/") + "/api/dang-nhap",
        data=du_lieu,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with mo.open(yeu_cau, timeout=10) as resp:
            ket = json.loads(resp.read().decode("utf-8"))
    except Exception as loi:  # noqa: BLE001
        _in("[CAMAI-QT] LOI dang-nhap http: %s" % loi)
        return False, ""
    if ket.get("ok") and ket.get("token"):
        return True, str(ket["token"])
    return False, ""


def _trang_thai_voi_token(url_may: str, token: str) -> tuple[int, bool]:
    """Gọi GET /api/trang-thai bằng token. Trả về (mã HTTP, ok).

    Chứng minh token lấy từ localStorage thực sự dùng được với API.
    """
    yeu_cau = urllib.request.Request(
        url_may.rstrip("/") + "/api/trang-thai",
        headers={"X-Camai-Token": str(token)},
    )
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with mo.open(yeu_cau, timeout=10) as resp:
            return resp.status, resp.status == 200
    except urllib.error.HTTPError as loi:
        return loi.code, False
    except Exception:  # noqa: BLE001
        return 0, False


class _MayChu:
    """Giữ uvicorn.Server để tắt sạch khi đóng cửa sổ."""

    def __init__(self, app_fastapi, host: str, cong: int) -> None:
        import uvicorn  # noqa: PLC0415

        self.cau_hinh = uvicorn.Config(
            app_fastapi,
            host=host,
            port=cong,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(self.cau_hinh)

    def chay(self) -> None:
        self.server.run()

    def tat(self) -> None:
        self.server.should_exit = True


# ------------------------------------------------------------------ giao dien Qt
if not _LOI_PY:

    class _Bridge(QObject):
        """Cầu nối giữa trang web và vỏ desktop.

        Slot `thong_bao(text)`: trang web (hoặc lớp gọi trong Python) báo trạng thái.
        Kết quả được in ra console và hiện ở thanh trạng thái dưới cùng.

        Slot `dang_nhap(mat_khauu)`: trang web yêu cầu vỏ desktop đăng nhập hộ
        (đường dự phòng khi fetch trong trang không chạy được).
        Trả về token phiên dạng chuỗi (chuỗi rỗng = thất bại).
        """

        tin_hieu = Signal(str)

        def __init__(self, parent=None, url_may: str = "", mat_khau: str = "") -> None:
            super().__init__(parent)
            self.url_may = url_may
            self.mat_khau = mat_khau

        @Slot(str)
        def thong_bao(self, text: str) -> None:
            noi_dung = str(text)
            _in("[CAMAI-QT] WEB: %s" % noi_dung)
            self.tin_hieu.emit(noi_dung)

        @Slot(str, result=str)
        def dang_nhap(self, mat_khauu: str) -> str:
            """Đăng nhập hộ cho webview: POST /api/dang-nhap rồi trả về token."""
            ok, token = _dang_nhap_http(self.url_may, str(mat_khauu))
            if ok:
                _in("[CAMAI-QT] KENH-DANG-NHAP: ok (token %d ky tu)" % len(token))
                return token
            _in("[CAMAI-QT] KENH-DANG-NHAP: that bai")
            return ""

    # Client QWebChannel toi thieu (tu viet, theo protocol Qt: type la SO).
    #   3 = init, 6 = invokeMethod, 8 = connectToSignal, 10 = response, 1 = signal
    # Sau khi noi xong, trang web goi window.camaiBao("...") de bao trang thai
    # cho vong desktop (vao console + thanh trang thai duoi cung).
    # window.camaiDangNhap(mk) la kenh DU PHONG: trang web goi len vong desktop
    # de vong desktop dang nhup giup (dung khi fetch trong trang that bai).
    JS_KHOI_DONG = r"""
    (function () {
      window.__camaiTin = '';
      window.__camaiShell = '';
      window.__bridgeReady = false;
      window.__camaiLoi = '';
      window.__camaiKQ = {trang_thai: 'cho', token: '', loi: ''};
      var t = (typeof qt !== 'undefined') ? qt.webChannelTransport : null;
      if (!t || typeof t.send !== 'function') {
        window.__camaiLoi = 'khong co transport';
        return;
      }
      var execId = 0;
      var callbacks = {};
      var handlers = {};
      t.onmessage = function (msg) {
        var d = msg;
        if (msg && typeof msg.data === 'string') {
          try { d = JSON.parse(msg.data); } catch (e) { return; }
        }
        if (!d) { return; }
        if (d.type === 10) {                       // response
          if (callbacks[d.id]) { callbacks[d.id](d.data); delete callbacks[d.id]; }
          return;
        }
        if (d.type === 1) {                        // signal tu Python
          var cb = handlers[d.signal];
          if (cb) { try { cb.apply(null, d.args || []); } catch (e) {} }
          return;
        }
      };
      function exec(data, cb) {
        data.id = execId++;
        callbacks[data.id] = cb;
        t.send(JSON.stringify(data));
      }
      window.__camaiExec = exec;
      exec({type: 3}, function (data) {            // init
        var o = data && data['bridge'];
        window.__bridgeReady = !!o;
        if (o) {
          window.__bridgeId = o.id;
          var mo = o.methods || [];
          for (var i = 0; i < mo.length; i++) {
            var m = mo[i][0];
            if (m === 'thong_bao' || m.indexOf('thong_bao(') === 0) {
              window.__bridgeMethod = (m.charAt(m.length - 1) === ')') ? mo[i][1] : m;
              break;
            }
          }
          // Ham moi: vong desktop (Python) dang nhup giup khi fetch trong trang that bai.
          window.__bridgeMethodDN = '';
          for (var t2 = 0; t2 < mo.length; t2++) {
            if (mo[t2][0] === 'dang_nhap') {
              window.__bridgeMethodDN = 'dang_nhap';
              break;
            }
          }
          if (!window.__bridgeMethodDN) {
            for (var t3 = 0; t3 < mo.length; t3++) {
              if (String(mo[t3][0]).indexOf('dang_nhap(') === 0) {
                window.__bridgeMethodDN = 'dang_nhap';
                break;
              }
            }
          }
          var sg = o.signals || [];
          for (var j = 0; j < sg.length; j++) {
            var s = sg[j][0];
            if (s === 'tin_hieu' || s.indexOf('tin_hieu(') === 0) {
              handlers[sg[j][1]] = function (text) { window.__camaiTuShell(String(text)); };
              exec({type: 8, object: 'bridge', signal: sg[j][1]});
              break;
            }
          }
        }
        window.__camaiKenh = 'xong';
      });
      window.__camaiTuShell = function (text) { window.__camaiShell = String(text); };
      window.camaiBao = function (text) {
        if (window.__bridgeReady && window.__bridgeMethod) {
          window.__camaiExec({type: 6, object: 'bridge', method: window.__bridgeMethod,
                              args: [String(text)]});
          return 'kenh';
        }
        window.__camaiTin = String(text);
        return 'hdem';
      };
      // Yeu cau vong desktop (Python) dang nhap giup va tra ve token.
      window.camaiDangNhap = function (mk) {
        window.__camaiKenh = {trang_thai: 'cho', token: '', loi: ''};
        if (!window.__bridgeReady || !window.__bridgeMethodDN) {
          window.__camaiKenh = {trang_thai: 'loi', token: '', loi: 'kenh chua noi'};
          return 'khong-co-kenh';
        }
        window.__camaiExec({type: 6, object: 'bridge', method: window.__bridgeMethodDN,
                            args: [String(mk || '')]},
          function (data) {
            var tok = '';
            if (data && typeof data === 'object') { tok = String(data.token || ''); }
            else if (data) { tok = String(data); }
            if (tok) {
              try { localStorage.setItem('camai_token', tok); } catch (e) {}
              try { localStorage.setItem('token', tok); } catch (e) {}
              window.__camaiKenh = {trang_thai: 'ok', token: tok, loi: ''};
            } else {
              window.__camaiKenh = {trang_thai: 'loi', token: '', loi: 've khong tra ve token'};
            }
          });
        return 'kenh';
      };
    })();
    """

    # Tu dang nhap tren DESKTOP: goi fetch('/api/dang-nhap') ngay trong trang
    # (cung origin 127.0.0.1 => khong co van de CORS) roi luu token vao localStorage
    # y hieu UI lam khi nguoi dung go tay.
    JS_TU_DANG_NHAP = r"""
    window.camaiTuDangNhap = function (mk) {
      window.__camaiKQ = {trang_thai: 'cho', token: '', loi: ''};
      try {
        fetch('/api/dang-nhap', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          credentials: 'same-origin',
          body: JSON.stringify({mat_khauu: mk})
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d && d.ok && d.token) {
            try { localStorage.setItem('camai_token', d.token); } catch (e) {}
            try { localStorage.setItem('token', d.token); } catch (e) {}
            window.__camaiKQ = {trang_thai: 'ok', token: String(d.token), loi: ''};
          } else {
            window.__camaiKQ = {trang_thai: 'loi', token: '',
                               loi: (d && d.loi) || 'Dang nhap khong thanh cong'};
          }
        }).catch(function (e) {
          window.__camaiKQ = {trang_thai: 'loi', token: '', loi: String(e)};
        });
      } catch (e) {
        window.__camaiKQ = {trang_thai: 'loi', token: '', loi: String(e)};
      }
      return 'da-gui';
    };
    """

    # Doc ket qua tu dang nhap + token trong localStorage (tuong doi voi trang web).
    JS_DOC_KQ = r"""
    (function () {
      try {
        var q = window.__camaiKQ || {trang_thai: 'cho', token: '', loi: ''};
        var k = window.__camaiKenh || {trang_thai: 'cho', token: '', loi: ''};
        var tk = '';
        try { tk = localStorage.getItem('camai_token') || ''; } catch (e) {}
        if (!tk) { try { tk = localStorage.getItem('token') || ''; } catch (e) {} }
        return JSON.stringify({trang_thai: String(q.trang_thai || ''),
                               token: String(q.token || ''),
                               loi: String(q.loi || ''),
                               kenh_trang_thai: String(k.trang_thai || ''),
                               kenh_token: String(k.token || ''),
                               kenh_loi: String(k.loi || ''),
                               ls: tk});
      } catch (e) { return JSON.stringify({trang_thai: 'loi', token: '', loi: String(e), ls: ''}); }
    })();
    """

    # Đọc tin nhắn dự phòng do trang web gửi lên (không cần qwebchannel.js).
    JS_DOC_TIN = """
    (function () {
      try {
        var t = window.__camaiTin || '';
        window.__camaiTin = '';
        return String(t);
      } catch (e) { return ''; }
    })();
    """

    QSS = """
    QMainWindow { background: %(nen)s; }
    QStatusBar { background: %(nen)s; color: %(phu)s; border-top: 1px solid %(vien)s; }
    QStatusBar QLabel { color: %(phu)s; background: transparent; }
    QPushButton {
        background: %(the)s; color: %(chu)s; border: 1px solid %(vien)s;
        border-radius: 4px; padding: 3px 14px;
    }
    QPushButton:hover { background: %(vien)s; }
    QPushButton:pressed { background: %(vien)s; }
    QDialog { background: %(nen)s; }
    QDialog QLabel { color: %(chu)s; }
    QLineEdit {
        background: #0F172A; color: %(xanh)s; border: 1px solid %(vien)s;
        border-radius: 4px; padding: 6px; font-family: Consolas, monospace;
    }
    QWebEngineView { background: %(nen)s; border: none; }
    """ % {
        "nen": MAU_NEN,
        "the": MAU_THE,
        "chu": MAU_CHU,
        "phu": MAU_CHU_PHU,
        "vien": MAU_VIEN,
        "xanh": MAU_XANH,
    }

    class _HopThoaiDienThoai(QDialog):
        """Hộp thoại 'Mở trên điện thoại': URL LAN SẴN DÙNG (có mã) + nút Sao chép.

        Không còn ô mật khẩu: URL đã gắn sẵn mã truy cập, copy dán vào trình
        duyệt điện thoại là vào thẳng, không gõ mật khẩu.
        """

        def __init__(self, url_lan: str, url_san_dung: str = "", parent=None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Mở trên điện thoại")
            self.setMinimumWidth(520)
            self.setStyleSheet(QSS)

            bo = QVBoxLayout(self)
            bo.setSpacing(10)

            tieu_de = QLabel("Mở trên điện thoại")
            tieu_de.setStyleSheet("font-size: 15px; font-weight: bold; color: %s;" % MAU_CHU)
            bo.addWidget(tieu_de)

            huong_dan = QLabel(
                "Điện thoại cùng Wi-Fi với máy tính → mở trình duyệt → dán URL bên dưới."
            )
            huong_dan.setWordWrap(True)
            huong_dan.setStyleSheet("color: %s;" % MAU_CHU_PHU)
            bo.addWidget(huong_dan)

            dong = QHBoxLayout()
            self.o_url = QLineEdit(url_san_dung or url_lan)
            self.o_url.setReadOnly(True)
            self.o_url.setCursorPosition(0)
            self.o_url.setToolTip("Chọn toàn bộ và sao chép (Ctrl+C)")
            dong.addWidget(self.o_url, 1)
            self.btn_sao_chep = QPushButton("Sao chép")
            self.btn_sao_chep.clicked.connect(self._sao_chep)
            dong.addWidget(self.btn_sao_chep)
            bo.addLayout(dong)

            ghi_chu = QLabel(
                "Dán đường dẫn này vào trình duyệt điện thoại (cùng Wi-Fi) là vào thẳng, "
                "không cần mật khẩu."
            )
            ghi_chu.setWordWrap(True)
            ghi_chu.setStyleSheet("color: %s;" % MAU_CHU_PHU)
            bo.addWidget(ghi_chu)

            canh_bao = QLabel("Chỉ trong mạng nội bộ. Không mở ra Internet.")
            canh_bao.setStyleSheet("color: #EF4444;")
            bo.addWidget(canh_bao)

            thoat = QPushButton("Đóng")
            thoat.clicked.connect(self.accept)
            bo.addWidget(thoat, 0, Qt.AlignRight)

            # Tab order ro rang (de kiem chung bam phim dua dung noi dung vao clipboard):
            #   o_url -> btn_sao_chep -> thoat
            QWidget.setTabOrder(self.o_url, self.btn_sao_chep)
            QWidget.setTabOrder(self.btn_sao_chep, thoat)

        def showEvent(self, su_kien):  # noqa: N802 - ten cua Qt
            """Dat focus o o dau tien de thu tu Tab co dinh."""
            super().showEvent(su_kien)
            try:
                self.o_url.setFocus()
            except Exception:  # noqa: BLE001
                pass
            # QLineEdit dua con tro ve CUOI khi nhan focus => dat lai ve DAU
            # (de doc duoc phan dau URL) sau khi focus da xu ly xong.
            try:
                QTimer.singleShot(0, lambda: self.o_url.setCursorPosition(0))
            except Exception:  # noqa: BLE001
                pass
            # Hook cho kiem chung: in noi dung hop thoai ra console.
            if os.environ.get("CAMAI_QT_IN_DIALOG", "").strip():
                _in("[CAMAI-QT] HOP-THOAI-URL: %s" % self.o_url.text())
                _in("[CAMAI-QT] HOP-THOAI-NUT: %s" % self.btn_sao_chep.text())
                # Tu kiem: sao chep URL vao clipboard (KHONG can bam phim).
                if os.environ.get("CAMAI_QT_TU_KIEM", "").strip():
                    self._sao_chep()
                    _in(
                        "[CAMAI-QT] HOP-THOAI-CLIPBOARD: %s"
                        % QGuiApplication.clipboard().text()
                    )

        def _sao_chep(self) -> None:
            url = self.o_url.text()
            try:
                QGuiApplication.clipboard().setText(url)
            except Exception as loi:  # noqa: BLE001
                _in("[CAMAI-QT] LOI sao chep: %s" % loi)
                return
            self.btn_sao_chep.setText("Đã sao chép")
            QTimer.singleShot(1500, lambda: self.btn_sao_chep.setText("Sao chép"))

    class _CuaSoCamAI(QMainWindow):
        """Cửa sổ desktop: webview + thanh trạng thái + nút mở trên điện thoại."""

        def __init__(
            self,
            url: str,
            url_lan: str,
            url_lan_san_dung: str = "",
            mat_khau: str = "",
            may_chu=None,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.setWindowTitle(TIEU_DE_CUA_SO)
            self.resize(1440, 900)
            self.setMinimumSize(1200, 760)
            self.setStyleSheet(QSS)
            self.may_chu = may_chu
            self.url_lan = url_lan
            self.url_lan_san_dung = url_lan_san_dung or url_lan
            self.url_may = url
            self.mat_khau = mat_khau
            self.tin_cuoi = ""
            self.da_tu_dang_nhap = False
            self.da_thu_kenh = False

            # --- webview ---
            self.web = QWebEngineView(self)
            self.trang = QWebEnginePage(self.web)
            self.web.setPage(self.trang)
            self.setCentralWidget(self.web)
            if hasattr(self.trang, "setBackgroundColor"):
                try:
                    self.trang.setBackgroundColor(QColor(MAU_NEN))
                except Exception:  # noqa: BLE001
                    pass

            # --- QWebChannel: trang web -> vong desktop ---
            self.kenh = QWebChannel(self.trang)
            self.bridge = _Bridge(self, url_may=url, mat_khau=mat_khau)
            self.kenh.registerObject("bridge", self.bridge)
            self.trang.setWebChannel(self.kenh)
            self.bridge.tin_hieu.connect(self._hien_trang_thai)

            # --- thanh trang thai duoi cung ---
            self.thanh = self.statusBar()
            self.thanh.setFixedHeight(30)
            self.lbl_trang_thai = QLabel("Đang khởi động…")
            self.lbl_trang_thai.setStyleSheet("color: %s;" % MAU_CHU_PHU)
            self.thanh.addWidget(self.lbl_trang_thai, 1)
            self.btn_dien_thoai = QPushButton("Điện thoại")
            self.btn_dien_thoai.setToolTip("Mở trên điện thoại: %s" % self.url_lan_san_dung)
            self.btn_dien_thoai.clicked.connect(self._mo_hop_thoai)
            self.thanh.addPermanentWidget(self.btn_dien_thoai)
            # Phim F2: mo hop thoai "Mo tren dien thoai" (tien khi ban phim).
            self.phim_f2 = QShortcut(QKeySequence("F2"), self)
            self.phim_f2.activated.connect(self._mo_hop_thoai)

            # --- quét tin nhắn dự phòng (trang web gọi window.camaiBao) ---
            self.bam_tin = QTimer(self)
            self.bam_tin.setInterval(400)
            self.bam_tin.timeout.connect(self._doc_tin)
            self.bam_tin.start()

            self.trang.loadFinished.connect(self._trang_tai_xong)
            self.trang.load(QUrl(url))

            # Hook kiem chung: mo hop thoai dien thoai TU DONG (KHONG can bam
            # phim) - dung khi kiem chung khong duoc gui phim vao may.
            if os.environ.get("CAMAI_QT_MO_HOP_THOAI", "").strip():
                QTimer.singleShot(3000, self._mo_hop_thoai)

        # ------------------------------------------------------------ trang thai
        def _hien_trang_thai(self, text: str) -> None:
            self.tin_cuoi = str(text)
            self.lbl_trang_thai.setText(self.tin_cuoi)
            _in("[CAMAI-QT] TRANG-THAI: %s" % self.tin_cuoi)

        def _trang_tai_xong(self, ok: bool) -> None:
            _in("[CAMAI-QT] TAI-TRANG: %s (%s)" % (self.trang.title(), "ok" if ok else "loi"))
            self.trang.runJavaScript(JS_KHOI_DONG)
            if ok:
                self._hien_trang_thai("Sẵn sàng")
            else:
                self._hien_trang_thai("Không tải được trang")
            QTimer.singleShot(1200, self._kiem_kenh)
            # Desktop tu dang nhap: cho trang web nap xong roi moi goi.
            if ok and self.mat_khau:
                QTimer.singleShot(1500, self._tu_dang_nhap)

        # ------------------------------------------------- tu dang nhap (desktop)
        def _tu_dang_nhap(self) -> None:
            """Tự đăng nhập hộ cho webview desktop (CHỈ máy này, điện thoại vẫn gõ tay).

            Cách 1 (ưu tiên): gọi thẳng fetch('/api/dang-nhap') từ trong trang.
            Cách 2 (dự phòng): JS gọi window.camaiDangNhap() qua QWebChannel,
            Python đăng nhập hộ rồi trả token về cho trang.
            """
            if self.da_tu_dang_nhap:
                return
            self.da_tu_dang_nhap = True
            try:
                self.trang.runJavaScript(JS_TU_DANG_NHAP)
                self.trang.runJavaScript(
                    "window.camaiTuDangNhap(%s)" % json.dumps(self.mat_khau)
                )
            except Exception as loi:  # noqa: BLE001
                _in("[CAMAI-QT] LOI tu dang nhap: %s" % loi)
            # Poll ket qua (token da luu trong localStorage).
            self.bam_dang_nhap = QTimer(self)
            self.bam_dang_nhap.setInterval(400)
            self.bam_dang_nhap.timeout.connect(self._kiem_dang_nhap)
            self.bam_dang_nhap.start()
            QTimer.singleShot(6000, self._het_dang_nhap)

        def _kiem_dang_nhap(self) -> None:
            """Đọc kết quả đăng nhập + token trong localStorage của trang."""
            def xu_ly(ket_qua):
                du_lieu = self._parse_kq(ket_qua)
                token = str(du_lieu.get("ls") or "")
                trang_thai = str(du_lieu.get("trang_thai") or "")
                kenh = str(du_lieu.get("kenh_trang_thai") or "")
                if trang_thai == "ok" and token:
                    self._xong_dang_nhap("fetch", token)
                    return
                if kenh == "ok" and token:
                    self._xong_dang_nhap("kenh", token)
                    return
                if trang_thai == "loi" and not self.da_thu_kenh:
                    # Fetch trong trang that bai -> thu duong du phong qua QWebChannel.
                    self.da_thu_kenh = True
                    _in(
                        "[CAMAI-QT] TU-DANG-NHAP: fetch that bai (%s) -> thu QWebChannel"
                        % (du_lieu.get("loi") or "khong ro")
                    )
                    try:
                        self.trang.runJavaScript(
                            "window.camaiDangNhap(%s)" % json.dumps(self.mat_khau)
                        )
                    except Exception as loi:  # noqa: BLE001
                        _in("[CAMAI-QT] LOI thu QWebChannel: %s" % loi)

            try:
                self.trang.runJavaScript(JS_DOC_KQ, xu_ly)
            except Exception:  # noqa: BLE001
                pass

        def _parse_kq(self, ket_qua) -> dict:
            try:
                du_lieu = json.loads(ket_qua) if ket_qua else {}
            except Exception:  # noqa: BLE001
                du_lieu = {}
            return du_lieu if isinstance(du_lieu, dict) else {}

        def _xong_dang_nhap(self, cach: str, token: str) -> None:
            self._dung_bam_dang_nhap()
            _in(
                "[CAMAI-QT] TU-DANG-NHAP: OK qua %s (token %d ky tu da luu vao localStorage)"
                % (cach, len(token))
            )
            # Kiem token that su dung duoc voi API (GET /api/trang-thai -> 200).
            ma, ok = _trang_thai_voi_token(self.url_may, token)
            _in(
                "[CAMAI-QT] TU-DANG-NHAP: GET /api/trang-thai -> HTTP %s (%s)"
                % (ma, "ok" if ok else "loi")
            )
            if ok:
                self._hien_trang_thai("Đã tự đăng nhập — sẵn sàng")
            else:
                self._hien_trang_thai(
                    "Không tự đăng nhập được — anh nhập mật khẩu trên webview"
                )
            # Hook cho kiem chung: in token da luu trong localStorage.
            if os.environ.get("CAMAI_QT_IN_TOKEN", "").strip():
                _in("[CAMAI-QT] TOKEN-LOCALSTORAGE: %s" % token)

        def _dung_bam_dang_nhap(self) -> None:
            if hasattr(self, "bam_dang_nhap"):
                self.bam_dang_nhap.stop()

        def _het_dang_nhap(self) -> None:
            """Hết thời gian chờ tự đăng nhập => báo rõ, KHÔNG crash."""
            self._dung_bam_dang_nhap()
            try:
                self.trang.runJavaScript(JS_DOC_KQ, self._biet_dang_nhap)
            except Exception:  # noqa: BLE001
                pass

        def _biet_dang_nhap(self, ket_qua) -> None:
            du_lieu = self._parse_kq(ket_qua)
            if du_lieu.get("ls"):
                return
            _in("[CAMAI-QT] TU-DANG-NHAP: het gio - can anh nhap mat khau tren webview")
            self._hien_trang_thai(
                "Không tự đăng nhập được — anh nhập mật khẩu trên webview"
            )

        def _kiem_kenh(self) -> None:
            """Kiểm tra kênh QWebChannel đã nối chưa (và tự kiểm nếu được yêu cầu)."""
            def xu_ly(ket_qua):
                try:
                    du_lieu = json.loads(ket_qua) if ket_qua else {}
                except Exception:  # noqa: BLE001
                    du_lieu = {}
                trang_thai = "da noi" if du_lieu.get("ready") else "chua noi"
                _in(
                    "[CAMAI-QT] KENH-WEB: %s (method=%s loi=%s)"
                    % (trang_thai, du_lieu.get("method"), du_lieu.get("loi") or "khong co")
                )
                tin = os.environ.get("CAMAI_QT_TU_KIEM", "").strip()
                if tin and du_lieu.get("ready"):
                    self.trang.runJavaScript(
                        "window.camaiBao(%s)" % json.dumps(tin, ensure_ascii=False)
                    )

            try:
                self.trang.runJavaScript(
                    "JSON.stringify({ready: !!window.__bridgeReady,"
                    " method: window.__bridgeMethod || '',"
                    " loi: window.__camaiLoi || ''})",
                    xu_ly,
                )
            except Exception:  # noqa: BLE001
                pass

        def _doc_tin(self) -> None:
            """Đường báo trạng thái dự phòng: không cần qwebchannel.js."""
            if not self.web.isVisible():
                return
            try:
                self.trang.runJavaScript(JS_DOC_TIN, self._nhan_tin)
            except Exception:  # noqa: BLE001
                pass

        def _nhan_tin(self, gia_tri) -> None:
            if not gia_tri:
                return
            self.bridge.thong_bao(str(gia_tri))

        # ------------------------------------------------------------ hop thoai
        def _mo_hop_thoai(self) -> None:
            hop = _HopThoaiDienThoai(self.url_lan, self.url_lan_san_dung, self)
            hop.exec()

        # ------------------------------------------------------------ dong app
        def closeEvent(self, su_kien) -> None:  # noqa: N802 - ten cua Qt
            _in("[CAMAI-QT] DONG-CUA-SO: tat may chu")
            self.bam_tin.stop()
            if self.may_chu is not None:
                try:
                    self.may_chu.tat()
                except Exception as loi:  # noqa: BLE001
                    _in("[CAMAI-QT] LOI tat may chu: %s" % loi)
            su_kien.accept()


else:  # noqa: E305 - PySide6 khong nap duoc
    _Bridge = None
    _TrangWeb = None
    _HopThoaiDienThoai = None
    _CuaSoCamAI = None


# ------------------------------------------------------------------ chay app
def _bao_loi(tieu_de: str, noi_dung: str) -> None:
    """Hiện lỗi bằng hộp thoại (chạy pythonw không có console để in)."""
    _in("%s: %s" % (tieu_de, noi_dung))
    try:
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

        hop = QMessageBox()
        hop.setWindowTitle("CamAI")
        hop.setIcon(QMessageBox.Icon.Critical)
        hop.setText(tieu_de)
        hop.setInformativeText(noi_dung)
        hop.exec()
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    if _LOI_PY:
        _in("CamAI: không nạp được PySide6: %s" % _LOI_PY)
        _in("Cài lại: .venv\\Scripts\\python.exe -m pip install PySide6==6.12.0")
        return 2

    # Tạo QApplication sớm để mọi lỗi đều hiện được bằng hộp thoại.
    app = QApplication(sys.argv)
    app.setApplicationName("CamAI")

    # Mat khau: co CAMAI_PASSWORD -> dung nguyen; khong co -> TU SINH ngau nhien
    # (double-click la chay, khong can cau hinh bien moi truong truoc).
    # PHAI gan vao os.environ TRUOC khi nap web_server.py (server doc bien nay
    # luc khoi tao _Phien).
    mat_khau, tu_sinh = _lay_hoac_sinh_mat_khau()
    if len(mat_khau) < DO_DAI_MAT_KHAU_TOI_THIEU:
        _in(
            "CamAI: mật khẩu quá ngắn (tối thiểu %d ký tự)." % DO_DAI_MAT_KHAU_TOI_THIEU
        )
        _bao_loi(
            "Mật khẩu quá ngắn",
            "Mật khẩu phải có ít nhất %d ký tự." % DO_DAI_MAT_KHAU_TOI_THIEU,
        )
        return 2
    if tu_sinh and CO_CONSOLE:
        # In ra console (chi khi co console) + canh bao doi moi lan khoi dong.
        # KHONG ghi ra file, KHONG ghi ra stderr.
        _in("[CAMAI-QT] MAT-KHAU-TU-SINH: %s" % mat_khau)
        _in("=" * 66)
        _in("  CAMAI: mat khau TAM SINH cho lan chay nay:")
        _in("      %s" % mat_khau)
        _in(
            "  (Mat khau doi moi LAN KHOI DONG app. Dien thoai go mat khau nay trong"
        )
        _in("   hop thoai 'Mo tren dien thoai'. Khong ghi mat khau ra file.)")
        _in("=" * 66)
    elif tu_sinh:
        # Chay bang pythonw => khong co console, chi hien trong hop thoai.
        _in("[CAMAI-QT] mat khau da duoc tu sinh (xem hop thoai 'Mo tren dien thoai').")

    # 1) Nạp web_server (chỉ đọc, không sửa).
    module, loi = _nap_web_server()
    if module is None:
        _in("CamAI: không nạp được web_server.py: %s" % loi)
        _bao_loi(
            "Không nạp được web_server.py",
            "%s\n\nHãy đóng ứng dụng và thử lại khi web_server.py sẵn sàng." % loi,
        )
        return 2

    # 2) Dựng server trong thread daemon.
    may_chu = None
    luong = None
    cong = _chon_cong()
    url_may = "http://127.0.0.1:%d" % cong
    try:
        module._chuan_bi_thu_muc()
    except Exception as loi:  # noqa: BLE001
        _in("CamAI: lỗi chuẩn bị thư mục: %s" % loi)
    try:
        may_chu = _MayChu(module.app, HOST_MAY_CHU, cong)
        luong = threading.Thread(
            target=may_chu.chay, name="camai-web-server", daemon=True
        )
        luong.start()
    except Exception as loi:  # noqa: BLE001
        _in("CamAI: không khởi động được server: %s" % loi)
        may_chu = None

    ok, ma = _cho_server_san_sang(cong)
    if ok:
        _in("[CAMAI-QT] SERVER-SAN-SANG: %s (HTTP %s)" % (url_may, ma))
    else:
        _in(
            "[CAMAI-QT] CANH-BAO: server chưa sẵn sàng sau %0.0f giây (%s)"
            % (THOI_GIAN_CHO_SERVER, url_may)
        )

    # 3) IP LAN cho điện thoại + URL SẴN DÙNG (có mã truy cập).
    ip = _ip_lan()
    url_lan = "http://%s:%d" % (ip, cong)
    khoa_truy_cap = str(getattr(module, "KHOA_TRUY_CAP", "") or "")
    url_lan_san_dung = url_lan + ("/?k=" + khoa_truy_cap if khoa_truy_cap else "/")
    _in("=" * 66)
    _in("  CamAI - vỏ desktop (PySide6 + QWebEngineView)")
    _in("  Trên máy tính : %s" % url_may)
    _in("  Trên điện thoại: %s" % url_lan)
    _in("  (điện thoại cùng Wi-Fi, mở URL SẴN DÙNG trong hộp thoại là vào thẳng)")
    _in("[CAMAI-QT] URL-LAN: %s" % url_lan)
    if CO_CONSOLE:
        # URL sẵn dùng chứa mã truy cập: chỉ in khi có console thật.
        _in("[CAMAI-QT] URL-LAN-SAN-DUNG: %s" % url_lan_san_dung)
    _in("=" * 66)

    # 4) Mở cửa sổ.
    cua_so = _CuaSoCamAI(url_may, url_lan, url_lan_san_dung, mat_khau, may_chu)
    cua_so.show()

    ma = app.exec()

    # 5) Dọn dẹp: tắt server, không để lại process treo.
    if may_chu is not None:
        try:
            may_chu.tat()
        except Exception:  # noqa: BLE001
            pass
    if luong is not None:
        luong.join(timeout=THOI_GIAN_DONG_SERVER)
        if luong.is_alive():
            _in("[CAMAI-QT] CANH-BAO: thread server chưa dừng, ép thoát")
    _in("[CAMAI-QT] KET-THUC")
    return ma


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as loi:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        _in("CamAI: lỗi không mong muốn: %s" % loi)
        sys.exit(1)
