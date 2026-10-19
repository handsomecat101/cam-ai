"""
Ve vung canh bang chuot - dung 1 lan, luu lai dung cho moi video.

Cach dung:
    .venv\\Scripts\\python.exe ve_vung.py --input video.mp4
    .venv\\Scripts\\python.exe ve_vung.py --input video.mp4 --out vung_cua_hang.txt

Sau do app.py dung chung file do:
    .venv\\Scripts\\python.exe app.py --input video2.mp4 --vung vung.txt

Toa do luu TUONG DOI (0.0 - 1.0) nen vung nam dung vi tri khi xem video khac
(ke ca video chup o goc khac nhung cung khu vuc canh).
"""

import argparse
import os

import cv2

from duong_dan import chuan_hoa_duong_dan

# File vung mac dinh: nam trong thu muc goc du an, khong phu thuoc thu muc
# dang chay (chay tu thu muc khac van ghi dung choi).
DEFAULT_OUT = chuan_hoa_duong_dan("vung.txt")


def first_usable_frame(source):
    """Lay 1 khung hinh de anh khoanh vung (bo qua cac khung dau qua toi)."""
    cap = cv2.VideoCapture(0 if str(source).strip() == "0" else source)
    if not cap.isOpened():
        raise SystemExit(f"[loi] khong mo duoc: {source}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if total > 10:
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)

    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("[loi] khong doc duoc khung hinh nao")
    return frame


def draw_by_mouse(frame):
    """Chuot keo ra hinh chu nhat. Escape / dong cua so = bo dung."""
    title = "Keo chuot ve vung canh - ENTER OK, ESC bo"
    try:
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        cv2.imshow(title, frame)
        picked = cv2.selectROI(title, frame, showCrosshair=True, fromCenter=False)
        cv2.destroyAllWindows()
    except cv2.error:
        return None

    x, y, w, h = picked
    if w < 5 or h < 5:
        return None
    return x, y, x + w, y + h


def draw_by_number(frame):
    """Duong danh cho may khong mo duoc cua so - anh tu nhap so."""
    height, width = frame.shape[:2]
    print("\n[Huong dan] Nhap 4 so theo ty le 0.0 - 1.0 (0.5 = canh giua hinh)")
    print("  x ben trai | y ben tren | x ben phai | y ben duoi")
    try:
        raw = input("  > ").strip()
    except EOFError:
        return None

    parts = [p for p in raw.replace(",", " ").split() if p]
    if len(parts) != 4:
        print("[loi] can dung 4 so, tach bang dau cach hoac dau phay.")
        return None
    try:
        x1, y1, x2, y2 = (float(p) for p in parts)
    except ValueError:
        print("[loi] co so khong phai chu so.")
        return None

    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    return (
        int(x1 * width), int(y1 * height),
        int(x2 * width), int(y2 * height),
    )


def save_zone(path, rect, width, height, source):
    fx1, fy1, fx2, fy2 = rect
    rx1, ry1, rx2, ry2 = fx1 / width, fy1 / height, fx2 / width, fy2 / height
    with open(path, "w", encoding="utf-8") as file:
        file.write("# CamAI - vung canh\n")
        file.write("# Toa do tuong doi 0.0 - 1.0, dung chung cho moi video\n")
        file.write(f"# Ve tuong: {source}\n")
        file.write(f"{rx1:.4f} {ry1:.4f} {rx2:.4f} {ry2:.4f}\n")
    return rx1, ry1, rx2, ry2


def parse_args():
    parser = argparse.ArgumentParser(description="CamAI - ve vung canh")
    parser.add_argument("--input", required=True, help="video/anh de khoanh, hoac 0 = webcam")
    parser.add_argument("--out", default=DEFAULT_OUT, help="file luu vung")
    parser.add_argument(
        "--manual",
        action="store_true",
        help="nhap toa do bang so thay vi keo chuot",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("CamAI - Ve vung canh")
    print("-" * 46)

    frame = first_usable_frame(args.input)
    height, width = frame.shape[:2]
    print(f"[anh] {width}x{height} tu {args.input}")

    print("\n[Hanh dong] Keo chuot tao hinh chu nhat bao quanh khu vuc canh giam sat.")
    rect = None if args.manual else draw_by_mouse(frame)
    if rect is None:
        print("[chua chon vung] nhap toa do thu cong:")
        rect = draw_by_number(frame)
    if rect is None:
        raise SystemExit("[huy] khong co vung nao duoc chon.")

    preview = frame.copy()
    x1, y1, x2, y2 = rect
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 0, 255), 3)
    cv2.putText(
        preview, "VUNG CANH", (x1 + 8, y1 + 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
    )

    rx1, ry1, rx2, ry2 = save_zone(args.out, rect, width, height, args.input)
    print(f"\n[da luu] {os.path.abspath(args.out)}")
    print(f"[vung]   x {rx1:.3f} -> {rx2:.3f} | y {ry1:.3f} -> {ry2:.3f}")

    show = f"{os.path.splitext(args.out)[0]}_xem_truoc.jpg"
    cv2.imwrite(show, preview)
    print(f"[anh xem truoc] {show}")
    print("\n[buoc sau] chay app voi vung do:")
    print(f'  .venv\\Scripts\\python.exe app.py --input ten_video.mp4 --vung {args.out}')


if __name__ == "__main__":
    main()