# CamAI

Xem video, tự động đếm người, đếm ra/vào và nhận diện khuôn mặt. Chạy trên GPU RTX 3090.

Phiên bản hiện tại: **v2.3**.

## Hai cách chạy

### 1. Giao diện cửa sổ (cách dễ nhất)

Nhấp đúp `chay_gui.bat`. Hoặc:

```
.venv\Scripts\pythonw.exe gui.py
```

Mọi tính năng đều nằm trong cửa sổ, tên tiếng Việt, từng nhóm gập/ bung được.

### 2. Web trên máy này

```
$env:CAMAI_PASSWORD = "<mật khẩu của anh, ít nhất 8 ký tự>"
.venv\Scripts\python.exe web_server.py
```

Rồi mở trình duyệt vào **http://127.0.0.1:8787**.

- Phải nhập mật khẩu mới vào được. Sai 5 lần thì khóa 5 phút.
- Mật khẩu lấy từ lệnh trên, **không lưu trong mã nguồn**. Không đặt biến đó thì chương trình báo và thoát.
- Toàn bộ hình ảnh và video **chỉ nằm trên máy này**, không gửi đi đâu cả.

### 3. Chạy bằng dòng lệnh

Kéo file video (.mp4) vào biểu tượng `run.bat`, hoặc nhấp đúp `run.bat` rồi dán đường dẫn video.

Xem camera trực tiếp: mở cmd trong thư mục này rồi gõ
`.venv\Scripts\python.exe app.py --input 0`

## Kết quả nhận được

| File | Ý nghĩa |
|---|---|
| `<tên>_ket_qua.mp4` | Video đã vẽ khung người, tên người, tuổi/giới tính, vạch đếm, khung vùng canh |
| `<tên>_bao_cao.csv` | Bảng theo từng giây: mấy người, mấy mặt, ai xuất hiện, bao nhiêu nam/nữ, tuổi trung bình, mấy người trong vùng |

Dòng đầu tiên của video cho biết: đang có mấy người trong khung hình, thấy mấy mặt, số người đi vào và đi ra qua vạch giữa khung hình.

## Vẽ khu vực cảnh báo (tính năng mới)

**Bước 1 — khoanh vùng (chạy 1 lần, xong xong là dùng cho mọi video):**

```
.venv\Scripts\python.exe ve_vung.py --input video_cua_anh.mp4
```

Một cửa sổ hiện lên. Anh **kéo chuột** quanh khu vực cần canh (ví dụ khu vực cấm, khu trước quầy, khu cửa) rồi nhấn **Enter**. Chương trình lưu ra file `vung.txt` và một ảnh xem trước để anh đối chiếu.

- Nhấn **Esc** trong lúc khoanh → huỷ, chương trình sẽ hỏi nhập toạ độ bằng tay.
- Máy không mở được cửa sổ? Thêm `--manual` để nhập số.

**Bước 2 — dùng vùng đó:**

```
.venv\Scripts\python.exe app.py --input video_cua_anh.mp4 --vung vung.txt
```

Video sẽ vẽ khung vùng: **xanh vàng = vùng trống**, **đỏ = đang có người**. Dòng đầu video thêm `Trong vung: N`.

Cuối video in tổng kết:

```
--- CANH VUNG ---
Vung          : 192,81 -> 768,513 (che do chac)
So nguoi nhieu nhat trong vung: 2
So lan co nguoi vao vung: 1
```

**Ba chế độ thêm:**

| Thêm vào lệnh | Tác dụng |
|---|---|
| `--vung-nhay` | Chỉ cần một phần thân chạm vào vùng là báo (mặc định: **chặt** — người phải nằm hẳn trong vùng mới báo) |
| `--vung-max 5` | Báo khi chỗ đó đông quá 5 người |
| `--canh-lau 30` | Báo khi có người đứng trong vùng quá 30 giây |

Ví dụ đầy đủ:

```
.venv\Scripts\python.exe app.py --input video_cua_anh.mp4 --vung vung.txt --vung-max 5 --canh-lau 30
```

**Báo cáo CSV thêm 3 cột:** `trong_vung` (số người trong vùng lúc đó) · `vi_pham` (1 = có người trong vùng) · `canh_lau` (số người bị báo đứng lâu). Mở bằng Excel, lọc cột `vi_pham` = 1 là ra đúng những lúc có chuyện.

**Lưu ý:** hiện mỗi lần chạy chỉ canh **1 vùng**. Muốn canh 2–3 khu vực thì anh nói em mở rộng.

## Dạy nó nhận diện người quen

**Cách nhanh nhất — lấy ảnh từ video của chính anh:**

```
.venv\Scripts\python.exe dang_ky_anh.py --input video_cua_anh.mp4 --names An,Binh
```

Máy tự tìm mặt trong video, gom từng người vào một thư mục, lưu tối đa 5 ảnh. Nhanh hơn nhiều so với tự chụp ảnh, và ảnh từ camera anh chắc chắn nhận được.

**Cách thủ công:** bỏ ảnh chụp mặt vào thư mục `known_faces`, mỗi người một thư mục con:

```
known_faces/
  An/
    anh_1.jpg
    anh_2.jpg
  Binh/
    anh_1.jpg
```

Càng nhiều ảnh (nhiều góc mặt, nhiều chỗ sáng) thì càng chính xác. Người không có trong thư mục sẽ hiện là **Nguoi la**.

Ảnh mẫu trong `known_faces/An` và `known_faces/Binh` được tạo từ video mẫu để thử — anh xoá đi rồi thay bằng người thật.

## Kiểm tra nhanh xem có nhận ra không

```
.venv\Scripts\python.exe kiem_tra_nhan_dien.py video_cua_anh.mp4
```

In ra: tìm thấy bao nhiêu mặt, ai được nhận, ước lượng tuổi/giới tính.

## Tùy chọn thêm

| Lệnh | Tác dụng |
|---|---|
| `--pixelate` | Làm mờ cả khung hình, chừa nguyên vùng có người |
| `--no-face` | Bỏ qua nhận diện khuôn mặt (chạy nhanh hơn) |
| `--face-every 3` | Phân tích mặt mỗi 3 frame (nhanh hơn ~20% nếu video dài) |
| `--face-threshold 0.5` | Khó hơn, chỉ nhận khi chắc chắn (mặc định 0.40) |
| `--min-face 40` | Bỏ qua mặt nhỏ hơn 40px — nhanh hơn và bớt nhận nhầm |
| `--model yolo11s.pt` | Model chính xác hơn, chậm hơn một chút |
| `--vung vung.txt` | Bật canh vùng (xem mục trên) |
| `--vung-nhay` | Vùng nhạy: thân chạm vùng là báo (mặc định chặt) |
| `--vung-max 5` | Cảnh báo khi trong vùng quá 5 người |
| `--canh-lau 30` | Cảnh báo khi có người đứng trong vùng quá 30 giây |

## Bộ video mẫu để tự kiểm tra (tính năng mới)

Thư mục `video_mau/` có sẵn **9 video** đủ tình huống khác nhau để anh thử khi không có footage nhà. Chạy thử:

```bash
# 1. Xem trước video nào đúng tình huống cần test
.venv\Scripts\python.exe kiem_tra_video_mau.py --buoc 30

# 2. Chạy thật lên một video
.venv\Scripts\python.exe app.py --input video_mau\store-aisle-detection.mp4 --vung vung.txt --vung-max 3
```

| Video | Dùng để test |
|---|---|
| `car-detection.mp4` | Chống báo nhầm — trong video **không có người**, phải đếm ra 0 |
| `classroom.mp4` | Phòng đông người (tối đa 5), không bao giờ vắng |
| `store-aisle-detection.mp4` | Lối hẹp đông người (tối đa 6) → đếm ra/vào, cảnh báo đông |
| `people-detection.mp4` | Người đi lại, lúc có lúc không |
| `face-demographics-walking.mp4` | Mặt rõ, người ra vào khung hình → tuổi / giới tính |
| `head-pose-face-detection-female.mp4` | Một người nữ, mặt rõ nhất → thử nhận diện người quen |
| `head-pose-face-detection-male.mp4` | Một người nam, mặt rõ → thử nhận diện người quen |
| `one-by-one-person-detection.mp4` | Từng người một đi qua → vạch đếm ra/vào |
| `worker-zone-detection.mp4` | Công nhân làm việc trong khu vực → **đúng case canh vùng** |

> Video lấy từ repo mẫu của Intel, dùng tự do cho mục đích thử nghiệm.

## Model đang dùng

| Việc | Model | Dung lượng |
|---|---|---|
| Phát hiện người / 80 loại vật thể | YOLO11n | 5,4 MB |
| Tìm khuôn mặt | SCRFD 10G | 16 MB |
| Nhận diện đây là ai | ArcFace w600k_r50 | 166 MB |
| Ước lượng tuổi / giới tính | genderage | 1,3 MB |

Toàn bộ nằm trong `models/`. Mất thì tải lại bằng `tai_tao_model.py`.

## Cần biết trước

- Vạch đếm nằm ở giữa khung hình, nên vị trí vạch có thể không hợp với cửa thật của anh. Muốn đổi thì sửa `sv.Point(width // 2, 0)` trong `app.py`.
- Nhận diện khuôn mặt chỉ tốt khi mặt **đủ lớn và đủ sáng**. Mặt nhỏ dưới ~40px thường không nhận được. Camera nhìn thẳng, rõ, đủ sáng sẽ chính xác hơn nhiều.
- Ảnh mẫu phải rõ, chính diện, không đeo kính râm. Bộ dò mặt mới **không tìm thấy** mặt che kính — đây là hành vi đúng, đừng tắt.
- Tuổi và giới tính chỉ là **ước lượng**, dùng để thống kê, không dùng để kết luận.
- Nếu không có card NVIDIA, chương trình tự chạy CPU và chậm hơn khoảng 5-6 lần. Không cần cấu hình gì thêm.
- Từ `supervision` phiên bản 0.31 sẽ bỏ class `ByteTrack`. Nếu sau này cập nhật mà báo lỗi, cài lại đúng phiên bản trong `requirements.txt`.