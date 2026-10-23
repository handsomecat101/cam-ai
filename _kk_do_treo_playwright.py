"""
Do do "treo app" theo goc nhin NGUOI DUNG (trinh duyet that, Playwright).

Do duoc 3 chi so:
  1. So lan poll /api/trang-thai thanh cong trong 10s dau (yeu cau >= 5).
  2. Do tre lon nhat giua 2 lan poll (yeu cau < 2s).
  3. Do tre lon nhat cua main thread trinh duyet (requestAnimationFrame) ->
     day la "ung hinh" / "treo app" that su. Yeu cau < 2s.
  4. Co overlay/spinner hien len duoi 1s hay khong.

Chay:
    .venv\\Scripts\\python.exe _kk_do_treo_playwright.py
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
CONG = 8802
BASE = "http://127.0.0.1:%d" % CONG
THU_MUC_LOG = os.path.join(APP_DIR, "_kk_out")
FILE_LOG = os.path.join(THU_MUC_LOG, "do_treo_pw_server.log")
THU_MUC_OUT = os.path.join(THU_MUC_LOG, "ui_web")
VIDEO = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
SO_GIAY_QUAN_SAT = 10.0

# Script chay trong trinh duyet: bam fetch + nhip rAF de do "ung hinh".
INSTRUMENT = """
(function () {
  window.__poll = [];
  window.__raf = [];
  window.__overlay = [];
  var of = window.fetch;
  window.fetch = function (u, o) {
    var url = String(u && u.url ? u.url : u);
    var laPoll = url.indexOf('/api/trang-thai') >= 0;
    var t0 = performance.now();
    return of.apply(this, arguments).then(function (r) {
      if (laPoll) window.__poll.push({t: performance.now(), ok: r.ok});
      return r;
    }, function (e) {
      if (laPoll) window.__poll.push({t: performance.now(), ok: false});
      throw e;
    });
  };
  function tick(ts) { window.__raf.push(ts); requestAnimationFrame(tick); }
  requestAnimationFrame(tick);
  // theo doi overlay: co phan tu overlay nao hien khong?
  window.__quetOverlay = function () {
    var res = [];
    var ds = document.querySelectorAll('#overlay_busy, .overlay-busy, [id*="overlay"]');
    for (var i = 0; i < ds.length; i++) {
      var e = ds[i];
      var cs = getComputedStyle(e);
      var hien = cs.display !== 'none' && cs.visibility !== 'hidden'
                 && parseFloat(cs.opacity || '1') > 0.01
                 && e.offsetParent !== null;
      if (hien) res.push({id: e.id, cls: e.className,
                          text: (e.textContent || '').trim().slice(0, 90)});
    }
    return res;
  };
})();
"""


def req(duong, method="GET", data=None, headers=None, timeout=30):
    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(BASE + duong, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception:  # noqa: BLE001
        return 0, b""


def _cho_server(proc, so_giay=90):
    het = time.time() + so_giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        try:
            if req("/", timeout=5)[0] == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    return False


def _lay_khoa(log_path: str, so_giay=30) -> str:
    het = time.time() + so_giay
    while time.time() < het:
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                noi_dung = f.read()
            tim = re.search(r"\[DEBUG\] URL san dung:\s*\S*\?k=(\S+)", noi_dung)
            if tim:
                return tim.group(1).strip()
        time.sleep(0.3)
    return ""


def _lon_nhat(gap_list: list[float]) -> float:
    return max(gap_list) if gap_list else 0.0


def do_poll(lenh: list[float]) -> tuple[int, float]:
    """Tinh so lan poll thanh cong + do tre lon nhat giua 2 lan poll."""
    if len(lenh) < 2:
        return len(lenh), 0.0
    return len(lenh), _lon_nhat([lenh[i] - lenh[i - 1] for i in range(1, len(lenh))])


def main() -> int:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    from playwright.sync_api import sync_playwright

    mat_khau = secrets.token_urlsafe(12)
    env = os.environ.copy()
    env["CAMAI_PASSWORD"] = mat_khau
    env["PYTHONIOENCODING"] = "utf-8"
    env["CAMAI_DEBUG_KHOA"] = "1"          # de lay khoa truy cap mo trinh duyet

    log = open(FILE_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(APP_DIR, "web_server.py"), "--port", str(CONG)],
        cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    ket_qua = {}
    try:
        if not _cho_server(proc):
            print("[LOI] server khong khoi dong")
            return 1
        khoa = _lay_khoa(FILE_LOG)
        if not khoa:
            print("[LOI] khong lay duoc khoa truy cap")
            return 1
        print("Server san sang. Khoa OK.")

        with sync_playwright() as p:
            khoi_dong = None
            for thu in ({"executable_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"},
                        {"executable_path": r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"},
                        {}):
                if "executable_path" in thu and not os.path.isfile(thu["executable_path"]):
                    continue
                try:
                    khoi_dong = p.chromium.launch(headless=True, **thu)
                    break
                except Exception as exc:  # noqa: BLE001
                    print("  [PW] khong khoi dong (%s): %s" % (list(thu)[0], str(exc)[:100]))
            if khoi_dong is None:
                print("[LOI] khong khoi dong duoc trinh duyet")
                return 1

            ctx = khoi_dong.new_context(viewport={"width": 1440, "height": 900})
            ctx.add_init_script(INSTRUMENT)
            page = ctx.new_page()
            page.goto(BASE + "/?k=" + khoa, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#man_chinh:not(.an)", timeout=30000)
            page.wait_for_timeout(1500)

            # ---- DO KHUNG VIDEO CO DINH (sticky) O 3 KICH THUOC ----
            print("")
            print("--- KHUNG VIDEO STICKY (cuon xuong roi do top cua khung video) ---")
            for rong, cao in ((1440, 900), (820, 1180), (390, 844)):
                page.set_viewport_size({"width": rong, "height": cao})
                page.wait_for_timeout(500)
                do = page.evaluate(
                    "() => {"
                    " const d=document.documentElement;"
                    " const h=document.querySelector('.thanh-dau');"
                    " const v=document.querySelector('.khung-video');"
                    " const w=document.querySelector('.the-video-stick');"
                    " const st=w?getComputedStyle(w).position:'';"
                    " const hh=h?Math.round(h.getBoundingClientRect().height):0;"
                    " const vr=v?v.getBoundingClientRect():null;"
                    " const vuong=vr?Math.round(vr.width):0, caoV=vr?Math.round(vr.height):0;"
                    " return {sh:d.scrollHeight, hh:hh, st:st,"
                    "  vuong:vuong, caoV:caoV,"
                    "  tiLe: vuong? Math.round(caoV*100/vuong*10)/10 : 0,"
                    "  trongKhung: vr ? (vr.bottom<=window.innerHeight+2) : false,"
                    "  tranNgang: d.scrollWidth>d.clientWidth};"
                    "}")
                # cuon xuong cho phan cau hinh
                page.evaluate("() => window.scrollTo(0, 900)")
                page.wait_for_timeout(500)
                do2 = page.evaluate(
                    "() => {"
                    " const h=document.querySelector('.thanh-dau');"
                    " const v=document.querySelector('.khung-video');"
                    " const hh=h?Math.round(h.getBoundingClientRect().height):0;"
                    " const vr=v?v.getBoundingClientRect():null;"
                    " return {hh:hh, top: vr?Math.round(vr.top):null,"
                    "  duoi: vr?Math.round(vr.bottom):null,"
                    "  vh: window.innerHeight,"
                    "  trongKhung: vr ? (vr.top<=hh+2 && vr.bottom<=window.innerHeight+2) : false};"
                    "}")
                print("  %dx%d: header=%dpx sticky=%s | video %dx%d (ti le %.1f%%) "
                      "| sau khi cuon: top=%s (yeu cau <= %d) | trong khung nhin=%s"
                      % (rong, cao, do["hh"], do["st"], do["vuong"], do["caoV"],
                         do["tiLe"], do2["top"], do2["hh"] + 2, do2["trongKhung"]))
                page.evaluate("() => window.scrollTo(0, 0)")
                page.wait_for_timeout(200)

            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(400)

            # chon video mau
            nut_mau = page.query_selector_all("#luoi_video_mau button")
            if nut_mau:
                nut_mau[0].click()
                page.wait_for_timeout(600)
            if not page.input_value("#o_duong_dan"):
                page.fill("#o_duong_dan", VIDEO)

            # bat dau quan sat
            page.evaluate("() => { window.__poll = []; window.__raf = []; }")
            t_click = time.perf_counter()
            page.click("#nut_chay")

            # chup manh hinh luc dang nap model
            time.sleep(0.8)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(250)
            duong_png = os.path.join(THU_MUC_OUT, "ui_dang_nap_model_1440x900.png")
            page.screenshot(path=duong_png)
            overlay_08s = page.evaluate("() => window.__quetOverlay()")
            print("Overlay luc 0.8s sau khi bam: %s" % overlay_08s)
            # anh chung minh khuong video DINH o tren khi da cuon xuong
            page.evaluate("() => window.scrollTo(0, 900)")
            page.wait_for_timeout(300)
            duong_png2 = os.path.join(THU_MUC_OUT, "ui_dang_nap_model_sticky_1440x900.png")
            page.screenshot(path=duong_png2)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(200)

            het = t_click + SO_GIAY_QUAN_SAT
            while time.perf_counter() < het:
                page.wait_for_timeout(250)
                ov = page.evaluate("() => window.__quetOverlay()")
                if ov:
                    ket_qua.setdefault("overlay_luc_dau", ov)
                    break

            page.wait_for_timeout(int(max(0, (t_click + SO_GIAY_QUAN_SAT) - time.perf_counter()) * 1000))

            du_lieu = page.evaluate(
                "() => ({poll: window.__poll, raf: window.__raf,"
                " overlay: window.__quetOverlay(),"
                " trang_thai: document.getElementById('nhan_trang_thai_chu')"
                "   ? document.getElementById('nhan_trang_thai_chu').textContent : ''})")
            ket_qua.update(du_lieu)
            khoi_dong.close()

        poll = [p_ for p_ in du_lieu["poll"] if p_.get("ok")]
        poll_all = du_lieu["poll"]
        so_poll, tre_poll = do_poll([p_["t"] for p_ in poll_all])
        raf = du_lieu["raf"]
        tre_raf = _lon_nhat([raf[i] - raf[i - 1] for i in range(1, len(raf))]) / 1000.0 if len(raf) > 1 else 0.0

        print("")
        print("=" * 74)
        print("KET QUA DO THAT (Playwright, quan sat %.0fs)" % SO_GIAY_QUAN_SAT)
        print("=" * 74)
        print("Poll /api/trang-thai gui di        : %d" % len(poll_all))
        print("Poll thanh cong                    : %d" % len(poll))
        print("Do tre lon nhat giua 2 lan poll     : %.3f s   (yeu cau < 2s)" % (tre_poll / 1000.0))
        print("Do tre lon nhat main thread (rAF)  : %.3f s   (yeu cau < 2s)" % tre_raf)
        print("So khung hinh rAF trong luc do     : %d" % len(raf))
        print("Overlay hien luc dang chay         : %s" % (du_lieu["overlay"] or "KHONG"))
        print("Chu tren thanh trang thai           : %s" % du_lieu["trang_thai"])
        print("Anh chung minh                     : %s" % duong_png)
        print("=" * 74)
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        log.close()


if __name__ == "__main__":
    sys.exit(main())
