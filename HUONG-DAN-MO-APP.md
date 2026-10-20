# Cách mở app CamAI

> Tài liệu này dành cho người dùng thường, **không cần biết lập trình**.
> Mọi thứ trong CamAI chạy **trên máy của bạn**, không gửi ảnh/video đi đâu.

---

## 1. Mở app (1 click)

Trong thư mục `H:\AI Project\cam-ai`, **double-click** vào file:

```
Mo CamAI.vbs
```

→ App mở ra. **Không** có cửa sổ đen nào hiện lên (đó là bình thường).

Sau khi app đã mở, file `Mo CamAI.vbs` không cần dùng nữa. Có thể đóng app bằng nút **X** ở góc trên bên phải.

### Nếu app không mở

Double-click vào file này thay thế:

```
Mo CamAI.bat
```

File `.bat` **có** hiện cửa sổ đen, và cửa sổ đó in ra lỗi nếu có. Chụp màn hình cửa sổ đen đó gửi mình là biết nguyên nhân.

### Nếu Windows hiện cảnh báo "Windows đã bảo vệ PC của bạn"

1. Bấm **Thông tin thêm** (More info).
2. Bấm **Vẫn chạy** (Run anyway).

### Nếu Windows không cho double-click (file bị chặn)

1. Chuột phải vào `Mo CamAI.vbs` → **Thuộc tính** (Properties).
2. Tích ô **Unblock / Bỏ chặn** ở dưới cùng.
3. Bấm **OK** → double-click lại.

### Đưa shortcut lên desktop (để mở nhanh)

1. Chuột phải vào `Mo CamAI.vbs` → **Gửi tới** (Send to) → **Desktop (màn hình chính)**.
2. Sau đó mở app chỉ cần double-click biểu tượng trên desktop.

---

## 2. App này làm gì (30 giây)

CamAI đọc **video** trên máy bạn rồi tự động:

| Việc | Nơi bật |
|---|---|
| **Đếm người** trong khung hình | Ô "Phát hiện người" |
| **Nhận diện khuôn mặt** + biết đây là ai trong danh sách "người quen" | Ô "Nhận diện khuôn mặt" |
| **Đếm người vào / ra** theo vùng đã vẽ | Ô "Đếm ra vào" + nút "Vẽ vùng ngay tại đây" |
| **Đọc biển số xe Việt Nam** (chạy trên video, hoặc thử nhanh trên 1 ảnh) | Nhóm "Đọc biển số xe" + nút "Đọc biển số thử…" |
| **Tự chụp ảnh** khi có sự kiện trong vùng | Ô "Tự chụp ảnh khi có sự kiện" |
| **Cảnh báo** khi có người lạ trong vùng (chuông/hộp thoại trên máy) | Ô "Cảnh báo (gửi tin ra ngoài)" |

Cách dùng cơ bản:

1. Bấm **Chọn video…** (hoặc bấm 1 thẻ ở dải **Video mẫu dùng thử** ở đáy màn hình).
2. Bấm **▶ BẮT ĐẦU**.
3. Xem kết quả ở khung **Xem video**, các con số ở giữa màn hình và danh sách **Danh sách sự kiện** bên phải.
4. Bấm **Mở video kết quả** / **Xem báo cáo** để xem file đã lưu.

---

## 3. Một vài nút anh sẽ dùng nhiều

| Nút | Tác dụng |
|---|---|
| **Vẽ vùng ngay tại đây** | Kéo chuột trên khung hình để đánh dấu vùng cần theo dõi (cửa sổ con mở ra, kéo chuột, bấm **Lưu vùng**) |
| **Đăng ký người quen…** | Chọn ảnh (hoặc video) có mặt người → gõ tên → app lưu vào thư mục `known_faces/<Tên>/`. Sau đó app nhận ra người đó trên video và ghi tên vào báo cáo |
| **Đọc biển số thử…** | Chọn **1 ảnh** biển số → app đọc thử trong vài giây (dùng để gửi ảnh cho mình kiểm tra) |
| **English** | Đổi giao diện sang tiếng Anh |

---

## 4. Khi có sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Double-click không mở gì | Dùng `Mo CamAI.bat` để xem lỗi, chụp màn hình cửa sổ đen gửi mình |
| App mở nhưng báo thiếu file model | Báo mình, có thể phải tải lại model |
| Bấm **BẮT ĐẦU** không chạy | Xem khung **Nhật ký** ở giữa màn hình, chụp màn hình gửi mình |
| Máy chậm khi chạy | Tắt ô "Nhận diện tên trên ảnh", hoặc dùng mô hình nhẹ hơn trong ô "Mô hình nhận diện" |

---

## 5. Ghi chú kỹ thuật (dành cho người muốn xem)

- Chạy bằng Python của riêng dự án: `.venv\Scripts\python.exe gui.py` (dùng `pythonw.exe` để không hiện cửa sổ console).
- Mã nguồn: `gui.py` (giao diện), `cam_ai_core.py` (lõi phân tích), `giao_dien.py` (màu/font/khoảng cách — xem `design-system/camai/MASTER.md`).
- Tài liệu trạng thái: `PROJECT_STATE.md` (mục 2.1d là bảng ĐÃ ĐẠT / CHƯA ĐẠT), `ISSUE_LOG.md` (các lỗi đã gặp), `CHANGELOG.md` (nhật ký thay đổi).
- Bộ script kiểm chứng: `_kk_kiem_*.py` (chạy bằng `.venv\Scripts\python.exe`).
