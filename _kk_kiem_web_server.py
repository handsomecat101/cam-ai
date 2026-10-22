"""
Kiem chung web_server.py (v3.7 web-first): dang nhap, API, anh nen, phan tich.

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_web_server.py            (nhanh)
    .venv\\Scripts\\python.exe _kk_kiem_web_server.py --co-video  (them video co nguoi)

Script tu:
  1. Khoi dong server o CONG RIENG (8799) bang subprocess.
  2. Kiem tra tung muc (GET /, 401, sai mat khau, dung mat khau, trang-thai,
     lop-viet, quet-camera, anh-nen, phan tich that, tai-video, Range).
  3. In URL LAN ma server in ra khi khoi dong.
  4. Tat server sach.

Video mac dinh: video_mau/car-detection.mp4 (CHU co nguoi - chi co xe).
  -> de kiem tra su kien vao/ra co that, them --co-video de chay them
     video_mau/people-detection.mp4 (co nguoi vao/ra).

v3.8: them phan kiem chung API MOI
  - GET  /api/cau-hinh  : 12 nhom + MOI field cua AnalysisConfig.
  - POST /api/phan-tich : body PHANG chua field cua AnalysisConfig.
  - GET  /api/ket-qua, /api/anh-su-kien, /api/bien-so.

KHONG hardcode mat khau: sinh mat khau ngau nhien roi truyen qua bien moi truong
CAMAI_PASSWORD cho subprocess.
"""

from __future__ import annotations

import http.cookiejar
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
CONG = 8799
BASE = "http://127.0.0.1:%d" % CONG
VIDEO_MAU = os.path.join(APP_DIR, "video_mau", "car-detection.mp4")
VIDEO_CO_NGUOI = os.path.join(APP_DIR, "video_mau", "people-detection.mp4")
THU_MUC_LOG = os.path.join(APP_DIR, "_kk_out")
FILE_LOG = os.path.join(THU_MUC_LOG, "web_server_khoi_dong.log")
CHAY_VIDEO_CO_NGUOI = "--co-video" in sys.argv

# Hop dong /api/trang-thai (UI moi doc dung ten nay).
FIELD_YEU_CAU = [
    "busy", "xong", "loai_nguon", "tep", "dong", "tong_khung", "fps_hien_tai",
    "nguoi", "mat", "nguoi_quen", "vao", "ra", "trong_vung", "xe",
    "su_kien", "nhat_ky", "loi",
]

KET_QUA: list[tuple[str, bool, str]] = []


def _ghi(ten: str, ok: bool, ghi_chu: str = "") -> None:
    KET_QUA.append((ten, ok, ghi_chu))
    print("[%s] %-46s %s" % ("PASS" if ok else "FAIL", ten, ghi_chu), flush=True)


def _in(text: str = "") -> None:
    print(text, flush=True)


# ------------------------------------------------------------------ HTTP
_COOKIE = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_COOKIE))


def req(duong, method="GET", data=None, headers=None, token=None, timeout=300):
    """Tra (status, body bytes, headers dict)."""
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
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def req_json(duong, method="GET", data=None, token=None):
    status, body, _ = req(duong, method=method, data=data, token=token)
    try:
        return status, json.loads(body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return status, None


def req_multipart(duong, fields, file_field=None, file_path=None,
                  file_name=None, token=None, timeout=300):
    """POST multipart/form-data. Tra (status, body bytes).

    `fields`: dict ten->gia tri (text). `file_field`/`file_path`: tep dinh kem.
    """
    ranh_gioi = "----CamAI" + secrets.token_hex(12)
    dong: list[bytes] = []
    for ten, gia_tri in (fields or {}).items():
        dong.append(("--%s" % ranh_gioi).encode("utf-8"))
        dong.append(
            ('Content-Disposition: form-data; name="%s"' % ten).encode("utf-8")
        )
        dong.append(b"")
        dong.append(str(gia_tri).encode("utf-8"))
    if file_field and file_path and os.path.isfile(file_path):
        ten_file = file_name or os.path.basename(file_path)
        dong.append(("--%s" % ranh_gioi).encode("utf-8"))
        dong.append(
            ('Content-Disposition: form-data; name="%s"; filename="%s"'
             % (file_field, ten_file)).encode("utf-8")
        )
        dong.append(b"Content-Type: image/jpeg")
        dong.append(b"")
        with open(file_path, "rb") as f:
            dong.append(f.read())
    dong.append(("--%s--" % ranh_gioi).encode("utf-8"))
    dong.append(b"")
    body = b"\r\n".join(dong)
    headers = {"Content-Type": "multipart/form-data; boundary=%s" % ranh_gioi}
    if token:
        headers["X-Camai-Token"] = token
    r = urllib.request.Request(BASE + duong, data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _parse_json(body: bytes):
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}


# ------------------------------------------------------------------ chay
def _cho_server_san_sang(proc, so_giay=90):
    het = time.time() + so_giay
    while time.time() < het:
        if proc.poll() is not None:
            return False
        try:
            status, _, _ = req("/", timeout=5)
            if status == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def _doc_url_lan():
    """Doc URL LAN trong log cua server."""
    if not os.path.isfile(FILE_LOG):
        return ""
    with open(FILE_LOG, "r", encoding="utf-8", errors="replace") as f:
        noi_dung = f.read()
    tim = re.search(r"Tren dien thoai:\s+(http://[0-9.]+:\d+)", noi_dung)
    return tim.group(1) if tim else ""


def _doc_canh_bao():
    if not os.path.isfile(FILE_LOG):
        return ""
    with open(FILE_LOG, "r", encoding="utf-8", errors="replace") as f:
        noi_dung = f.read()
    return noi_dung


# ------------------------------------------------------------------ v3.8
def _lay_field_dataclass():
    """Tra (danh sach ten field, so field) cua `cam_ai_core.AnalysisConfig`.

    NGUON SU THAT: doc truc tiep dataclass trong cam_ai_core.py (import mot
    lan, mat ~9 giay vi torch - chi lam trong may kiem chung).
    """
    try:
        sys.path.insert(0, APP_DIR)
        import cam_ai_core

        truong = cam_ai_core.AnalysisConfig.__dataclass_fields__
        return list(truong.keys()), len(truong)
    except Exception as exc:  # noqa: BLE001
        _in("  [LOI] khong import duoc cam_ai_core: %s" % exc)
        return [], 0


def _wait_cfg_log(so_giay=90):
    """Cho server in dong '[web] cfg: ...' (config da dung) roi tra ve noi dung log."""
    het = time.time() + so_giay
    while time.time() < het:
        noi_dung = _doc_canh_bao()
        if "[web] cfg:" in noi_dung:
            return noi_dung
        time.sleep(1)
    return _doc_canh_bao()


# Log server GHI THEM lien tuc -> phai biet phan NAO la moi, khong doc lai
# toan bo log (se lay nham config cua lan chay truoc).
_LOG_VI_TRI = 0        # vi tri ky tu da doc toi trong log
_SO_CFG = 0            # so dong '[web] cfg:' da thay


def _bat_dau_lan():
    """Ghi nhan vi tri hien tai cua log (dung cho lan kiem chung sau)."""
    global _LOG_VI_TRI, _SO_CFG
    noi_dung = _doc_canh_bao()
    _LOG_VI_TRI = len(noi_dung)
    _SO_CFG = noi_dung.count("[web] cfg:")


def _log_va_cfg_moi(so_giay=120):
    """Cho config MOI xuat hien. Tra (phan log moi, dict config moi)."""
    global _LOG_VI_TRI, _SO_CFG
    het = time.time() + so_giay
    noi_dung = _doc_canh_bao()
    while time.time() < het:
        noi_dung = _doc_canh_bao()
        if noi_dung.count("[web] cfg:") > _SO_CFG:
            break
        time.sleep(1)
    phan = noi_dung[_LOG_VI_TRI:]
    _LOG_VI_TRI = len(noi_dung)
    _SO_CFG = noi_dung.count("[web] cfg:")
    return phan, _lay_cfg_log(phan)


def _lay_cfg_log(noi_dung):
    """Lay cac dong '[web] cfg: ten = gia tri' tu log server -> dict."""
    ket = {}
    for dong in (noi_dung or "").splitlines():
        if "[web] cfg:" not in dong:
            continue
        phan = dong.split("[web] cfg:", 1)[1].strip()
        if "=" not in phan:
            continue
        ten, gia_tri = phan.split("=", 1)
        ket[ten.strip()] = gia_tri.strip()
    return ket


def _doi_chieu_cfg(ten_field, mong_doi):
    """So gia tri config server in ra voi gia tri mong doi."""
    for k, v in mong_doi.items():
        gia_tri = ten_field.get(k)
        if gia_tri is None:
            return False, "%s: thieu trong log" % k
        if gia_tri.strip() != v:
            return False, "%s: log=%r, mong doi=%r" % (k, gia_tri.strip(), v)
    return True, "khop %d truong" % len(mong_doi)


def _cho_xong(token, so_giay=420):
    """Cho phan tich chay xong. Tra (da_xong, trang_thai_cuoi)."""
    het = time.time() + so_giay
    trang_thai: dict = {}
    while time.time() < het:
        _, trang_thai = req_json("/api/trang-thai", token=token)
        if isinstance(trang_thai, dict):
            if trang_thai.get("busy"):
                pass
            elif trang_thai.get("xong") or trang_thai.get("loi"):
                return True, trang_thai
        time.sleep(1)
    return False, trang_thai if isinstance(trang_thai, dict) else {}


def main() -> int:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    mat_khau = secrets.token_urlsafe(12)          # KHONG hardcode
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
    _in("=" * 72)
    _in("Kiem chung web_server.py - cong %d" % CONG)
    _in("=" * 72)

    try:
        if not _cho_server_san_sang(proc):
            _ghi("Server khoi dong", False, "khong san sang sau 90s")
            _in(_doc_canh_bao()[-3000:])
            return 1
        _ghi("Server khoi dong", True, "cong %d" % CONG)

        # --- 1. GET / ---
        status, body, _ = req("/")
        la_html = b"<html" in body.lower() or b"<!doctype html" in body.lower()
        _ghi("GET / -> 200 + HTML", status == 200 and la_html,
             "status=%d, %d byte" % (status, len(body)))

        # --- 2. GET /api/trang-thai khong token -> 401 ---
        status, _, _ = req("/api/trang-thai")
        _ghi("GET /api/trang-thai (khong token) -> 401", status == 401,
             "status=%d" % status)

        # --- 3. Sai mat khau ---
        status, du_lieu = req_json("/api/dang-nhap", method="POST",
                                   data={"mat_khauu": "sai-mat-khau-123"})
        vao_duoc = bool(du_lieu and du_lieu.get("ok"))
        token_sai = (du_lieu or {}).get("token")
        _ghi("POST /api/dang-nhap sai mat khau -> bi tu choi",
             status != 200 or not vao_duoc,
             "status=%d, ok=%s, co_token=%s" % (status, vao_duoc, bool(token_sai)))

        # --- 4. Dung mat khau -> token ---
        status, du_lieu = req_json("/api/dang-nhap", method="POST",
                                   data={"mat_khauu": mat_khau})
        token = (du_lieu or {}).get("token") or ""
        _ghi("POST /api/dang-nhap dung mat khau -> token", status == 200 and bool(token),
             "status=%d, token=%s" % (status, ("da nhan" if token else "THIEU")))
        if not token:
            return 1

        # --- 5. GET /api/trang-thai co token -> 200 + du field ---
        status, trang_thai = req_json("/api/trang-thai", token=token)
        co_field = []
        thieu = []
        if isinstance(trang_thai, dict):
            for ten in FIELD_YEU_CAU:
                (co_field if ten in trang_thai else thieu).append(ten)
        _in("")
        _in("  DANH SACH FIELD THUC TE cua /api/trang-thai (%d):"
            % (len(trang_thai) if isinstance(trang_thai, dict) else 0))
        if isinstance(trang_thai, dict):
            for ten in sorted(trang_thai.keys()):
                _in("    - %s" % ten)
        _in("  THIEU field theo hop dong: %s" % (", ".join(thieu) if thieu else "KHONG"))
        _in("")
        _ghi("GET /api/trang-thai co token -> 200 + du field",
             status == 200 and not thieu,
             "status=%d, thieu=%s" % (status, thieu if thieu else "khong"))

        # --- 6. GET /api/lop-viet ---
        status, du_lieu = req_json("/api/lop-viet", token=token)
        danh = (du_lieu or {}).get("danh_sach") or []
        rong = [x for x in danh if not (x.get("ten_viet") or "").strip()]
        _ghi("GET /api/lop-viet -> 80 lop, ten_viet khong rong",
             status == 200 and len(danh) == 80 and not rong,
             "status=%d, so_lop=%d, ten_rong=%d" % (status, len(danh), len(rong)))

        # --- 7. GET /api/quet-camera ---
        status, du_lieu = req_json("/api/quet-camera", token=token)
        danh_cam = (du_lieu or {}).get("danh_sach")
        _ghi("GET /api/quet-camera -> 200 (khong 500)",
             status == 200 and isinstance(danh_cam, list),
             "status=%d, so_camera=%s" % (status, len(danh_cam) if isinstance(danh_cam, list) else "?"))

        # --- 8. GET /api/anh-nen (placeholder) ---
        status, body, headers = req("/api/anh-nen", token=token)
        kieu = (headers.get("Content-Type") or headers.get("content-type") or "")
        anh_placeholder = body
        _ghi("GET /api/anh-nen -> 200 + image/jpeg",
             status == 200 and "image/jpeg" in kieu and len(body) > 100,
             "status=%d, content-type=%s, %d byte" % (status, kieu, len(body)))

        # --- 9. POST /api/phan-tich voi video mau ---
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={
                                       "duong_dan": VIDEO_MAU,
                                       "nhan_mat": True,
                                       "dem_ra_vao": True,
                                       "vat_the": True,
                                       "ve_khung": True,
                                       "ve_nhan": True,
                                       "lop": "",
                                   })
        _ghi("POST /api/phan-tich -> ok + thong_bao",
             status == 200 and bool((du_lieu or {}).get("ok"))
             and bool((du_lieu or {}).get("thong_bao")),
             "status=%d, du_lieu=%s" % (status, du_lieu))

        # poll: thay busy=true roi xong=true
        thay_busy = False
        thay_xong = False
        het = time.time() + 420
        trang_thai_cu = {}
        while time.time() < het:
            _, trang_thai_cu = req_json("/api/trang-thai", token=token)
            if not isinstance(trang_thai_cu, dict):
                time.sleep(1)
                continue
            if trang_thai_cu.get("busy"):
                thay_busy = True
            if thay_busy and not trang_thai_cu.get("busy") and trang_thai_cu.get("xong"):
                thay_xong = True
                break
            if trang_thai_cu.get("loi"):
                break
            time.sleep(1)
        _ghi("Phan tich chay that: thay busy=true", thay_busy, "busy=%s" % trang_thai_cu.get("busy"))
        _ghi("Phan tich chay that: ket thuc xong=true", thay_xong,
             "xong=%s, loi=%r" % (trang_thai_cu.get("xong"), trang_thai_cu.get("loi")))
        _in("")
        _in("  TRANG THAI CUOI: " + json.dumps(
            {k: v for k, v in (trang_thai_cu or {}).items()
             if k in ("busy", "xong", "loai_nguon", "tep", "dong", "tong_khung",
                      "fps_hien_tai", "nguoi", "mat", "nguoi_quen", "vao", "ra",
                      "trong_vung", "xe", "loi")},
            ensure_ascii=False))
        _in("  SO SU KIEN: %d | SO DONG NHAT KY: %d"
            % (len(trang_thai_cu.get("su_kien") or []),
               len(trang_thai_cu.get("nhat_ky") or [])))
        _in("")

        # --- 9b. anh nen sau khi chay -> khac placeholder ---
        status, body, headers = req("/api/anh-nen", token=token)
        _ghi("GET /api/anh-nen -> anh that (khac placeholder)",
             status == 200 and len(body) > 100 and body != anh_placeholder,
             "status=%d, %d byte, khac placeholder=%s"
             % (status, len(body), body != anh_placeholder))

        # --- 10. GET /api/tai-video ---
        status, body, headers = req("/api/tai-video", token=token)
        la_mp4 = len(body) > 1000 and body[4:8] == b"ftyp"
        _ghi("GET /api/tai-video -> 200 + file mp4 doc duoc",
             status == 200 and la_mp4,
             "status=%d, %d byte, chuoi mp4=%s" % (status, len(body), la_mp4))

        # --- 10b. Range request (Safari/iOS) ---
        status, body, headers = req("/api/tai-video", token=token,
                                    headers={"Range": "bytes=0-1023"})
        content_range = headers.get("Content-Range") or headers.get("content-range") or ""
        accept = headers.get("Accept-Ranges") or headers.get("accept-ranges") or ""
        _ghi("GET /api/tai-video voi Range -> 206 Partial Content",
             status == 206 and len(body) == 1024 and "bytes 0-1023/" in content_range,
             "status=%d, %d byte, content-range=%s, accept-ranges=%s"
             % (status, len(body), content_range, accept))

        # --- 10c. Video CO NGUOI: kiem tra su kien vao/ra that ---
        # video_mau/car-detection.mp4 CHI co xe (0 nguoi) -> khong co su kien.
        # Video nay co nguoi vao/ra -> su_kien phai co du lieu that.
        if CHAY_VIDEO_CO_NGUOI:
            status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                       data={
                                           "duong_dan": VIDEO_CO_NGUOI,
                                           "nhan_mat": True,
                                           "dem_ra_vao": True,
                                           "vat_the": True,
                                           "ve_khung": True,
                                           "ve_nhan": True,
                                           "lop": "",
                                       })
            het = time.time() + 420
            trang_thai_2: dict = {}
            while time.time() < het:
                _, trang_thai_2 = req_json("/api/trang-thai", token=token)
                if (isinstance(trang_thai_2, dict) and not trang_thai_2.get("busy")
                        and trang_thai_2.get("xong")):
                    break
                time.sleep(1)
            su_kien = (trang_thai_2 or {}).get("su_kien") or []
            _ghi("Video co nguoi: su_kien vao/ra co du lieu that",
                 len(su_kien) > 0,
                 "so_su_kien=%d, mau=%s" % (len(su_kien), json.dumps(su_kien[:3],
                                                                     ensure_ascii=False)))
            _in("  (video co nguoi) nguoi=%s vao=%s ra=%s xe=%s dong=%s/%s"
                % (trang_thai_2.get("nguoi"), trang_thai_2.get("vao"),
                   trang_thai_2.get("ra"), trang_thai_2.get("xe"),
                   trang_thai_2.get("dong"), trang_thai_2.get("tong_khung")))
            _in("")

        # ================= PHAN MOI (v3.8): API cau hinh + body phang ============
        _in("")
        _in("  " + "=" * 68)
        _in("  PHAN MOI: /api/cau-hinh + POST /api/phan-tich (body phang)")
        _in("  " + "=" * 68)

        # --- A. GET /api/cau-hinh ---
        status, cau_hinh = req_json("/api/cau-hinh", token=token)
        nhom = (cau_hinh or {}).get("nhom") or []
        _ghi("GET /api/cau-hinh -> 200", status == 200, "status=%d" % status)
        _ghi("GET /api/cau-hinh -> DUNG 12 NHOM", len(nhom) == 12,
             "so_nhom=%d" % len(nhom))

        # Field cua dataclass (nguon su that) so voi field trong response.
        ten_dataclass, so_dataclass = _lay_field_dataclass()
        ten_response = []
        for n in nhom:
            for f in (n.get("truong") or []):
                ten_response.append(f.get("ten"))
        trung = [t for t in set(ten_response) if ten_response.count(t) > 1]
        thieu = [t for t in ten_dataclass if t not in ten_response]
        thua = [t for t in ten_response if t not in ten_dataclass]
        _in("")
        _in("  SO FIELD TRONG DATACLASS (cam_ai_core.AnalysisConfig): %d" % so_dataclass)
        _in("  SO FIELD TRONG RESPONSE /api/cau-hinh:                %d" % len(ten_response))
        _in("  SO NHOM TRONG RESPONSE:                               %d" % len(nhom))
        _in("  BANG NHAU (dataclass == response): %s"
            % (so_dataclass == len(ten_response) and not thieu and not thua
               and not trung))
        _in("  THIEU: %s | THUA: %s | TRUNG: %s"
            % (thieu or "khong", thua or "khong", trung or "khong"))
        _ghi("/api/cau-hinh: moi field xuat hien DUNG 1 LAN",
             bool(ten_dataclass) and not thieu and not thua and not trung
             and so_dataclass == len(ten_response),
             "dataclass=%d, response=%d, thieu=%s, thua=%s, trung=%s"
             % (so_dataclass, len(ten_response), thieu, thua, trung))

        # --- B. In bang mapping nhom -> field (de coordinator doi chieu voi GUI) ---
        _in("")
        _in("  BANG MAPPING NHOM -> FIELD (12 nhom, thu tu control trong GUI):")
        for i, n in enumerate(nhom, 1):
            ds = [f.get("ten") for f in (n.get("truong") or [])]
            _in("   %2d. %-32s (%d field)" % (i, n.get("ten"), len(ds)))
            _in("        %s" % (", ".join(ds) if ds else "(khong co field)"))
        _in("")

        # --- C. POST /api/phan-tich voi body PHANG day du field ---
        _bat_dau_lan()
        body_phang = {
            "input": VIDEO_MAU,
            "conf": 0.3,
            "nhan_vat_the": True,
            "lop": "ô tô",
            "doc_bien_so": True,
            "dem_phuong_tien": True,
            "vung_max": 5,
            "canh_lau": 3.5,
            "tu_luu_clip": "clip_thu",
            "face_threshold": 0.45,
            "clip_giay": 15,
        }
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data=body_phang)
        _ghi("POST /api/phan-tich (body phang) -> ok, tra ve NGAY",
             status == 200 and bool((du_lieu or {}).get("ok")),
             "status=%d, du_lieu=%s" % (status, du_lieu))

        # Server in config da dung ra -> doi chieu tung truong.
        phan_log, cfg_log = _log_va_cfg_moi(150)
        _in("")
        _in("  CONFIG SERVER IN RA (dong '[web] cfg:'):")
        for k in sorted(cfg_log):
            _in("      %-24s = %s" % (k, cfg_log[k]))
        _in("")
        ok_cfg, ghi_chu_cfg = _doi_chieu_cfg(
            cfg_log,
            {
                "conf": "0.3",
                "nhan_vat_the": "True",
                "lop": "ô tô",
                "doc_bien_so": "True",
                "dem_phuong_tien": "True",
                "vung_max": "5",
                "canh_lau": "3.5",
                "tu_luu_clip": "clip_thu",
                "face_threshold": "0.45",
                "clip_giay": "15.0",
            },
        )
        _ghi("Log server in config DUNG voi body gui len", ok_cfg, ghi_chu_cfg)

        # Cho chay xong lan nay.
        xong, trang_thai_phang = _cho_xong(token, 420)
        _ghi("Phan tich body phang chay xong (khong loi)",
             xong and not (trang_thai_phang or {}).get("loi"),
             "xong=%s, loi=%r" % (xong, (trang_thai_phang or {}).get("loi")))

        # --- D. GET /api/ket-qua ---
        status, ket_qua = req_json("/api/ket-qua", token=token)
        truong_ky = ["so_nguoi_max", "so_mat_max", "ten_da_nhan", "nam", "nu",
                     "tuoi_tb", "phuong_tien", "bien_so", "so_vi_pham",
                     "so_crowd", "so_loiter", "thoi_luong_clip", "so_khung",
                     "fps", "duong_dan_video", "duong_dan_bao_cao", "so_su_kien"]
        thieu_kq = [t for t in truong_ky if not isinstance(ket_qua, dict)
                    or t not in ket_qua]
        _in("")
        _in("  GET /api/ket-qua: " + json.dumps(
            {k: v for k, v in (ket_qua or {}).items() if k in truong_ky},
            ensure_ascii=False)[:600])
        _ghi("GET /api/ket-qua -> 200 + du 17 truong hop dong",
             status == 200 and not thieu_kq,
             "status=%d, thieu=%s" % (status, thieu_kq or "khong"))
        _ghi("GET /api/ket-qua -> co so_nguoi_max",
             isinstance(ket_qua, dict) and "so_nguoi_max" in ket_qua,
             "so_nguoi_max=%s" % (ket_qua or {}).get("so_nguoi_max"))

        # --- E. GET /api/anh-su-kien + /api/bien-so ---
        status, anh = req_json("/api/anh-su-kien", token=token)
        ds_anh = (anh or {}).get("danh_sach")
        _ghi("GET /api/anh-su-kien -> 200 + danh sach",
             status == 200 and isinstance(ds_anh, list),
             "status=%d, so_anh=%s" % (status, len(ds_anh) if isinstance(ds_anh, list) else "?"))
        status, bien = req_json("/api/bien-so", token=token)
        ds_bien = (bien or {}).get("danh_sach")
        _ghi("GET /api/bien-so -> 200 + danh sach",
             status == 200 and isinstance(ds_bien, list),
             "status=%d, so_bien_so=%s"
             % (status, len(ds_bien) if isinstance(ds_bien, list) else "?"))
        _in("  /api/bien-so: " + json.dumps(ds_bien or [], ensure_ascii=False)[:400])
        _in("")

        # --- F. Body co FIELD LA -> khong crash ---
        _bat_dau_lan()
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={"input": VIDEO_MAU, "conf": 0.3,
                                         "xyz_khong_co": 123})
        ok_la = status == 200 and bool((du_lieu or {}).get("ok"))
        phan_la, cfg_la = _log_va_cfg_moi(150)
        co_canh_bao_la = "field la" in phan_la
        # Dung ngay lan phan tich nay (khong can chay het video).
        req_json("/api/dung", method="POST", token=token)
        xong_la, _ = _cho_xong(token, 180)
        status_sau, _ = req_json("/api/trang-thai", token=token)
        _in("")
        _in("  CANH BAO SERVER IN RA (field la): %s"
            % (" | ".join(d.strip() for d in phan_la.splitlines()
                          if "field la" in d) or "KHONG CO"))
        _ghi("Body co field LA -> khong crash, van chay",
             ok_la and co_canh_bao_la and status_sau == 200,
             "status=%d, co_canh_bao_log=%s, server_song=%s"
             % (status, co_canh_bao_la, status_sau == 200))

        # --- G. Body SAI KIEU -> khong crash, ep kieu/bỏ qua + ghi log ---
        _bat_dau_lan()
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={"input": VIDEO_MAU, "conf": "abc",
                                         "vung_max": "xyz", "canh_lau": True,
                                         "clip_giay": "12.5"})
        ok_kieu = status == 200 and bool((du_lieu or {}).get("ok"))
        phan_kieu, cfg_kieu = _log_va_cfg_moi(150)
        co_canh_bao_kieu = "sai kieu" in phan_kieu
        req_json("/api/dung", method="POST", token=token)
        _cho_xong(token, 180)
        status_sau, _ = req_json("/api/trang-thai", token=token)
        _in("")
        _in("  CANH BAO SERVER IN RA (sai kieu): %s"
            % (" | ".join(d.strip() for d in phan_kieu.splitlines()
                          if "sai kieu" in d) or "KHONG CO"))
        _in("  CONFIG SAU KHI GUI SAI KIEU: conf=%s vung_max=%s canh_lau=%s clip_giay=%s"
            % (cfg_kieu.get("conf"), cfg_kieu.get("vung_max"),
               cfg_kieu.get("canh_lau"), cfg_kieu.get("clip_giay")))
        _ghi("Body sai kieu -> khong crash, bo qua + ghi log",
             ok_kieu and co_canh_bao_kieu and status_sau == 200,
             "status=%d, co_canh_bao_log=%s, server_song=%s"
             % (status, co_canh_bao_kieu, status_sau == 200))
        _ghi("Body sai kieu: gia tri hop le van duoc ep dung",
             cfg_kieu.get("conf") == "0.25" and cfg_kieu.get("clip_giay") == "12.5",
             "conf=%s (mac dinh), clip_giay=%s (ep tu chuoi)"
             % (cfg_kieu.get("conf"), cfg_kieu.get("clip_giay")))

        # --- H. Cac route CU van chay ---
        status, _ = req_json("/api/trang-thai", token=token)
        _ghi("Route CU /api/trang-thai -> 200", status == 200, "status=%d" % status)
        status, _ = req_json("/api/lop-viet", token=token)
        _ghi("Route CU /api/lop-viet -> 200", status == 200, "status=%d" % status)
        status, _ = req_json("/api/quet-camera", token=token)
        _ghi("Route CU /api/quet-camera -> 200", status == 200, "status=%d" % status)
        status, body, headers = req("/api/anh-nen", token=token)
        kieu_anh = (headers.get("Content-Type") or headers.get("content-type") or "")
        _ghi("Route CU /api/anh-nen -> 200 + image/jpeg",
             status == 200 and "image/jpeg" in kieu_anh,
             "status=%d, content-type=%s" % (status, kieu_anh))
        status, body, headers = req("/api/tai-video", token=token)
        _ghi("Route CU /api/tai-video -> 200", status == 200, "status=%d" % status)
        status, body, headers = req("/api/tai-video", token=token,
                                    headers={"Range": "bytes=0-1023"})
        content_range = headers.get("Content-Range") or headers.get("content-range") or ""
        _ghi("Route CU /api/tai-video Range -> 206",
             status == 206 and "bytes 0-1023/" in content_range,
             "status=%d, content-range=%s" % (status, content_range))
        _in("")

        # --- I. TINH NANG MOI (7 route moi) ---
        _in("")
        _in("  === I. TINH NANG MOI (dang ky nguoi quen / ve vung / canh bao / thong tin) ===")
        thu_muc_kf = os.path.join(APP_DIR, "known_faces")
        file_vung = os.path.join(APP_DIR, "vung.txt")
        anh_nguoi = os.path.join(thu_muc_kf, "An", "01.jpg")

        # --- I.1 GET /api/nguoi-quen ---
        status, du_lieu = req_json("/api/nguoi-quen", token=token)
        ds = (du_lieu or {}).get("danh_sach")
        _ghi("GET /api/nguoi-quen -> 200 + danh sach",
             status == 200 and bool((du_lieu or {}).get("ok")) and isinstance(ds, list),
             "status=%d, so_nguoi=%s" % (status, (du_lieu or {}).get("so_nguoi")))

        # --- I.2 POST /api/nguoi-quen voi ten HOP LE ---
        so_anh_truoc = len(os.listdir(os.path.join(thu_muc_kf, "An")))
        status, body = req_multipart("/api/nguoi-quen", {"ten": "An"}, "anh",
                                      anh_nguoi, token=token)
        du_lieu = _parse_json(body)
        so_anh_sau = len(os.listdir(os.path.join(thu_muc_kf, "An")))
        _in("  DANG KY: %s" % json.dumps(du_lieu, ensure_ascii=False)[:300])
        _ghi("POST /api/nguoi-quen (ten hop le) -> 200 + luu anh",
             status == 200 and bool(du_lieu.get("ok")) and so_anh_sau == so_anh_truoc + 1,
             "status=%d, so_anh %d -> %d, thu_muc=%s"
             % (status, so_anh_truoc, so_anh_sau, du_lieu.get("thu_muc")))
        file_anh_tao = du_lieu.get("file_anh") or ""

        # --- I.3 Ten KHONG hop le -> 400 + KHONG ghi file ra ngoai known_faces ---
        ten_sai = ["../../etc", "a/b", "", "..", "a\\b", "C:\\Windows",
                   "An/../Binh", ".", "x" * 41, "An%00"]
        truoc_kf = sorted(os.listdir(thu_muc_kf))
        truoc_app = sorted(os.listdir(APP_DIR))
        truoc_ngoai = sorted(os.listdir(os.path.dirname(APP_DIR)))
        ket_qua_sai = []
        for t in ten_sai:
            status, body = req_multipart("/api/nguoi-quen", {"ten": t}, "anh",
                                          anh_nguoi, token=token)
            ket_qua_sai.append((t, status))
        sau_kf = sorted(os.listdir(thu_muc_kf))
        sau_app = sorted(os.listdir(APP_DIR))
        sau_ngoai = sorted(os.listdir(os.path.dirname(APP_DIR)))
        _ghi("Ten khong hop le -> 400 (chan path traversal)",
             all(s == 400 for _, s in ket_qua_sai),
             ", ".join("%r:%d" % (t, s) for t, s in ket_qua_sai))
        _ghi("Ten khong hop le -> KHONG ghi file ra ngoai known_faces",
             sau_kf == truoc_kf and sau_app == truoc_app and sau_ngoai == truoc_ngoai,
             "known_faces doi=%s, thu muc doi=%s, thu muc cha doi=%s"
             % (sau_kf != truoc_kf, sau_app != truoc_app, sau_ngoai != truoc_ngoai))

        # --- I.4 POST /api/nguoi-quen-tai-lai (reload_known that) ---
        truoc_da_hoc = _doc_canh_bao().count("[da hoc]")
        status, du_lieu = req_json("/api/nguoi-quen-tai-lai", method="POST", token=token)
        sau_da_hoc = _doc_canh_bao().count("[da hoc]")
        so_nguoi = (du_lieu or {}).get("so_nguoi")
        _in("  DOC LAI: %s" % json.dumps(du_lieu, ensure_ascii=False)[:300])
        _ghi("POST /api/nguoi-quen-tai-lai -> 200 + so nguoi",
             status == 200 and bool((du_lieu or {}).get("ok"))
             and isinstance(so_nguoi, int) and so_nguoi >= 2,
             "status=%d, so_nguoi=%s, thong_bao=%s"
             % (status, so_nguoi, (du_lieu or {}).get("thong_bao")))
        _ghi("reload_known that (model in lai danh sach nguoi)",
             sau_da_hoc > truoc_da_hoc,
             "so dong '[da hoc]' trong log server: %d -> %d" % (truoc_da_hoc, sau_da_hoc))

        # --- I.5 POST /api/vung (toado chuan hoa -> pixel that + file dung format) ---
        import cv2

        cap = cv2.VideoCapture(VIDEO_CO_NGUOI)
        rong = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        cao = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        status, du_lieu = req_json("/api/vung", method="POST", token=token,
                                   data={"x1": 0.1, "y1": 0.2, "x2": 0.6, "y2": 0.8,
                                         "video": VIDEO_CO_NGUOI})
        px = (du_lieu or {}).get("toa_do_px") or {}
        mong_doi_px = {"x1": int(0.1 * rong), "y1": int(0.2 * cao),
                       "x2": int(0.6 * rong), "y2": int(0.8 * cao)}
        _in("  LUU VUNG: %s" % json.dumps(du_lieu, ensure_ascii=False)[:400])
        _ghi("POST /api/vung -> 200 + toa do pixel dung video that",
             status == 200 and bool((du_lieu or {}).get("ok")) and px == mong_doi_px,
             "status=%d, video %dx%d, px=%s (mong doi %s)"
             % (status, rong, cao, px, mong_doi_px))
        noi_dung_vung = ""
        if os.path.isfile(file_vung):
            with open(file_vung, encoding="utf-8") as f:
                noi_dung_vung = f.read()
        _in("  NOI DUNG vung.txt (doc lai tu dia):")
        for dong in noi_dung_vung.splitlines():
            _in("    | " + dong)
        dong_du_lieu = [
            d for d in noi_dung_vung.splitlines()
            if d.strip() and not d.strip().startswith("#")
        ]
        _ghi("vung.txt dung format cam_ai_core.load_zone doc",
             len(dong_du_lieu) == 1 and len(dong_du_lieu[0].split()) == 4,
             "dong du lieu = %r" % (dong_du_lieu[0] if dong_du_lieu else None))

        # --- I.6 Phan tich THAT voi vung vua luu ---
        _bat_dau_lan()
        status, du_lieu = req_json("/api/phan-tich", method="POST", token=token,
                                   data={"input": VIDEO_CO_NGUOI, "vung": file_vung})
        ok_bat_dau = status == 200 and bool((du_lieu or {}).get("ok"))
        # Bat '[vung]' trong nhat ky (log cua cam_ai_core -> TT.ghi_log).
        dong_vung_log: list[str] = []
        het = time.time() + 40
        while time.time() < het:
            _, trang_thai = req_json("/api/trang-thai", token=token)
            for muc in (trang_thai or {}).get("nhat_ky") or []:
                noi_dung_muc = str(muc.get("noi_dung") or "")
                if "[vung]" in noi_dung_muc and noi_dung_muc.strip() not in dong_vung_log:
                    dong_vung_log.append(noi_dung_muc.strip())
            if dong_vung_log:
                break
            time.sleep(1)
        xong, trang_thai = _cho_xong(token, 420)
        _ghi("Phan tich that voi vung da luu -> chay duoc, khong loi",
             ok_bat_dau and xong and not trang_thai.get("loi"),
             "xong=%s, loi=%r" % (xong, trang_thai.get("loi")))
        _in("  NHAT KY (vung): %s" % (" | ".join(dong_vung_log[-2:]) or "KHONG CO"))
        _ghi("cam_ai_core doc vung.txt va ap dung vung that",
             bool(dong_vung_log),
             dong_vung_log[-1] if dong_vung_log else "khong co dong '[vung]' trong nhat ky")

        # --- I.7 Thu canh bao (CHI THU - khong gui ra ngoai) ---
        status, du_lieu = req_json("/api/thu-canh-bao", method="POST", token=token)
        noi_dung = (du_lieu or {}).get("noi_dung") or ""
        _in("  CANH BAO THU: %s" % json.dumps(du_lieu, ensure_ascii=False)[:400])
        _ghi("POST /api/thu-canh-bao -> 200 + co noi dung",
             status == 200 and bool((du_lieu or {}).get("ok")) and bool(noi_dung),
             "status=%d, noi_dung=%r" % (status, noi_dung[:100]))
        _ghi("Thu canh bao -> KHONG gui ra ngoai (che do chi thu)",
             (du_lieu or {}).get("mo_phong") is True
             and (du_lieu or {}).get("da_gui_thuc") is False,
             "mo_phong=%s, da_gui_thuc=%s"
             % ((du_lieu or {}).get("mo_phong"), (du_lieu or {}).get("da_gui_thuc")))
        _ghi("Khong co tin Telegram nao duoc gui trong log",
             "[gui OK] Telegram" not in _doc_canh_bao(),
             "khong co dong '[gui OK] Telegram'")

        # --- I.8 Thong tin model + thiet bi ---
        status, du_lieu = req_json("/api/thong-tin-model", token=token)
        models = (du_lieu or {}).get("models") or []
        _in("  MODEL: %s" % json.dumps(
            [{"ten": m.get("ten_hien_thi"), "mb": m.get("kich_thuoc_mb_thuc"),
              "gpu": m.get("co_gpu")} for m in models], ensure_ascii=False)[:400])
        _ghi("GET /api/thong-tin-model -> 200 + co du lieu model",
             status == 200 and bool((du_lieu or {}).get("ok")) and bool(models),
             "status=%d, so_model=%d" % (status, len(models)))
        status, du_lieu = req_json("/api/thong-tin-thiet-bi", token=token)
        gpu = (du_lieu or {}).get("gpu") or {}
        _in("  THIET BI: %s" % json.dumps(du_lieu, ensure_ascii=False)[:400])
        _ghi("GET /api/thong-tin-thiet-bi -> 200 + CPU/GPU/RAM",
             status == 200 and bool((du_lieu or {}).get("ok"))
             and bool((du_lieu or {}).get("ram")),
             "status=%d, cpu=%s, gpu=%s, ram=%s"
             % (status, (du_lieu or {}).get("so_lan_cpu"), gpu.get("ten_gpu"),
                (du_lieu or {}).get("ram")))

        # Don dep: xoa anh dang ky thu (khong de lam doi du lieu nguoi quen that).
        if file_anh_tao:
            duong_anh_tao = os.path.join(thu_muc_kf, "An", file_anh_tao)
            if os.path.isfile(duong_anh_tao):
                os.remove(duong_anh_tao)
                _in("  (da xoa anh thu: %s)" % file_anh_tao)
        _in("")

        # --- 11. URL LAN ---
        url_lan = _doc_url_lan()
        _in("")
        _in("  URL LAN (server in khi khoi dong): %s" % (url_lan or "KHONG DOC DUOC"))
        _ghi("Server in URL LAN", bool(url_lan), url_lan)

        noi_dung_log = _doc_canh_bao()
        _in("")
        _in("  CANH BAO SERVER IN RA:")
        for dong in noi_dung_log.splitlines():
            if ("WI-FI" in dong) or ("Internet" in dong) or ("giao_dien_web" in dong) \
                    or ("dien thoai" in dong.lower()):
                _in("    " + dong.strip())
        _ghi("Co canh bao 'cung Wi-Fi / khong Internet'", "KHONG mo ra Internet" in noi_dung_log,
             "trong log khoi dong")

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
                proc.wait(timeout=10)
        _ghi("Server tat sach (khong con process treo)", proc.poll() is not None,
             "exit code=%s" % proc.poll())

    _in("")
    _in("=" * 72)
    tong = len(KET_QUA)
    do = sum(1 for _, ok, _ in KET_QUA if ok)
    for ten, ok, ghi_chu in KET_QUA:
        _in("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", ten, ghi_chu))
    _in("-" * 72)
    _in("  KET QUA: %d/%d PASS" % (do, tong))
    _in("=" * 72)
    return 0 if do == tong else 1


if __name__ == "__main__":
    sys.exit(main())
