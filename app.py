"""
CamAI - phan tich video: phat hien nguoi, dem nguoi ra/vào, nhan dien khuon mat, canh vung.

Chay:
    .venv\\Scripts\\python.exe app.py --input video.mp4
    .venv\\Scripts\\python.exe app.py --input 0            (webcam)
    .venv\\Scripts\\python.exe app.py --input a.mp4 --pixelate

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

from cam_ai_core import (AnalysisConfig, CamAIError, THIET_BI_CHON,
                         THIET_BI_MAC_DINH, VERSION, run_analysis)

__all__ = ["VERSION", "parse_args", "main"]


# -------------------------------------------------------------------------- CLI

def parse_args():
    parser = argparse.ArgumentParser(description="CamAI - phan tich video")
    parser.add_argument("--input", required=True, help="duong dan video, hoac 0 = webcam")
    parser.add_argument("--output", default="output.mp4", help="video ket qua")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cfg = AnalysisConfig(
        input=args.input,
        output=args.output,
        no_face=args.no_face,
        faces_dir=args.faces,
        model=args.model,
        thiet_bi=args.thiet_bi,
        face_every=args.face_every,
        face_threshold=args.face_threshold,
        min_face=args.min_face,
        pixelate=args.pixelate,
        vung=args.vung,
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
    )

    try:
        run_analysis(cfg, log=print)
    except CamAIError as exc:
        # Giu nguyen hanh vi cu: loi ra stderr roi dung chay.
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()