"""Coordinator kiem tra lai: RapidOCR/Detection co can cho bien so khong?

Goc do: khi da BIET vung bien so (tu khung xe), viec tim chu = thua.
Hay chay RapidOCR o che do CHI DOC (bo qua khai tim).
"""
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/arialbd.ttf"


def tao_bien(noi_dung, w=220, h=50, mo=False):
    anh = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(anh)
    size = 34
    font = ImageFont.truetype(FONT, size)
    while d.textlength(noi_dung, font=font) > w - 10 and size > 8:
        size -= 1
        font = ImageFont.truetype(FONT, size)
    bb = d.textbbox((0, 0), noi_dung, font=font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1]),
           noi_dung, fill="black", font=font)
    if mo:
        from PIL import ImageFilter
        anh = anh.filter(ImageFilter.GaussianBlur(0.6))
    return np.array(anh)[:, :, ::-1].copy()


def chuan_hoa(s):
    ch = "".join(c for c in s.upper() if c.isdigit() or ("A" <= c <= "Z"))
    return ch


def _flat(kq):
    """RapidOCR tra ve kieu long nhau. CHI lay chuoi, BO diem so (float).
    Diem so duoc trong chuoi hoac chuoi rieng nen phai loai khi chuan hoa."""
    ra = []

    def walk(x):
        if isinstance(x, str):
            # chuoi chua toan so la diem so -> bo
            try:
                float(x)
                return
            except ValueError:
                pass
            ra.append(x)
        elif isinstance(x, (int, float)):
            return
        elif isinstance(x, (list, tuple)):
            if x and isinstance(x[0], str):
                # cap [str, score]
                walk(x[0])
            else:
                for y in x:
                    walk(y)

    walk(kq)
    return ra


OCR = None


def chay_rapid(img, tim=True):
    """DUNG 1 lan khoi tao engine. Tao lai moi lan thi do sai hoac toan khong doi
    duoc - dung xong thay doi khong kieu gi."""
    global OCR
    if OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        OCR = RapidOCR()
    if tim:
        kq, _ = OCR(img)
        return [x[1] for x in kq] if kq else []
    # chi doc: bo qua khai tim, cam 1 dong chu
    kq, _ = OCR(img, use_det=False, use_cls=False, use_rec=True)
    return _flat(kq)


def chay_easy(img, reader):
    kq = reader.readtext(img, detail=1)
    return kq


if __name__ == "__main__":
    import easyocr
    from rapidocr_onnxruntime import RapidOCR

    print("RapidOCR: khoi tao...", flush=True)
    ocr = RapidOCR()
    print("EasyOCR: khoi tao Reader (lan dau co the tai model)...", flush=True)
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    tru = ["30A-12345", "51F-678.90", "B1X-234.56", "61A-999.99", "30H-876.54"]
    print(f"\n{'anh':<22}{'nhan':<14}{'Rapid CO TIM':<22}{'Rapid CHI DOC':<20}{'EasyOCR':<20}{'ms(chi doc)'}")
    print("-" * 118)
    tong = {"tim": 0, "doc": 0, "easy": 0}
    tong_anh = 0
    for t in tru:
        for mo in (False, True):
            tong_anh += 1
            img = tao_bien(t, mo=mo)
            ten = f"{t}{'_mo' if mo else ''}"

            r1 = chay_rapid(img, tim=True)
            s1 = "|".join(r1) if r1 else "(khong doc)"

            t0 = time.perf_counter()
            r2 = chay_rapid(img, tim=False)
            s2 = "|".join(r2) if r2 else "(khong doc)"
            ms = (time.perf_counter() - t0) * 1000

            r3 = chay_easy(img, reader)
            s3 = "|".join([x[1] for x in r3]) if r3 else "(khong doc)"

            n = chuan_hoa(t)
            if chuan_hoa(s1) == n:
                tong["tim"] += 1
            if chuan_hoa(s2) == n:
                tong["doc"] += 1
            if chuan_hoa(s3) == n:
                tong["easy"] += 1

            print(f"{ten:<22}{t:<14}{s1:<22}{s2:<20}{s3:<20}{ms:.0f}")

    print("-" * 118)
    print(f"DUNG  RapidOCR co tim: {tong['tim']}/{tong_anh}   "
          f"RapidOCR CHI DOC: {tong['doc']}/{tong_anh}   EasyOCR: {tong['easy']}/{tong_anh}")

    # --- kiem tra tren crop bien so THAT tu video ---
    print("\n=== BIEN SO THAT tu video xe-co-giao-thong.mp4 ===")
    video = "video_mau/moi/xe-co-giao-thong.mp4"
    cap = cv2.VideoCapture(video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for khung in (int(n * f) for f in (0.1, 0.28, 0.4)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, khung)
        ok, fr = cap.read()
        if not ok:
            continue
        from ultralytics import YOLO
        det = YOLO("yolo11n.pt")
        res = det(fr, verbose=False, conf=0.25)[0]
        print(f"\nkhung {khung}: {len(res.boxes)} xe")
        for b in res.boxes:
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cw, chh = x2 - x1, y2 - y1
            # bien so thuong o gan dia giua - phia duoi
            vung = fr[int(cy + chh * 0.05):int(cy + chh * 0.50),
                       int(cx - cw * 0.38):int(cx + cw * 0.38)]
            if vung.size == 0:
                continue
            rr = chay_rapid(vung, tim=False)
            print(f"   xe {cw}x{chh}px -> vung bien so {vung.shape[1]}x{vung.shape[0]}px "
                  f"-> chi-doc ra: {rr[0][0] if rr else '(khong doc)'}")
    cap.release()