# -*- coding: utf-8 -*-
"""Kiem chung them cho camai-qa (CamAI v3.10).

H1. Badge tren thanh dau co cap nhat theo giai doan khi dang chay khong?
H2. Overlay co doi ten giai doan theo chuoi nap model -> mo video -> phan tich?
H3. Do muc do "text bi cat" khi noi dung cuon duoi panel sticky (chong lan
    voi dau tieu de/button bi che 1/2).
H4. Chup anh theo doi trong khi chay (de nhin bang mat).

Chay:
    .venv\\Scripts\\python.exe _kk_qa_kiem_badge_va_chap.py
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
OUT = os.path.join(APP_DIR, "_kk_out", "qa")
TMP = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "camai_qa")
VIDEO_MAU = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
CONG = 8814

KET_QUA: list[tuple[str, bool, str]] = []


def _in(s):
    print(s, flush=True)


def _ghi(ten, ok, ct=""):
    KET_QUA.append((ten, bool(ok), ct))
    _in("  [%s] %s%s" % ("PASS" if ok else "FAIL", ten, (" - " + ct) if ct else ""))
    return bool(ok)


def _bang():
    _in("")
    _in("=" * 74)
    for ten, ok, ct in KET_QUA:
        _in("  %-4s %s" % ("PASS" if ok else "FAIL", ten))
        if not ok and ct:
            _in("       -> %s" % ct)
    du = sum(1 for _, ok, _ in KET_QUA if ok)
    _in("  TONG KET: %d/%d PASS, %d FAIL" % (du, len(KET_QUA),
                                             len(KET_QUA) - du))
    _in("=" * 74)
    return 0 if du == len(KET_QUA) else 1


def _bat_server():
    os.makedirs(TMP, exist_ok=True)
    log = os.path.join(TMP, "qa_badge_server.log")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CAMAI_DEBUG_KHOA"] = "1"
    env.setdefault("CAMAI_PASSWORD", secrets.token_urlsafe(12))
    f = open(log, "w", encoding="utf-8")
    p = subprocess.Popen([PY, "-W", "ignore", WEB_SERVER, "--port", str(CONG)],
                         cwd=APP_DIR, env=env, stdout=f,
                         stderr=subprocess.STDOUT)
    return p, log


def _doc(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _req(duong, method="GET", data=None, cookie="", timeout=30):
    h = {}
    if cookie:
        h["Cookie"] = cookie
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (CONG, duong),
                               data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)
    except Exception as e:                                    # noqa: BLE001
        return 0, str(e).encode("utf-8"), {}


def _dung(proc):
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    except Exception:                                        # noqa: BLE001
        pass


def main():
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    proc, log = _bat_server()
    try:
        het = time.time() + 180
        while time.time() < het:
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d/api/ping" % CONG, timeout=3) as r:
                    if r.status == 200:
                        break
            except Exception:                                # noqa: BLE001
                pass
            time.sleep(0.4)
        m = re.search(r"URL san dung:\s*http://[0-9.]+:\d+/\?k=([A-Za-z0-9_\-]+)",
                      _doc(log))
        if not m:
            _ghi("Server khoi dong", False, _doc(log)[-800:])
            return _bang()
        khoa = m.group(1)
        _, _, hd = _req("/?k=" + khoa)
        cookie = ""
        for k, v in hd.items():
            if str(k).lower() == "set-cookie" and "camai_phien=" in str(v):
                cookie = ("camai_phien="
                          + str(v).split("camai_phien=", 1)[1].split(";", 1)[0])

        user_dir = os.path.join(TMP, "edge_profile_badge")
        os.makedirs(user_dir, exist_ok=True)
        with sync_playwright() as p:
            br = None
            for thu in ({"channel": "msedge"}, {}):
                try:
                    br = p.chromium.launch_persistent_context(
                        user_dir, headless=True, **thu)
                    break
                except Exception:                            # noqa: BLE001
                    continue
            if br is None:
                _ghi("Playwright", False, "khong mo duoc")
                return _bang()
            page = br.pages[0] if br.pages else br.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:%d/?k=%s" % (CONG, khoa),
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
            page.wait_for_timeout(800)

            # ---- H3: text bi che boi panel sticky ----
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(600)
            cat = page.evaluate(
                "() => {"
                " const st=document.querySelector('.the-video-stick');"
                " if(!st) return {loi:'khong co sticky'};"
                " const sb=st.getBoundingClientRect();"
                " const out=[];"
                " document.querySelectorAll('.cot-chinh .the > *').forEach(function(el){"
                "  const r=el.getBoundingClientRect();"
                "  if(r.height===0) return;"
                "  if(r.top < sb.bottom-1 && r.bottom > sb.bottom+1){"
                "   out.push({tag:el.tagName, txt:(el.textContent||'').trim().slice(0,40),"
                "    top:Math.round(r.top), bottom:Math.round(r.bottom),"
                "    sb:Math.round(sb.bottom)});}});"
                " return {sb:Math.round(sb.bottom), out:out};}"
            )
            _in("  Panel sticky bottom = %s px" % cat.get("sb"))
            for o in cat.get("out", []):
                _in("    BI CAT: <%s> %r  (top=%s bottom=%s, panel bottom=%s)"
                    % (o["tag"], o["txt"], o["top"], o["bottom"], o["sb"]))
            _ghi("H3. Khong co chu/button bi CAT 1/2 boi panel sticky",
                 len(cat.get("out", [])) == 0,
                 "so phan bi cat=%d: %s"
                 % (len(cat.get("out", [])),
                    [(o["tag"], o["txt"]) for o in cat.get("out", [])]))

            # ---- H1/H2/H4: theo doi trong khi chay ----
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            page.fill("#o_duong_dan", VIDEO_MAU)
            page.click("#nut_chay")
            _in("")
            _in("  Theo doi trong khi chay (badge tren thanh dau + overlay):")
            chuoi_badge = []
            chuoi_overlay = []
            cac_moc = [1.0, 2.0, 4.0, 7.0, 12.0, 18.0, 25.0, 35.0]
            truoc = 0.0
            for giay in cac_moc:
                page.wait_for_timeout(int((giay - truoc) * 1000))
                truoc = giay
                du = page.evaluate(
                    "() => {const d=document.querySelector('.thanh-dau');"
                    " const b=d?(d.innerText||'').replace(/\\s+/g,' ').trim():'';"
                    " const o=document.getElementById('overlay_chu');"
                    " const ov=document.getElementById('overlay_busy');"
                    " const cs=ov?getComputedStyle(ov):null;"
                    " const hien=ov&&cs.display!=='none'&&cs.visibility!=='hidden'"
                    "  &&parseFloat(cs.opacity||'1')>0.01&&ov.offsetParent!==null;"
                    " return {badge:b, ov:(o||{}).textContent||'', hien:hien,"
                    "  tt:(()=>{const x=document.getElementById('dong_giai_doan');"
                    "   return x?(x.textContent||'').trim():'';})()};}"
                )
                badge = du.get("badge", "")
                # chi giu phan badge trang thai
                chuoi_badge.append((giay, badge))
                chuoi_overlay.append((giay, du.get("ov", ""), du.get("hien")))
                _in("    t=%4.1fs | badge=%-28r | overlay=%-32r | hien=%s"
                    % (giay, badge[:60], du.get("ov", "")[:40], du.get("hien")))
                if giay in (2.0, 7.0, 18.0):
                    page.screenshot(path=os.path.join(
                        OUT, "qa_badge_t%02ds.png" % int(giay)))
            b_chu = " ".join(b for _, b in chuoi_badge)
            co_giai_doan_badge = ("Đang" in b_chu or "Lỗi" in b_chu)
            _ghi("H1. Badge thanh dau co CAPI NHAT ten giai doan khi chay",
                 co_giai_doan_badge,
                 "badge theo thoi gian: %s" % chuoi_badge)
            o_chu = [o for _, o, _ in chuoi_overlay]
            _ghi("H2. Overlay doi ten giai doan theo chuoi (>=2 giai doan khac nhau)",
                 len(set(o_chu)) >= 2, " -> ".join(dict.fromkeys(o_chu)))
            br.close()
    finally:
        _dung(proc)
    return _bang()


if __name__ == "__main__":
    sys.exit(main())
