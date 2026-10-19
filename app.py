"""
CamAI - phan tich video: phat hien nguoi, dem nguoi ra/vào, nhan dien khuon mat, canh vung.

Chay:
    .venv\\Scripts\\python.exe app.py --input video.mp4
    .venv\\Scripts\\python.exe app.py --input 0            (webcam)
    .venv\\Scripts\\python.exe app.py --input a.mp4 --pixelate

Doc bien so Viet Nam (chay 100% tren may, khong gui anh ra ngoai):
    .venv\\Scripts\\python.exe app.py --input video.mp4 --doc-bien-so
    .venv\\Scripts\\python.exe app.py --input video.mp4 --doc-bien-so --vung-bien-so 0.1,0.3,0.9,0.8

Tu chup anh su kien:
    .venv\\Scripts\\python.exe app.py --input video.mp4 --tu-chup
    .venv\\Scripts\\python.exe app.py --input video.mp4 --tu-chup --tu-chup-dir anh_su_kien

Canh vung (khoanh 1 lan, dung lai cho moi video):
    .venv\\Scripts\\python.exe ve_vung.py --input video.mp4
    .venv\\Scripts\\python.exe app.py --input video.mp4 --vung vung.txt

Nhan dien "day la ai": bo anh vao known_faces/<Ten>/, hoac chay dang_ky_anh.py.
Ket qua ghi ra <ten>_ket_qua.mp4 va <ten>_bao_cao.csv.

Giao dien do hoa (de khong phai go lenh):
    chay_gui.bat   hoac   .venv\\Scripts\\python.exe gui.py

File nay chi lo phan giao dien dong lenh. Toan bo xu ly video nam trong
cam_ai_core.py (dung chung voi gui.py) - doi logic o do, khong doi o day.
"""

import argparse
import os
import re
import sys

from cam_ai_core import (AnalysisConfig, CamAIError, THIET_BI_CHON,
                         THIET_BI_MAC_DINH, VERSION, run_analysis)
from duong_dan import APP_DIR, chuan_hoa_duong_dan

__all__ = ["VERSION", "parse_args", "main"]


# -------------------------------------------------------------------------- CLI

def _chuan_hoa_console() -> None:
    """Console Windows mac dinh la cp1252 -> ep UTF-8 de in tieng Viet co dau
    (va de argparse bao loi ma khong vong ra UnicodeEncodeError)."""
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _parse_tin_cay(gia_tri: str) -> float:
    """--bien-so-tin-cay: so thuc trong khoang 0..1."""
    try:
        x = float(gia_tri)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            f"giá trị không hợp lệ: '{gia_tri}' (cần là số trong khoảng 0..1)"
        )
    if not 0.0 <= x <= 1.0:
        raise argparse.ArgumentTypeError(
            f"giá trị {x} nằm ngoài khoảng cho phép 0..1"
        )
    return x


def _parse_giay(gia_tri: str) -> float:
    """--tu-chup-nhoan-lai-giay: so thuc khong am."""
    try:
        x = float(gia_tri)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            f"giá trị không hợp lệ: '{gia_tri}' (cần là số không âm)"
        )
    if x < 0:
        raise argparse.ArgumentTypeError(
            f"giá trị {x} phải lớn hơn hoặc bằng 0"
        )
    return x


def _parse_vung_bien_so(gia_tri: str) -> str | None:
    """--vung-bien-so: 'x1,y1,x2,y2' (4 so, tach bang khoang trang/dau phay).
    De trong -> None (de loi tu tim vung bien so)."""
    goc = str(gia_tri or "").strip()
    if not goc:
        return None
    phan = [p for p in re.split(r"[\s,;]+", goc) if p]
    if len(phan) != 4:
        raise argparse.ArgumentTypeError(
            f"vùng biển số sai định dạng: '{goc}' "
            "(cần đúng 4 số theo dạng x1,y1,x2,y2)"
        )
    so = []
    for p in phan:
        try:
            so.append(float(p))
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(
                f"vùng biển số sai định dạng: '{goc}' "
                "(cần đúng 4 số theo dạng x1,y1,x2,y2)"
            )
    # Giu nguyen chuoi goc de log hien thi dung nhu nguoi dung go.
    # (cam_ai_core.py tu tach va parse lai 4 so nay.)
    return goc


class _LogCLI:
    """Boc ham log cua cam_ai_core cho phan CLI.

    Loi in dong '[bien so] DANG BAT: ...' / '[tu chup] DANG BAT: ...' khi bat
    tinh nang moi. Dong do duoc VIET LAI 1 LAN bang tieng Viet co dau, giu
    nguyen ten mang + noi dung (RapidOCR / 100% tren may / luu o thu muc nao /
    nhoan lai bao nhieu giay) de khop voi lenh 'CamAI ... | ... | ...'.
    """

    def __init__(self, cfg: AnalysisConfig):
        self.cfg = cfg

    def __call__(self, dong: str) -> None:
        if dong.startswith("[bien so] DANG BAT"):
            self._in(self._dong_bien_so(dong))
            return
        if dong.startswith("[tu chup] DANG BAT"):
            self._in(self._dong_tu_chup())
            return
        self._in(dong)

    @staticmethod
    def _in(dong: str) -> None:
        """In ra console. Console cp1252 khong in duoc -> lui ve ban khong dau
        (khong du con so la du, log khong bao gio lam chet luan phan tich)."""
        try:
            print(dong)
        except UnicodeEncodeError:
            try:
                print(dong.encode("ascii", "replace").decode("ascii"))
            except Exception:                                # noqa: BLE001
                pass
        except Exception:                                    # noqa: BLE001
            pass

    def _dong_bien_so(self, dong_loi: str) -> str:
        cfg = self.cfg
        thu_muc = cfg.bien_so_dir or "(không lưu)"
        co_lop = " | class plate có sẵn" if "class plate co san" in dong_loi else ""
        vung = f" | vùng ROI: {cfg.vung_bien_so}" if cfg.vung_bien_so else ""
        return (
            "[bien so] DANG BAT: đọc biển số Việt Nam bằng RapidOCR "
            "(100% trên máy, không gửi ảnh ra ngoài)"
            f"{co_lop}{vung}"
            f" | lưu crop vào: {thu_muc}"
            f" | cùng biển số chỉ lưu 1 lần/{cfg.bien_so_nhoan_lai_giay:.0f}s"
        )

    def _dong_tu_chup(self) -> str:
        cfg = self.cfg
        return (
            "[tu chup] DANG BAT: lưu ảnh sự kiện vào: "
            f"{cfg.tu_chup_dir or '(không lưu)'}"
            f" | mỗi loại sự kiện chụp 1 lần/{cfg.tu_chup_nhoan_lai_giay:.0f}s"
        )

def _kiem_tra_input(duong_dan: str) -> None:
    """Kiem tra file video co ton tai khong.

    Sai -> bao loi tieng Viet co dau roi thoat ma loi (khong bao gio vong
    traceback). '0' = webcam nen khong kiem tra.
    """
    goc = str(duong_dan or "").strip()
    if not goc or goc == "0":
        return
    if not os.path.isfile(goc):
        raise SystemExit(f"[lỗi] không tìm thấy file video: {goc}")


def _chuan_hoa_input(input_path: str) -> str:
    """Chuan hoa --input: '0' (webcam) giu nguyen.

    Duong dan tuong duong -> chuan hoa theo quy tac: ban trong CWD truoc,
    chua co thi dung ban trong thu muc goc du an (APP_DIR).
    """
    goc = str(input_path or "").strip()
    if not goc or goc == "0":
        return goc
    return chuan_hoa_duong_dan(goc)


def _chuan_hoa_output(output: str | None) -> str:
    """Chuan hoa --output (duong dan GHI RA video ket qua + CSV bao cao).

    - Khong truyen --output -> ghi vao thu muc goc du an (APP_DIR), de chay
      app tu thu muc khac van ghi dung choi.
    - Truyen duong dan TUYET DOI -> giu nguyen ven.
    - Truyen duong dan TUONG DOI -> giu theo CWD (y do nguoi dung). Thu muc
      cha se duoc cam_ai_core tu tao neu chua co (xem run_analysis).
    """
    if not output:
        return os.path.join(APP_DIR, "output.mp4")
    # Duong dan tuyet doi: giu nguyen ven. Duong dan tuong doi: giu theo CWD
    # (y do nguoi dung) - xem ghi chu o tren.
    return output


def parse_args():
    parser = argparse.ArgumentParser(description="CamAI - phan tich video")
    parser.add_argument("--input", required=True, help="duong dan video, hoac 0 = webcam")
    # default=None de phan biet "nguoi dung khong truyen --output" voi
    # "nguoi dung truyen duong dan tuong doi" (xem _chuan_hoa_output).
    parser.add_argument(
        "--output",
        default=None,
        help="video ket qua (mac dinh: ghi trong thu muc CamAI)",
    )
    parser.add_argument("--faces", default="known_faces", help="thu muc chua anh nguoi quen")
    parser.add_argument("--model", default="yolo11n.pt", help="model phat hien vat the")
    parser.add_argument(
        "--thiet-bi",
        choices=THIET_BI_CHON,
        default=THIET_BI_MAC_DINH,
        help="chon thiet bi chay model (mac dinh: auto)",
    )
    parser.add_argument(
        "--face-every",
        type=int,
        default=1,
        help="quet khuon mat moi bao nhieu khung hinh (1 = moi khung hinh)",
    )
    parser.add_argument("--no-face", action="store_true", help="tat nhan dien khuon mat")
    parser.add_argument(
        "--face-threshold",
        type=float,
        default=0.40,
        help="nguong rut ten, 0.28 = tha long, 0.50 = chat",
    )
    parser.add_argument(
        "--min-face",
        type=int,
        default=0,
        help="bo qua mat nho hon bao nhieu pixel (0 = khong bo qua)",
    )
    parser.add_argument(
        "--pixelate",
        action="store_true",
        help="lam mo toan bo khung hinh, chi giu nguyen vung co nguoi",
    )
    zone_group = parser.add_argument_group("canh vung")
    zone_group.add_argument(
        "--vung",
        help="file vung.txt tao boi ve_vung.py (khong co o mac dinh)",
    )
    zone_group.add_argument(
        "--vung-nhay",
        action="store_true",
        help="chi can 1 phan chan vao vung la bi bao (mac dinh: canh - nguoi ca nguoi trong vung)",
    )
    zone_group.add_argument(
        "--vung-max",
        type=int,
        default=0,
        help="canh bao khi so nguoi trong vung vuot qua so nay (0 = tat)",
    )
    zone_group.add_argument(
        "--canh-lau",
        type=float,
        default=0.0,
        help="canh bao khi co nguoi dung trong vung lau hon bao nhieu giay (0 = tat)",
    )

    clip_group = parser.add_argument_group("tu luu clip")
    clip_group.add_argument(
        "--tu-luu-clip",
        help="tu dong cat va luu clip khi co su kien vao thu muc nay (mac dinh: tat)",
    )
    clip_group.add_argument(
        "--clip-giay",
        type=float,
        default=10.0,
        help="tong thoi luong 1 clip, chia doi truoc/sau (mac dinh: 10.0)",
    )
    clip_group.add_argument(
        "--clip-ghi-tat-ca",
        action="store_true",
        help="ghi clip ca khi khong co --vung (dung so_nguoi > 0 lam dieu kien)",
    )

    vat_group = parser.add_argument_group("nhan vat the")
    vat_group.add_argument(
        "--nhan-vat-the",
        action="store_true",
        help="ve khung + nhan + dem cac lop vat the khac (mac dinh: tat)",
    )
    vat_group.add_argument(
        "--lop",
        default="",
        help="danh sach lop can nhan, cach nhau bang dau phay, vi du --lop car,motorcycle "
             "(mac dinh: nhom pho bien; 'all' = tat ca lop tru nguoi; "
             "truyen --lop se tu dong bat --nhan-vat-the)",
    )

    nhan_group = parser.add_argument_group("do nhan nguoi o xa")
    nhan_group.add_argument(
        "--tach-o",
        action="store_true",
        help="do TOAN KHUH + 2x2 o co chong de nhan tot hon nguoi o xa "
             "(mac dinh: tat). CHAM HON ~5.3 lan, live view rut fps. "
             "Chi bat khi phan tich video quay san o cu ly xa",
    )

    alert_group = parser.add_argument_group("canh bao ngoai (canh_bao.py)")
    alert_group.add_argument(
        "--bat-canh-bao",
        action="store_true",
        help="gui tin canh bao khi vuot nguong nguoi / co nguoi dung lau "
             "(mac dinh: tat)",
    )
    alert_group.add_argument(
        "--canh-bao-mo-phong",
        action="store_true",
        help="chi thu canh bao, KHONG gui tin ra ngoai",
    )
    alert_group.add_argument(
        "--canh-bao-gioi-han",
        type=int,
        default=5,
        help="toi da gui bao nhieu tin canh bao trong 1 phut (mac dinh: 5)",
    )
    alert_group.add_argument(
        "--canh-bao-go",
        type=float,
        default=60.0,
        help="gop tin canh bao cung loai trong bao nhieu giay (mac dinh: 60)",
    )

    bien_so_group = parser.add_argument_group("doc bien so (bien_so.py)")
    bien_so_group.add_argument(
        "--doc-bien-so",
        action="store_true",
        help="đọc biển số Việt Nam bằng RapidOCR, chạy 100%% trên máy này, "
             "không gửi ảnh ra ngoài (mặc định: tắt)",
    )
    bien_so_group.add_argument(
        "--bien-so-dir",
        default="anh_bien_so",
        help="thư mục lưu ảnh crop biển số (mặc định: anh_bien_so)",
    )
    bien_so_group.add_argument(
        "--bien-so-tin-cay",
        type=_parse_tin_cay,
        default=0.5,
        help="ngưỡng tin cậy OCR, phải trong khoảng 0..1 (mặc định: 0.5)",
    )
    bien_so_group.add_argument(
        "--bien-so-nhoan-lai-giay",
        type=_parse_giay,
        default=30.0,
        help="cùng một biển số chỉ lưu 1 lần trong N giây (mặc định: 30)",
    )
    bien_so_group.add_argument(
        "--vung-bien-so",
        type=_parse_vung_bien_so,
        default=None,
        help="vùng ROI đọc biển số theo dạng \"x1,y1,x2,y2\" "
             "(4 số ≤ 1 = tọa độ tương đối, > 1 = pixel; "
             "để trống = tự tìm theo class plate)",
    )

    tu_chup_group = parser.add_argument_group("tu chup anh (tu_chup.py)")
    tu_chup_group.add_argument(
        "--tu-chup",
        action="store_true",
        help="tự lưu ảnh khi có sự kiện, 100%% trên máy này, "
             "không gửi ảnh ra ngoài (mặc định: tắt)",
    )
    tu_chup_group.add_argument(
        "--tu-chup-dir",
        default="anh_su_kien",
        help="thư mục lưu ảnh sự kiện, chỉ dùng khi bật --tu-chup "
             "(mặc định: anh_su_kien)",
    )
    tu_chup_group.add_argument(
        "--tu-chup-nhoan-lai-giay",
        type=_parse_giay,
        default=10.0,
        help="mỗi loại sự kiện chỉ chụp 1 lần trong N giây (mặc định: 10)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --- duong dan: chuan hoa theo thu muc goc du an (xem duong_dan.py).
    # Quan trong: app.py chay tu thu muc khac (double-click tu Explorer,
    # shortcut, service/CI) thi duong dan tuong doi nhu "known_faces",
    # "models/..." hay "yolo11n.pt" deu phai tro ve thu muc goc du an.
    input_path = _chuan_hoa_input(args.input)
    _kiem_tra_input(input_path)

    faces_dir = chuan_hoa_duong_dan(args.faces)
    model = chuan_hoa_duong_dan(args.model)
    vung = chuan_hoa_duong_dan(args.vung)
    output = _chuan_hoa_output(args.output)

    cfg = AnalysisConfig(
        input=input_path,
        output=output,
        no_face=args.no_face,
        faces_dir=faces_dir,
        model=model,
        thiet_bi=args.thiet_bi,
        face_every=args.face_every,
        face_threshold=args.face_threshold,
        min_face=args.min_face,
        pixelate=args.pixelate,
        vung=vung,
        vung_nhay=args.vung_nhay,
        vung_max=args.vung_max,
        canh_lau=args.canh_lau,
        tu_luu_clip=args.tu_luu_clip or "",
        clip_giay=max(2.0, args.clip_giay),
        clip_ghi_tat_ca=args.clip_ghi_tat_ca,
        nhan_vat_the=args.nhan_vat_the,
        lop=args.lop,
        tach_o=args.tach_o,
        bat_canh_bao=args.bat_canh_bao,
        canh_bao_mo_phong=args.canh_bao_mo_phong,
        canh_bao_go=max(0.0, args.canh_bao_go),
        canh_bao_gioi_han=max(1, args.canh_bao_gioi_han),
        # --- nhom tinh nang moi (v3.0) ---
        doc_bien_so=args.doc_bien_so,
        bien_so_dir=args.bien_so_dir,
        bien_so_tin_cay=args.bien_so_tin_cay,
        bien_so_nhoan_lai_giay=args.bien_so_nhoan_lai_giay,
        vung_bien_so=args.vung_bien_so,
        # Chuoi rong = TAT (dung quy uoc cua cam_ai_core.py).
        tu_chup_dir=args.tu_chup_dir if args.tu_chup else "",
        tu_chup_nhoan_lai_giay=args.tu_chup_nhoan_lai_giay,
    )

    try:
        run_analysis(cfg, log=_LogCLI(cfg))
    except CamAIError as exc:
        # Giu nguyen hanh vi cu: loi ra stderr roi dung chay.
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()