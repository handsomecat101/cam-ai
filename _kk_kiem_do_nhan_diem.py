# -*- coding: utf-8 -*-
"""Do do nhan dien tren TOAN BO video demo.

Muc dich: dua so do co the doi chieu cho nguoi dung khi ho xac nhan
"do nhan dien co dung khong" (muc 8). Agent KHONG tu ket luan muc 8 -
script nay chi do va ban bang chung.

Dung Y DUNG ban chay that:
  - model  : yolo11n.pt  (giong AnalysisConfig.model)
  - conf   : 0.25        (giong AnalysisConfig.conf)
  - class  : person      (PERSON_CLASS_ID trong cam_ai_core)

Khong sua file san pham. Chi doc video, ghi bao cao + anh tong hop.
"""

import os
import sys
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw
from ultralytics import YOLO

from cam_ai_core import AnalysisConfig

THU_MUC_VIDEO = os.path.join("video_mau", "moi")
THU_MUC_KIEM_CHUNG = "_kiem_chung"
SO_KHUNG_MAU = 12               # so khung lay mau tren moi video
BE_RONG_MOI_O = 320             # bề rộng 1 ô trong ảnh tổng hợp
HANG = 4                        # 4 hang x 3 cot = 12 khung
COT = 3
PERSON_CLASS_ID = 0

FONT = None
try:
    from PIL import ImageFont

    for duong in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        if os.path.exists(duong):
            FONT = ImageFont.truetype(duong, 15)
            break
except Exception:
    FONT = None


def ve_nhan(anh, text, vi_tri, mau=(0, 255, 0)):
    """Ve chu tieng Viet co dau bang PIL (KHONG dung cv2.putText)."""
    if FONT is None:
        return
    ve = ImageDraw.Draw(anh)
    x, y = vi_tri
    box = ve.textbbox((0, 0), text, font=FONT)
    rong, cao = box[2] - box[0], box[3] - box[1]
    nen = (0, 0, 0) if mau == (0, 255, 0) else (0, 0, 0)
    ve.rectangle([x - 2, y - cao - 5, x + rong + 3, y + 2], fill=nen)
    ve.text((x, y - cao - 3), text, fill=mau, font=FONT)


def lay_video():
    ds = []
    if os.path.isdir(THU_MUC_VIDEO):
        for ten in sorted(os.listdir(THU_MUC_VIDEO)):
            if ten.lower().endswith(".mp4"):
                ds.append(os.path.join(THU_MUC_VIDEO, ten))
    if os.path.exists("video_test.mp4"):
        ds.append("video_test.mp4")
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


def tong_hop_anh(ten, mau):
    """Gop cac khung mau thanh 1 anh de agent/nguoi dung xem bang mat."""
    if not mau:
        return None
    mau = mau[: HANG * COT]
    anh0 = cv2.cvtColor(mau[0][0], cv2.COLOR_BGR2RGB)
    img0 = Image.fromarray(anh0)
    t_le = BE_RONG_MOI_O / img0.width
    cao = int(img0.height * t_le)
    canh = Image.new("RGB", (BE_RONG_MOI_O * COT, cao * HANG), (18, 18, 22))
    ve = ImageDraw.Draw(canh)
    for i, (khung, nguoi, do_tin) in enumerate(mau):
        im = Image.fromarray(cv2.cvtColor(khung, cv2.COLOR_BGR2RGB)).resize(
            (BE_RONG_MOI_O, cao)
        )
        t_x, t_y = (i % COT) * BE_RONG_MOI_O, (i // COT) * cao
        canh.paste(im, (t_x, t_y))
        sx = BE_RONG_MOI_O / khung.shape[1]
        for xyxy, _cf in nguoi:
            d = imDraw = None
            x1 = t_x + int(xyxy[0] * sx)
            y1 = t_y + int(xyxy[1] * (cao / khung.shape[0]))
            x2 = t_x + int(xyxy[2] * sx)
            y2 = t_y + int(xyxy[3] * (cao / khung.shape[0]))
            ve.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=2)
        tb = f"#{i + 1}  nguoi={len(nguoi)}"
        if do_tin:
            tb += f"  confTB={min(do_tin):.2f}-{max(do_tin):.2f}"
        ve.rectangle([t_x, t_y, t_x + BE_RONG_MOI_O - 1, t_y + cao - 1],
                     outline=(70, 70, 80), width=1)
        ve_nhan(canh, tb, (t_x + 6, t_y + 20))
    return canh


def main():
    os.makedirs(THU_MUC_KIEM_CHUNG, exist_ok=True)
    cfg = AnalysisConfig()
    print(f"model={cfg.model}  conf={cfg.conf}", flush=True)
    model = YOLO(cfg.model)

    video = lay_video()
    print(f"So video: {len(video)}", flush=True)
    dong = []
    tong_tt = []

    for duong in video:
        ten = os.path.splitext(os.path.basename(duong))[0]
        print(f"\n=== {ten} ===", flush=True)
        r = do_video(model, duong, SO_KHUNG_MAU)
        if not r:
            print("  khong doc duoc", flush=True)
            continue
        dem = [len(m[1]) for m in r["mau"]]
        co = [d for d in dem if d > 0]
        tat = [d for m in r["mau"] for d in m[2]]
        dong.append(
            f"--- {ten} (video {r['tong_frame']} khung, lay {len(dem)} khung mau) ---"
        )
        if dem:
            dong.append(
                f"  so nguoi / khung mau: {dem}"
            )
            dong.append(
                f"  khung co nguoi      : {len(co)}/{len(dem)}"
                f"   it nhat={min(dem)}  tb={sum(dem)/len(dem):.1f}  nhieu nhat={max(dem)}"
            )
        if tat:
            tat_s = sorted(tat)
            n = len(tat_s)
            dong.append(
                f"  do tin cay        : thap nhat={tat_s[0]:.2f}  p25={tat_s[n//4]:.2f}"
                f"  trung viet={tat_s[n//2]:.2f}  cao nhat={tat_s[-1]:.2f}"
                f"  (n={n})"
            )
            thap = sum(1 for c in tat if c < 0.40)
            if thap:
                dong.append(
                    f"  CANH BAO: {thap}/{n} nhan co conf < 0.40 (nghi do nho/nap mo)"
                )
        else:
            dong.append("  KHONG phat hien nguoi nao tren cac khung mau")
        tong_tt.append((ten, dem, tat))
        dong.append("")

        anh = tong_hop_anh(ten, r["mau"])
        if anh is not None:
            p = os.path.join(THU_MUC_KIEM_CHUNG, f"nhan_diem_{ten}.png")
            anh.save(p)
            dong.append(f"  anh: {p}")
            dong.append("")

    dong.append("=== TONG HOP ===")
    for ten, dem, tat in tong_tt:
        if dem:
            dong.append(
                f"  {ten:<22} tb={sum(dem)/len(dem):5.1f}  max={max(dem):3d}"
                f"  co nguoi={sum(1 for d in dem if d>0)}/{len(dem)} khung mau"
            )
    tong_dem = [d for _, dem, _ in tong_tt for d in dem]
    if tong_dem:
        dong.append("")
        dong.append(
            f"  TAT CA video: {len(tong_dem)} khung mau, "
            f"trung binh {sum(tong_dem)/len(tong_dem):.1f} nguoi/khung, "
            f"nhieu nhat {max(tong_dem)}"
        )

    duong_bao_cao = os.path.join(THU_MUC_KIEM_CHUNG, "do_nhan_diem.txt")
    with open(duong_bao_cao, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    print("\n".join(dong))
    print(f"\nBAO CAO: {duong_bao_cao}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)