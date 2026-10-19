# -*- coding: utf-8 -*-
"""Do DO CHINH XAC that cua tung model YOLO11 tren video mau cua CamAI.

Bam sat cach lam cua _kk_kiem_do_nhan_diem.py (12 khung mau rai deu moi video,
conf=0.25, PERSON_CLASS_ID, ve chu tieng Viet bang PIL - KHONG cv2.putText),
chi khac co MOT thu: NHAN THAM SO MODEL de so sanh n/s/m/l/x tren cung bo
video, cung cung hinh.

Khong sua file san pham. Chi doc video, ghi bao cao + anh tong hop.

Dung:
    python _kk_kiem_do_model.py                 # do 5 model
    python _kk_kiem_do_model.py yolo11m.pt      # do 1 model
    python _kk_kiem_do_model.py --tach-o        # them so sanh che do tach o
"""

import os
import sys
import time
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw
from ultralytics import YOLO

from cam_ai_core import AnalysisConfig
import cam_ai_core as core

THU_MUC_VIDEO = os.path.join("video_mau", "moi")
THU_MUC_KIEM_CHUNG = "_kiem_chung"
SO_KHUNG_MAU = 12               # so khung lay mau tren moi video (giong ban goc)
PERSON_CLASS_ID = 0

# 2 khung moi video x 7 video = 14 o -> 1 anh tong hop cho moi model
SO_KHUNG_MOI_VIDEO_TRONG_ANH = 2
BE_RONG_MOI_O = 320
COT = 3

# thu tu video: 6 video trong video_mau/moi + video_test.mp4
TEN_VIDEO = [
    ("nguoi-di-lai", "nguoi-di-lai.mp4"),
    ("cua-hang", "cua-hang.mp4"),
    ("xe-co-giao-thong", "xe-co-giao-thong.mp4"),
    ("nguoi-dung-cho", "nguoi-dung-cho.mp4"),
    ("dam-dong", "dam-dong.mp4"),
    ("tre-em-san-choi", "tre-em-san-choi.mp4"),
    ("video_test", "video_test.mp4"),
]

FONT = None
FONT_NHAN = None
try:
    from PIL import ImageFont

    for duong in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        if os.path.exists(duong):
            FONT = ImageFont.truetype(duong, 15)
            FONT_NHAN = ImageFont.truetype(duong, 13)
            break
except Exception:
    FONT = None
    FONT_NHAN = None


def ve_nhan(anh, text, vi_tri, mau=(0, 255, 0), font=None):
    """Ve chu tieng Viet co dau bang PIL (KHONG dung cv2.putText)."""
    if FONT is None:
        return
    f = font or FONT
    ve = ImageDraw.Draw(anh)
    x, y = vi_tri
    box = ve.textbbox((0, 0), text, font=f)
    rong, cao = box[2] - box[0], box[3] - box[1]
    ve.rectangle([x - 2, y - cao - 5, x + rong + 3, y + 2], fill=(0, 0, 0))
    ve.text((x, y - cao - 3), text, fill=mau, font=f)


def lay_video():
    """6 video trong video_mau/moi + video_test.mp4 (dung thu tu de bao cao)."""
    ds = []
    for nhan, ten in TEN_VIDEO:
        if ten == "video_test.mp4":
            duong = "video_test.mp4"
        else:
            duong = os.path.join(THU_MUC_VIDEO, ten)
        if os.path.exists(duong):
            ds.append((nhan, duong))
        else:
            print(f"  !! khong tim thay {duong}", flush=True)
    return ds


def do_video(model, duong, chi_lay_so):
    cap = cv2.VideoCapture(duong)
    if not cap.isOpened():
        return None
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    buoc = max(1, tong // (chi_lay_so + 1))
    mau = []
    for i in range(chi_lay_so):
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(tong - 1, i * buoc + buoc // 2))
        ok, khung = cap.read()
        if not ok:
            continue
        kq = model.predict(khung, conf=AnalysisConfig.conf, verbose=False)[0]
        nguoi, do_tin = [], []
        for xyxy, cid, cf in zip(
            kq.boxes.xyxy.tolist(), kq.boxes.cls.tolist(), kq.boxes.conf.tolist()
        ):
            if int(cid) == PERSON_CLASS_ID:
                nguoi.append((xyxy, float(cf)))
                do_tin.append(float(cf))
        mau.append((khung, nguoi, do_tin))
    cap.release()
    return {"tong_frame": tong, "mau": mau}


def do_tach_o(model, duong, so_khung=8):
    """So sanh nen vs detect_tach_o (HAM SAN PHAM cua cam_ai_core)."""
    cap = cv2.VideoCapture(duong)
    if not cap.isOpened():
        return None
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    buoc = max(1, tong // (so_khung + 1))
    khung = []
    for i in range(so_khung):
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(tong - 1, i * buoc + buoc // 2))
        ok, k = cap.read()
        if ok:
            khung.append(k)
    cap.release()
    if not khung:
        return None
    model.predict(khung[0], conf=AnalysisConfig.conf, verbose=False)

    t = time.perf_counter()
    a = []
    for k in khung:
        r = model.predict(k, conf=AnalysisConfig.conf, verbose=False)[0]
        a.append(sum(1 for c in r.boxes.cls.tolist() if int(c) == PERSON_CLASS_ID))
    ms_a = (time.perf_counter() - t) / len(khung) * 1000

    t = time.perf_counter()
    b = [sum(1 for c in core.detect_tach_o(model, k, AnalysisConfig.conf).class_id.tolist()
             if int(c) == PERSON_CLASS_ID) for k in khung]
    ms_b = (time.perf_counter() - t) / len(khung) * 1000
    return {"nen": a, "ms_nen": ms_a, "tach_o": b, "ms_tach_o": ms_b}


def tong_hop_anh(ten_model, tong_hop):
    """Gop 2 khung mau cua MOI video vao 1 anh de xem bang mat."""
    o = []
    for nhan_video, mau in tong_hop:
        if not mau:
            continue
        chon = mau[:SO_KHUNG_MOI_VIDEO_TRONG_ANH]
        for i, (khung, nguoi, do_tin) in enumerate(chon):
            o.append((nhan_video, i, khung, nguoi, do_tin))
    if not o:
        return None
    anh0 = cv2.cvtColor(o[0][2], cv2.COLOR_BGR2RGB)
    img0 = Image.fromarray(anh0)
    t_le = BE_RONG_MOI_O / img0.width
    cao = int(img0.height * t_le)
    hang = (len(o) + COT - 1) // COT
    tieu_de = 26
    canh = Image.new("RGB", (BE_RONG_MOI_O * COT, cao * hang + tieu_de), (18, 18, 22))
    ve = ImageDraw.Draw(canh)
    ve_nhan(canh, f"MODEL {ten_model} - tong hop {len(o)} khung mau / "
                  f"{len(tong_hop)} video",
            (8, 20), (255, 220, 60), FONT_NHAN)
    for i, (nhan_video, stt, khung, nguoi, do_tin) in enumerate(o):
        im = Image.fromarray(cv2.cvtColor(khung, cv2.COLOR_BGR2RGB)).resize(
            (BE_RONG_MOI_O, cao)
        )
        t_x = (i % COT) * BE_RONG_MOI_O
        t_y = tieu_de + (i // COT) * cao
        canh.paste(im, (t_x, t_y))
        sx = BE_RONG_MOI_O / khung.shape[1]
        sy = cao / khung.shape[0]
        for xyxy, _cf in nguoi:
            x1 = t_x + int(xyxy[0] * sx)
            y1 = t_y + int(xyxy[1] * sy)
            x2 = t_x + int(xyxy[2] * sx)
            y2 = t_y + int(xyxy[3] * sy)
            ve.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=2)
        tb = f"{nhan_video} #{stt + 1}  nguoi={len(nguoi)}"
        if do_tin:
            tb += f"  conf={min(do_tin):.2f}-{max(do_tin):.2f}"
        ve.rectangle([t_x, t_y, t_x + BE_RONG_MOI_O - 1, t_y + cao - 1],
                     outline=(70, 70, 80), width=1)
        ve_nhan(canh, tb, (t_x + 6, t_y + 20), (0, 255, 0), FONT_NHAN)
    return canh


def do_mot_model(ten_model, co_tach_o):
    print(f"\n########## {ten_model} ##########", flush=True)
    model = YOLO(ten_model)
    video = lay_video()
    dong = []
    dong.append(f"=== {ten_model} | conf={AnalysisConfig.conf} "
                f"| {SO_KHUNG_MAU} khung mau/video ===")
    tong_hop = []
    tat_ca = []
    for nhan, duong in video:
        r = do_video(model, duong, SO_KHUNG_MAU)
        if not r:
            print(f"  {nhan}: khong doc duoc", flush=True)
            dong.append(f"--- {nhan}: KHONG DOC DUOC ---")
            continue
        dem = [len(m[1]) for m in r["mau"]]
        tat = [d for m in r["mau"] for d in m[2]]
        co = [d for d in dem if d > 0]
        tb = sum(dem) / len(dem) if dem else 0
        dong.append(
            f"  {nhan:<20} TB={tb:5.1f}  max={max(dem) if dem else 0:3d}"
            f"  co nguoi={len(co)}/{len(dem)}"
            f"  {[d for d in dem]}"
        )
        if tat:
            s = sorted(tat)
            n = len(s)
            dong.append(f"  {'':<20} conf thap={s[0]:.2f} tb={s[n//2]:.2f} "
                        f"cao={s[-1]:.2f} | so conf<0.40: "
                        f"{sum(1 for c in tat if c < 0.40)}/{n}")
        else:
            dong.append(f"  {'':<20} KHONG phat hien nguoi nao tren cac khung mau")
        tong_hop.append((nhan, r["mau"]))
        tat_ca.extend(dem)
        print(f"  {nhan:<20} TB={tb:5.1f} max={max(dem) if dem else 0:3d} "
              f"{dem}", flush=True)

    if tat_ca:
        dong.append(
            f"  TAT CA video: {len(tat_ca)} khung mau, "
            f"TB={sum(tat_ca)/len(tat_ca):.2f} nguoi/khung, max={max(tat_ca)}, "
            f"tong={sum(tat_ca)}, so khung co nguoi="
            f"{sum(1 for d in tat_ca if d > 0)}/{len(tat_ca)}"
        )

    if co_tach_o:
        dong.append("  --- SO SANH TACH O (8 khung mau/video) ---")
        for nhan, duong in video:
            r = do_tach_o(model, duong)
            if not r:
                continue
            a, b = r["nen"], r["tach_o"]
            dong.append(
                f"    {nhan:<20} nen TB={np.mean(a):5.1f} {r['ms_nen']:6.1f} ms"
                f" | tach-o TB={np.mean(b):5.1f} {r['ms_tach_o']:6.1f} ms"
                f" | them {sum(b)-sum(a):+d} nguoi | cham {r['ms_tach_o']/r['ms_nen']:.2f}x"
            )
            print(f"    {nhan:<20} nen={np.mean(a):5.1f} "
                  f"tach_o={np.mean(b):5.1f} "
                  f"{r['ms_tach_o']/r['ms_nen']:.2f}x", flush=True)

    anh = tong_hop_anh(ten_model, tong_hop)
    if anh is not None:
        p = os.path.join(THU_MUC_KIEM_CHUNG,
                         f"model_{ten_model.replace('.pt', '')}.png")
        anh.save(p)
        dong.append(f"  anh tong hop: {p}")
        print(f"  -> {p}", flush=True)
    return dong


def main():
    os.makedirs(THU_MUC_KIEM_CHUNG, exist_ok=True)
    argv = sys.argv[1:]
    co_tach_o = "--tach-o" in argv
    ds = [a for a in argv if not a.startswith("--")]
    if not ds:
        ds = ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt"]

    tat_ca = []
    for m in ds:
        tat_ca.extend(do_mot_model(m, co_tach_o))

    duong_bao_cao = os.path.join(THU_MUC_KIEM_CHUNG, "do_chinh_xac_model.txt")
    with open(duong_bao_cao, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(tat_ca) + "\n")
    print(f"\nBAO CAO: {duong_bao_cao}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)