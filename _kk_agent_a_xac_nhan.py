# -*- coding: utf-8 -*-
"""KIEM CHUNG co che XAC NHAN DA KHUNG HINH trong bien_so.py.

Tao 2 video nho (nen trang, dan bien so "30A-12345" vao mot vung):
  A) bien so chi xuat hien o 1 khung hinh      -> CSV KHONG duoc ghi bien so
  B) bien so xuat hien o nhieu khung hinh lien tiep -> CSV CO bien so

Chay pipeline THAT qua cam_ai_core.run_analysis (KHONG sua app.py / cam_ai_core.py)
roi doc CSV -> kiem tra cot bien_so.

Ket qua dang text -> _kiem_chung/kiem_xac_nhan_da_khung.txt
Anh bang chung (khung hinh co bien so) -> _kiem_chung/plate_thu/kiem_v3/xac_nhan/

Chay: .venv\\Scripts\\python.exe -W ignore _kk_agent_a_xac_nhan.py
"""
import csv
import io
import os
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

import cv2
import numpy as np

from cam_ai_core import AnalysisConfig, run_analysis  # noqa: E402
from bien_so import BoDocBienSo  # noqa: E402

OUT_DIR = os.path.join(GOC, "_kk_out", "xac_nhan")
THU_ANH = os.path.join(GOC, "_kiem_chung", "plate_thu", "kiem_v3", "xac_nhan")
FILE_KET_QUA = os.path.join(GOC, "_kiem_chung", "kiem_xac_nhan_da_khung.txt")

ANH_BIEN_SO = os.path.join(GOC, "_kiem_chung", "plate_thu", "synthetic",
                           "00_sach_30A12345.png")
RONG, CAO, FPS = 640, 480, 10
VI_TRI = (100, 200)            # goc tren trai cua bien so trong khung hinh
LE = 2                          # phong to bien so gap 2 lan (de doc deu sau nen)


def tai_bien_so():
    """Bien so (anh that, kich thuoc 2 lan) de dan vao khung hinh."""
    img = cv2.imread(ANH_BIEN_SO)
    if img is None:
        raise SystemExit("KHONG DOC DUOC anh bien so: %s" % ANH_BIEN_SO)
    img = cv2.resize(img, (img.shape[1] * LE, img.shape[0] * LE),
                     interpolation=cv2.INTER_CUBIC)
    return img


def tao_video(duong, so_khung, cac_khung_co_bien_so, bien_so_img):
    """Video: nen sang, o cac khung hinh chi dinh thi dan bien so vao."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    writer = cv2.VideoWriter(duong, cv2.VideoWriter_fourcc(*"mp4v"), FPS,
                              (RONG, CAO))
    for i in range(so_khung):
        anh = np.full((CAO, RONG, 3), 245, dtype=np.uint8)
        if i in cac_khung_co_bien_so:
            h, w = bien_so_img.shape[:2]
            anh[VI_TRI[1]:VI_TRI[1] + h, VI_TRI[0]:VI_TRI[0] + w] = bien_so_img
        writer.write(anh)
    writer.release()
    return duong


def vung_roi():
    """ROI tuong doi bao trum bien so."""
    img = cv2.imread(ANH_BIEN_SO)
    h, w = img.shape[0] * LE, img.shape[1] * LE
    x1 = VI_TRI[0] / RONG
    y1 = VI_TRI[1] / CAO
    return "%.4f,%.4f,%.4f,%.4f" % (x1, y1,
                                    min(1.0, (VI_TRI[0] + w) / RONG),
                                    min(1.0, (VI_TRI[1] + h) / CAO))


def chay_pipeline(duong_video, ten):
    """Chay pipeline co bat doc bien so -> tra (so dong co bien so, ds bien so)."""
    out = os.path.join(OUT_DIR, "%s.mp4" % ten)
    cfg = AnalysisConfig(
        input=duong_video, output=out, no_face=True,
        doc_bien_so=True,
        bien_so_dir=os.path.join(OUT_DIR, "anh_%s" % ten),
        vung_bien_so=vung_roi(),
    )
    kq = run_analysis(cfg, log=lambda d: None)
    rows = list(csv.reader(io.open(kq.report_path, encoding="utf-8-sig")))
    co_bien = []
    for r in rows[1:]:
        if len(r) > 10 and r[10].strip():
            co_bien.append((r[0], r[10], r[11]))
    return rows, co_bien, kq


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(THU_ANH, exist_ok=True)
    dong_ky = []
    bien_so_img = tai_bien_so()
    h, w = bien_so_img.shape[:2]
    print("Bien so: %dx%d, dat tai %s" % (w, h, VI_TRI))

    # ---------- A) bien so chi o 1 khung hinh ----------
    video_a = tao_video(os.path.join(OUT_DIR, "a_1_khung.mp4"), 12, {5}, bien_so_img)
    rows_a, bien_a, kq_a = chay_pipeline(video_a, "a_1_khung")
    # ---------- B) bien so o nhieu khung hinh lien tiep ----------
    video_b = tao_video(os.path.join(OUT_DIR, "b_20_khung.mp4"), 20,
                         set(range(2, 20)), bien_so_img)
    rows_b, bien_b, kq_b = chay_pipeline(video_b, "b_20_khung")

    dong_ky.append("=" * 92)
    dong_ky.append("KIEM CHUNG XAC NHAN DA KHUNG HINH (bien_so.py)")
    dong_ky.append("Chay %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    dong_ky.append("=" * 92)
    dong_ky.append("Nguyen tac: chi bien so xuat hien o >= 2 khung hinh lien tiep")
    dong_ky.append("moi duoc ghi vao CSV / luu anh. Chuoi 1 khung hinh -> 'nghi'.")
    dong_ky.append("")

    dong_ky.append("-" * 92)
    dong_ky.append("A) BIEN SO CHI O 1 KHUNG HINH (video 12 khung hinh, bien so o khung 5)")
    dong_ky.append("-" * 92)
    dong_ky.append("  CSV: %d dong x %d cot" % (len(rows_a), len(rows_a[0])))
    dong_ky.append("  So dong co bien so ghi ra: %d" % len(bien_a))
    dong_ky.append("  AnalysisResult.bien_so: %r" % (kq_a.bien_so,))
    for b in bien_a:
        dong_ky.append("     khung %s -> '%s' (so=%s)" % b)
    ok_a = (len(bien_a) == 0 and len(kq_a.bien_so) == 0)
    dong_ky.append("  -> %s (mong doi: 0 dong co bien so)" % ("PASS" if ok_a else "FAIL"))
    dong_ky.append("")

    dong_ky.append("-" * 92)
    dong_ky.append("B) BIEN SO O 20 KHUNG HINH LIEN TIEP (video 20 khung hinh, bien so o khung 2-19)")
    dong_ky.append("-" * 92)
    dong_ky.append("  CSV: %d dong x %d cot" % (len(rows_b), len(rows_b[0])))
    dong_ky.append("  So dong co bien so ghi ra: %d" % len(bien_b))
    dong_ky.append("  AnalysisResult.bien_so: %r" % (kq_b.bien_so,))
    for b in bien_b[:4]:
        dong_ky.append("     khung %s -> '%s' (so=%s)" % b)
    if len(bien_b) > 4:
        dong_ky.append("     ... (con %d dong)" % (len(bien_b) - 4))
    ok_b = (len(bien_b) >= 2 and len(kq_b.bien_so) >= 1)
    dong_ky.append("  -> %s (mong doi: >= 2 dong co bien so)" % ("PASS" if ok_b else "FAIL"))
    dong_ky.append("")

    # ---------- C) kiem tra truc tiep tren BoDocBienSo ----------
    dong_ky.append("-" * 92)
    dong_ky.append("C) KIEM TRA TRUC TIEP tren BoDocBienSo.doc()")
    dong_ky.append("-" * 92)
    bds = BoDocBienSo(nguong_tin_cay=0.3, vung=vung_roi(), log=lambda d: None)
    bds.nap()
    anh_co = np.full((CAO, RONG, 3), 245, dtype=np.uint8)
    anh_co[VI_TRI[1]:VI_TRI[1] + h, VI_TRI[0]:VI_TRI[0] + w] = bien_so_img
    anh_khong = np.full((CAO, RONG, 3), 245, dtype=np.uint8)
    kq_lan = []
    for i in range(4):
        kq_lan.append(bds.doc(anh_co if i == 0 else anh_khong))
        dong_ky.append("  khung %d: doc %d ket qua | xac nhan_chac=%s | nghi=%r" % (
            i, len(kq_lan[-1]),
            [b.xac_nhan_chac("30A-12345") for b in [bds]][0],
            bds.danh_sach_nghi()))
    ok_c1 = (len(kq_lan[0]) == 0)          # khung 0: chi 1 khung -> chua ghi
    dong_ky.append("  -> 1 khung hinh: doc() tra %d ket qua (mong doi 0) -> %s" % (
        len(kq_lan[0]), "PASS" if ok_c1 else "FAIL"))
    kq_lan2 = []
    bds2 = BoDocBienSo(nguong_tin_cay=0.3, vung=vung_roi(), log=lambda d: None)
    bds2.nap()
    for i in range(3):
        kq_lan2.append(bds2.doc(anh_co))
    ok_c2 = (len(kq_lan2[0]) == 0 and len(kq_lan2[1]) >= 1 and len(kq_lan2[2]) >= 1)
    dong_ky.append("  -> 3 khung hinh lien tiep: doc() tra %d, %d, %d ket qua "
                    "(mong doi 0, >=1, >=1) -> %s" % (
                        len(kq_lan2[0]), len(kq_lan2[1]), len(kq_lan2[2]),
                        "PASS" if ok_c2 else "FAIL"))
    dong_ky.append("")

    # ---------- D) bien so NGHIENG 11 do: 2 cach doc lech nhau -> khong bao cao ----------
    dong_ky.append("-" * 92)
    dong_ky.append("D) BIEN SO NGHIENG ~11 DO (doc thang ra '30A-12346', doc cat muc "
                   "toi ra '30A-12345' -> MAU THUAN)")
    dong_ky.append("-" * 92)
    p_ngh = os.path.join(GOC, "_kiem_chung", "plate_gia", "vn_1hang_30A_12345.png")
    if os.path.exists(p_ngh):
        bds3 = BoDocBienSo(nguong_tin_cay=0.3, vung=vung_roi(), log=lambda d: None)
        bds3.nap()
        anh_ngh = cv2.imread(p_ngh)
        # xoay 11 do bang ham cua chinh bien_so.py
        anh_ngh = bds3._xoa_y_goc(anh_ngh, 11)
        nhan = []
        for _i in range(3):
            nhan.append(len(bds3.doc(anh_ngh)))
        ok_d = all(n == 0 for n in nhan)
        dong_ky.append("  doc() tren 3 khung hinh lien tiep: %s" % nhan)
        dong_ky.append("  -> %s (mong doi: 0,0,0 - KHONG bao cao bien so nghien sai)" % (
            "PASS" if ok_d else "FAIL"))
    else:
        dong_ky.append("  THIEU ANH: %s" % p_ngh)
        ok_d = False
    dong_ky.append("")

    # ---------- anh bang chung ----------
    cv2.imwrite(os.path.join(THU_ANH, "khung_co_bien_so.png"), anh_co)
    cv2.imwrite(os.path.join(THU_ANH, "khung_khong_bien_so.png"), anh_khong)
    dong_ky.append("Anh bang chung: %s" % THU_ANH)
    dong_ky.append("  khung_co_bien_so.png (khung hinh co bien so)")
    dong_ky.append("  khung_khong_bien_so.png (khung hinh nen)")

    tong = (ok_a and ok_b and ok_c1 and ok_c2 and ok_d)
    dong_ky.append("")
    dong_ky.append("=" * 92)
    dong_ky.append("KET LUAN: %s" % ("PASS" if tong else "FAIL"))
    dong_ky.append("=" * 92)

    noi_dung = "\n".join(dong_ky)
    os.makedirs(os.path.dirname(FILE_KET_QUA), exist_ok=True)
    with open(FILE_KET_QUA, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung + "\n")
    print(noi_dung)
    print()
    print("  -> Luu: %s" % FILE_KET_QUA)
    return 0 if tong else 1


if __name__ == "__main__":
    sys.exit(main())
