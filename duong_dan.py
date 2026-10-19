"""
CamAI - nguồn sự thật duy nhất cho đường dẫn của ứng dụng.

Vì sao cần file này: trước đây các đường dẫn tương đối (models/...,
known_faces, vung.txt, yolo11n.pt) được phân giải theo THƯ MỤC ĐANG CHẠY
(CWD). Khi chạy app.py bằng cách double-click từ Explorer, chạy từ shortcut,
chạy từ service/CI, hay gõ "python <đường dẫn app.py>" từ console ở thư mục
khác, thì CWD không phải thư mục gốc dự án -> app báo "không thấy bộ model
ArcFace" dù model đã có đủ trên đĩa.

Cách sửa: đường dẫn MẶC ĐỊNH của ứng dụng luôn phân giải theo thư mục gốc
dự án (APP_DIR). Đường dẫn người dùng gõ tay giữ nguyên ý định: ưu tiên bản
trong CWD, không có thì mới lấy bản trong APP_DIR, còn không có ở đâu cả thì
giữ nguyên để lỗi báo đúng chỗ người dùng trỏ tới (không tự bịa đường dẫn).

Dùng:
    from duong_dan import APP_DIR, chuan_hoa_duong_dan, duong_dan_app
"""

from __future__ import annotations

import os

# Thu muc goc du an (noi chua app.py) - KHONG phu thuoc thu muc dang chay.
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def chuan_hoa_duong_dan(duong_dan: str | None, uu_tien_cwd: bool = True) -> str | None:
    """Phân giải một đường dẫn tương đối thành đường dẫn dùng được.

    Quy tắc:
      - None hoặc rỗng -> trả về nguyên trạng.
      - Đường dẫn tuyệt đối -> trả về nguyên vẹn, KHÔNG đổi.
      - Đường dẫn tương đối:
          + có trong CWD -> giữ nguyên bản CWD (ưu tiên ý định người dùng);
          + không có trong CWD nhưng có trong APP_DIR -> trả về bản nối với
            APP_DIR;
          + không có ở cả hai -> trả về nguyên vẹn (để lỗi báo đúng chỗ
            người dùng trỏ tới, không tự bịa đường dẫn).

    uu_tien_cwd=False -> đảo thứ tự: ưu tiên bản trong APP_DIR trước, CWD sau.
    """
    if not duong_dan:
        return duong_dan
    if os.path.isabs(duong_dan):
        return duong_dan

    ban_cwd = duong_dan
    ban_app = os.path.join(APP_DIR, duong_dan)
    choi = (ban_cwd, ban_app) if uu_tien_cwd else (ban_app, ban_cwd)

    for ban in choi:
        if os.path.exists(ban):
            return ban
    return duong_dan


def duong_dan_app(duong_dan: str | None) -> str | None:
    """Nối luôn đường dẫn tương đối với thư mục gốc dự án.

    Dùng cho đường dẫn tài nguyên nội bộ luôn tồn tại trong dự án
    (models/..., yolo11n.pt, known_faces...). Đường dẫn tuyệt đối giữ nguyên.
    """
    if not duong_dan:
        return duong_dan
    if os.path.isabs(duong_dan):
        return duong_dan
    return os.path.join(APP_DIR, duong_dan)
