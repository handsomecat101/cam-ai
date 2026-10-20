"""Kiem chung lop_viet.py: doi chieu 80 lop voi model that + tra cuu tieng Viet.

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_lop_viet.py

KHONG sua file nao khac. Chi doc + in ket qua.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(APP_DIR, "yolo11n.pt")

FAIL = []
OK = []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))


def main():
    import lop_viet

    print("=" * 70)
    print("1. IMPORT CHE (khong duoc import ultralytics/torch)")
    print("=" * 70)
    code = (
        "import sys; sys.path.insert(0, r'%s'); import lop_viet; "
        "print('TORCH' if 'torch' in sys.modules else 'NO_TORCH'); "
        "print('ULTRA' if 'ultralytics' in sys.modules else 'NO_ULTRA')" % APP_DIR
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8"
    )
    check("lop_viet khong import torch", "NO_TORCH" in out.stdout, out.stdout.strip())
    check("lop_viet khong import ultralytics", "NO_ULTRA" in out.stdout, out.stdout.strip())

    print()
    print("=" * 70)
    print("2. DOI CHIEU 80 LOP VOI MODEL THAT (yolo11n.pt)")
    print("=" * 70)
    from ultralytics import YOLO

    names = YOLO(MODEL).names
    model_names = [names[i] for i in sorted(names)]
    my_names = list(lop_viet.TEN_LOP_VIET.keys())
    check("model co dung 80 lop", len(model_names) == 80, f"model={len(model_names)}")
    check("bang Viet co dung 80 lop", len(my_names) == 80, f"bang={len(my_names)}")
    check(
        "thu tu + ten khop 100% voi model",
        model_names == my_names,
        "khop 100%" if model_names == my_names else "LECH",
    )
    if model_names != my_names:
        for i, (a, b) in enumerate(zip(model_names, my_names)):
            if a != b:
                print(f"   LECH id {i}: model='{a}' bang='{b}'")
    # so sanh thu tu id
    ds = lop_viet.DANH_SACH_LOP_VIET()
    check(
        "DANH_SACH_LOP_VIET() dung thu tu id cua model",
        [d[0] for d in ds] == list(range(80))
        and [d[1] for d in ds] == model_names
        and [d[2] for d in ds] == [lop_viet.TEN_LOP_VIET[n] for n in model_names],
    )
    check(
        "mọi lop đều có tên tiếng Việt có dấu khác rỗng",
        all(d[2].strip() for d in ds),
    )

    print()
    print("=" * 70)
    print("3. TRA CUU LOP (tieng Viet co dau / khong dau / tieng Anh / dong nghia)")
    print("=" * 70)
    cases = [
        ("ô tô", ["car"]),
        ("o to", ["car"]),
        ("Ô TÔ", ["car"]),
        ("xe hơi", ["car"]),
        ("xe ô tô", ["car"]),
        ("xe máy", ["motorcycle"]),
        ("xe may", ["motorcycle"]),
        ("mô tô", ["motorcycle"]),
        ("xe gắn máy", ["motorcycle"]),
        ("xe đạp", ["bicycle"]),
        ("xe khách", ["bus"]),
        ("xe buýt", ["bus"]),
        ("xe tải", ["truck"]),
        ("xe hàng", ["truck"]),
        ("người", ["person"]),
        ("nguoi", ["person"]),
        ("điện thoại", ["cell phone"]),
        ("dien thoai", ["cell phone"]),
        ("điện thoại di động", ["cell phone"]),
        ("ô tô,xe máy", ["car", "motorcycle"]),
        ("o to,xe may", ["car", "motorcycle"]),
        ("car,motorcycle", ["car", "motorcycle"]),
        ("car, ô tô", ["car"]),
        ("Ô TÔ, Xe Máy, Điện Thoại", ["car", "motorcycle", "cell phone"]),
        ("xe đạp thể thao", ["bicycle"]),
        ("bóng thể thao", ["sports ball"]),
        ("ly rượu", ["wine glass"]),
        ("cây trong chậu", ["potted plant"]),
        ("đèn giao thông", ["traffic light"]),
        ("bình chữa cháy", ["fire hydrant"]),
        ("biển dừng xe", ["stop sign"]),
        ("đồng hồ đỗ xe", ["parking meter"]),
        ("gấu bông", ["teddy bear"]),
        ("tàu hỏa", ["train"]),
        ("thuyền", ["boat"]),
    ]
    for text, expect in cases:
        got = lop_viet.TRA_CUU_LOP_VIET(text)
        check(f"TRA_CUU_LOP_VIET({text!r})", got == expect, f"-> {got}")

    # tu dong nghia "tat ca"
    check("LA_TAT_CA('all')", lop_viet.LA_TAT_CA("all"))
    check("LA_TAT_CA('tất cả')", lop_viet.LA_TAT_CA("tất cả"))
    check("LA_TAT_CA('tat ca')", lop_viet.LA_TAT_CA("tat ca"))
    check("LA_TAT_CA('ô tô') == False", not lop_viet.LA_TAT_CA("ô tô"))

    # tra cuu khong phai bi bo qua im lang
    ra, sai = lop_viet.TRA_CUU_LOP_VIET_CHI_TIET("ô tô,xyzabc,xe máy")
    check(
        "tra cuu tach duoc lop sai",
        ra == ["car", "motorcycle"] and sai == ["xyzabc"],
        f"ra={ra} sai={sai}",
    )

    print()
    print("=" * 70)
    print("4. GOI Y LOP KHI GO SAI")
    print("=" * 70)
    for text in ("xyzabc", "oto", "xemay", "chao ban", "motarcycle", "dienthoai"):
        g = lop_viet.GOI_Y_LOP_VIET(text)
        print(f"   GOI_Y_LOP_VIET({text!r}) -> {g!r}")
    # "oto" (ghi sai "ô tô") va "xemay" (ghi sai "xe máy") phai co goi y
    check("GOI_Y_LOP_VIET('oto') co goi y", bool(lop_viet.GOI_Y_LOP_VIET("oto")),
          lop_viet.GOI_Y_LOP_VIET("oto"))
    check("GOI_Y_LOP_VIET('xemay') co goi y", bool(lop_viet.GOI_Y_LOP_VIET("xemay")),
          lop_viet.GOI_Y_LOP_VIET("xemay"))
    check("GOI_Y_LOP_VIET tra chuoi rong khi khong doan duoc",
          isinstance(lop_viet.GOI_Y_LOP_VIET("qqqqzzzzxxxx"), str))

    print()
    print("=" * 70)
    print("5. XE PHUONG TIEN")
    print("=" * 70)
    check(
        "XE_PHUONG_TIEN khop model",
        all(x in lop_viet.TEN_LOP_VIET for x in lop_viet.XE_PHUONG_TIEN),
        str(lop_viet.XE_PHUONG_TIEN),
    )
    check(
        "XE_PHUONG_TIEN_MO_RONG khop model",
        all(x in lop_viet.TEN_LOP_VIET for x in lop_viet.XE_PHUONG_TIEN_MO_RONG),
        str(lop_viet.XE_PHUONG_TIEN_MO_RONG),
    )
    check(
        "tra cuu lop phuong tien bang tieng Viet",
        lop_viet.TRA_CUU_LOP_VIET("ô tô, xe khách, xe tải, xe máy, xe đạp")
        == ["car", "bus", "truck", "motorcycle", "bicycle"],
    )

    print()
    print("=" * 70)
    print(f"KET QUA: {len(OK)} PASS / {len(FAIL)} FAIL")
    if FAIL:
        for f in FAIL:
            print("  FAIL:", f)
    print("=" * 70)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
