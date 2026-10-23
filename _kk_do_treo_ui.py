"""
Do do treo UI khi bam "BAT DAU" (poll /api/trang-thai).

Do chay thuc tren server that (cong rieng 8801), KHONG dung app cua anh:
  1. Khoi dong web_server.py o CONG 8801 bang subprocess.
  2. Dang nhap -> lay token.
  3. POST /api/phan-tich (lan dau = nnap model, truong hop nang nhat).
  4. Poll /api/trang-thai moi 500 ms trong 12s, ghi lai:
       - so lan poll thanh cong
       - do tre lon nhat giua 2 lan poll (giay)
       - thoi gian moi phan hoi (giay)
  5. In ket qua dang bang.

Chay:
    .venv\\Scripts\\python.exe _kk_do_treo_ui.py
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONG = 8801
BASE = "http://127.0.0.1:%d" % CONG
VIDEO = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
THU_MUC_LOG = os.path.join(APP_DIR, "_kk_out")
FILE_LOG = os.path.join(THU_MUC_LOG, "do_treo_server.log")
SO_GIAY_QUAN_SAT = 75.0
KHOANG_POLL = 0.5

_COOKIE = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_COOKIE))


def req(duong, method="GET", data=None, headers=None, token=None, timeout=60):
    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    if token:
        h["X-Camai-Token"] = token
    r = urllib.request.Request(BASE + duong, data=body, headers=h, method=method)
    try:
        with _OPENER.open(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc).encode("utf-8")


def req_json(duong, method="GET", data=None, token=None, timeout=60):
    status, body = req(duong, method=method, data=data, token=token, timeout=timeout)
    try:
        return status, json.loads(body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return status, None


def _cho_server_san_sang(proc, so_giay=90):
    het = time.time() + so_giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        try:
            status, _ = req("/", timeout=5)
            if status == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    return False


def main() -> int:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    mat_khau = secrets.token_urlsafe(12)
    env = os.environ.copy()
    env["CAMAI_PASSWORD"] = mat_khau
    env["PYTHONIOENCODING"] = "utf-8"

    log = open(FILE_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(APP_DIR, "web_server.py"), "--port", str(CONG)],
        cwd=APP_DIR,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        if not _cho_server_san_sang(proc):
            print("[LOI] server khong khoi dong duoc")
            return 1

        status, du_lieu = req_json("/api/dang-nhap", method="POST",
                                   data={"mat_khauu": mat_khau})
        token = (du_lieu or {}).get("token") or ""
        if not token:
            print("[LOI] dang nhap that bai: %s" % status)
            return 1
        print("Dang nhap OK (token %d ky tu)" % len(token))

        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={"input": VIDEO, "conf": 0.25})
        print("POST /api/phan-tich -> %s %s" % (status, json.dumps(du_lieu, ensure_ascii=False)))
        if status != 200:
            print("[LOI] khong bat dau duoc phan tich")
            return 1

        t0 = time.perf_counter()
        lan = 0
        thanh_cong = 0
        tre_lon_nhat = 0.0
        lan_cuoi = None
        do_tre = []
        giai_doan = []
        tre_anh_nen = []
        poll_data = []
        chay_phan_tich = []
        while time.perf_counter() - t0 < SO_GIAY_QUAN_SAT:
            tg = time.perf_counter()
            status, du_lieu = req_json("/api/trang-thai", token=token, timeout=30)
            lan += 1
            poll_data.append(du_lieu if du_lieu else {})
            if status == 200:
                thanh_cong += 1
                if du_lieu and du_lieu.get("giai_doan"):
                    gd = du_lieu["giai_doan"]
                    if not giai_doan or giai_doan[-1] != gd:
                        giai_doan.append(gd)
                    if gd == "Đang phân tích" and not chay_phan_tich:
                        chay_phan_tich.append(round(tg - t0, 2))
                if lan_cuoi is not None:
                    tre = tg - lan_cuoi
                    tre_lon_nhat = max(tre_lon_nhat, tre)
                    do_tre.append(tre)
            else:
                do_tre.append(time.perf_counter() - tg)
            # UI thuc te cung goi /api/anh-nen moi 500ms khi dang chay.
            tg2 = time.perf_counter()
            req("/api/anh-nen", token=token, timeout=30)
            tre_anh_nen.append(time.perf_counter() - tg2)
            lan_cuoi = time.perf_counter()
            time.sleep(KHOANG_POLL)

        # --- LAN 2: model da nap -> phai chay nhanh hon nhieu ---
        lan2_bat_dau = None
        lan2_phan_tich = None
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={"input": VIDEO, "conf": 0.25})
        print("")
        print("LAN 2 (model da nap roi): POST /api/phan-tich -> %s" % status)
        t2 = time.perf_counter()
        het2 = t2 + 60
        while time.perf_counter() < het2:
            _, d2 = req_json("/api/trang-thai", token=token, timeout=30)
            gd2 = (d2 or {}).get("giai_doan")
            if gd2 == "Đang phân tích":
                lan2_phan_tich = time.perf_counter() - t2
                break
            time.sleep(0.2)

        print("")
        print("=" * 70)
        print("KET QUA DO (quan sat %.0fs, poll moi %.0fms)" % (SO_GIAY_QUAN_SAT, KHOANG_POLL * 1000))
        print("=" * 70)
        print("So lan poll gui di           : %d" % lan)
        print("So lan poll thanh cong (200) : %d" % thanh_cong)
        print("Do tre lon nhat giua 2 lan   : %.3f s" % tre_lon_nhat)
        if do_tre:
            do_tre_s = sorted(do_tre)
            print("Do tre trung binh            : %.3f s" % (sum(do_tre) / len(do_tre)))
            print("Do tre median                : %.3f s" % do_tre_s[len(do_tre_s) // 2])
        print("Giai doan thay doi           : %s" % " -> ".join(giai_doan))
        if tre_anh_nen:
            print("Do tre lon nhat /api/anh-nen : %.3f s" % max(tre_anh_nen))
        if chay_phan_tich:
            print("LAN 1: bat dau phan tich sau : %.2f s (nap model lan dau)" % chay_phan_tich[0])
        if lan2_phan_tich is not None:
            print("LAN 2: bat dau phan tich sau : %.2f s (model da nap roi)" % lan2_phan_tich)
        else:
            print("LAN 2: KHONG bat duoc phan tich trong 60s")
        # dong thoi gian: cho biet treo xay ra luc nao (nap model hay chay pipeline)
        print("")
        print("DONG THOI GIAN (chi poll > 0.9s hoac moi bat dau):")
        print("  %8s | %-22s | %6s | %s" % ("giay", "giai_doan", "%", "trang_thai"))
        for i, p_ in enumerate(poll_data):
            du = p_ if isinstance(p_, dict) else {}
            if i == 0 or (i > 0 and isinstance(poll_data[i - 1], dict)
                          and du.get("dong") != poll_data[i - 1].get("dong")):
                print("  %8.2f | %-22s | %6s | %s" % (
                    i * KHOANG_POLL, du.get("giai_doan", "")[:22],
                    du.get("phan_tram", ""), du.get("trang_thai", "")))
        print("=" * 70)
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
