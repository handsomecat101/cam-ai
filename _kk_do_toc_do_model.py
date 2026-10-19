r"""Do FPS cua luong UI xem video truc tiep voi TUNG MODEL YOLO khac nhau.

KHONG sua gui.py. Script nay bat chuc _kk_do_fps_live.py Y HET (cung boc
`_hien_khung_hinh`, cung dem khung hinh da ve len man hinh, cung pipeline
`run_analysis`), chi khac co MOT thu: nhan them model de chon.

Model duoc dua vao qua `app.v_model` (StringVar) - HAM THAT GUI doc model
o gui.py:2409 (`model=self.v_model.get()`), nen day la duong chon model
GIONG HET nguoi dung bam trong GUI, khong phai monkeypatch la.

Cach dung:
    python _kk_do_toc_do_model.py <video> <giay> <che_do> <nhan> <model>
    <che_do> = full   : live view + pipeline run_analysis (trai thuc te)
              = xem   : chi live view, pipeline bi tat (de do chi phi rieng)
    <model>  = yolo11n.pt | yolo11s.pt | yolo11m.pt | yolo11l.pt | yolo11x.pt

Ket qua ghi ra _kiem_chung\fps_<nhan>.txt va in ra man hinh.
Video dung de so sanh: video_test_300s.mp4 (giong ban do 300s nghiem thu).
"""

from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

KT = os.path.join(APP_DIR, "_kiem_chung")


def _chay(video: str, giay: float, che_do: str, nhan: str, model: str) -> int:
    os.makedirs(KT, exist_ok=True)

    import customtkinter as ctk

    import gui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = gui.CamAIGui()

    moc = []                      # moc thoi gian tung khung da ve len UI
    goc = time.perf_counter()

    # --- boc ham ve khung hinh de dem khung hinh that su len MAN HINH ---
    ham_goc = app._hien_khung_hinh

    def _dem(jpeg, _ham=ham_goc):
        moc.append(time.perf_counter() - goc)
        return _ham(jpeg)

    app._hien_khung_hinh = _dem

    if che_do == "xem":
        # Tat pipeline: chi do chi phi cua vong xem truc tiep.
        # KHONG duoc day ("done", None) o day: pump xu ly "done" se goi
        # `_dung_xem_truc_tiep()` -> dat co `_ket_thuc_xem`, tuc la TU TAT
        # chinh vong xem dang do (roi 0 khung hinh).
        def _hoa_pipeline(cfg, _gia=None):
            return None
        app._chay_pipeline = _hoa_pipeline

    # --- cau hinh ---
    app.v_video.set(video)

    # --- CHON MODEL: cung bien StringVar ma GUI doc (gui.py:2409) ---
    duong_model = model
    if not os.path.isabs(duong_model):
        _ung_vien = os.path.join(APP_DIR, model)
        duong_model = _ung_vien if os.path.exists(_ung_vien) else model
    app.v_model.set(duong_model)

    thu_muc_out = os.path.join(APP_DIR, "_kk_out")
    os.makedirs(thu_muc_out, exist_ok=True)
    app.v_output.set(thu_muc_out)
    app.v_xem_video.set("1")          # bat xem truc tiep
    app.v_face.set("0")               # TAT nhan dien mat: do rieng YOLO video
    app.v_vung.set("0")
    app.v_clip.set("0")
    app.v_pixelate.set("0")

    dong = []
    log_gui = []
    _xong = {"ok": False}

    # --- bat moi dong log GUI de biet vi sao khung hinh khong len ---
    ham_log = app._ghi_log

    def _bam_log(text, _ham=ham_log):
        log_gui.append(str(text))
        return _ham(text)

    app._ghi_log = _bam_log

    def _tick():
        if _xong["ok"]:
            app.after(150, _ket_thuc)
            return
        if time.perf_counter() - goc >= giay:
            _xong["ok"] = True
            app.after(150, _ket_thuc)      # PHAI hen _ket_thuc o day
            return
        app.after(200, _tick)

    def _chay_bam():
        try:
            app._bat_dau()
        except Exception as exc:                     # noqa: BLE001
            dong.append(f"LOI khi bat dau: {exc}")
            _xong["ok"] = True
            return
        app.after(300, _tick)

    def _ket_thuc():
        tong = time.perf_counter() - goc
        n = len([m for m in moc if m > 0])
        dong.append("")
        dong.append("=== DO FPS LUONG UI XEM TRUC TIEP (THEO MODEL) ===")
        dong.append(f"video            : {os.path.basename(video)}")
        dong.append(f"che do           : {che_do}")
        dong.append(f"MODEL            : {model}")
        kich = ""
        if os.path.exists(duong_model):
            kich = f"{os.path.getsize(duong_model) / 1048576:.2f} MB"
        dong.append(f"kich thuoc model : {kich or 'khong tim thay file'}")
        dong.append(f"thoi gian do     : {tong:.1f} s")
        dong.append(f"khung ve len UI  : {n}")
        dong.append(f"FPS TRUNG BINH   : {(n / tong) if tong > 0 else 0:.2f}")
        # chia tung giay - CHI dem tu khung hinh DAU TIEN (bo qua giai doan
        # nap model YOLO ~10s, khong phai trang thai xem video dang chay).
        moc_roi = sorted(m for m in moc if m > 0)
        moc_roi.append(tong)
        moc_1s = []
        if moc_roi:
            t_dau = moc_roi[0]
            for i in range(int(tong - t_dau)):
                lo, hi = t_dau + i, t_dau + i + 1
                moc_1s.append(sum(1 for m in moc_roi if lo <= m < hi))
            dong.append(f"khoi dong (nap model): {t_dau:.1f} s")
            dong.append(f"do giai doan       : {tong - t_dau:.1f} s")
            dong.append(f"FPS GIAI DOAN      : "
                        f"{sum(moc_1s) / len(moc_1s) if moc_1s else 0:.2f}")
        if moc_1s:
            thap = min(moc_1s)
            cao = max(moc_1s)
            tb = sum(moc_1s) / len(moc_1s)
            duoi = sum(1 for v in moc_1s if v < 10)
            dong.append(f"FPS/giay thap nhat: {thap}")
            dong.append(f"FPS/giay trung binh: {tb:.2f}")
            dong.append(f"FPS/giay cao nhat : {cao}")
            dong.append(f"so giay < 10 fps  : {duoi}/{len(moc_1s)}"
                        f" ({duoi * 100 // len(moc_1s)}%)")
            nhat10 = len(moc_1s) - duoi
            chuoi = 0
            chuoi_dai = 0
            for v in moc_1s:
                if v >= 10:
                    chuoi += 1
                    chuoi_dai = max(chuoi_dai, chuoi)
                else:
                    chuoi = 0
            dong.append(f"chuoi >=10 fps dai nhat: {chuoi_dai} giay")
            dong.append(f"tong so giay >=10 fps  : {nhat10}/{len(moc_1s)}")
        # khoang trong lon nhat giua 2 lan ve
        if len(moc_roi) > 2:
            lech = [moc_roi[i + 1] - moc_roi[i] for i in range(len(moc_roi) - 1)]
            dong.append(f"kich thuoc lon nhat giua 2 lan ve: {max(lech) * 1000:.0f} ms")
        dong.append("")
        dong.append(f"KET LUAN >= 10 fps lien tuc: "
                    f"{'DA DAT' if (moc_1s and thap >= 10) else 'CHUA DAT'}")

        dong.append("")
        dong.append("=== LOG GUI ===")
        dong.extend(log_gui[-40:])
        dong.append("")

        bao = "\n".join(dong)
        with open(os.path.join(KT, f"fps_{nhan}.txt"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(bao + "\n")
        print(bao)
        try:
            app.stop_flag.set()
            app._ket_thuc_xem.set()
            app.quit()
            app.destroy()
        except Exception:                            # noqa: BLE001
            pass

    app.after(600, _chay_bam)
    app.mainloop()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("dung: _kk_do_toc_do_model.py <video> <giay> <full|xem> "
              "<nhan> <model>")
        raise SystemExit(2)
    raise SystemExit(_chay(sys.argv[1], float(sys.argv[2]), sys.argv[3],
                           sys.argv[4], sys.argv[5]))