# -*- coding: utf-8 -*-
"""
Kiem chung app_qt.py (vo desktop PySide6 + QWebEngineView).

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_app_qt.py

Kiem 6 muc:
    1. KHONG co CAMAI_PASSWORD -> app VAN MO DUOC (tu sinh mat khau), mat khau do
       in ra console (chi tiet tung ky tu) va DANG NHAP DUOC (POST /api/dang-nhap).
    2. CO CAMAI_PASSWORD -> app dung DUNG mat khau do, dang nhap duoc.
    3. TU DANG NHAP tren desktop: webview doc localStorage['camai_token'] /
       localStorage['token'] bang runJavaScript -> phai co token, va
       GET /api/trang-thai voi token do -> HTTP 200.
    4. Hop thoai "Mo tren dien thoai" hien du: URL + mat khau + 2 nut "Sao chep"
       -> chup anh _kk_out/app_qt/app_qt_dien_thoai.png.
    5. Dong cua so => khong con process app_qt.py nao song.
    6. Mat khau KHONG bi ghi ra file: quet thu muc du an, in ra ket qua.

Chup anh dung mau bat buoc cua du an (xem _kk_chup_cua_so.py):
    SetWindowPos TOPMOST -> ShowWindow(SW_RESTORE) / SetForegroundWindow
    -> GetAncestor(hwnd, 2) -> GetWindowRect -> ImageGrab.grab(bbox, all_screens=True)
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_QT = os.path.join(APP_DIR, "app_qt.py")
OUT_DIR = os.path.join(APP_DIR, "_kk_out", "app_qt")
OUT_ANH = os.path.join(OUT_DIR, "app_qt_full.png")
OUT_ANH_DT = os.path.join(OUT_DIR, "app_qt_dien_thoai.png")
TIEU_DE_CUA_SO = "CamAI — Phân tích video giám sát"
TIEU_DE_HOP = "Mở trên điện thoại"
THOI_GIAN_CHO_CUA_SO = 90
THOI_GIAN_CHO_TRANG = 40
THOI_GIAN_CHO_DANG_NHAP = 40
THOI_GIAN_DONG = 6.0

# Cac thu muc bo qua khi quet file (khong phai output cua du an).
BO_QUET = {
    ".venv",
    "__pycache__",
    ".git",
    "node_modules",
    ".venv.bak",
}

ket_qua = []


def _bao(ok: bool, ten: str, chi_tiet: str = "") -> bool:
    ket_qua.append((ok, ten, chi_tiet))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", ten, (" - " + chi_tiet) if chi_tiet else ""))
    return ok


def _chay_app(mat_khau=None, them_env=None):
    """Chay app_qt.py, doc stdout theo thread. Tra (proc, dong).

    mat_khau=None  -> KHONG dat CAMAI_PASSWORD (app phai tu sinh).
    mat_khau=str   -> dat CAMAI_PASSWORD (app phai dung dung mat khau do).
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("CAMAI_PASSWORD", None)
    if mat_khau is not None:
        env["CAMAI_PASSWORD"] = mat_khau
    for khoa, gia_tri in (them_env or {}).items():
        env[khoa] = gia_tri
    proc = subprocess.Popen(
        [sys.executable, "-W", "ignore", APP_QT],
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    dong = []

    def doc():
        for dong_moi in proc.stdout:
            dong.append(dong_moi.rstrip())
            print("   [app] " + dong_moi.rstrip(), flush=True)

    threading.Thread(target=doc, daemon=True).start()
    return proc, dong


def _dong_co(chu: str, dong: list) -> str:
    """Tra ve dong dau tien chua `chu` (hoac chuoi rong)."""
    for d in dong:
        if chu in d:
            return d
    return ""


def _tim_cua_so(ten_chua: str):
    """Tim cua so theo tieu de (dung win32gui nhu mau cua du an)."""
    import win32gui

    ket = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        tieu_de = win32gui.GetWindowText(hwnd)
        if ten_chua.lower() in tieu_de.lower():
            ket.append((hwnd, tieu_de))

    win32gui.EnumWindows(callback, None)
    return ket


def _ep_truoc(hwnd) -> None:
    """Ép cửa sổ lên trước (AttachThreadInput để SetForegroundWindow có tác dụng)."""
    import ctypes
    import win32gui
    import win32process

    try:
        fg = win32gui.GetForegroundWindow()
        luong_fg = win32process.GetWindowThreadProcessId(fg)[0]
        luong_dst = win32process.GetWindowThreadProcessId(hwnd)[0]
        if luong_fg != luong_dst:
            ctypes.windll.user32.AttachThreadInput(luong_fg, luong_dst, True)
        win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
        if luong_fg != luong_dst:
            ctypes.windll.user32.AttachThreadInput(luong_fg, luong_dst, False)
    except Exception as loi:  # noqa: BLE001
        print("   focus loi (bo qua):", loi)


def _mo_hop_thoai(hwnd):
    """Mo hop thoai 'Mo tren dien thoai' bang phim F2 (phim tat app).

    Tra (hwnd hop thoai, tieu de) hoac (None, loi).
    """
    import win32api
    import win32con
    import win32gui

    _ep_truoc(hwnd)
    time.sleep(0.6)
    win32api.keybd_event(win32con.VK_F2, 0, 0, 0)
    win32api.keybd_event(win32con.VK_F2, 0, win32con.KEYEVENTF_KEYUP, 0)

    het = time.time() + 8
    while time.time() < het:
        for h, t in _tim_cua_so(TIEU_DE_HOP):
            return h, t
        time.sleep(0.3)

    # Cách 2: gui WM_KEYDOWN truc tiep vao cua so.
    try:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_F2, 0)
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_F2, 0)
    except Exception as loi:  # noqa: BLE001
        print("   post F2 loi:", loi)
    het = time.time() + 8
    while time.time() < het:
        for h, t in _tim_cua_so(TIEU_DE_HOP):
            return h, t
        time.sleep(0.3)
    return None, "khong thay hop thoai"


def _chup_an(hwnd, duong_dan: str):
    """Chup theo mau bat buoc cua du an."""
    import win32con
    import win32gui
    from PIL import ImageGrab

    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
    except Exception as loi:  # noqa: BLE001
        print("   topmost loi (bo qua):", loi)

    try:
        win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
    except Exception as loi:  # noqa: BLE001
        print("   focus loi (bo qua):", loi)

    time.sleep(1.2)

    goc = win32gui.GetAncestor(hwnd, 2)  # GA_ROOT
    left, top, right, bottom = win32gui.GetWindowRect(goc)
    print("   GetWindowRect =", (left, top, right, bottom))
    anh = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    anh.save(duong_dan)
    return anh


def _phan_tich_anh(anh):
    """Kiem tra vung webview co that su nap (khong phai trang xam/trang).

    Tra (so_mau, ty_le_trang) trong vung webview (bo thanh trang thai 30px).
    """
    from PIL import Image

    rong, cao = anh.size
    vung = anh.crop((0, 0, rong, max(1, cao - 30))).convert("RGB")
    mau = vung.getcolors(maxcolors=1_000_000)
    so_mau = len(mau) if mau else 1_000_001
    tong = max(1, vung.size[0] * vung.size[1])
    trang = 0
    if mau:
        for so, (r, g, b) in mau:
            if r > 235 and g > 235 and b > 235:
                trang += so
    return so_mau, trang / tong


def _process_con_song(pid_app: int) -> list:
    """Danh sach process app_qt.py con song (khong dung process vua chay).

    Khop DUNG duong dan app_qt.py, khong dung chuoi con: "_kk_kiem_app_qt.py"
    cung chua "app_qt.py" nen se bao sai.
    """
    ket = []
    try:
        import psutil
    except ImportError:
        return ket
    me = os.getpid()
    duong_dan = os.path.normcase(os.path.abspath(APP_QT))
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            if p.info["pid"] in (me, pid_app):
                continue
            for arg in p.info["cmdline"] or []:
                if os.path.normcase(os.path.abspath(arg)) == duong_dan:
                    ket.append((p.info["pid"], " ".join(p.info["cmdline"])[:160]))
                    break
        except Exception:  # noqa: BLE001
            continue
    return ket


def _post_dang_nhap(cong: int, mat_khau: str):
    """POST /api/dang-nhap. Tra (ok, token, loi)."""
    du_lieu = json.dumps({"mat_khauu": mat_khau}).encode("utf-8")
    yeu_cau = urllib.request.Request(
        "http://127.0.0.1:%d/api/dang-nhap" % cong,
        data=du_lieu,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with mo.open(yeu_cau, timeout=10) as resp:
            ket = json.loads(resp.read().decode("utf-8"))
    except Exception as loi:  # noqa: BLE001
        return False, "", str(loi)
    if ket.get("ok"):
        return True, str(ket.get("token") or ""), ""
    return False, "", str(ket.get("loi") or "")


def _get_trang_thai(cong: int, token: str):
    """GET /api/trang-thai voi token. Tra (ma_http, ok)."""
    yeu_cau = urllib.request.Request(
        "http://127.0.0.1:%d/api/trang-thai" % cong,
        headers={"X-Camai-Token": token},
    )
    mo = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with mo.open(yeu_cau, timeout=10) as resp:
            return resp.status, resp.status == 200
    except urllib.error.HTTPError as loi:
        return loi.code, False
    except Exception:  # noqa: BLE001
        return 0, False


def _lay_cong(dong: list):
    """Tim port cua server tu dong output app."""
    for d in dong:
        tim = re.search(r"http://127\.0\.0\.1:(\d+)", d)
        if tim:
            return int(tim.group(1))
    return None


def _quet_file_mat_khau(mat_khau: str):
    """Quet thu muc du an xem co file nao chua mat khau sinh ra hay khong.

    Tra (danh_sach_file_bi_lo, so_file_da_quet).
    """
    if not mat_khau:
        return [], 0
    mau = mat_khau.encode("utf-8")
    bi_lo = []
    da_quet = 0
    for thu_muc, _, ten_tin in os.walk(APP_DIR):
        if os.path.basename(thu_muc) in BO_QUET:
            continue
        for ten in ten_tin:
            duong_dan = os.path.join(thu_muc, ten)
            if os.path.abspath(duong_dan) == os.path.abspath(__file__):
                continue
            try:
                if os.path.getsize(duong_dan) > 20 * 1024 * 1024:
                    continue
                with open(duong_dan, "rb") as f:
                    noi_dung = f.read()
            except Exception:  # noqa: BLE001
                continue
            da_quet += 1
            if mau in noi_dung:
                bi_lo.append(duong_dan)
    return bi_lo, da_quet


def _doc_clipboard() -> str:
    """Doc noi dung clipboard (chuoi rong neu loi)."""
    import win32clipboard
    import win32con

    try:
        win32clipboard.OpenClipboard()
        try:
            return str(win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT))
        finally:
            win32clipboard.CloseClipboard()
    except Exception:  # noqa: BLE001
        return ""


def _xoa_clipboard() -> None:
    import win32clipboard

    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
        finally:
            win32clipboard.CloseClipboard()
    except Exception:  # noqa: BLE001
        pass


def _bam_sao_chep(hwnd_hop) -> list:
    """Di chuyen focus bang Tab va bam Space, thu 3 lan.

    Thu tu Tab trong app: o_url -> btn_sao_chep -> o_mk -> btn_sao_chep_mk -> thoat.
    Focus bat dau o o_url, nen 3 vong Tab+Space cham dung 2 nut "Sao chep"
    (khong bao gio cham nut "Dong" => hop thoai khong bi dong).

    Tra danh sach noi dung clipboard sau moi vong.
    """
    import win32api
    import win32con
    import win32gui

    try:
        win32gui.SetForegroundWindow(hwnd_hop)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.6)
    _xoa_clipboard()

    ket = []
    for _ in range(3):
        win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)
        win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.25)
        win32api.keybd_event(win32con.VK_SPACE, 0, 0, 0)
        win32api.keybd_event(win32con.VK_SPACE, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.6)
        ket.append(_doc_clipboard())
    return ket


def _cho_den_khi(dong: list, chu: str, tong: float) -> bool:
    """Cho toi khi xuat hien dong chua `chu` trong output app."""
    het = time.time() + tong
    while time.time() < het:
        if any(chu in d for d in dong):
            return True
        time.sleep(0.4)
    return False


def _dong_cua_so(proc, dong: list, tong: float = THOI_GIAN_CHO_CUA_SO):
    """Cho cua so chinh cua app xuat hien. Tra (hwnd, tieu_de) hoac (None, loi)."""
    het = time.time() + tong
    while time.time() < het:
        cua_so = _tim_cua_so(TIEU_DE_CUA_SO)
        if cua_so:
            return cua_so[0][0], cua_so[0][1]
        if proc.poll() is not None:
            return None, "app thoat som (ma=%s)" % proc.poll()
        time.sleep(0.5)
    return None, "khong tim thay cua so '%s'" % TIEU_DE_CUA_SO


def _main_kiem_1_mat_khau_tu_sinh():
    """Kiem 1 + 3 + 4 + 5 + 6: app tu sinh mat khau, tu dang nhap, hop thoai, dong app."""
    print("\n" + "=" * 70)
    print("PHAN 1: KHONG co CAMAI_PASSWORD -> app phai tu sinh mat khau va van mo duoc")
    print("=" * 70)

    proc, dong = _chay_app(
        mat_khau=None,
        them_env={
            "CAMAI_QT_IN_TOKEN": "1",
            "CAMAI_QT_IN_DIALOG": "1",
            "CAMAI_QT_TU_KIEM": "Sẵn sàng",
        },
    )

    hwnd, tieu_de = _dong_cua_so(proc, dong)
    if hwnd is None:
        _bao(False, "1a. App mo duoc khi KHONG co CAMAI_PASSWORD", tieu_de)
        _dung_app(proc)
        return None
    _bao(True, "1a. App mo duoc khi KHONG co CAMAI_PASSWORD", "hwnd=%s tieu de=%r" % (hwnd, tieu_de))
    _bao(
        tieu_de == TIEU_DE_CUA_SO,
        "1b. Tieu de cua so dung chuan",
        repr(tieu_de),
    )

    # --- app co dung hien hop thoai "Chưa đặt mật khẩu" khong? ---
    hop_loi = _tim_cua_so("Chưa đặt mật khẩu")
    _bao(
        not hop_loi,
        "1c. Khong dung hien hop thoai loi 'Chưa đặt mật khẩu'",
        "khong thay" if not hop_loi else repr(hop_loi),
    )

    # --- mat khau da duoc sinh + in ra console ---
    dong_mk = _dong_co("MAT-KHAU-TU-SINH:", dong)
    mat_khau = dong_mk.split("MAT-KHAU-TU-SINH:")[-1].strip() if dong_mk else ""
    _bao(
        bool(mat_khau),
        "1d. App tu sinh mat khau va in ra console",
        dong_mk or "khong thay dong MAT-KHAU-TU-SINH",
    )
    if mat_khau:
        print("   MAT KHAU (chi tiet tung ky tu): %s" % " ".join(list(mat_khau)))
        print("   Do dai: %d ky tu" % len(mat_khau))
        co_canh_bao = any(
            "doi moi LAN KHOI DONG" in d or "MAT-KHAU-TU-SINH" in d for d in dong
        )
        _bao(
            co_canh_bao,
            "1e. Canh bao 'doi moi lan khoi dong' co trong console",
            "co" if co_canh_bao else "khong thay",
        )

    # --- cho trang web nap + tu dang nhap ---
    _cho_den_khi(dong, "TAI-TRANG:", THOI_GIAN_CHO_TRANG)
    # Tu dang nhap chay SAU khi trang nap -> phai CHO TIEP cho marker,
    # neu kiem ngay se bao FAIL gia (nhu da gap o phan 1).
    _cho_den_khi(dong, "TU-DANG-NHAP: OK", THOI_GIAN_CHO_DANG_NHAP)
    dong_dn = _dong_co("TU-DANG-NHAP: OK", dong)
    _bao(
        bool(dong_dn),
        "3a. Tu dang nhap tren desktop thanh cong",
        dong_dn or "khong thay dong TU-DANG-NHAP: OK",
    )

    # --- token doc tu localStorage bang runJavaScript ---
    dong_token = _dong_co("TOKEN-LOCALSTORAGE:", dong)
    token = dong_token.split("TOKEN-LOCALSTORAGE:")[-1].strip() if dong_token else ""
    _bao(
        bool(token),
        "3b. Webview doc duoc token trong localStorage (runJavaScript)",
        "token %d ky tu" % len(token) if token else "khong thay dong TOKEN-LOCALSTORAGE",
    )

    # --- GET /api/trang-thai voi token do -> 200 ---
    cong = _lay_cong(dong)
    if cong and token:
        ma, ok = _get_trang_thai(cong, token)
        _bao(
            ok and ma == 200,
            "3c. GET /api/trang-thai voi token localStorage -> HTTP 200",
            "cong=%d ma=%d" % (cong, ma),
        )
        # --- mat khau do dang nhap duoc ---
        ok_dn, tok_dn, loi = _post_dang_nhap(cong, mat_khau)
        _bao(
            ok_dn,
            "1f. Mat khau sinh ra dang nhap duoc (POST /api/dang-nhap ok=True)",
            "token %d ky tu" % len(tok_dn) if ok_dn else "loi: %s" % loi,
        )
    else:
        _bao(False, "3c. GET /api/trang-thai voi token localStorage -> HTTP 200",
             "khong tim thay cong/token")

    # --- hop thoai dien thoai: URL + mat khau + 2 nut Sao chep ---
    url_lan = ""
    for d in dong:
        if "URL-LAN:" in d:
            url_lan = d.split("URL-LAN:")[-1].strip()

    h_hop, t_hop = _mo_hop_thoai(hwnd)
    if h_hop is None:
        _bao(False, "4a. Hop thoai 'Mo tren dien thoai' mo duoc", t_hop)
    else:
        _bao(True, "4a. Hop thoai 'Mo tren dien thoai' mo duoc", repr(t_hop))

        # --- noi dung hop thoai (doc qua hook console cua app) ---
        _kiem_noi_dung_hop_thoai(dong, url_lan, mat_khau)

        # --- 2 nut "Sao chep" dua dung noi dung vao clipboard ---
        noi_dungs = _bam_sao_chep(h_hop)
        print("   Clipboard sau moi vong Tab+Space: %r" % (noi_dungs,))
        co_url = any(url_lan and url_lan in n for n in noi_dungs)
        _bao(
            co_url,
            "4b. Nut 'Sao chep' dua dung URL LAN vao clipboard",
            "tim thay URL trong clipboard" if co_url else "khong thay URL: %r" % (noi_dungs,),
        )
        co_mk = any(mat_khau and mat_khau in n for n in noi_dungs)
        _bao(
            co_mk,
            "4c. Nut 'Sao chep mat khau' dua dung mat khau vao clipboard",
            "tim thay mat khau trong clipboard" if co_mk else "khong thay mat khau: %r" % (noi_dungs,),
        )

        try:
            anh_hop = _chup_an(h_hop, OUT_ANH_DT)
            _bao(
                os.path.isfile(OUT_ANH_DT),
                "4d. Anh hop thoai da luu",
                "kich thuoc=%s" % (anh_hop.size,),
            )
        except Exception as loi:  # noqa: BLE001
            _bao(False, "4d. Anh hop thoai da luu", "loi chup: %s" % loi)

        import win32con
        import win32gui

        try:
            win32gui.PostMessage(h_hop, win32con.WM_CLOSE, 0, 0)
            time.sleep(0.8)
        except Exception as loi:  # noqa: BLE001
            print("   loi dong hop thoai:", loi)

    # --- chup man hinh chinh + kiem webview nap that ---
    try:
        anh = _chup_an(hwnd, OUT_ANH)
        so_mau, ty_le_trang = _phan_tich_anh(anh)
        _bao(
            so_mau > 20 and ty_le_trang < 0.90,
            "4e. WebView nap that (khong trang xam)",
            "so mau=%d ty le trang=%.3f kich thuoc=%s" % (so_mau, ty_le_trang, anh.size),
        )
        _bao(os.path.isfile(OUT_ANH), "4f. Anh cua so chinh da luu", OUT_ANH)
    except Exception as loi:  # noqa: BLE001
        _bao(False, "4e. WebView nap that", "loi chup: %s" % loi)

    # --- 5) Dong cua so => khong con process treo ---
    import win32con
    import win32gui

    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception as loi:  # noqa: BLE001
        print("   loi dong cua so:", loi)

    time.sleep(THOI_GIAN_DONG)
    con_song = _process_con_song(proc.pid)
    _bao(
        not con_song,
        "5a. Dong cua so => khong con process app_qt.py",
        "con song: %s" % (con_song if con_song else "khong co"),
    )
    _bao(
        proc.poll() is not None,
        "5b. Tien trinh app_qt.py da thoat",
        "ma thoat=%s" % proc.poll(),
    )
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass

    # --- 6) Mat khau KHONG bi ghi ra file ---
    bi_lo, da_quet = _quet_file_mat_khau(mat_khau)
    print("   Da quet %d file trong thu muc du an." % da_quet)
    if bi_lo:
        for duong_dan in bi_lo:
            print("   FOUND mat khau trong: %s" % duong_dan)
    _bao(
        not bi_lo,
        "6. Mat khau KHONG bi ghi ra file trong thu muc du an",
        "khong file nao chua mat khau" if not bi_lo else "%d file chua" % len(bi_lo),
    )

    return mat_khau


def _kiem_noi_dung_hop_thoai(dong: list, url_lan: str, mat_khau: str):
    """Kiem noi dung hop thoai qua hook console cua app (HOP-THOAI-*).

    Qt khong tao HWND con cho widget => khong doc duoc bang EnumChildWindows.
    """
    dong_url = _dong_co("HOP-THOAI-URL:", dong)
    dong_mk = _dong_co("HOP-THOAI-MK:", dong)
    dong_nut = _dong_co("HOP-THOAI-NUT:", dong)

    url_hop = dong_url.split("HOP-THOAI-URL:")[-1].strip() if dong_url else ""
    mk_hop = dong_mk.split("HOP-THOAI-MK:")[-1].strip() if dong_mk else ""
    nut_hop = dong_nut.split("HOP-THOAI-NUT:")[-1].strip() if dong_nut else ""

    _bao(
        bool(url_hop) and (not url_lan or url_hop == url_lan),
        "4g. Hop thoai hien dung URL LAN",
        url_hop or "khong thay HOP-THOAI-URL",
    )
    _bao(
        bool(mk_hop) and (not mat_khau or mk_hop == mat_khau),
        "4h. Hop thoai hien dung mat khau",
        ("mat khau %d ky tu khop" % len(mk_hop)) if mk_hop else "khong thay HOP-THOAI-MK",
    )
    so_nut = len([t for t in nut_hop.split("|") if t.strip()])
    _bao(
        so_nut == 2,
        "4i. Hop thoai co 2 nut 'Sao chep'",
        nut_hop or "khong thay HOP-THOAI-NUT",
    )


def _dung_app(proc):
    """Dung app phat sinh (dung khi co loi)."""
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


def _main_kiem_2_mat_khau_co_san():
    """Kiem 2: co CAMAI_PASSWORD -> app dung dung mat khau do."""
    print("\n" + "=" * 70)
    print("PHAN 2: CO CAMAI_PASSWORD -> app phai dung dung mat khau do")
    print("=" * 70)

    mat_khau = secrets.token_urlsafe(12)
    print("   CAMAI_PASSWORD trong moi truong: %s" % mat_khau)

    proc, dong = _chay_app(mat_khau=mat_khau, them_env={"CAMAI_QT_IN_TOKEN": "1"})

    hwnd, tieu_de = _dong_cua_so(proc, dong)
    if hwnd is None:
        _bao(False, "2a. App mo duoc khi co CAMAI_PASSWORD", tieu_de)
        _dung_app(proc)
        return
    _bao(True, "2a. App mo duoc khi co CAMAI_PASSWORD", "hwnd=%s" % hwnd)

    # App KHONG duoc tu sinh mat khau (vi da co san trong moi truong).
    khong_tu_sinh = not any("MAT-KHAU-TU-SINH:" in d for d in dong)
    _bao(
        khong_tu_sinh,
        "2b. App KHONG tu sinh mat khau khi bien moi truong da co",
        "khong co dong MAT-KHAU-TU-SINH" if khong_tu_sinh else "CO dong tu sinh",
    )

    _cho_den_khi(dong, "TU-DANG-NHAP: OK", THOI_GIAN_CHO_DANG_NHAP)
    dong_dn = _dong_co("TU-DANG-NHAP: OK", dong)
    _bao(
        bool(dong_dn),
        "2c. Tu dang nhap desktop van chay voi mat khau co san",
        dong_dn or "khong thay dong TU-DANG-NHAP: OK",
    )

    cong = _lay_cong(dong)
    if cong:
        ok_dn, tok_dn, loi = _post_dang_nhap(cong, mat_khau)
        _bao(
            ok_dn,
            "2d. Mat khau trong bien moi truong dang nhap duoc (ok=True)",
            "token %d ky tu" % len(tok_dn) if ok_dn else "loi: %s" % loi,
        )
        # Mat khau sai phai bi tu choi.
        ok_sai, _, _ = _post_dang_nhap(cong, mat_khau + "x")
        _bao(
            not ok_sai,
            "2e. Mat khau sai bi tu choi",
            "bi tu choi" if not ok_sai else "LOI: mat khau sai van vao duoc",
        )
    else:
        _bao(False, "2d. Mat khau trong bien moi truong dang nhap duoc", "khong tim thay cong")

    dong_token = _dong_co("TOKEN-LOCALSTORAGE:", dong)
    token = dong_token.split("TOKEN-LOCALSTORAGE:")[-1].strip() if dong_token else ""
    _bao(
        bool(token),
        "2f. Token trong localStorage co san",
        "token %d ky tu" % len(token) if token else "khong thay",
    )

    import win32con
    import win32gui

    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(THOI_GIAN_DONG)
    con_song = _process_con_song(proc.pid)
    _bao(
        not con_song,
        "2g. Dong cua so => khong con process app_qt.py",
        "con song: %s" % (con_song if con_song else "khong co"),
    )
    if proc.poll() is None:
        _dung_app(proc)


def main() -> int:
    if not os.path.isfile(APP_QT):
        print("KHONG tim thay app_qt.py")
        return 1

    print("=" * 70)
    print("KIEM CHUNG app_qt.py")
    print("=" * 70)

    _main_kiem_1_mat_khau_tu_sinh()
    _main_kiem_2_mat_khau_co_san()

    return _tong_ket()


def _tong_ket() -> int:
    print("\n" + "=" * 70)
    tong = len(ket_qua)
    dat = sum(1 for ok, _, _ in ket_qua if ok)
    for ok, ten, chi_tiet in ket_qua:
        print("  %-4s %s %s" % ("PASS" if ok else "FAIL", ten, ("- " + chi_tiet) if chi_tiet else ""))
    print("KET QUA: %d/%d PASS" % (dat, tong))
    print("=" * 70)
    return 0 if dat == tong else 1


if __name__ == "__main__":
    sys.exit(main())
