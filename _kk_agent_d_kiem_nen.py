# -*- coding: utf-8 -*-
"""Agent D: KIEM CHUNG CHUC NANG sau khi chuyen pha tim vung sang thread nen.

3 che do:
  1. KHONG ROI  -> pha TIM VUNG trong ca khung hinh (thread nen) -> phai
     doc duoc bien so sau >= 2 khung hinh lien tiep.
  2. ROI NHO   -> doc truc tiep vung (duong chinh) -> phai doc duoc.
  3. ROI RONG   -> pha TIM VUNG trong ROI (thread nen) -> phai doc duoc.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_agent_d_kiem_nen.py
"""
import os
import sys
import time

import cv2
import numpy as np

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

from bien_so import BoDocBienSo  # noqa: E402

ANH_BIEN_SO = os.path.join(GOC, "_kiem_chung", "plate_thu", "synthetic",
                           "00_sach_30A12345.png")
RONG, CAO = 640, 480
VI_TRI = (100, 200)
LE = 2
SO_KHUNG = 60


def tao_anh():
    img = cv2.imread(ANH_BIEN_SO)
    img = cv2.resize(img, (img.shape[1] * LE, img.shape[0] * LE),
                     interpolation=cv2.INTER_CUBIC)
    khung = np.full((CAO, RONG, 3), 245, dtype=np.uint8)
    h, w = img.shape[:2]
    khung[VI_TRI[1]:VI_TRI[1] + h, VI_TRI[0]:VI_TRI[0] + w] = img
    return khung, w, h


def chay(nhan, vung, khung):
    bd = BoDocBienSo(nguong_tin_cay=0.3, vung=vung, log=lambda d: None)
    bd.nap()
    doc_duoc = []
    ts = []
    for _i in range(SO_KHUNG):
        t0 = time.perf_counter()
        kq = bd.doc(khung)
        ts.append((time.perf_counter() - t0) * 1000.0)
        for r in kq:
            doc_duoc.append((r.chuoi, r.xac_nhan))
        time.sleep(0.04)      # gia lap 25 fps: de thread nen quet xong
    bd.close()
    ts_s = sorted(ts)
    chuoi = sorted({c for c, _x in doc_duoc})
    print("  %-22s -> doc duoc: %-28s | xac nhan: %-6s | ghi CSV duoc: %d lan"
          % (nhan, chuoi or "(khong co)",
             doc_duoc[0][1] if doc_duoc else "-", len(doc_duoc)))
    print("      doc() ms: median %5.2f | p95 %6.2f | MAX %6.2f"
          % (ts_s[len(ts_s) // 2], ts_s[int(len(ts_s) * 0.95)], max(ts)))
    print("      cache vung: %d vung | so lan quet: %d | thread nen: %s"
          % (len(bd._cache_vung["vung"]), bd.so_lan_quet,
             "chay" if (bd._thread_nen and bd._thread_nen.is_alive()) else "dung"))
    return len(doc_duoc) > 0


def main():
    khung, w, h = tao_anh()
    print("=" * 92)
    print("KIEM CHUNG CHUC NANG BIEN SO - 3 CHE DO (v3.1: pha tim vung o thread nen)")
    print("=" * 92)
    print("  khung hinh %dx%d, bien so %dx%d tai %s" % (RONG, CAO, w, h, VI_TRI))
    print()
    r1 = chay("1. KHONG ROI (tu tim)", None, khung)
    r2 = chay("2. ROI nho (44.000 px)",
              "%.4f,%.4f,%.4f,%.4f" % (VI_TRI[0] / RONG, VI_TRI[1] / CAO,
                                       (VI_TRI[0] + w) / RONG, (VI_TRI[1] + h) / CAO),
              khung)
    r3 = chay("3. ROI rong (0.05,0.05,0.95,0.95)", "0.05,0.05,0.95,0.95", khung)
    print()
    print("=" * 92)
    print("KET LUAN: %s" % ("PASS - ca 3 che do deu doc duoc bien so"
                             if (r1 and r2 and r3) else
                             "FAIL (khong roi: %s / %s / %s)" % (r1, r2, r3)))
    print("=" * 92)
    return 0 if (r1 and r2 and r3) else 1


if __name__ == "__main__":
    sys.exit(main())
