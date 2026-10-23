"""
Kiem chung UI web CamAI (giao_dien_web/index.html).

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_ui_web.py

Script tu kiem tra 6 phan:

  A. TINH FILE (khong can trinh duyet)
     A1. File ton tai, UTF-8 KHONG BOM, chi LF (khong CRLF).
     A2. KHONG co tai nguyen ngoai (http:// hoac https://) - app phai chay offline.
     A3. Dem so <input>/<select>/<button> theo tung nhom (12 nhom) doc truc tiep
         tu file HTML.
     A4. Dem so control thuc te cua 12 nhom trong gui.py (dung ast) va so sanh.
         - moi nhom phai >= 1 control
         - TONG so control UI phai >= TONG so control cua gui.py

  B. CHUP ANH THAT (server that + Edge headless)
     B1. Chay web_server.py o CONG RIENG (8798).
     B2. Chup 3 kich thuoc: 1440x900, 820x1180, 390x844 -> _kk_out/ui_web/
         - uu tien: msedge.exe --headless=new --screenshot=...
         - fallback: Playwright dieu khien Edge da cai
     B3. Do trang ngang (scrollWidth > clientWidth) - phai KHONG tran ngang.
     B4. Dem control trong DOM thuc te + bat loi JavaScript.

  C. KIEM CHUNG LAI _kk_kiem_web_server.py (chay rieng, khong chay trong script nay
     de khong tranh cong 8799).

KHONG hardcode mat khhau: sinh mat khau ngau nhien roi truyen qua bien moi truong
CAMAI_PASSWORD cho subprocess.
"""

from __future__ import annotations

import ast
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser

APP_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_UI = os.path.join(APP_DIR, "giao_dien_web", "index.html")
FILE_GUI = os.path.join(APP_DIR, "gui.py")
THU_MUC_OUT = os.path.join(APP_DIR, "_kk_out", "ui_web")
FILE_BOOTSTRAP = os.path.join(APP_DIR, "giao_dien_web", "_kk_dang_nhap.html")
CONG = 8798
BASE = "http://127.0.0.1:%d" % CONG
VIDEO_MAU = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")

MSEDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
KICH_THUOC = [(1440, 900), (820, 1180), (390, 844)]

KET_QUA: list[tuple[str, bool, str]] = []


def _ghi(ten: str, ok: bool, ghi_chu: str = "") -> None:
    KET_QUA.append((ten, ok, ghi_chu))
    print("[%s] %-52s %s" % ("PASS" if ok else "FAIL", ten, ghi_chu), flush=True)


def _in(text: str = "") -> None:
    print(text, flush=True)


# ====================================================================== A
# A1. ENCODING / DONG CUOI FILE
def kiem_tra_tinh_file() -> None:
    _in("=" * 78)
    _in("A. KIEM TRA TINH FILE")
    _in("=" * 78)
    if not os.path.isfile(FILE_UI):
        _ghi("File UI ton tai", False, FILE_UI)
        return
    _ghi("File UI ton tai", True, "%d byte" % os.path.getsize(FILE_UI))

    raw = open(FILE_UI, "rb").read()
    co_bom = raw[:3] == b"\xef\xbb\xbf"
    _ghi("UTF-8 KHONG BOM", not co_bom, "BOM=%s" % co_bom)

    try:
        text = raw.decode("utf-8")
        ok_utf8 = True
    except UnicodeDecodeError as exc:
        text = ""
        ok_utf8 = False
        _in("  loi giai ma: %s" % exc)
    _ghi("Giai ma UTF-8 duoc", ok_utf8, "charset=utf-8")

    n_cr = raw.count(b"\r")
    n_crlf = raw.count(b"\r\n")
    _ghi("Chi xuong dong LF (khong CRLF)", n_cr == 0,
         "CR=%d, CRLF=%d" % (n_crlf, n_cr))

    # A2. tai nguyen ngoai
    ngoai = []
    for mo in re.finditer(r"https?://[^\s\"'<>)\\]+", text):
        url = mo.group(0)
        if url.startswith("http://www.w3.org/"):     # namespace XML, khong tai ve
            continue
        dong = text.count("\n", 0, mo.start()) + 1
        ngoai.append((dong, url))
    if ngoai:
        for dong, url in ngoai:
            _in("  dong %d: %s" % (dong, url))
    _ghi("KHONG tai tai nguyen ngoai (offline)", not ngoai,
         "so_url_ngoai=%d" % len(ngoai))

    # them: khong co <script src> hay <link href> tro ra ngoai
    the_ngoai = re.findall(r"<(?:script|link)\b[^>]*\b(?:src|href)\s*=\s*[\"']([^\"']+)",
                           text, re.I)
    the_ngoai = [u for u in the_ngoai if not u.startswith("#") and u != ""]
    _ghi("Khong co <script src>/<link href> tro ngoai", not the_ngoai,
         "so=%d %s" % (len(the_ngoai), the_ngoai[:5]))

    # A4 (v3.9): UI MOI - khong con form mat khau, co man huong dan.
    co_input_mk = '<input type="password"' in text
    _ghi("UI KHONG con form mat khau (v3.9)", not co_input_mk,
         "co_input_password=%s" % co_input_mk)
    _ghi("UI co man huong dan + nut 'Lay duong dan co ma'",
         "Lấy đường dẫn có mã" in text and "Mở bằng đường dẫn có mã" in text,
         "co_nut=%s co_huong_dan=%s"
         % ("Lấy đường dẫn có mã" in text,
            "Mở bằng đường dẫn có mã" in text))


# ====================================================================== A3
class _DemControl(HTMLParser):
    """Dem <input>/<select>/<button> trong tung <details data-nhom=...>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.dem: dict[str, int] = {}
        self.tieu_de: dict[str, str] = {}
        self._nhom: list[str] = []
        self._summary: list[bool] = []
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "details":
            ten = d.get("data-nhom", "")
            self._nhom.append(ten)
            self._summary.append(False)
            self.dem.setdefault(ten, 0)
            self._text = []
            return
        if tag == "summary":
            if self._summary:
                self._summary[-1] = True
                self._text = []
            return
        if tag in ("input", "select", "button") and self._nhom:
            ten = self._nhom[-1]
            self.dem[ten] = self.dem.get(ten, 0) + 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "summary" and self._summary and self._summary[-1]:
            self._summary[-1] = False
            ten = self._nhom[-1] if self._nhom else ""
            self.tieu_de[ten] = " ".join("".join(self._text).split())
            self._text = []
            return
        if tag == "details":
            if self._nhom:
                self._nhom.pop()
                self._summary.pop()

    def handle_data(self, data):
        if self._summary and self._summary[-1]:
            self._text.append(data)


TEN_NHOM_UI = [
    ("phat_hien", "Phát hiện người"),
    ("mat", "Nhận diện khuôn mặt"),
    ("dem", "Đếm ra vào"),
    ("vung", "Canh vùng"),
    ("clip", "Lưu clip khi có sự kiện"),
    ("vat_the", "Thêm vật thể khác"),
    ("tach_o", "Nhận người ở xa (chậm hơn)"),
    ("bien_so", "Đọc biển số xe"),
    ("tu_chup", "Tự chụp ảnh khi có sự kiện"),
    ("canh_bao", "Cảnh báo (gửi tin ra ngoài)"),
    ("model", "Thông tin mô hình AI"),
    ("thiet_bi", "Máy này chạy bằng gì"),
]

# ten nhom trong gui.py -> ten ham tao control (None = nhom chi co 1 checkbox chinh)
TEN_NHOM_GUI = {
    "Phát hiện người": "_n_phat_hien",
    "Nhận diện khuôn mặt": "_n_mat",
    "Đếm ra vào": None,
    "Canh vùng": "_n_vung",
    "Lưu clip khi có sự kiện": "_n_clip",
    "Thêm vật thể khác": "_n_vat_the",
    "Nhận người ở xa (chậm hơn)": "_n_tach_o",
    "Đọc biển số xe": "_n_bien_so",
    "Tự chụp ảnh khi có sự kiện": "_n_tu_chup",
    "Cảnh báo (gửi tin ra ngoài)": "_n_canh_bao",
    "Thông tin mô hình AI": "_n_model",
    "Máy này chạy bằng gì": "_n_thiet_bi",
}
WIDGET = ("CTkEntry", "CTkCheckBox", "CTkOptionMenu", "CTkButton",
          "CTkComboBox", "CTkSlider", "CTkSwitch", "_checkbox")


def _dem_widget_node(node) -> int:
    """Dem widget trong 1 node (ast).

    XU LY VONG FOR: neu than vong tao widget va bien lap khai bao bang
    tuple/list co N phan tu thi dem N widget (giong luc chay that).
    """
    if isinstance(node, ast.For):
        so = sum(_dem_widget_node(x) for x in node.body)
        n_item = 1
        it = node.iter
        if isinstance(it, (ast.Tuple, ast.List)):
            n_item = max(1, len(it.elts))
        return so * n_item
    n = 0
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr in WIDGET:
        n += 1
    for x in ast.iter_child_nodes(node):
        n += _dem_widget_node(x)
    return n


def dem_control_gui() -> dict[str, int]:
    """Dem control that cua 12 nhom trong gui.py (dung ast, khong do chuoi)."""
    tree = ast.parse(open(FILE_GUI, "r", encoding="utf-8").read())
    lop = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(
                isinstance(f, ast.FunctionDef) and f.name == "_khung_tinh_nang"
                for f in node.body):
            lop = node
            break
    if lop is None:
        return {}

    # 1. ten nhom + co checkbox chinh khong
    nhom: list[tuple[str, int]] = []
    for node in ast.walk(lop):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_them_nhom"):
            continue
        if len(node.args) < 3:
            continue
        ten = node.args[2].value
        co = True
        for kw in node.keywords:
            if kw.arg == "co_checkbox" and isinstance(kw.value, ast.Constant):
                co = bool(kw.value.value)
        nhom.append((ten, 1 if co else 0))

    # 2. so widget trong tung ham _n_*
    dem_widget = {}
    for f in lop.body:
        if not isinstance(f, ast.FunctionDef) or not f.name.startswith("_n_"):
            continue
        dem_widget[f.name] = sum(_dem_widget_node(x) for x in f.body)

    ket_qua: dict[str, int] = {}
    for ten, master in nhom:
        ham = TEN_NHOM_GUI.get(ten)
        ket_qua[ten] = master + (dem_widget.get(ham, 0) if ham else 0)
    return ket_qua


def kiem_tra_so_control(text: str) -> None:
    _in("")
    _in("-" * 78)
    _in("A3/A4. SO CONTROL: UI WEB (doc tu file) vs gui.py (dem bang ast)")
    _in("-" * 78)
    p = _DemControl()
    p.feed(text)

    dem_gui = dem_control_gui()

    _in("")
    _in("  %-34s %8s %8s %8s %s"
        % ("NHOM", "UI", "GUI", "CHENH", "TIEU DE TRONG UI"))
    _in("  " + "-" * 74)
    tong_ui = 0
    tong_gui = 0
    for key, ten in TEN_NHOM_UI:
        n_ui = p.dem.get(key, 0)
        n_gui = dem_gui.get(ten, -1)
        tong_ui += n_ui
        tong_gui += max(0, n_gui)
        _in("  %-34s %8d %8d %8s  %s"
            % (ten[:34], n_ui, n_gui,
               ("+" + str(n_ui - n_gui)) if n_ui >= n_gui else str(n_ui - n_gui),
               (p.tieu_de.get(key, "") or "(THIEU NHOM)")[:28]))
    _in("  " + "-" * 74)
    _in("  %-34s %8d %8d" % ("TONG", tong_ui, tong_gui))
    _in("")

    # moi nhom phai >= 1 control
    thieu = [ten for key, ten in TEN_NHOM_UI if p.dem.get(key, 0) < 1]
    _ghi("Moi nhom trong UI co >= 1 control", not thieu,
         "thieu: %s" % (", ".join(thieu) if thieu else "khong"))

    # du 12 nhom, dung ten
    sai_ten = []
    for key, ten in TEN_NHOM_UI:
        tieu_de = p.tieu_de.get(key, "")
        if not tieu_de:
            sai_ten.append(ten + " (khong tim thay)")
        elif ten.split("(")[0].strip().lower() not in tieu_de.lower():
            sai_ten.append("%s -> '%s'" % (ten, tieu_de))
    _ghi("Dung 12 nhom dung ten gui.py", not sai_ten,
         "; ".join(sai_ten) if sai_ten else "12/12 khop")

    _ghi("TONG control UI >= TONG control gui.py", tong_ui >= tong_gui,
         "UI=%d, gui.py=%d" % (tong_ui, tong_gui))

    # so control gui.py phai doc duoc (khong phai -1)
    _ghi("Dem duoc control gui.py cho ca 12 nhom",
         len(dem_gui) == 12 and all(v >= 0 for v in dem_gui.values()),
         "so_nhom_gui=%d" % len(dem_gui))


# ====================================================================== B
def _req(duong, method="GET", data=None, headers=None, token=None, timeout=120):
    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    if token:
        h["X-Camai-Token"] = token
    r = urllib.request.Request(BASE + duong, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _cho_server(proc, so_giay=120) -> bool:
    het = time.time() + so_giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        try:
            status, _, _ = _req("/", timeout=5)
            if status == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def _kich_thuoc_png(path: str) -> tuple[int, int]:
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return (0, 0)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


def _viet_bootstrap(token: str) -> None:
    html = (
        "<!doctype html><meta charset=\"utf-8\"><title>kk</title>"
        "<script>try{localStorage.setItem('camai_token','%s');}catch(e){}"
        "location.replace('/');</script>" % token
    )
    with open(FILE_BOOTSTRAP, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


def _xoa_bootstrap() -> None:
    try:
        if os.path.isfile(FILE_BOOTSTRAP):
            os.remove(FILE_BOOTSTRAP)
    except OSError:
        pass


def chup_edge_cli(token: str) -> dict[str, str]:
    """Chup bang msedge.exe --headless=new --screenshot (khong can Playwright)."""
    ket_qua: dict[str, str] = {}
    if not os.path.isfile(MSEDGE):
        _in("  [Edge CLI] khong tim thay msedge.exe -> bo qua")
        return ket_qua
    _viet_bootstrap(token)
    profile = os.path.join(APP_DIR, "_kk_out", "_edge_profile")
    os.makedirs(profile, exist_ok=True)
    for rong, cao in KICH_THUOC:
        ten = "ui_edge_%dx%d.png" % (rong, cao)
        duong = os.path.join(THU_MUC_OUT, ten)
        if os.path.isfile(duong):
            os.remove(duong)
        cmd = [
            MSEDGE, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions",
            "--user-data-dir=" + profile,
            "--window-size=%d,%d" % (rong, cao),
            "--virtual-time-budget=9000",
            "--screenshot=" + duong,
            BASE + "/_kk_dang_nhap.html",
        ]
        try:
            subprocess.run(cmd, timeout=120, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except Exception as exc:  # noqa: BLE001
            _in("  [Edge CLI] %s -> loi: %s" % (ten, exc))
            continue
        w, h = _kich_thuoc_png(duong)
        if w and h:
            ket_qua["%dx%d" % (rong, cao)] = duong
            _in("  [Edge CLI] %-26s -> %dx%d px, %d byte"
                % (ten, w, h, os.path.getsize(duong)))
        else:
            _in("  [Edge CLI] %-26s -> KHONG tao duoc anh" % ten)
    _xoa_bootstrap()
    shutil.rmtree(profile, ignore_errors=True)
    return ket_qua


def chup_playwright(token: str, mat_khau: str, khoa: str = "") -> list[dict]:
    """Chup + do layout bang Playwright dieu khien Edge da cai."""
    from playwright.sync_api import sync_playwright

    ket_qua: list[dict] = []
    loi_js: list[str] = []
    loi_mang: list[str] = []
    with sync_playwright() as p:
        khoi_dong = None
        for thu in ({"executable_path": MSEDGE}, {}):
            if not os.path.isfile(MSEDGE) and "executable_path" in thu:
                continue
            try:
                khoi_dong = p.chromium.launch(headless=True, **thu)
                break
            except Exception as exc:  # noqa: BLE001
                _in("  [Playwright] khong khoi dong duoc (%s): %s"
                    % (list(thu)[0] if thu else "bundled", str(exc)[:120]))
        if khoi_dong is None:
            _ghi("Playwright chup anh duoc", False, "khong khoi dong duoc trinh duyet")
            return ket_qua

        try:
            ctx = khoi_dong.new_context(viewport={"width": 1440, "height": 900},
                                        device_scale_factor=1)
            page = ctx.new_page()
            gui_body: dict = {}

            def _bam_request(req):
                if "/api/phan-tich" in req.url and req.method == "POST":
                    try:
                        gui_body["data"] = json.loads(req.post_data or "{}")
                    except Exception:  # noqa: BLE001
                        gui_body["raw"] = req.post_data

            page.on("request", _bam_request)
            page.on("pageerror", lambda e: loi_js.append("pageerror: %s" % e))
            page.on("console", lambda m: loi_js.append("console.error: %s" % m.text)
                    if (m.type == "error" and "Failed to load resource" not in m.text)
                    else (loi_mang.append(m.text) if m.type == "error" else None))

            # v3.9: mo bang DUONG DAN CO MA => vao thang, khong co form mat khau.
            if khoa:
                page.goto(BASE + "/?k=" + khoa, wait_until="domcontentloaded", timeout=60000)
            else:
                page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
            _ghi("Dang nhap trong trinh duyet -> man chinh hien ra", True,
                 "URL %s" % page.url.replace(khoa, "<KHOA>"))
            co_form = page.query_selector("#form_dang_nhap")
            co_mk = page.query_selector('input[type="password"]')
            _ghi("Trinh duyet: KHONG co form mat khau (vao thang bang ?k=)",
                 co_form is None and co_mk is None,
                 "form=%s input_password=%s" % (co_form, co_mk))
            co_cookie = [c for c in ctx.cookies() if c["name"] == "camai_phien"]
            _ghi("Trinh duyet nhan duoc cookie phien 'camai_phien'",
                 bool(co_cookie), "so=%d" % len(co_cookie))

            page.wait_for_timeout(1200)

            # cho /api/cau-hinh nap xong (gioi han do may chu tra ve)
            try:
                page.wait_for_function(
                    "() => { const e=document.getElementById('o_vung_max');"
                    " return e && e.max == '10000'; }", timeout=15000)
                _ghi("UI nap /api/cau-hinh (gioi han do may chu tra ve)", True,
                     "o_vung_max.max=10000")
            except Exception:  # noqa: BLE001
                _ghi("UI nap /api/cau-hinh (gioi han do may chu tra ve)", False,
                     "khong thay gia tri gioi han tu API")

            # --- v3.9.1: KHUNG VIDEO LUON O TREN (sticky) o 3 kich thuoc ---
            # Cuon xuong roi do getBoundingClientRect().top cua khung video:
            # phai <= chieu cao thanh dau + 2px (video dinh ngay duoi thanh dau).
            ket_sticky = []
            for rong, cao in KICH_THUOC:
                page.set_viewport_size({"width": rong, "height": cao})
                page.wait_for_timeout(400)
                page.evaluate("() => window.scrollTo(0, 1200)")
                page.wait_for_timeout(400)
                do = page.evaluate(
                    "() => {"
                    " const d=document.documentElement;"
                    " const h=document.querySelector('.thanh-dau');"
                    " const v=document.querySelector('.khung-video');"
                    " const w=document.querySelector('.the-video-stick');"
                    " const hh=h?Math.round(h.getBoundingClientRect().height):0;"
                    " const vr=v?v.getBoundingClientRect():null;"
                    " return {hh:hh, st:w?getComputedStyle(w).position:'',"
                    "  top:vr?Math.round(vr.top):null,"
                    "  bottom:vr?Math.round(vr.bottom):null,"
                    "  w:vr?Math.round(vr.width):0, h:vr?Math.round(vr.height):0,"
                    "  vh:window.innerHeight,"
                    "  tranNgang:d.scrollWidth>d.clientWidth};"
                    "}")
                do["rong"] = rong
                do["cao"] = cao
                ket_sticky.append(do)
                _in("  [STICKY] %dx%d: header=%dpx, position=%s, video %dx%d, top=%s "
                    "(can <= %d), bottom=%s (man hinh %d)"
                    % (rong, cao, do["hh"], do["st"], do["w"], do["h"], do["top"],
                       do["hh"] + 2, do["bottom"], do["vh"]))
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(400)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(300)

            sai_sticky = [d for d in ket_sticky
                          if d["st"] != "sticky" or d["top"] is None
                          or d["top"] > d["hh"] + 2]
            _ghi("Khung video Dinh (sticky) o ca 3 kich thuoc",
                 not sai_sticky,
                 "sai: %s" % ([("%dx%d top=%s hh=%s" % (d["rong"], d["cao"], d["top"],
                                                      d["hh"])) for d in sai_sticky]
                              if sai_sticky else "1440x900, 820x1180, 390x844 OK"))
            trong_khung = [d for d in ket_sticky
                           if d["bottom"] is None or d["bottom"] > d["vh"] + 2]
            _ghi("Khung video nam trong khung nhin (khong can cuon)",
                 not trong_khung,
                 "sai: %s" % ([("%dx%d bottom=%s vh=%s" % (d["rong"], d["cao"],
                                                           d["bottom"], d["vh"]))
                               for d in trong_khung] if trong_khung else "3/3 OK"))
            sai_ti_le = [d for d in ket_sticky
                         if not d["w"] or abs((d["h"] / float(d["w"])) - 9.0 / 16.0) > 0.02]
            _ghi("Khung video giu ti le 16:9 (khong meo)", not sai_ti_le,
                 "sai: %s" % ([("%dx%d %dx%d" % (d["rong"], d["cao"], d["w"], d["h"]))
                               for d in sai_ti_le] if sai_ti_le else
                              ", ".join("%dx%d=%dx%d" % (d["rong"], d["cao"], d["w"], d["h"])
                                        for d in ket_sticky)))
            tran = [d for d in ket_sticky if d["tranNgang"]]
            _ghi("Khong tran ngang sau khi them khung video sticky", not tran,
                 "tran: %s" % ([("%dx%d" % (d["rong"], d["cao"])) for d in tran]
                               if tran else "khong"))

            # --- E2E: bam nut BAT DAU, chay phan tich that ---
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(400)
            nut_mau = page.query_selector_all("#luoi_video_mau button")
            if nut_mau:
                nut_mau[0].click()
                _in("  [E2E] bam nut video mau -> duong dan: %s"
                    % page.input_value("#o_duong_dan"))
                _ghi("Nut video mau dien duong dan vao o", True,
                     page.input_value("#o_duong_dan")[-40:])
            else:
                page.fill("#o_duong_dan", VIDEO_MAU)
            # dung video ngan de test nhanh (video mau 1 rat dai)
            page.fill("#o_duong_dan", VIDEO_MAU)
            _in("  [E2E] chay video ngan: %s" % VIDEO_MAU)
            page.click("#nut_chay")

            # --- v3.9.1: phai co spinner + overlay ngay (duoi 1 giay) ---
            page.wait_for_timeout(400)
            overlay = page.evaluate(
                "() => { const o=document.getElementById('overlay_busy');"
                " if(!o) return null;"
                " const cs=getComputedStyle(o);"
                " const hien = cs.display!=='none' && cs.visibility!=='hidden'"
                "   && parseFloat(cs.opacity||'1')>0.01 && o.offsetParent!==null;"
                " const v=document.querySelector('.vong-xoay');"
                " const csV=v?getComputedStyle(v):null;"
                " return {hien:hien,"
                "  chu:(document.getElementById('overlay_chu')||{}).textContent||'',"
                "  coSpinner:!!(v && csV && csV.animationName && csV.animationName!=='none')};"
                "}")
            _ghi("Bam BAT DAU -> overlay 'dang lam viec' hien ngay (<1s)",
                 bool(overlay and overlay.get("hien")),
                 "chu=%r" % ((overlay or {}).get("chu", "")[:60]))
            _ghi("Overlay co spinner CSS (khong dung emoji)",
                 bool(overlay and overlay.get("coSpinner")),
                 "animationName=%s" % (overlay or {}).get("coSpinner"))
            _ghi("Overlay co chu 'dang nap model' (tieng Viet, dau dau)",
                 "nạp model" in ((overlay or {}).get("chu", "").lower()),
                 "chu=%r" % ((overlay or {}).get("chu", "")[:60]))
            page.screenshot(path=os.path.join(
                THU_MUC_OUT, "ui_dang_nap_model_1440x900.png"))
            _in("  [E2E] da chup anh luc dang nap model")

            page.wait_for_timeout(2500)
            tb = page.inner_text("#noi_dung_thong_bao")
            _in("  [E2E] thong bao sau khi bam BAT DAU: %r" % tb[:110])
            _ghi("Bam BAT DAU khong bao loi", "không chạy được" not in tb
                 and "Chưa chọn" not in tb and "Cần bật" not in tb,
                 tb[:90])

            # --- body POST /api/phan-tich do UI gui len ---
            body = gui_body.get("data") or {}
            _in("  [E2E] body POST /api/phan-tich (%d khoa): %s"
                % (len(body), ", ".join(sorted(body.keys()))))
            can_co = ["conf", "model", "thiet_bi", "show_box", "show_label",
                      "pixelate", "no_face", "face_threshold", "min_face",
                      "face_every", "faces_dir", "show_line", "vung_nhay",
                      "vung_max", "canh_lau", "clip_giay", "clip_ghi_tat_ca",
                      "nhan_vat_the", "lop", "dem_phuong_tien", "tach_o",
                      "doc_bien_so", "bien_so_dir", "bien_so_tin_cay",
                      "bien_so_nhoan_lai_giay", "tu_chup_nhoan_lai_giay",
                      "bat_canh_bao", "canh_bao_mo_phong", "canh_bao_go",
                      "canh_bao_gioi_han"]
            thieu = [k for k in can_co if k not in body]
            _ghi("Body gui len co day du field AnalysisConfig", not thieu,
                 "thieu: %s" % thieu if thieu else "%d/%d" % (len(can_co), len(can_co)))
            _ghi("Body KHONG gui input/output (server so huu)",
                 "input" not in body and "output" not in body,
                 "input=%s output=%s" % ("input" in body, "output" in body))
            can_cu = ["duong_dan", "nhan_mat", "dem_ra_vao", "vat_the",
                      "canh_vung", "ve_khung", "ve_nhan", "lam_mo", "nguong_mat",
                      "luu_clip"]
            thieu_cu = [k for k in can_cu if k not in body]
            _ghi("Body van giu hop dong CU (server cu chay duoc)", not thieu_cu,
                 "thieu: %s" % thieu_cu if thieu_cu else "10/10")

            thay_busy = False
            thay_xong = False
            het = time.time() + 300
            trang = {}
            while time.time() < het:
                _, body, _ = _req("/api/trang-thai", token=token)
                try:
                    trang = json.loads(body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    time.sleep(1)
                    continue
                if trang.get("busy"):
                    if not thay_busy:
                        page.wait_for_timeout(1500)
                        page.screenshot(path=os.path.join(
                            THU_MUC_OUT, "ui_pw_dang_chay_1440x900.png"))
                        _in("  [E2E] da chup anh luc dang chay")
                    thay_busy = True
                if thay_busy and not trang.get("busy") and trang.get("xong"):
                    thay_xong = True
                    break
                if trang.get("loi"):
                    break
                time.sleep(1)
            _ghi("E2E: phan tich chay that (busy -> xong)", thay_busy and thay_xong,
                 "busy=%s xong=%s loi=%r" % (thay_busy, thay_xong,
                                            (trang or {}).get("loi")))
            page.wait_for_timeout(1200)
            so_ui = page.evaluate(
                "() => ({nguoi:document.getElementById('s_nguoi').textContent,"
                " xe:document.getElementById('s_xe').textContent,"
                " khung:document.getElementById('dong_khung_hinh').textContent,"
                " ket_qua:document.getElementById('dong_ket_qua').textContent})")
            _in("  [E2E] so dem tren UI: %s" % json.dumps(so_ui, ensure_ascii=False))
            _ghi("E2E: UI hien so dem + thong tin khung hinh",
                 bool(so_ui["khung"]) and "Khung hình" in so_ui["khung"],
                 so_ui["khung"][:90])

            # --- 2 nut xem ket qua cua nhom 8 va nhom 9 ---
            page.evaluate("() => { for (const k of ['bien_so','tu_chup']) {"
                          " const d=document.querySelector('details[data-nhom=\"'+k+'\"]');"
                          " if (d) d.open = true; } }")
            page.wait_for_timeout(300)
            page.click("#nut_xem_bien_so")
            page.wait_for_timeout(1500)
            bs = page.inner_text("#dong_bien_so")
            _ghi("Nut 'Xem bien so da doc' tra ve du lieu", "chưa có API" not in bs,
                 bs[:70])
            page.click("#nut_xem_anh_su_kien")
            page.wait_for_timeout(1500)
            ak = page.inner_text("#dong_anh_su_kien")
            _ghi("Nut 'Xem anh su kien da chup' tra ve du lieu",
                 "chưa có API" not in ak, ak[:70])

            # --- 3. NHOM 2 / 4 / 10 / 11 / 12: nut da lam THAT ---
            page.evaluate("() => { for (const k of ['mat','vung','canh_bao',"
                          "'model','thiet_bi']) {"
                          " const d=document.querySelector('details[data-nhom=\"'+k+'\"]');"
                          " if (d) d.open = true; } }")
            page.wait_for_timeout(400)

            co_form = page.evaluate(
                "() => { const t=document.getElementById('o_ten_nguoi_quen');"
                " const a=document.getElementById('o_anh_nguoi_quen');"
                " const c=document.getElementById('canvas_vung');"
                " return {ten: !!t, anh: !!a, kieu: a ? a.type : '',"
                "  canvas: !!c, nut: !!document.getElementById('nut_dang_ky_nguoi_quen'),"
                "  nut_luu: !!document.getElementById('nut_luu_vung')}; }")
            _ghi("Nhom 2/4: co form dang ky nguoi quen + canvas ve vung",
                 co_form["ten"] and co_form["anh"] and co_form["kieu"] == "file"
                 and co_form["canvas"] and co_form["nut"] and co_form["nut_luu"],
                 json.dumps(co_form))

            # Bam "Dang ky" ma chua nhap ten -> thong bao loi tieng Viet (khong loi chung chung)
            page.click("#nut_dang_ky_nguoi_quen")
            page.wait_for_timeout(700)
            tb = page.inner_text("#noi_dung_thong_bao")
            _ghi("Nut 'Dang ky nguoi quen' phan hoi bang thong bao tieng Viet",
                 "Chưa nhập tên người quen." in tb, tb[:80])

            # Bam "Ve vung" khi chua co khung hinh -> huong dan ro rang
            page.click("#nut_ve_vung")
            page.wait_for_timeout(700)
            tb = page.inner_text("#noi_dung_thong_bao")
            _ghi("Nut 'Ve vung' huong dan ro rang khi chua co khung hinh",
                 "BẮT ĐẦU" in tb and "chưa có khung hình" in tb.lower(), tb[:90])

            # Thu canh bao (chi thu - khong gui ra ngoai)
            page.click("#nut_thu_canh_bao")
            page.wait_for_timeout(3000)
            tb = page.inner_text("#noi_dung_thong_bao")
            noi_dung_modal = page.inner_text("#modal_ket_qua_noi_dung")
            _ghi("Nut 'Thu gui 1 canh bao' tra ve noi dung canh bao that",
                 "cảnh báo" in noi_dung_modal.lower(),
                 noi_dung_modal[:70].replace("\n", " "))
            _ghi("Nut 'Thu gui 1 canh bao' bao ro KHONG gui ra ngoai",
                 "không" in tb.lower() and "gửi ra ngoài" in tb.lower(), tb[:80])
            page.click("#modal_ket_qua_dong")
            page.wait_for_timeout(300)

            # Thong tin mo hinh AI
            page.click("#nut_thong_tin_model")
            page.wait_for_timeout(20000)
            noi_dung_modal = page.inner_text("#modal_ket_qua_noi_dung")
            _ghi("Nut 'Xem thong tin mo hinh AI' tra ve du lieu that",
                 "chưa có API" not in noi_dung_modal
                 and "thư viện" in noi_dung_modal.lower()
                 and "trọng số" in noi_dung_modal.lower(),
                 noi_dung_modal[:70].replace("\n", " "))
            page.click("#modal_ket_qua_dong")
            page.wait_for_timeout(300)

            # Thong tin thiet bi
            page.click("#nut_thong_tin_thiet_bi")
            page.wait_for_timeout(20000)
            noi_dung_modal = page.inner_text("#modal_ket_qua_noi_dung")
            _ghi("Nut 'Xem thong tin thiet bi' tra ve du lieu that",
                 "chưa có API" not in noi_dung_modal and "RAM" in noi_dung_modal,
                 noi_dung_modal[:70].replace("\n", " "))
            page.click("#modal_ket_qua_dong")
            page.wait_for_timeout(300)

            page.wait_for_timeout(500)

            for rong, cao in KICH_THUOC:
                page.set_viewport_size({"width": rong, "height": cao})
                page.wait_for_timeout(700)
                ten = "ui_pw_%dx%d.png" % (rong, cao)
                duong = os.path.join(THU_MUC_OUT, ten)
                page.screenshot(path=duong)
                duong_full = os.path.join(THU_MUC_OUT,
                                          "ui_pw_%dx%d_full.png" % (rong, cao))
                page.screenshot(path=duong_full, full_page=True)

                do = page.evaluate(
                    "() => {"
                    " const d=document.documentElement;"
                    " return {sw:d.scrollWidth, cw:d.clientWidth,"
                    "  sh:d.scrollHeight,"
                    "  trang:document.querySelectorAll('#man_chinh details[data-nhom]').length,"
                    "  ctl:document.querySelectorAll('#man_chinh details[data-nhom] "
                    "input, #man_chinh details[data-nhom] select, "
                    "#man_chinh details[data-nhom] button').length,"
                    "  tao_dong:[...document.querySelectorAll('[id^=\"o_cfg_\"]')]"
                    "   .map(e=>e.id),"
                    "  trung:[...document.querySelectorAll('#man_chinh [data-truong]')]"
                    "   .map(e=>e.getAttribute('data-truong'))"
                    "   .filter((v,i,a)=>a.indexOf(v)!==i),"
                    "  nhom:[...document.querySelectorAll('#man_chinh details[data-nhom]')]"
                    "   .map(e=>e.dataset.nhom+':'+e.querySelectorAll('input,select,button').length)"
                    " }; }")
                w, h = _kich_thuoc_png(duong)
                wf, hf = _kich_thuoc_png(duong_full)
                trang_ngang = do["sw"] > do["cw"] + 1
                _in("  [Playwright] %-22s viewport %dx%d px | trang-day %dx%d px | "
                    "scrollW=%d clientW=%d | tran ngang=%s"
                    % (ten, w, h, wf, hf, do["sw"], do["cw"], trang_ngang))
                if do["tao_dong"]:
                    _in("  [Playwright] control sinh them tu /api/cau-hinh: %s"
                        % ", ".join(do["tao_dong"]))
                ket_qua.append({
                    "ten": ten, "rong": rong, "cao": cao,
                    "kich_thuoc": (w, h), "kich_thuoc_full": (wf, hf),
                    "tran_ngang": trang_ngang,
                    "so_nhom": do["trang"], "so_control": do["ctl"],
                    "chi_tiet_nhom": do["nhom"], "trung_ten": do["trung"],
                    "duong": duong, "duong_full": duong_full,
                })

            # drawer tren may tinh be (820px)
            page.set_viewport_size({"width": 820, "height": 1180})
            page.wait_for_timeout(400)
            page.click("#nut_menu")
            page.wait_for_timeout(700)
            duong_drawer = os.path.join(THU_MUC_OUT, "ui_pw_820x1180_drawer.png")
            page.screenshot(path=duong_drawer)
            drawer = page.evaluate(
                "() => { const e=document.getElementById('cot_trai');"
                " const r=e.getBoundingClientRect();"
                " return {mo:e.classList.contains('mo'), x:Math.round(r.x),"
                "  w:Math.round(r.width)}; }")
            w, h = _kich_thuoc_png(duong_drawer)
            _in("  [Playwright] drawer 820px: mo=%s, x=%s, rong=%s -> %dx%d px"
                % (drawer["mo"], drawer["x"], drawer["w"], w, h))
            ket_qua.append({"ten": "ui_pw_820x1180_drawer.png",
                            "rong": 820, "cao": 1180,
                            "kich_thuoc": (w, h), "kich_thuoc_full": (0, 0),
                            "tran_ngang": False, "so_nhom": 0, "so_control": 0,
                            "chi_tiet_nhom": [], "trung_ten": [],
                            "duong": duong_drawer,
                            "duong_full": duong_drawer})
            _ghi("Drawer mo duoc tren 820px", bool(drawer["mo"]) and drawer["x"] >= 0,
                 "mo=%s x=%s" % (drawer["mo"], drawer["x"]))

            _ghi("Khong co loi JavaScript tren man hinh", not loi_js,
                 "; ".join(loi_js[:4]) if loi_js else "sach")
            if loi_mang:
                _in("  [Playwright] loi MANG (khong phai loi JS): %s"
                    % " | ".join(sorted(set(loi_mang))[:4]))

            ctx.close()
        finally:
            try:
                khoi_dong.close()
            except Exception:  # noqa: BLE001
                pass
    return ket_qua


# ====================================================================== main
def main() -> int:
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    kiem_tra_tinh_file()
    text = open(FILE_UI, "r", encoding="utf-8").read()
    kiem_tra_so_control(text)

    _in("")
    _in("=" * 78)
    _in("B. CHUP ANH THAT (server that + Edge headless)")
    _in("=" * 78)

    mat_khau = secrets.token_urlsafe(12)
    env = os.environ.copy()
    env["CAMAI_PASSWORD"] = mat_khau
    env["PYTHONIOENCODING"] = "utf-8"
    # Cho phep doc khoa truy cap san dung tu log server (che do debug).
    env["CAMAI_DEBUG_KHOA"] = "1"
    log_path = os.path.join(APP_DIR, "_kk_out", "ui_web_server.log")
    log = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(APP_DIR, "web_server.py"), "--port", str(CONG)],
        cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        if not _cho_server(proc):
            _ghi("Server khoi dong", False, "khong san sang sau 120s")
            return 1
        _ghi("Server khoi dong", True, "cong %d" % CONG)

        # --- doc khoa truy cap san dung tu log server ---
        khoa = ""
        het = time.time() + 30
        while time.time() < het:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    noi_dung = f.read()
            except OSError:
                noi_dung = ""
            tim = re.search(
                r"URL san dung:\s*http://[0-9.]+:\d+/\?k=([A-Za-z0-9_\-]+)", noi_dung
            )
            if tim:
                khoa = tim.group(1)
                break
            time.sleep(0.5)
        _ghi("Server sinh khoa truy cap san dung (>= 32 ky tu)", len(khoa) >= 32,
             "do dai=%d ky tu" % len(khoa))
        if not khoa:
            return 1

        status, body, _ = _req("/api/dang-nhap", method="POST",
                               data={"mat_khauu": mat_khau})
        try:
            du_lieu = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            du_lieu = {}
        token = du_lieu.get("token") or ""
        _ghi("Dang nhap lay duoc token", bool(token), "status=%d" % status)
        if not token:
            return 1

        anh_cli = chup_edge_cli(token)
        _ghi("Edge headless chup duoc 3 anh", len(anh_cli) == 3,
             "so_anh=%d" % len(anh_cli))

        ket_pw = chup_playwright(token, mat_khau, khoa)

        trang = [k for k in ket_pw if k.get("tran_ngang")]
        _ghi("KHONG tran ngang o bat ky be rong nao", not trang,
             "cot tran ngang: %s" % [k["ten"] for k in trang] if trang else "khong")

        trung = []
        for k in ket_pw:
            trung += k.get("trung_ten", []) or []
        _ghi("Khong co 2 control cung mot field trong 1 nhom", not trung,
             "trung: %s" % sorted(set(trung)) if trung else "khong")

        for k in ket_pw:
            if k.get("so_nhom"):
                _ghi("DOM that co du 12 nhom (%dx%d)" % (k["rong"], k["cao"]),
                     k["so_nhom"] == 12,
                     "nhom=%d, control=%d" % (k["so_nhom"], k["so_control"]))
                break

        _in("")
        _in("  ANH DA LUU TRONG: %s" % THU_MUC_OUT)
        for ten in sorted(os.listdir(THU_MUC_OUT)):
            if not ten.lower().endswith(".png"):
                continue
            w, h = _kich_thuoc_png(os.path.join(THU_MUC_OUT, ten))
            _in("    %-34s %5d x %-5d  %8d byte"
                % (ten, w, h, os.path.getsize(os.path.join(THU_MUC_OUT, ten))))
    finally:
        _xoa_bootstrap()
        try:
            log.close()
        except Exception:  # noqa: BLE001
            pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        _ghi("Server tat sach", proc.poll() is not None, "exit=%s" % proc.poll())

    _in("")
    _in("=" * 78)
    tong = len(KET_QUA)
    do = sum(1 for _, ok, _ in KET_QUA if ok)
    for ten, ok, ghi_chu in KET_QUA:
        _in("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", ten, ghi_chu))
    _in("-" * 78)
    _in("  KET QUA _kk_kiem_ui_web.py: %d/%d PASS" % (do, tong))
    _in("=" * 78)
    return 0 if do == tong else 1


if __name__ == "__main__":
    sys.exit(main())
