# -*- coding: utf-8 -*-
"""Kiem chung doc lap phan 2 - camai-qa (CamAI v3.10).

4 nhom kiem:
  D. LAN 1 (LAN) - do "warm": process con giu model nen lan 2 phai nhanh hon
     lan 1 (lan 1 phai nap model).
  E. WORKER CHET - giet process con (spawn) that roi chay lai: server co tu
     hoi sinh worker khong? co chay duoc khong?
  F. DUNG GIUA CHUNG - bam DUNG khi dang phan tich: server co treo khong?
  G. FAVICON 404 - request nao tra 404? co phai favicon.ico tu trinh duyet?
     co phai loi that khong?

Chay:
    .venv\\Scripts\\python.exe _kk_qa_kiem_worker_va_favicon.py
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

CONG = 8813

KET_QUA: list[tuple[str, bool, str]] = []


def _in(s: str) -> None:
    print(s, flush=True)


def _ghi(ten: str, ok: bool, chi_tiet: str = "") -> bool:
    KET_QUA.append((ten, bool(ok), chi_tiet))
    _in("  [%s] %s%s" % ("PASS" if ok else "FAIL", ten,
                         (" - " + chi_tiet) if chi_tiet else ""))
    return bool(ok)


def _bang() -> int:
    _in("")
    _in("=" * 74)
    _in("BANG TONG KET - _kk_qa_kiem_worker_va_favicon.py")
    _in("=" * 74)
    for ten, ok, ct in KET_QUA:
        _in("  %-4s %s" % ("PASS" if ok else "FAIL", ten))
        if not ok and ct:
            _in("       -> %s" % ct)
    du = sum(1 for _, ok, _ in KET_QUA if ok)
    _in("-" * 74)
    _in("  TONG KET: %d/%d PASS, %d FAIL" % (du, len(KET_QUA),
                                             len(KET_QUA) - du))
    _in("=" * 74)
    return 0 if du == len(KET_QUA) else 1


# ----------------------------------------------------------------- server
def _bat_dau_server(cong: int, ten_log: str):
    os.makedirs(THU_MUC_TMP, exist_ok=True)
    duong_log = os.path.join(THU_MUC_TMP, ten_log)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CAMAI_DEBUG_KHOA"] = "1"
    env.setdefault("CAMAI_PASSWORD", secrets.token_urlsafe(12))
    log = open(duong_log, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PY, "-W", "ignore", WEB_SERVER, "--port", str(cong)],
        cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT)
    return proc, duong_log


def _doc_log(p: str) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _cho_server(cong: int, proc, giay: int = 180) -> bool:
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
    if proc is None:
        return
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        proc.wait(timeout=15)
    except Exception:                                        # noqa: BLE001
        pass


def _doc_khoa(log: str) -> str:
    t = re.search(r"URL san dung:\s*http://[0-9.]+:\d+/\?k=([A-Za-z0-9_\-]+)",
                  _doc_log(log))
    return t.group(1) if t else ""


# ------------------------------------------------------------------ http
def _req(duong: str, method="GET", data=None, cookie="", timeout=30):
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
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)
    except Exception as exc:                                 # noqa: BLE001
        return 0, str(exc).encode("utf-8"), {}


def _cookie_phien(khoa: str) -> str:
    _, _, hd = _req("/?k=" + khoa)
    for k, v in hd.items():
        if str(k).lower() == "set-cookie" and "camai_phien=" in str(v):
            return "camai_phien=" + str(v).split("camai_phien=", 1)[1].split(";", 1)[0]
    return ""


def _trang_thai(cookie: str) -> dict:
    st, body, _ = _req("/api/trang-thai", cookie=cookie, timeout=15)
    if st != 200:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:                                        # noqa: BLE001
        return {}


# ------------------------------------------------------ tim process con
def _tim_process_con(pid_server: int) -> list:
    """Tra danh sach PID cac process con 'spawn' cua server."""
    import psutil
    ket = []
    try:
        goc = psutil.Process(pid_server)
    except Exception:                                        # noqa: BLE001
        return ket
    # .venv\\Scripts\\python.exe la LAUNCHER STUB -> tiến trình thật là CON.
    for p in goc.children(recursive=True):
        try:
            cmd = " ".join(p.cmdline())
        except Exception:                                    # noqa: BLE001
            continue
        if "spawn_main" in cmd or "multiprocessing" in cmd:
            ket.append((p.pid, cmd[:90]))
    return ket


def _giai_ma_ten(pid: int) -> str:
    import psutil
    try:
        return psutil.Process(pid).name()
    except Exception:                                        # noqa: BLE001
        return "?"


# ------------------------------------------------------ chay 1 lan phan tich
def _chay_phan_tich(cookie: str, nhan: str, doi_dung: bool = False) -> dict:
    """Bat dau phan tich, theo doi den khi xong (hoac het gio)."""
    st, body, _ = _req("/api/phan-tich", method="POST",
                       data={"input": VIDEO_MAU}, cookie=cookie, timeout=30)
    if st != 200:
        return {"loi": "POST /api/phan-tich -> %d %s"
                % (st, body[:200].decode("utf-8", "replace"))}
    t0 = time.perf_counter()
    tre_poll = []
    lan_cuoi = None
    giai_doan = []
    ket = {"lan_cuoi": None, "so_poll": 0, "tre_lon_nhat": 0.0,
           "thoi_gian": 0.0, "giai_doan": giai_doan}
    het = time.time() + 600
    da_dung = False
    while time.time() < het:
        tg = time.perf_counter()
        tt = _trang_thai(cookie)
        ket["so_poll"] += 1
        if lan_cuoi is not None:
            tre_poll.append(tg - lan_cuoi)
        lan_cuoi = time.perf_counter()
        if tt:
            gd = tt.get("giai_doan")
            if gd and (not giai_doan or giai_doan[-1] != gd):
                giai_doan.append(gd)
            ket["lan_cuoi"] = tt
            if tt.get("busy") and doi_dung and not da_dung:
                # chi dung khi da thuc su vao phan tich
                if gd in ("Đang phân tích", "Đang mở video"):
                    da_dung = True
                    td0 = time.perf_counter()
                    st_d, body_d, _ = _req("/api/dung", method="POST",
                                           cookie=cookie, timeout=20)
                    ket["st_dung"] = st_d
                    ket["tre_dung"] = time.perf_counter() - td0
            if da_dung and not tt.get("busy"):
                break
            if not tt.get("busy") and tt.get("xong"):
                break
            if tt.get("loi"):
                break
        time.sleep(0.25)
    ket["tre_lon_nhat"] = max(tre_poll) if tre_poll else 0.0
    ket["thoi_gian"] = time.perf_counter() - t0
    return ket


def _do_ping(cookie: str, so: int = 5) -> float:
    """Do do tre lon nhat cua GET /api/ping (bang chung server con song)."""
    tre = []
    for _ in range(so):
        t0 = time.perf_counter()
        _req("/api/ping", cookie=cookie, timeout=15)
        tre.append(time.perf_counter() - t0)
        time.sleep(0.1)
    return max(tre)


def main() -> int:
    os.makedirs(THU_MUC_OUT, exist_ok=True)
    os.makedirs(THU_MUC_TMP, exist_ok=True)
    _in("=" * 74)
    _in("Kiem chung phan 2 (warm / worker chet / dung giua chung / favicon)")
    _in("cong rieng %d - KHONG dung 8765" % CONG)
    _in("=" * 74)

    proc, log = _bat_dau_server(CONG, "qa_worker_server.log")
    try:
        if not _cho_server(CONG, proc, 180):
            _ghi("Server khoi dong", False, _doc_log(log)[-1200:])
            return _bang()
        khoa = _doc_khoa(log)
        _ghi("Server khoi dong + co khoa", bool(khoa), "do dai=%d" % len(khoa))
        if not khoa:
            return _bang()
        cookie = _cookie_phien(khoa)
        _ghi("Lay duoc cookie phien", bool(cookie), "")

        # ---------------- G. FAVICON (lam truoc, nhanh) ----------------
        _in("")
        _in("-" * 74)
        _in("PHAN G - FAVICON / 404")
        _in("-" * 74)
        st_fav, _, _ = _req("/favicon.ico")
        _in("  GET /favicon.ico -> %d" % st_fav)
        st_root, body_root, hd_root = _req("/")
        _ghi("GET / van tra 200 (khong bi 404)",
             st_root == 200, "status=%d" % st_root)
        co_link_icon = b"rel=" in body_root and b"icon" in body_root.lower()
        _in("  index.html co <link rel=icon>? %s" % co_link_icon)
        _ghi("404 chi la /favicon.ico (trinh duyet tu xin, khong phai loi API)",
             st_fav == 404,
             "favicon=%d | co link icon trong HTML=%s | server KHONG phai nguon"
             % (st_fav, co_link_icon))

        # ---------------- D. LAN 1 (LAN) ----------------
        _in("")
        _in("-" * 74)
        _in("PHAN D - LAN 1 (nap model) VA LAN 2 (warm)")
        _in("-" * 74)
        lan1 = _chay_phan_tich(cookie, "LAN 1")
        _in("  LAN 1: thoi gian=%.1fs | so poll=%d | tre poll lon nhat=%.3fs"
            % (lan1.get("thoi_gian", 0), lan1.get("so_poll", 0),
               lan1.get("tre_lon_nhat", 0)))
        _in("  LAN 1 chuoi giai doan: %s" % " -> ".join(lan1.get("giai_doan", [])))
        _ghi("LAN 1 chay xong khong loi",
             bool(lan1.get("lan_cuoi")) and not (lan1.get("lan_cuoi") or {}).get("loi"),
             "loi=%r" % ((lan1.get("lan_cuoi") or {}).get("loi"),))
        _ghi("LAN 1 co chuoi giai doan nhieu giai doan (>=2)",
             len(lan1.get("giai_doan", [])) >= 2,
             " -> ".join(lan1.get("giai_doan", [])))
        _ghi("LAN 1: do tre poll lon nhat < 2.0s",
             lan1.get("tre_lon_nhat", 99) < 2.0,
             "%.3fs" % lan1.get("tre_lon_nhat", 0))

        lan2 = _chay_phan_tich(cookie, "LAN 2 (warm)")
        _in("  LAN 2: thoi gian=%.1fs | so poll=%d | tre poll lon nhat=%.3fs"
            % (lan2.get("thoi_gian", 0), lan2.get("so_poll", 0),
               lan2.get("tre_lon_nhat", 0)))
        _in("  LAN 2 chuoi giai doan: %s" % " -> ".join(lan2.get("giai_doan", [])))
        _ghi("LAN 2 chay xong khong loi",
             bool(lan2.get("lan_cuoi")) and not (lan2.get("lan_cuoi") or {}).get("loi"),
             "loi=%r" % ((lan2.get("lan_cuoi") or {}).get("loi"),))
        nhanh_hon = lan2.get("thoi_gian", 999) < lan1.get("thoi_gian", 0)
        _ghi("LAN 2 (warm) NHANH HON lan 1 (process con giu model)",
             nhanh_hon,
             "lan1=%.1fs lan2=%.1fs" % (lan1.get("thoi_gian", 0),
                                       lan2.get("thoi_gian", 0)))

        # ---------------- E. WORKER CHET ----------------
        _in("")
        _in("-" * 74)
        _in("PHAN E - GIET PROCESS CON, LAN SAU CO HOI SINH KHONG?")
        _in("-" * 74)
        con = _tim_process_con(proc.pid)
        _in("  Process con 'spawn' cua server: %s" % (con if con else "(khong thay)"))
        if not con:
            _ghi("Tim thay process con giu model", False, "khong thay")
        else:
            pid_worker = con[0][0]
            _in("  Giet PID %d (%s)" % (pid_worker, _giai_ma_ten(pid_worker)))
            subprocess.run(["taskkill", "/PID", str(pid_worker), "/T", "/F"],
                           capture_output=True, timeout=30)
            time.sleep(2.0)
            con_sau = _tim_process_con(proc.pid)
            _in("  Process con sau khi giet: %s"
                % (con_sau if con_sau else "(khong con)"))
            lan3 = _chay_phan_tich(cookie, "LAN 3 (sau khi giet worker)")
            _in("  LAN 3: thoi gian=%.1fs | so poll=%d | tre=%.3fs | giai doan: %s"
                % (lan3.get("thoi_gian", 0), lan3.get("so_poll", 0),
                   lan3.get("tre_lon_nhat", 0),
                   " -> ".join(lan3.get("giai_doan", []))))
            _ghi("SAU KHI GIET WORKER, LAN CHAY MOI VAN CHAY DUOC (tu hoi sinh)",
                 bool(lan3.get("lan_cuoi"))
                 and not (lan3.get("lan_cuoi") or {}).get("loi"),
                 "loi=%r" % ((lan3.get("lan_cuoi") or {}).get("loi"),))
            con_cuoi = _tim_process_con(proc.pid)
            _ghi("Server da tao process con MOI sau khi worker cu chet",
                 bool(con_cuoi) and con_cuoi[0][0] != pid_worker,
                 "cu=%s moi=%s" % (pid_worker,
                                   con_cuoi[0][0] if con_cuoi else "khong"))

        # ---------------- F. DUNG GIUA CHUNG ----------------
        _in("")
        _in("-" * 74)
        _in("PHAN F - DUNG GIUA CHUNG CO TREO KHONG?")
        _in("-" * 74)
        lan4 = _chay_phan_tich(cookie, "LAN 4 (dung giua chung)", doi_dung=True)
        _in("  LAN 4: thoi gian=%.1fs | st_dung=%s | tre_dung=%.3fs"
            % (lan4.get("thoi_gian", 0), lan4.get("st_dung", "?"),
               lan4.get("tre_dung", 0)))
        _ghi("POST /api/dung tra ve 200 (khong loi)",
             lan4.get("st_dung") == 200, "status=%s" % lan4.get("st_dung"))
        _ghi("Server phan hoi /api/ping sau khi dung (<1s)",
             _do_ping(cookie) < 1.0, "%.3fs" % _do_ping(cookie))
        lan_cuoi = lan4.get("lan_cuoi") or {}
        _ghi("Sau khi dung: busy=False (ket thuc, khong treo)",
             lan_cuoi.get("busy") is False,
             "busy=%r xong=%r" % (lan_cuoi.get("busy"), lan_cuoi.get("xong")))
        tre_poll4 = lan4.get("tre_lon_nhat", 99)
        _ghi("Khong treo: do tre poll lon nhat trong lan dung < 2.0s",
             tre_poll4 < 2.0, "%.3fs" % tre_poll4)

        # ---------------- 1 LAN CHAY NUA: server con song ----------------
        lan5 = _chay_phan_tich(cookie, "LAN 5 (sau khi dung)")
        _ghi("Server van chay duoc sau khi DUNG (khong hong)",
             bool(lan5.get("lan_cuoi"))
             and not (lan5.get("lan_cuoi") or {}).get("loi"),
             "loi=%r" % ((lan5.get("lan_cuoi") or {}).get("loi"),))
    finally:
        _dung_server(proc)
    return _bang()


if __name__ == "__main__":
    sys.exit(main())
