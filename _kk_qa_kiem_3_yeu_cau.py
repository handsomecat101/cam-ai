# -*- coding: utf-8 -*-
"""Kiem chung DOC LAP 3 yeu cau nghiep thu ban CamAI v3.10 (agent camai-qa).

Khong dung lai ham kiem cua agent khac: viet lai tu dau, do truc tiep.

(A) Khoa truy cap bootstrap trong URL:
    - GET /?k=<khoa SAI>  -> KHONG cap phien (khong Set-Cookie), API -> 401
    - GET /?k=<khoa DUNG> -> cap phien (Set-Cookie camai_phien), API -> 200
    - GET /api/ping -> 200 ok=true
    - GET /api/phien -> 200 + token
    - Server KHONG in khoa ra console khi CAMAI_DEBUG_KHOA khong bat

(B) Khung video LUON O TREN (sticky) o 1440 / 820 / 390:
    - getBoundingClientRect().top cua .khung-video <= chieu cao .thanh-dau + 2px
    - PHẢI thuc su cuon duoc (scrollY > 0) moi co y nghia
    - video phai nhin thay trong viewport

(C) KHONG TREO + co indicator:
    - sau khi bam BAT DAU: overlay hien < 1.0s
    - trong 10s: so lan poll /api/trang-thai >= 5
    - do tre lon nhat giua 2 lan poll < 2.0s
    - overlay co spinner CSS + ten giai doan tieng Viet

Chay:
    .venv\\Scripts\\python.exe _kk_qa_kiem_3_yeu_cau.py

Ghi chu: log server ghi ra %TEMP% (KHONG ghi trong thu muc du an) de khong
lam sai script _kk_kiem_app_qt.py (quet mat khau trong thu muc du an).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(APP_DIR, ".venv", "Scripts", "python.exe")
WEB_SERVER = os.path.join(APP_DIR, "web_server.py")
THU_MUC_OUT = os.path.join(APP_DIR, "_kk_out", "qa")
THU_MUC_TMP = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "camai_qa")
VIDEO_MAU = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")

CONG_CHINH = 8811
CONG_KHONG_IN_KHOA = 8812
MSEDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

KICH_THUOC = [(1440, 900), (820, 1180), (390, 844)]

KET_QUA: list[tuple[str, bool, str]] = []


def _in(noi_dung: str) -> None:
    print(noi_dung, flush=True)


def _ghi(ten: str, ok: bool, chi_tiet: str = "") -> bool:
    KET_QUA.append((ten, bool(ok), chi_tiet))
    _in("  [%s] %s%s" % ("PASS" if ok else "FAIL", ten,
                         (" - " + chi_tiet) if chi_tiet else ""))
    return bool(ok)


def _bang_tong_ket() -> int:
    _in("")
    _in("=" * 74)
    _in("BANG TONG KET - _kk_qa_kiem_3_yeu_cau.py")
    _in("=" * 74)
    for ten, ok, chi_tiet in KET_QUA:
        _in("  %-4s %s" % ("PASS" if ok else "FAIL", ten))
        if not ok and chi_tiet:
            _in("       -> %s" % chi_tiet)
    tong = len(KET_QUA)
    du = sum(1 for _, ok, _ in KET_QUA if ok)
    _in("-" * 74)
    _in("  TONG KET: %d/%d PASS, %d FAIL" % (du, tong, tong - du))
    _in("=" * 74)
    return 0 if du == tong else 1


# ----------------------------------------------------------------- server
def _bat_dau_server(cong: int, ten_log: str, bien_moi_truong=None):
    """Mo web_server.py tren `cong`. Tra (proc, duong_dan_log)."""
    os.makedirs(THU_MUC_TMP, exist_ok=True)
    duong_log = os.path.join(THU_MUC_TMP, ten_log)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Server BAT BUOC co CAMAI_PASSWORD. Sinh ngau nhien MOI LAN chay
    # (khong hardcode mat khau trong file nay).
    env.setdefault("CAMAI_PASSWORD", secrets.token_urlsafe(12))
    if bien_moi_truong:
        env.update(bien_moi_truong)
    log = open(duong_log, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PY, "-W", "ignore", WEB_SERVER, "--port", str(cong)],
        cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    return proc, duong_log


def _doc_log(duong_log: str) -> str:
    try:
        with open(duong_log, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _cho_server(cong: int, proc, giay: int = 120) -> bool:
    het = time.time() + giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/api/ping" % cong, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.4)
    return False


def _dung_server(proc) -> None:
    """Dung ca cay process (stub + process con) cua server do ta tu sinh."""
    if proc is None:
        return
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    except Exception:                                        # noqa: BLE001
        try:
            proc.kill()
        except Exception:                                    # noqa: BLE001
            pass
    try:
        proc.wait(timeout=15)
    except Exception:                                        # noqa: BLE001
        pass


def _doc_khoa(duong_log: str) -> str:
    tim = re.search(
        r"URL san dung:\s*http://[0-9.]+:\d+/\?k=([A-Za-z0-9_\-]+)",
        _doc_log(duong_log))
    return tim.group(1) if tim else ""


# ------------------------------------------------------------------ http
def _req(duong: str, method: str = "GET", data=None, headers=None,
         timeout: int = 30):
    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (CONG_CHINH, duong),
                               data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)
    except Exception as exc:                                 # noqa: BLE001
        return 0, str(exc).encode("utf-8"), {}


def _head(headers: dict, ten: str) -> str:
    for k, v in (headers or {}).items():
        if str(k).lower() == ten.lower():
            return str(v)
    return ""


# ================================================================== PHAN A
def phan_a_khoa_truy_cap() -> None:
    _in("")
    _in("=" * 74)
    _in("PHAN A - KHOA TRUY CAP BOOTSTRAP TRONG URL")
    _in("=" * 74)

    khoa = _doc_khoa(os.path.join(THU_MUC_TMP, "qa_server.log"))
    _ghi("Server tu sinh khoa truy cap san dung (>=32 ky tu)",
         len(khoa) >= 32, "do dai=%d" % len(khoa))
    if not khoa:
        return

    # --- A1: khoa SAI ---
    st, _, hd = _req("/?k=" + secrets.token_urlsafe(32))
    _ghi("GET /?k=<khoa SAI> -> KHONG cap phien (khong Set-Cookie camai_phien)",
         "camai_phien=" not in _head(hd, "Set-Cookie"),
         "set_cookie=%r" % _head(hd, "Set-Cookie")[:50])
    st, _, _ = _req("/api/trang-thai")
    _ghi("GET /api/trang-thai voi khoa SAI -> 401", st == 401, "status=%d" % st)
    st, _, _ = _req("/api/phien")
    _ghi("GET /api/phien voi khoa SAI -> 401", st == 401, "status=%d" % st)

    # --- A2: khoa DUNG ---
    st, _, hd = _req("/?k=" + khoa)
    cookie = _head(hd, "Set-Cookie")
    _ghi("GET /?k=<khoa DUNG> -> cap phien (Set-Cookie camai_phien)",
         st == 200 and "camai_phien=" in cookie,
         "status=%d set_cookie=%r" % (st, cookie[:60]))
    _ghi("Cookie phien httponly + samesite=lax + max_age 12h",
         "httponly" in cookie.lower() and "samesite=lax" in cookie.lower()
         and "max-age=43200" in cookie.lower(),
         "cookie=%r" % cookie[:140])
    _ghi("KHONG co thuoc tinh Secure tren cookie LAN (http://)",
         "secure" not in cookie.lower(), "cookie=%r" % cookie[:140])

    token = ""
    if "camai_phien=" in cookie:
        token = cookie.split("camai_phien=", 1)[1].split(";", 1)[0]
    st, _, _ = _req("/api/trang-thai", headers={"Cookie": "camai_phien=" + token})
    _ghi("GET /api/trang-thai voi cookie phien -> 200", st == 200, "status=%d" % st)
    st, body, _ = _req("/api/phien", headers={"Cookie": "camai_phien=" + token})
    try:
        du_lieu = json.loads(body.decode("utf-8"))
    except Exception:                                        # noqa: BLE001
        du_lieu = {}
    _ghi("GET /api/phien -> 200 + token phien",
         st == 200 and bool(du_lieu.get("token")),
         "status=%d token=%s" % (st, "co" if du_lieu.get("token") else "khong"))

    # --- A3: khoa KHONG doi giua 2 lan goi ---
    st2, _, hd2 = _req("/?k=" + khoa)
    _ghi("Khoa truy cap KHONG doi giua 2 lan truy cap (module-level)",
         st2 == 200 and "camai_phien=" in _head(hd2, "Set-Cookie"),
         "status=%d" % st2)

    # --- A4: /api/ping ---
    t0 = time.perf_counter()
    st, body, _ = _req("/api/ping", timeout=10)
    tre = time.perf_counter() - t0
    try:
        du_ping = json.loads(body.decode("utf-8"))
    except Exception:                                        # noqa: BLE001
        du_ping = {}
    _ghi("GET /api/ping -> 200 + ok=true, tra ve nhanh (<1s)",
         st == 200 and bool(du_ping.get("ok")) and tre < 1.0,
         "status=%d ok=%s %.3fs" % (st, du_ping.get("ok"), tre))

    # --- A5: khoa KHONG bi in ra console khi khong bat CAMAI_DEBUG_KHOA ---
    proc2, log2 = _bat_dau_server(CONG_KHONG_IN_KHOA, "qa_server_nodbg.log",
                                  {"CAMAI_DEBUG_KHOA": ""})
    try:
        ok_server = _cho_server(CONG_KHONG_IN_KHOA, proc2, 120)
        _ghi("Server thu 2 (khong CAMAI_DEBUG_KHOA) khoi dong",
             ok_server, "cong=%d" % CONG_KHONG_IN_KHOA)
        noi_dung = _doc_log(log2)
        co_khoa = "URL san dung:" in noi_dung or "[DEBUG]" in noi_dung
        # tim mot chuoi dai dang token_urlsafe trong log (>=32 ky tu)
        token_trong_log = re.findall(r"[A-Za-z0-9_\-]{32,}", noi_dung)
        _ghi("KHONG in khoa truy cap ra console khi khong bat CAMAI_DEBUG_KHOA",
             not co_khoa,
             "co dong DEBUG=%s" % co_khoa)
        _ghi("Log server khong chua token dai (>=32 ky tu) giong khoa truy cap",
             len(token_trong_log) == 0,
             "so chuoi dai=%d" % len(token_trong_log))
    finally:
        _dung_server(proc2)


# ================================================================== PHAN B/C
def phan_bc_sticky_va_treo() -> None:
    from playwright.sync_api import sync_playwright

    _in("")
    _in("=" * 74)
    _in("PHAN B - KHUNG VIDEO STICKY  |  PHAN C - KHONG TREO + INDICATOR")
    _in("=" * 74)

    khoa = _doc_khoa(os.path.join(THU_MUC_TMP, "qa_server.log"))
    if not khoa:
        _ghi("Doc duoc khoa de mo trinh duyet", False, "khong co khoa")
        return

    user_dir = os.path.join(THU_MUC_TMP, "edge_profile_qa")
    os.makedirs(user_dir, exist_ok=True)
    loi_404: list[str] = []
    loi_js: list[str] = []

    with sync_playwright() as p:
        khoi_dong = None
        for thu in ({"channel": "msedge"}, {"executable_path": MSEDGE}, {}):
            try:
                khoi_dong = p.chromium.launch_persistent_context(
                    user_dir, headless=True, **thu)
                break
            except Exception as exc:                          # noqa: BLE001
                _in("  [Playwright] khong khoi dong duoc (%s): %s"
                    % (list(thu)[0] if thu else "bundled", str(exc)[:100]))
        if khoi_dong is None:
            _ghi("Playwright khoi dong duoc trinh duyet", False, "khong mo duoc")
            return

        page = khoi_dong.pages[0] if khoi_dong.pages else khoi_dong.new_page()
        page.on("response", lambda r: loi_404.append("%d %s" % (r.status, r.url))
                if r.status >= 400 else None)
        page.on("pageerror", lambda e: loi_js.append(str(e)))

        # --- mo bang duong dan co khoa ---
        page.goto("http://127.0.0.1:%d/?k=%s" % (CONG_CHINH, khoa),
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
        _ghi("Mo bang duong dan co khoa -> vao thang khong co form mat khau",
             True, "URL=%s" % page.url.replace(khoa, "<KHOA>"))
        co_form = page.query_selector("#form_dang_nhap")
        co_mk = page.query_selector('input[type="password"]')
        _ghi("UI KHONG con form mat khau / input password",
             co_form is None and co_mk is None,
             "form=%s input_password=%s" % (co_form, co_mk))
        cookies = [c for c in khoi_dong.cookies() if c["name"] == "camai_phien"]
        _ghi("Trinh duyet nhan duoc cookie phien 'camai_phien'",
             bool(cookies), "so=%d" % len(cookies))

        # ---------------- PHAN B: STICKY ----------------
        _in("")
        _in("  [STICKY] do o 3 kich thuoc (cuon xuong truoc khi do)")
        ket_sticky = []
        for rong, cao in KICH_THUOC:
            page.set_viewport_size({"width": rong, "height": cao})
            page.wait_for_timeout(600)
            # cuon xuong THAT: can trang phai du cao de scrollY > 0
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)
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
                "  scrollY:Math.round(window.scrollY),"
                "  scrollMax:Math.round(d.scrollHeight-window.innerHeight),"
                "  vh:window.innerHeight,"
                "  tranNgang:d.scrollWidth>d.clientWidth+1,"
                "  hDauVar:getComputedStyle(d).getPropertyValue('--h-dau').trim(),"
                "  parentOverflow:(()=>{const p=w?w.parentElement:null;"
                "   return p?getComputedStyle(p).overflowY:'';})()};"
                "}")
            do["rong"], do["cao"] = rong, cao
            ket_sticky.append(do)
            _in("    %dx%d | header=%dpx (--h-dau=%s) pos=%s | video %dx%d "
                "top=%s (can <=%d) bottom=%s vh=%d | scrollY=%d/%d | "
                "overflowY(parent)=%s"
                % (rong, cao, do["hh"], do["hDauVar"], do["st"], do["w"],
                   do["h"], do["top"], do["hh"] + 2, do["bottom"], do["vh"],
                   do["scrollY"], do["scrollMax"], do["parentOverflow"]))
            duong = os.path.join(THU_MUC_OUT, "qa_sticky_%dx%d.png" % (rong, cao))
            page.screenshot(path=duong)

        sai = [d for d in ket_sticky
               if d["st"] != "sticky" or d["top"] is None
               or d["top"] > d["hh"] + 2]
        _ghi("B.1 Khung video DAN (sticky) o ca 3 kich thuoc: top <= header+2px",
             not sai,
             "sai: %s" % ([("%dx%d top=%s hh=%s" % (d["rong"], d["cao"], d["top"],
                                                  d["hh"])) for d in sai]
                          if sai else "1440/820/390 OK"))
        khong_cuon = [d for d in ket_sticky if d["scrollY"] <= 0]
        _ghi("B.2 Trang THUC su cuon duoc (scrollY>0) - khong phai pass gia",
             not khong_cuon,
             "sai: %s" % ([("%dx%d scrollY=%d" % (d["rong"], d["cao"], d["scrollY"]))
                           for d in khong_cuon] if khong_cuon else
                          ", ".join("%dx%d scrollY=%d/%d"
                                    % (d["rong"], d["cao"], d["scrollY"],
                                       d["scrollMax"]) for d in ket_sticky)))
        ngoai_khung = [d for d in ket_sticky
                       if d["bottom"] is None or d["bottom"] > d["vh"] + 2
                       or d["top"] < -2]
        _ghi("B.3 Khung video van nhin thay trong viewport khi da cuon",
             not ngoai_khung,
             "sai: %s" % ([("%dx%d top=%s bottom=%s vh=%d"
                           % (d["rong"], d["cao"], d["top"], d["bottom"], d["vh"]))
                           for d in ngoai_khung] if ngoai_khung else "3/3 OK"))
        tran = [d for d in ket_sticky if d["tranNgang"]]
        _ghi("B.4 Khong tran ngang o ca 3 kich thuoc", not tran,
             "tran: %s" % ([("%dx%d" % (d["rong"], d["cao"])) for d in tran]
                           if tran else "khong"))

        # ---------------- PHAN C: KHONG TREO + OVERLAY ----------------
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(500)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(300)

        # bom fetch de do thoi gian tung lan poll /api/trang-thai
        page.evaluate(
            "() => {"
            " window.__qaPoll=[];"
            " if(!window.__qaHooked){ window.__qaHooked=true;"
            "  const f=window.fetch.bind(window);"
            "  window.fetch=function(u,o){"
            "    const su=String(u);"
            "    if(su.indexOf('/api/trang-thai')>=0){"
            "     const t0=performance.now();"
            "     return f(u,o).then(function(r){"
            "      window.__qaPoll.push({t0:t0,t1:performance.now(),"
            "       st:r.status,url:su}); return r;},"
            "      function(e){ window.__qaPoll.push({t0:t0,"
            "       t1:performance.now(),st:-1,url:su,err:String(e)});"
            "       throw e;});}"
            "    return f(u,o);};}"
            "}")

        page.fill("#o_duong_dan", VIDEO_MAU)
        t_click = time.perf_counter()
        page.click("#nut_chay")

        # overlay hien bao lau?
        t_overlay = None
        het = time.time() + 5
        while time.time() < het:
            trang = page.evaluate(
                "() => {const o=document.getElementById('overlay_busy');"
                " if(!o) return {hien:false,chu:'',spin:false};"
                " const cs=getComputedStyle(o);"
                " const v=document.querySelector('.vong-xoay');"
                " const cv=v?getComputedStyle(v):null;"
                " return {hien:(cs.display!=='none'&&cs.visibility!=='hidden'"
                "   &&parseFloat(cs.opacity||'1')>0.01&&o.offsetParent!==null),"
                "  chu:(document.getElementById('overlay_chu')||{}).textContent||'',"
                "  spin:!!(cv&&cv.animationName&&cv.animationName!=='none'),"
                "  anim:cv?cv.animationName:''};}")
            if trang.get("hien"):
                t_overlay = time.perf_counter() - t_click
                break
            time.sleep(0.05)
        _ghi("C.1 Bam BAT DAU -> overlay 'dang xu ly' hien < 1.0s",
             t_overlay is not None and t_overlay < 1.0,
             "%.3fs" % (t_overlay if t_overlay is not None else -1))
        _ghi("C.2 Overlay co spinner CSS (animation, khong emoji)",
             bool(trang.get("spin")), "animationName=%r" % trang.get("anim"))
        chu_overlay = trang.get("chu", "")
        _ghi("C.3 Overlay co ten giai doan tieng Viet",
             bool(chu_overlay.strip()),
             "chu=%r" % chu_overlay[:60])
        page.screenshot(path=os.path.join(THU_MUC_OUT, "qa_overlay_1440x900.png"))

        # do 10s: so lan poll + do tre lon nhat
        page.wait_for_timeout(10000)
        polls = page.evaluate("() => window.__qaPoll || []")
        so_poll = len(polls)
        # do tre = khoang cach giua lan poll (bat dau -> ket thuc)
        tre = []
        for i in range(1, len(polls)):
            tre.append((polls[i]["t0"] - polls[i - 1]["t1"]) / 1000.0)
        tre_lon_nhat = max(tre) if tre else 0.0          # GIAY
        thoi_gian_call = [(p["t1"] - p["t0"]) / 1000.0 for p in polls]
        call_lon_nhat = max(thoi_gian_call) if thoi_gian_call else 0.0
        _ghi("C.4 Trong 10s co >= 5 lan poll /api/trang-thai", so_poll >= 5,
             "so poll=%d" % so_poll)
        _ghi("C.5 Do tre lon nhat giua 2 lan poll < 2.0s", tre_lon_nhat < 2.0,
             "tre lon nhat=%.3fs | thoi gian 1 lan goi toi da=%.3fs"
             % (tre_lon_nhat, call_lon_nhat))
        _ghi("C.5b Do tre lon nhat cua 1 LAN GOI /api/trang-thai < 2.0s",
             call_lon_nhat < 2.0, "%.3fs" % call_lon_nhat)
        _ghi("C.6 Moi lan poll deu tra 200 (khong loi mang)",
             bool(polls) and all(p.get("st") == 200 for p in polls),
             "ma: %s" % sorted(set(p.get("st") for p in polls)))
        _in("    [C] chuoi giai doan quan sat tu server:")
        chuoi_gd = []
        try:
            st, body, _ = _req("/api/trang-thai", headers={
                "Cookie": "camai_phien=%s" % (
                    cookies[0]["value"] if cookies else "")})
            du_lieu = json.loads(body.decode("utf-8"))
            chuoi_gd.append(du_lieu.get("giai_doan", ""))
        except Exception:                                    # noqa: BLE001
            pass
        _in("      giai_doan hien tai=%r" % (chuoi_gd[0] if chuoi_gd else "?"))

        # co phai UI bi treo? (main thread con phan hoi JS)
        t_js = time.perf_counter()
        page.evaluate("() => 1+1")
        _ghi("C.7 UI khong treo: JS van chay sau khi phan tich",
             (time.perf_counter() - t_js) < 1.0,
             "%.3fs" % (time.perf_counter() - t_js))

        # ---------------- log 404 ----------------
        _in("")
        _in("  [404] cac request loi trong phien trinh duyet:")
        if loi_404:
            for d in sorted(set(loi_404)):
                _in("    %s" % d)
        else:
            _in("    (khong co)")
        _ghi("C.8 Danh sach 404 da thu thap (de phan tich nghi van)",
             True, "so=%d" % len(set(loi_404)))
        if loi_js:
            _in("  [JS ERROR] %s" % sorted(set(loi_js))[:5])
        _ghi("C.9 Khong co loi JavaScript (pageerror)",
             not loi_js, "so loi=%d" % len(loi_js))

        try:
            khoi_dong.close()
        except Exception:                                    # noqa: BLE001
            pass


def main() -> int:
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    os.makedirs(THU_MUC_TMP, exist_ok=True)
    _in("=" * 74)
    _in("Kiem chung doc lap 3 yeu cau nghiep thu v3.10 - camai-qa")
    _in("cong rieng: %d (khong dung 8765) | cong phu: %d" % (CONG_CHINH,
                                                            CONG_KHONG_IN_KHOA))
    _in("=" * 74)

    proc, log = _bat_dau_server(CONG_CHINH, "qa_server.log",
                                {"CAMAI_DEBUG_KHOA": "1"})
    try:
        if not _cho_server(CONG_CHINH, proc, 180):
            _ghi("Server khoi dong", False, _doc_log(log)[-1500:])
            return _bang_tong_ket()
        _ghi("Server khoi dong tren cong %d" % CONG_CHINH, True, "")
        phan_a_khoa_truy_cap()
        phan_bc_sticky_va_treo()
    finally:
        _dung_server(proc)
    return _bang_tong_ket()


if __name__ == "__main__":
    sys.exit(main())
