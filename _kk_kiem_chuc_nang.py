"""Kiem chung tong hop: encoding, API lõi, cot CSV, thu tu truong dataclass.

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_chuc_nang.py
"""

import csv
import io
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

FAIL = []
OK = []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))


def main():
    print("=" * 74)
    print("A. ENCODING: UTF-8 khong BOM + LF (khong co CR)")
    print("=" * 74)
    for ten in ("lop_viet.py", "cam_ai_core.py", "app.py"):
        duong = os.path.join(APP_DIR, ten)
        raw = open(duong, "rb").read()
        bom = raw[:3] == b"\xef\xbb\xbf"
        cr = raw.count(b"\r")
        lf = raw.count(b"\n")
        check(f"{ten}: BOM=False", not bom, f"BOM={bom}")
        check(f"{ten}: CR=0 (LF thuan)", cr == 0, f"CR={cr} LF={lf}")
        try:
            raw.decode("utf-8")
            check(f"{ten}: giai ma UTF-8 dung", True)
        except UnicodeDecodeError as exc:
            check(f"{ten}: giai ma UTF-8 dung", False, str(exc))

    print()
    print("=" * 74)
    print("B. API LÕI cam_ai_core: ten + hanh vi giu nguyen")
    print("=" * 74)
    import cam_ai_core as core
    import lop_viet

    for ten in ("loai_nguon", "la_live", "quet_camera", "run_analysis",
                "AnalysisConfig", "Progress", "AnalysisResult", "CamAIError",
                "PERSON_CLASS_ID", "LOAI_ANH", "LOAI_CAMERA",
                "LOAI_MANG", "LOAI_VIDEO", "DUOI_ANH", "VAT_THE_MAC_DINH",
                "TEN_VAT_THE", "ten_vat_the", "_goi_y_lop",
                "CSV_FIELDS", "CSV_FIELDS_BIEN_SO", "CSV_FIELDS_PHUONG_TIEN"):
        check(f"cam_ai_core.{ten} con ton tai", hasattr(core, ten))

    # duong_dan.py la MODULE (khong phai attribute cua cam_ai_core).
    try:
        import duong_dan
        check("duong_dan.py con ton tai + import duoc",
              hasattr(duong_dan, "chuan_hoa_duong_dan")
              and hasattr(duong_dan, "APP_DIR"),
              f"APP_DIR={duong_dan.APP_DIR}")
    except ImportError as exc:
        check("duong_dan.py con ton tai + import duoc", False, str(exc))

    check("PERSON_CLASS_ID == 0", core.PERSON_CLASS_ID == 0)
    check("VAT_THE_MAC_DINH giu nguyen",
          core.VAT_THE_MAC_DINH == ["car", "motorcycle", "bicycle", "bus",
                                    "truck", "backpack", "handbag", "suitcase",
                                    "cell phone"])
    check("CSV_FIELDS giu nguyen 10 cot",
          core.CSV_FIELDS == ["giay", "so_nguoi", "so_mat", "nguoi_quen", "nam",
                              "nu", "tuoi_tb", "trong_vung", "vi_pham",
                              "canh_lau"], str(core.CSV_FIELDS))
    check("CSV_FIELDS_BIEN_SO giu nguyen",
          core.CSV_FIELDS_BIEN_SO == ["bien_so", "so_bien_so"])
    check("CSV_FIELDS_PHUONG_TIEN them o CUOI",
          core.CSV_FIELDS_PHUONG_TIEN == ["phuong_tien", "so_phuong_tien",
                                          "tong_phuong_tien", "max_phuong_tien"])
    check("TEN_VAT_THE giu nguyen cac key cu",
          all(core.TEN_VAT_THE.get(k) == v for k, v in {
              "car": "xe o to", "motorcycle": "xe may", "bicycle": "xe dap",
              "bus": "xe khach", "truck": "xe tai", "backpack": "ba loi",
              "handbag": "tui xach", "suitcase": "vali",
              "cell phone": "dien thoai", "boat": "thuyen", "bench": "ghe",
              "chair": "ghe", "potted plant": "cay", "tv": "tivi",
              "laptop": "may tinh", "bird": "chim", "cat": "meo", "dog": "cho",
              "bird nest": "to chim"}.items()))
    check("ten_vat_the() giu nguyen", core.ten_vat_the("motorcycle") == "xe may")
    check("TEN_VAT_THE phu 80 lop COCO",
          len([k for k in core.TEN_VAT_THE if k != "bird nest"]) == 80,
          str(len(core.TEN_VAT_THE)))
    check("loai_nguon('0') == 'camera'", core.loai_nguon("0") == "camera")
    check("loai_nguon('a.mp4') == 'video'", core.loai_nguon("a.mp4") == "video")
    check("loai_nguon('a.jpg') == 'anh'", core.loai_nguon("a.jpg") == "anh")
    check("loai_nguon('rtsp://x') == 'mang'", core.loai_nguon("rtsp://x") == "mang")
    check("la_live('0') is True", core.la_live("0") is True)
    check("la_live('a.mp4') is False", core.la_live("a.mp4") is False)

    print()
    print("=" * 74)
    print("C. AnalysisConfig: 2 truong MOI o CUOI (khong doi thu tu vi tri cu)")
    print("=" * 74)
    import dataclasses

    truong = [f.name for f in dataclasses.fields(core.AnalysisConfig)]
    check("dem_phuong_tien la truong CUOI-CUOI",
          truong[-2] == "dem_phuong_tien", truong[-2])
    check("lop_phuong_tien la truong CUOI",
          truong[-1] == "lop_phuong_tien", truong[-1])
    check("dem_phuong_tien mac dinh = False",
          core.AnalysisConfig().dem_phuong_tien is False)
    check("lop_phuong_tien mac dinh = ''",
          core.AnalysisConfig().lop_phuong_tien == "")
    check("thu tu truong cu giu nguyen",
          truong[:10] == ["input", "output", "no_face", "faces_dir", "model",
                          "thiet_bi", "conf", "face_every", "face_threshold",
                          "min_face"], str(truong[:10]))
    cfg = core.AnalysisConfig(input="a.mp4", output="b.mp4")
    check("property .loai_nguon con", cfg.loai_nguon == "video")
    check("property .la_live con", cfg.la_live is False)

    print()
    print("=" * 74)
    print("C2. _chon_lop: ten lop cua model + tra cuu tieng Viet")
    print("=" * 74)
    id_lop_gia = {ten: cid for cid, ten in enumerate(
        list(lop_viet.TEN_LOP_VIET) + ["bird nest"]
    )}
    chon, sai = core._chon_lop("ô tô,xe máy", id_lop_gia)
    check("_chon_lop tieng Viet -> 2 lop", chon == ["car", "motorcycle"] and not sai,
          f"chon={chon} sai={sai}")
    chon, sai = core._chon_lop("o to,xe may", id_lop_gia)
    check("_chon_lop khong dau -> 2 lop", chon == ["car", "motorcycle"] and not sai,
          f"chon={chon} sai={sai}")
    chon, sai = core._chon_lop("car,motorcycle", id_lop_gia)
    check("_chon_lop tieng Anh -> 2 lop", chon == ["car", "motorcycle"] and not sai,
          f"chon={chon} sai={sai}")
    chon, sai = core._chon_lop("bird nest", id_lop_gia)
    check("_chon_lop giu ten lop rieng cua model ('bird nest')",
          chon == ["bird nest"] and not sai, f"chon={chon} sai={sai}")
    chon, sai = core._chon_lop("ô tô,xyzabc,xe máy", id_lop_gia)
    check("_chon_lop bao loi DUNG token sai",
          chon == ["car", "motorcycle"] and sai == ["xyzabc"],
          f"chon={chon} sai={sai}")
    chon, sai = core._chon_lop("ô tô,xe khách", {"car": 2})   # model chi co 'car'
    check("_chon_lop bao loi khi model thieu lop",
          chon == ["car"] and sai == ["xe khách"], f"chon={chon} sai={sai}")

    print()
    print("=" * 74)
    print("D. AnalysisResult: truong moi o CUOI")
    print("=" * 74)
    truong_rs = [f.name for f in dataclasses.fields(core.AnalysisResult)]
    check("phuong_tien / tong_phuong_tien / max_phuong_tien o CUOI",
          truong_rs[-3:] == ["phuong_tien", "tong_phuong_tien",
                             "max_phuong_tien"], str(truong_rs[-3:]))
    rs = core.AnalysisResult()
    check("mac dinh tong_phuong_tien = 0", rs.tong_phuong_tien == 0)
    check("mac dinh max_phuong_tien = 0", rs.max_phuong_tien == 0)
    check("mac dinh phuong_tien = {}", rs.phuong_tien == {})

    print()
    print("=" * 74)
    print("E. CSV: cot CU giu nguyen + cot MOI o CUOI")
    print("=" * 74)
    goc = os.path.join(APP_DIR, "_kk_out", "base_goc_bao_cao.csv")
    moi = os.path.join(APP_DIR, "_kk_out", "dem_xe_bao_cao.csv")
    if not (os.path.isfile(goc) and os.path.isfile(moi)):
        check("co du 2 file CSV de so sanh", False, "thieu file CSV")
    else:
        with open(goc, encoding="utf-8-sig", newline="") as f:
            rows_goc = list(csv.reader(f))
        with open(moi, encoding="utf-8-sig", newline="") as f:
            rows_moi = list(csv.reader(f))
        check("so dong giong nhau", len(rows_goc) == len(rows_moi),
              f"{len(rows_goc)} vs {len(rows_moi)}")
        check("header goc = 10 cot", len(rows_goc[0]) == 10, str(rows_goc[0]))
        check("header moi = 14 cot", len(rows_moi[0]) == 14, str(rows_moi[0]))
        check("10 cot CU giong het (ten)", rows_goc[0] == rows_moi[0][:10])
        check("4 cot MOI o CUOI dung thu tu",
              rows_moi[0][10:] == ["phuong_tien", "so_phuong_tien",
                                  "tong_phuong_tien", "max_phuong_tien"])
        giong = all(r_goc == r_moi[:10] for r_goc, r_moi in zip(rows_goc, rows_moi))
        check("GIA TRI 10 cot CU giong het tren MOI dong", giong)
        # tong phuong tien dong cuoi == tong cong
        tong = int(rows_moi[-1][12])
        max_cung_luc = int(rows_moi[-1][13])
        check("tong_phuong_tien dong cuoi > 0", tong > 0, f"tong={tong}")
        check("max_phuong_tien dong cuoi > 0", max_cung_luc > 0,
              f"max={max_cung_luc}")
        # so_phuong_tien khop voi max_phuong_tien
        check("max_phuong_tien = max(so_phuong_tien)",
              max_cung_luc == max(int(r[11]) for r in rows_moi[1:]),
              f"max_cot={max_cung_luc} max_tinh={max(int(r[11]) for r in rows_moi[1:])}")
        # nguoi KHONG bi dem vao xe
        co_nguoi = [r for r in rows_moi[1:] if int(r[1]) > 0]
        check("co dong co nguoi nhung so_phuong_tien doc lap",
              len(co_nguoi) > 0,
              f"{len(co_nguoi)} dong co nguoi; vi du so_nguoi="
              f"{co_nguoi[0][1]} so_phuong_tien={co_nguoi[0][11]}")
        check("cot phuong_tien co dau tieng Viet",
              any("ô tô" in r[10] or "xe khách" in r[10] or "xe tải" in r[10]
                  for r in rows_moi[1:]),
              rows_moi[1][10])

    print()
    print("=" * 74)
    print(f"KET QUA: {len(OK)} PASS / {len(FAIL)} FAIL")
    for f in FAIL:
        print("  FAIL:", f)
    print("=" * 74)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
