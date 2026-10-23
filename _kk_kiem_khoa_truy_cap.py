"""
Kiem chung KHOA TRUY CAP SAN DUNG (v3.9) - CamAI web-first.

Kiem 1: GET / (khong co ?k=) -> 200, HTML KHONG co <input type="password">.
Kiem 2: GET /?k=<khoa dung> -> Set-Cookie phien -> /api/trang-thai -> 200.
Kiem 3: GET /?k=<khoa sai> -> KHONG Set-Cookie -> /api/trang-thai -> 401.
Kiem 4: POST /api/dang-nhap (mat khau dung) -> token -> /api/trang-thai -> 200.
Kiem 5: Mo UI trong trinh duyet THAT bang ?k=... -> vao thang, khong co form.
        chup anh 1440x900 va 390px.

Server chay TRONG TIEN TRINH (import web_server) de doc duoc KHOA_TRUY_CAP
(khoa KHONG duoc in ra console). Cong rieng 8801 - KHONG dung cong cua app
that cua anh.

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_khoa_truy_cap.py
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONG = 8801
BASE = "http://127.0.0.1:%d" % CONG
THU_MUC_OUT = os.path.join(APP_DIR, "_kk_out", "ui_web")
MSEDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

KET_QUA: list[tuple[bool, str, str]] = []


def _bao(ok: bool, ten: str, chi_tiet: str = "") -> bool:
    KET_QUA.append((ok, ten, chi_tiet))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", ten, (" - " + chi_tiet) if chi_tiet else ""))
    return ok


def _in(text: str = "") -> None:
    print(text, flush=True)


# ------------------------------------------------------------------ HTTP
class _Bo:
    """Bo request co cookie jar rieng (mo phong trinh duyet)."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(self.jar),
        )

    def go(self, duong: str, method: str = "GET", data=None, headers=None):
        """Tra (status, body_bytes, headers_dict)."""
        body = None
        head = dict(headers or {})
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            head["Content-Type"] = "application/json"
        yeu_cau = urllib.request.Request(BASE + duong, data=body, headers=head, method=method)
        try:
            with self.opener.open(yeu_cau, timeout=20) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as loi:
            return loi.code, loi.read(), dict(loi.headers or {})

    def cookie(self, ten: str) -> str:
        for ck in self.jar:
            if ck.name == ten:
                return ck.value or ""
        return ""


def _cho_server_san_sang(tong: float = 60.0) -> bool:
    het = time.time() + tong
    while time.time() < het:
        try:
            with urllib.request.build_opener(
                urllib.request.ProxyHandler({})
            ).open(BASE + "/", timeout=3) as resp:
                if resp.status < 500:
                    return True
        except urllib.error.HTTPError:
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def _head(headers: dict, ten: str) -> str:
    """Doc header KHONG phan biet hoa/thuong (uvicorn gui 'set-cookie')."""
    for k, v in (headers or {}).items():
        if str(k).lower() == ten.lower():
            return str(v)
    return ""


# ------------------------------------------------------------------ kiem 1-4
def _kiem_http(khoa: str, mat_khau: str) -> None:
    _in("\n" + "=" * 70)
    _in("KIEM 1-4: co che khoa truy cap tren HTTP")
    _in("=" * 70)

    # --- 1) GET / khong co ?k= ---
    bo = _Bo()
    status, body, _ = bo.go("/")
    html = body.decode("utf-8", "replace")
    co_form = '<input type="password"' in html
    co_nut = "Lấy đường dẫn có mã" in html
    co_huong_dan = "Mở bằng đường dẫn có mã" in html
    _bao(
        status == 200 and not co_form,
        "1a. GET / (khong ?k=) -> 200 va KHONG co form mat khau",
        "status=%d co_input_password=%s" % (status, co_form),
    )
    _bao(
        co_huong_dan and co_nut,
        "1b. UI co thong bao huong dan + nut 'Lay duong dan co ma'",
        "huong_dan=%s nut=%s" % (co_huong_dan, co_nut),
    )
    _bao(
        bo.cookie("camai_phien") == "",
        "1c. GET / khong ?k= -> KHONG cap phien (khong co cookie)",
        "cookie=%r" % bo.cookie("camai_phien"),
    )

    # --- 2) GET /?k=<dung> ---
    bo2 = _Bo()
    status, _, head = bo2.go("/?k=" + khoa)
    set_cookie = _head(head, "Set-Cookie")
    _bao(
        status == 200 and "camai_phien=" in set_cookie,
        "2a. GET /?k=<khoa dung> -> set cookie phien",
        "status=%d set_cookie=%r" % (status, set_cookie[:60]),
    )
    cookie = bo2.cookie("camai_phien")
    _bao(bool(cookie), "2b. Cookie 'camai_phien' nho trong trinh duyet", "gia tri dai %d ky tu" % len(cookie))
    status2, _, _ = bo2.go("/api/trang-thai")
    _bao(status2 == 200, "2c. GET /api/trang-thai voi cookie -> 200", "status=%d" % status2)

    # --- 3) GET /?k=<sai> ---
    bo3 = _Bo()
    khoa_sai = secrets.token_urlsafe(32)
    status3, _, head3 = bo3.go("/?k=" + khoa_sai)
    set3 = _head(head3, "Set-Cookie")
    _bao(
        "camai_phien=" not in set3 and bo3.cookie("camai_phien") == "",
        "3a. GET /?k=<khoa sai> -> KHONG cap phien",
        "set_cookie=%r" % set3[:60],
    )
    status4, _, _ = bo3.go("/api/trang-thai")
    _bao(status4 == 401, "3b. GET /api/trang-thai (khong phien) -> 401", "status=%d" % status4)

    # --- 4) POST /api/dang-nhap (du phong) ---
    bo4 = _Bo()
    status5, body5, _ = bo4.go("/api/dang-nhap", method="POST", data={"mat_khauu": mat_khau})
    try:
        du_lieu = json.loads(body5.decode("utf-8"))
    except Exception:  # noqa: BLE001
        du_lieu = {}
    token = du_lieu.get("token") or ""
    _bao(
        status5 == 200 and bool(token),
        "4a. POST /api/dang-nhap (mat khau dung) -> van tra token",
        "status=%d token=%d ky tu" % (status5, len(token)),
    )
    status6, _, _ = bo4.go("/api/trang-thai")
    _bao(status6 == 200, "4b. GET /api/trang-thai voi cookie sau dang nhap -> 200", "status=%d" % status6)

    # Token qua header (cach UI moi dung) cung phai chay.
    status7, _, _ = bo4.go("/api/trang-thai", headers={"X-Camai-Token": token})
    _bao(status7 == 200, "4c. GET /api/trang-thai voi header X-Camai-Token -> 200", "status=%d" % status7)

    # Mat khau sai van bi tu choi (khong noi loi bao mat).
    bo5 = _Bo()
    status8, body8, _ = bo5.go("/api/dang-nhap", method="POST", data={"mat_khauu": mat_khau + "x"})
    _bao(status8 != 200, "4d. POST /api/dang-nhap sai mat khau -> bi tu choi", "status=%d" % status8)

    # Khong co khoa => API van khoa (khong lo qua co che bao mat).
    _bao(
        status4 == 401,
        "4e. GET / khong khoa KHONG mo khoa API",
        "/api/trang-thai -> %d" % status4,
    )


# ------------------------------------------------------------------ kiem 5
def _kiem_browser(khoa: str) -> None:
    _in("\n" + "=" * 70)
    _in("KIEM 5: mo UI trong trinh duyet THAT bang duong dan co ma")
    _in("=" * 70)
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        _bao(False, "5a. Playwright nap duoc", "loi: %s" % exc)
        return

    os.makedirs(THU_MUC_OUT, exist_ok=True)
    loi_js: list[str] = []
    with sync_playwright() as p:
        khoi_dong = None
        for thu in ({"executable_path": MSEDGE}, {}):
            if not os.path.isfile(MSEDGE) and "executable_path" in thu:
                continue
            try:
                khoi_dong = p.chromium.launch(headless=True, **thu)
                break
            except Exception as exc:  # noqa: BLE001
                _in("  [Playwright] khong khoi dong duoc (%s): %s" % (list(thu)[0], str(exc)[:120]))
        if khoi_dong is None:
            _bao(False, "5a. Playwright chup anh duoc", "khong khoi dong duoc trinh duyet")
            return
        try:
            ctx = khoi_dong.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            page.on("pageerror", lambda e: loi_js.append("pageerror: %s" % e))

            # --- 5a) MO BANG DUONG DAN CO MA -> vao thang ---
            page.goto(BASE + "/?k=" + khoa, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
            _bao(True, "5a. Mo bang duong dan co ma -> vao thang (man chinh hien ra)",
                 "URL %s" % page.url.replace(khoa, "<KHOA>"))
            co_form = page.query_selector("#form_dang_nhap")
            co_input = page.query_selector('input[type="password"]')
            _bao(
                co_form is None and co_input is None,
                "5b. Khong co form mat khau nao trong trang (da vao thang)",
                "form=%s input_password=%s" % (co_form, co_input),
            )
            # Cookie phien phai duoc dat.
            cookies = [c for c in ctx.cookies() if c["name"] == "camai_phien"]
            _bao(bool(cookies), "5c. Trinh duyet nhan duoc cookie phien 'camai_phien'",
                 "so cookie=%d" % len(cookies))
            # Token phai duoc luu vao localStorage.
            token_ls = page.evaluate("() => localStorage.getItem('camai_token') || ''")
            _bao(bool(token_ls), "5d. Token phien duoc luu trong localStorage",
                 "%d ky tu" % len(token_ls))

            # --- 5e) API trong trinh duyet -> 200 ---
            ma = page.evaluate(
                "async () => { const r = await fetch('/api/trang-thai',"
                " {credentials:'same-origin'}); return r.status; }"
            )
            _bao(ma == 200, "5e. GET /api/trang-thai tu trong trinh duyet -> 200", "status=%s" % ma)

            # --- chup anh 1440x900 ---
            page.wait_for_timeout(1200)
            duong_1440 = os.path.join(THU_MUC_OUT, "ui_khoa_mo_1440x900.png")
            page.screenshot(path=duong_1440, full_page=False)
            _bao(os.path.isfile(duong_1440), "5f. Anh 1440x900 da luu", duong_1440)

            # --- chup anh 390px ---
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(800)
            duong_390 = os.path.join(THU_MUC_OUT, "ui_khoa_mo_390x844.png")
            page.screenshot(path=duong_390, full_page=False)
            _bao(os.path.isfile(duong_390), "5g. Anh 390x844 da luu", duong_390)

            # --- 5h) MO KHONG CO KHOA -> thong bao huong dan, KHONG co form ---
            # Context MOI (khong cookie) => dung nhu lan dau mo tren dien thoai.
            ctx2 = khoi_dong.new_context(viewport={"width": 1440, "height": 900})
            page2 = ctx2.new_page()
            page2.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
            page2.wait_for_selector("#man_dang_nhap:not(.an)", timeout=30000)
            page2.wait_for_timeout(3500)      # cho het thoi gian cho desktop
            co_form2 = page2.query_selector("#form_dang_nhap")
            co_input2 = page2.query_selector('input[type="password"]')
            _bao(
                co_form2 is None and co_input2 is None,
                "5h. Khong co ?k= -> van KHONG co form mat khau",
                "form=%s input_password=%s" % (co_form2, co_input2),
            )
            nut = page2.query_selector("#nut_lay_duong_dan")
            _bao(nut is not None, "5i. Khong co ?k= -> hien nut 'Lay duong dan co ma'",
                 "nut=%s" % (nut.inner_text() if nut else "KHONG CO"))
            tt = page2.query_selector("#tt_dang_nhap")
            _bao(
                bool(tt) and "Mở bằng đường dẫn có mã" in tt.inner_text(),
                "5j. Khong co ?k= -> hien thong bao huong dan tieng Viet",
                (tt.inner_text()[:80] if tt else "KHONG CO"),
            )
            # Bam nut -> mo hop thoai huong dan.
            duong_hd = os.path.join(THU_MUC_OUT, "ui_huong_dan_man_1440x900.png")
            page2.screenshot(path=duong_hd, full_page=False)
            _bao(os.path.isfile(duong_hd), "5k0. Anh man huong dan da luu", duong_hd)
            if nut:
                nut.click()
                page2.wait_for_selector("#modal_khoa.mo", timeout=5000)
                _bao(True, "5k. Bam nut -> mo hop thoai huong dan", "modal_khoa.mo")
                duong_hd2 = os.path.join(THU_MUC_OUT, "ui_huong_dan_1440x900.png")
                page2.screenshot(path=duong_hd2, full_page=False)
            else:
                _bao(False, "5k. Bam nut -> mo hop thoai huong dan", "khong co nut")
            ctx2.close()
        finally:
            khoi_dong.close()

    _bao(not loi_js, "5l. Khong co loi JavaScript trong trang", "; ".join(loi_js)[:200] or "sach")


def main() -> int:
    os.environ["PYTHONIOENCODING"] = "utf-8"
    mat_khau = secrets.token_urlsafe(12)      # KHONG hardcode
    os.environ["CAMAI_PASSWORD"] = mat_khau
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)

    import uvicorn

    import web_server

    khoa = web_server.KHOA_TRUY_CAP
    print("=" * 70)
    print("KIEM CHUNG khoa truy cap san dung - cong %d" % CONG)
    print("=" * 70)
    print("Do dai khoa truy cap: %d ky tu" % len(khoa))
    print("URL san dung (che giua phan khoa): %s" % web_server.url_san_dung("192.168.1.50", CONG)[:40]
          + "...%s" % khoa[-6:])

    cau_hinh = uvicorn.Config(web_server.app, host="127.0.0.1", port=CONG, log_level="warning")
    may_chu = uvicorn.Server(cau_hinh)
    luong = threading.Thread(target=may_chu.run, daemon=True)
    luong.start()
    if not _cho_server_san_sang():
        print("[FAIL] Server khong san sang sau 60s")
        return 1
    print("[OK] Server san sang tren cong %d" % CONG)

    try:
        _kiem_http(khoa, mat_khau)
        _kiem_browser(khoa)
    finally:
        may_chu.should_exit = True
        luong.join(timeout=10)

    # ---- tong ket ----
    print("\n" + "=" * 70)
    tong = len(KET_QUA)
    fail = [k for k in KET_QUA if not k[0]]
    print("TONG KET: %d/%d PASS, %d FAIL" % (tong - len(fail), tong, len(fail)))
    for ok, ten, chi_tiet in fail:
        print("  FAIL: %s - %s" % (ten, chi_tiet))
    print("=" * 70)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
