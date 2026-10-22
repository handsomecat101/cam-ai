"""
Chup anh UI cho TINH NANG MOI (dang ky nguoi quen / ve vung) + KIEM CHUNG
that bang chuot trinh duet (ve vung tren khung hinh, luu vung len may chu).

Chay:
    .venv\\Scripts\\python.exe _kk_chup_ui_tinh_nang.py

Khoi dong web_server.py o CONG RIENG (8797), dang nhap bang Edge (Playwright),
ve vung that tren khung hinh video, luu vung, chup anh 1440x900 + 390x844.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
THU_MUC_OUT = os.path.join(APP_DIR, "_kk_out", "ui_web")
CONG = 8797
BASE = "http://127.0.0.1:%d" % CONG
VIDEO = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
FILE_LOG = os.path.join(APP_DIR, "_kk_out", "web_server_chup.log")
MSEDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def _in(text: str = "") -> None:
    print(text, flush=True)


def _req(duong, method="GET", data=None, token=None, timeout=60):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Camai-Token"] = token
    r = urllib.request.Request(BASE + duong, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc).encode("utf-8")


def _cho_server(proc, so_giay=90):
    het = time.time() + so_giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        status, _ = _req("/", timeout=5)
        if status == 200:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    from playwright.sync_api import sync_playwright

    mat_khau = secrets.token_urlsafe(12)
    env = os.environ.copy()
    env["CAMAI_PASSWORD"] = mat_khau
    env["PYTHONIOENCODING"] = "utf-8"
    log = open(FILE_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(APP_DIR, "web_server.py"), "--port", str(CONG)],
        cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    loi: list[str] = []
    try:
        if not _cho_server(proc):
            _in("KHONG khoi dong duoc server")
            return 1
        _in("Server san sang (cong %d)" % CONG)

        status, body = _req("/api/dang-nhap", method="POST",
                            data={"mat_khauu": mat_khau})
        du_lieu = json.loads(body.decode("utf-8"))
        token = du_lieu.get("token") or ""
        if not token:
            _in("Dang nhap that bai: %s" % du_lieu)
            return 1
        _in("Dang nhap OK")

        with sync_playwright() as p:
            khoi_dong = p.chromium.launch(headless=True, executable_path=MSEDGE)
            ctx = khoi_dong.new_context(viewport={"width": 1440, "height": 900},
                                        device_scale_factor=1)
            page = ctx.new_page()
            page.on("pageerror", lambda e: loi.append("pageerror: %s" % e))
            page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
            page.fill("#o_mat_khauu", mat_khau)
            page.click("#form_dang_nhap button[type=submit]")
            page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
            page.wait_for_timeout(1500)

            # --- 1. Mo nhom 2 + 4, chup form dang ky nguoi quen ---
            page.evaluate("() => { for (const k of ['mat','vung']) {"
                          " const d=document.querySelector('details[data-nhom=\"'+k+'\"]');"
                          " if (d) { d.open = true; d.scrollIntoView({block:'start'}); } } }")
            page.wait_for_timeout(600)
            page.evaluate("() => { const d=document.querySelector('details[data-nhom=\"mat\"]');"
                          " if (d) d.scrollIntoView({block:'center'}); }")
            page.wait_for_timeout(500)
            duong = os.path.join(THU_MUC_OUT, "ui_moi_nhom2_1440x900.png")
            page.screenshot(path=duong)
            _in("Chup %s" % duong)

            # --- 2. Chay phan tich that de co khung hinh ---
            page.fill("#o_duong_dan", VIDEO)
            page.click("#nut_chay")
            _in("Da bam BAT DAU, cho khung hinh...")
            co_khung = False
            het = time.time() + 120
            while time.time() < het:
                page.wait_for_timeout(1000)
                if page.evaluate("() => { const i=document.getElementById('img_live');"
                                 " return i && !i.classList.contains('an') && i.naturalWidth>0; }"):
                    co_khung = True
                    break
            _in("Co khung hinh live: %s" % co_khung)

            # --- 3. Bam "Ve vung" roi KEO CHUOT tren canvas ---
            page.click("#nut_ve_vung")
            page.wait_for_timeout(1500)
            thong_bao = page.inner_text("#noi_dung_thong_bao")
            _in("Thong bao sau khi bam 'Ve vung': %r" % thong_bao[:110])
            # UI tu dua khung hinh vao khung nhin -> doc lai rect canvas sau do.
            page.wait_for_timeout(800)
            khung = page.evaluate("() => { const c=document.getElementById('canvas_vung');"
                                  " const r=c.getBoundingClientRect();"
                                  " return {x:r.x, y:r.y, w:r.width, h:r.height,"
                                  "  cw:c.width, ch:c.height,"
                                  "  trong_khung: r.y > 0 && r.y < window.innerHeight}; }")
            _in("Canvas: %s" % json.dumps(khung))
            if khung["w"] > 10 and khung["h"] > 10:
                x0 = khung["x"] + khung["w"] * 0.20
                y0 = khung["y"] + khung["h"] * 0.25
                x1 = khung["x"] + khung["w"] * 0.70
                y1 = khung["y"] + khung["h"] * 0.80
                page.mouse.move(x0, y0)
                page.mouse.down()
                page.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=6)
                page.mouse.move(x1, y1, steps=6)
                page.mouse.up()
                page.wait_for_timeout(700)
                _in("Da keo chuot ve vung tren canvas")
            dong_vung = page.inner_text("#dong_vung")
            _in("Dong trang thai vung: %r" % dong_vung[:160])

            duong = os.path.join(THU_MUC_OUT, "ui_moi_ve_vung_1440x900.png")
            page.screenshot(path=duong)
            _in("Chup %s" % duong)

            # --- 4. Bam "Luu vung" ---
            page.click("#nut_luu_vung")
            page.wait_for_timeout(4000)
            tb = page.inner_text("#noi_dung_thong_bao")
            dong_vung = page.inner_text("#dong_vung")
            _in("Thong bao sau khi LUU VUNG: %r" % tb[:160])
            _in("Dong trang thai vung: %r" % dong_vung[:200])
            duong = os.path.join(THU_MUC_OUT, "ui_moi_luu_vung_1440x900.png")
            page.screenshot(path=duong)

            # Kiem tra server da nhan vung that
            status, body = _req("/api/vung", method="POST", token=token,
                                data={"x1": 0.1, "y1": 0.2, "x2": 0.6, "y2": 0.8,
                                      "video": VIDEO})
            _in("POST /api/vung -> %s %s" % (status, body.decode("utf-8")[:200]))

            # --- 5. Dung phan tich ---
            page.click("#nut_dung")
            page.wait_for_timeout(3000)

            # --- 6. Chup 390x844 (mo drawer de thay nhom 2 + 4) ---
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(800)
            page.click("#nut_menu")
            page.wait_for_timeout(800)
            page.evaluate("() => { const d=document.querySelector('details[data-nhom=\"mat\"]');"
                          " if (d) { d.open = true; d.scrollIntoView({block:'start'}); } }")
            page.wait_for_timeout(600)
            duong = os.path.join(THU_MUC_OUT, "ui_moi_nhom2_390x844.png")
            page.screenshot(path=duong)
            _in("Chup %s" % duong)
            page.evaluate("() => { const d=document.querySelector('details[data-nhom=\"vung\"]');"
                          " if (d) { d.open = true; d.scrollIntoView({block:'start'}); } }")
            page.wait_for_timeout(600)
            duong = os.path.join(THU_MUC_OUT, "ui_moi_nhom4_390x844.png")
            page.screenshot(path=duong)
            _in("Chup %s" % duong)

            _in("Loi JavaScript: %s" % (loi or "khong co"))
            ctx.close()
            khoi_dong.close()
    finally:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
