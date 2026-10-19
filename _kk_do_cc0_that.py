# -*- coding: utf-8 -*-
"""Do that tren video CC0 thuc te - nguoi qua vach/duong gan camera.
Chay qua chinh run_analysis() cua cam_ai_core, khong vong lap rut gon.
Bo 50 khung dau (video co fade-in + model warmup).
"""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cam_ai_core import AnalysisConfig, run_analysis

GOC = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(GOC, "video_mau", "moi")
OUT_DIR = os.path.join(GOC, "_kk_out", "cc0")

BO_KHUNG_DAU = 50      # bo fade-in + warmup
MAX_KHUNG = 250

VIDEO = [
    ("di-bo-he-pho.mp4", "Nguoi di bo hep pho - sat camera"),
    ("di-bo-duong-pedestrian.mp4", "Nguoi di bo pho - nhieu nguoi"),
    ("nguoi-qua-duong-vach-bo.mp4", "Nguoi qua vach bo - doan xa"),
]

CASE = [
    ("chi dem nguoi", dict(no_face=True)),
    ("dem nguoi + mat moi 5 khung", dict(no_face=False, face_every=5)),
    ("dem nguoi + mat moi khung", dict(no_face=False, face_every=1)),
]


def do_mot(ten_file, nhan, **kw):
    os.makedirs(OUT_DIR, exist_ok=True)
    duong_dan = os.path.join(VIDEO_DIR, ten_file)
    goc = os.path.splitext(ten_file)[0]
    cfg = AnalysisConfig(
        input=duong_dan,
        output=os.path.join(OUT_DIR, f"{goc}_{len(kw)}_{abs(hash(nhan)) % 9999}.mp4"),
        **kw,
    )
    dem_nguoi, dem_mat = [], []
    trong = [0.0]
    bat_dau = [0.0]

    def cb(p):
        if p.frame_index == BO_KHUNG_DAU:
            bat_dau[0] = time.perf_counter()
        if p.frame_index <= BO_KHUNG_DAU:
            return True
        dem_nguoi.append(p.so_nguoi)
        dem_mat.append(p.so_mat)
        if p.frame_index - BO_KHUNG_DAU >= MAX_KHUNG:
            return False
        return True

    chay = time.perf_counter()
    run_analysis(cfg, progress_cb=cb, log=lambda d: None)
    tong = time.perf_counter() - chay
    trong[0] = time.perf_counter() - bat_dau[0] if bat_dau[0] else tong
    so_khung = len(dem_nguoi)
    fps = so_khung / trong[0] if trong[0] > 0 else 0.0
    tn = sum(dem_nguoi) / so_khung if so_khung else 0.0
    tm = sum(dem_mat) / so_khung if so_khung else 0.0
    lon_nhat = max(dem_nguoi) if dem_nguoi else 0
    return fps, tn, tm, lon_nhat, so_khung


def main():
    dong = []
    dong.append("=" * 86)
    dong.append("DO THAT TREN VIDEO CC0 THUC TE")
    dong.append(f"Bo {BO_KHUNG_DAU} khung dau, do toi da {MAX_KHUNG} khung, chay qua run_analysis()")
    dong.append("=" * 86)
    for ten, nhan in VIDEO:
        duong_dan = os.path.join(VIDEO_DIR, ten)
        if not os.path.exists(duong_dan):
            dong.append(f"[THIEU FILE] {ten}")
            continue
        dong.append("")
        dong.append(f"--- {nhan}")
        dong.append(f"    file: {ten}")
        for nhan_case, kw in CASE:
            fps, tn, tm, lon_nhat, n = do_mot(ten, nhan_case, **kw)
            dong.append(
                f"    {nhan_case:28s} {fps:6.2f} fps | nguoi TB {tn:5.2f} max {lon_nhat:2d}"
                f" | mat TB {tm:5.2f} | {n} khung"
            )
            sys.stdout.write(dong[-1] + "\n")
            sys.stdout.flush()

    van = "\n".join(dong) + "\n"
    thu_muc = os.path.join(GOC, "_kiem_chung")
    os.makedirs(thu_muc, exist_ok=True)
    duong_out = os.path.join(thu_muc, "do_cc0_nguoi_that.txt")
    with open(duong_out, "w", encoding="utf-8") as f:
        f.write(van)
    print("\nDa luu: " + duong_out)


if __name__ == "__main__":
    main()