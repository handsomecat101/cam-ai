# Changelog - CamAI

## v2.3 (2026-10-18) - Báo cáo Excel + trang xem lại · sửa bug đứng lâu · tự lưu clip

Phiên bản này có **phần đã xong và phần đang làm dở**. Đọc kỹ mục "ĐANG LÀM DỞ" trước khi báo cáo anh.

> ⚠️ **Số version trong code CHƯA được nâng.** `cam_ai_core.py:41` vẫn là `VERSION = "2.2"`.
> Muốn đóng v2.3 thì phải sửa dòng đó.

### ĐÃ XONG

#### 1. Báo cáo Excel + trang xem lại video (`bao_cao_tong_ket.py`)

Đọc CSV 10 cột → sinh ra 2 file:

| File | Nội dung |
|---|---|
| `<ten>_tong_ket.xlsx` | 3 sheet: `Tong ket` · `Theo gio` · `Cu theo giay`. Cả 3 đều có `freeze_panes='A5'` + `autofilter`, có màu. |
| `<ten>_xem_lai.html` | 1 trang xem lại **offline 100%**: biểu đồ Canvas thuần, bấm điểm nào nhảy video tới giây đó, nút lớn nhảy tới giây đông nhất, danh sách sự kiện bấm được |

Cách dùng:
```
.venv\Scripts\python.exe bao_cao_tong_ket.py --csv ten_bao_cao.csv --video ten_ket_qua.mp4 [--xuat THU_MUC] [--nguong-dong N]
```

**Đã kiểm chứng (18/10):** chạy thật ra đủ 2 file; đếm trong file HTML được **0** tham chiếu `https://`,
**0** tham chiếu `http://`, **0** lệnh `fetch`, đúng **1** thẻ `<canvas>`.
Đọc Excel bằng openpyxl xác nhận đủ 3 sheet, đúng `freeze_panes` và `autofilter`.

**CHƯA kiểm chứng:** chưa ai **xem bằng mắt** bản render thật. Xem `PROJECT_STATE.md` mục 11.4.

#### 2. Sửa bug "đứng lâu" in đúng bằng ngưỡng

| | |
|---|---|
| **Triệu chứng** | Chạy `--canh-lau 3` thì dòng `Nguoi dung lao nhat` **luôn ra `3.0s`** — bằng đúng ngưỡng, dù người đó đứng 2 giây hay 30 giây |
| **Nguyên nhân** | Chụp thời điểm vượt ngưỡng lần đầu, thay vì đo thời gian thật khi rời vùng |
| **Đã sửa** | `cam_ai_core.py:635-636` — gán `longest_loiter = held` (đo liên tục từ lúc vào vùng) thay vì lấy ngưỡng |
| **Kiểm chứng** | `--canh-lau 3` giờ ra `Dung lau hon 3.0s: 1 lan, lan dai nhat 10.0s` — **10.0s** là thời gian đo thật (video dài 10s), **không còn bằng ngưỡng** |

Bản v2.1 ghi trong changelog này vẫn còn "đứng lâu 1 lần (3.0s)" — đó chính là **bằng chứng bug**.

#### 3. Tự lưu clip khi có sự kiện

Lớp `ClipRecorder` (`cam_ai_core.py:198`). Video chỉ ghi được 1 chiều nên phần **trước** sự kiện
lấy từ vòng đệm khung hình — không ghi cả video ra đĩa rồi cắt sau (vừa chậm vừa tốn đĩa).

| Cờ | Việc |
|---|---|
| `--tu-luu-clip THU_MUC` | Bật tự lưu clip (mặc định **TẮT**) |
| `--clip-giay N` | Tổng thời lượng 1 clip, mặc định 10.0s, chia đôi trước/sau |
| `--clip-ghi-tat-ca` | Ghi cả khi không dùng `--vung` |

Lý do: người mới xem sẽ không biết **vì sao** phần mềm báo cảnh báo.
Tên file đặt theo lý do, ví dụ: `clip_20261018_170927_vao_vung+vuot_nguong_dong.mp4`.

Có chặn tự bảo vệ RAM: `BO_NHO_VONG_DEM_MB = 300 MB` (`cam_ai_core.py:53`) — video độ phân giải cao
sẽ tự rút ngắn vòng đệm và in cảnh báo `[clip] anh pha gian: ...`.

**Đã kiểm chứng (18/10 17:09):** sinh được 4 file clip thử trong `_t/clip/`.
**CHƯA kiểm chứng:** nội dung và thời lượng từng clip có đúng 10s, đúng quanh sự kiện không.

#### 4. Nhận diện vật thể khác ngoài người

| Cờ | Việc |
|---|---|
| `--nhan-vat-the` | Vẽ khung + nhãn tiếng Việt + đếm cho lớp khác (mặc định **TẮT**) |
| `--lop car,motorcycle` | Chọn lớp cần nhận. Rỗng = nhóm phổ biến, `all` = tất cả trừ người |

Nguyên tắc bất di bất dịch: vật thể khác **chỉ vẽ + đếm, KHÔNG vào logic canh vùng**
(`cam_ai_core.py:549-561` tách riêng khỏi `detections` của người).
→ **Xe chạm vùng không được tính là "người vào vùng".**

#### 5. Cảnh báo Telegram + chuông Windows (`canh_bao.py`)

2 kênh: Telegram (cần Internet) và chuông/hộp thoại ngay trên máy (không cần Internet).
**Chỉ gửi CHỮ. Tuyệt đối không gửi hình ảnh hay video lên cloud.**
Hướng dẫn cài cho người chưa dùng Telegram Bot: `HUONG_DAN_CANH_BAO.md`.

#### 6. Sổ đăng ký model tiếng Việt (`model_info.py`)

In bảng 4 model: tên, thư viện, file, dung lượng, trạng thái, vai trò — viết cho người không rành công nghệ.
Tự đo kích thước file trên đĩa thay vì ghi cứng. Có sẵn cảnh báo dữ liệu `known_faces` là giả lập.

### ĐANG LÀM DỞ

| Việc | Trạng thái | Người phụ trách |
|---|---|---|
| 3 việc của Agent A (sửa đứng lâu · tự lưu clip · nhận diện vật thể) | **Code đã trên đĩa, 4 lệnh hồi quy vẫn đúng. Chưa ai báo xong chính thức.** | Agent A — giữ `cam_ai_core.py`, `app.py`, `gui.py` |
| Nối báo cáo + cảnh báo + thông tin model vào GUI | **Chưa làm.** `gui.py` chưa import `bao_cao_tong_ket`, `canh_bao`, `model_info` | Agent A |
| Làm lại GUI cho người không rành công nghệ | **Chưa làm** | Agent A |
| Nâng `VERSION` lên `"2.3"` | **Chưa làm** (`cam_ai_core.py:41` vẫn là `"2.2"`) | Agent A |
| Xem bằng mắt trang HTML xem lại | **Chưa làm** | ai cũng được |
| Cập nhật `README.md` (đang ghi v2.1) | **Chưa làm** | không ai giữ |

### Viết lại toàn bộ tài liệu bàn giao

`PROJECT_STATE.md` (viết lại từ đầu) · `AGENT_CHAT.md` (tạo mới) · `ISSUE_LOG.md` (tạo mới) ·
`CHANGELOG.md` (mục này) · `ROADMAP.md` (cập nhật trạng thái).

### Không phá gì

4 lệnh hồi quy chạy lại ngày 18/10 — **kết quả y hệt**:
MD5 `base1 = new1`, `base2 = new2`, `base3 = new3`.
CSV vẫn **đúng 10 cột**. Dòng chuẩn vẫn ra:
`[vung] 192,81 -> 768,513 | che do chac | toi da 2 nguoi | canh dung lau 3.0s`

---

## v2.2 (2026-10-18) - Bộ 9 video mẫu + công cụ quét video

Anh bảo "không có nhiều footage để kiểm tra". Thay vì chờ video nhà, em tải về
**9 video mẫu đủ tình huống** và viết thêm công cụ đo đặc tính từng video.

### Thêm mới

| Thứ | Vai trò |
|---|---|
| `video_mau/` (9 file, 80 MB) | Video mẫu: ít người / đông người / không có người / mặt rõ / công nhân trong khu vực |
| `kiem_tra_video_mau.py` | Quét video: đo độ phân giải, số người max/TB/%rỗng, tự gợi ý video đó dùng test gì |
| `video_mau/_ket_qua/` | Kết quả chạy thử kèm theo |

Nguồn video: repo mẫu của Intel (`intel-iot-devkit/sample-videos`), dùng tự do.

### Kết quả chạy thật (không phải hứa suông)

**Quét 9 video** — `kiem_tra_video_mau.py --buoc 30`:

| Video | Kích thước | max người | TB | % rỗng |
|---|---|---|---|---|
| car-detection | 768x432 | 0 | 0.00 | 100% |
| classroom | 1920x1080 | 5 | 4.18 | 0% |
| store-aisle-detection | 720x404 | 6 | 3.43 | 12% |
| people-detection | 768x432 | 4 | 0.75 | 60% |
| face-demographics-walking | 768x432 | 4 | 0.80 | 56% |
| head-pose-face-detection-female | 768x432 | 1 | 1.00 | 0% |
| head-pose-face-detection-male | 768x432 | 1 | 1.00 | 0% |
| one-by-one-person-detection | 768x432 | 1 | 0.74 | 26% |
| worker-zone-detection | 1920x1080 | 2 | 0.91 | 22% |

**Chạy `app.py` thật trên 3 tình huống:**

| Test | Lệnh | Kết quả |
|---|---|---|
| A — chống báo nhầm | `car-detection.mp4 --no-face` | 377 khung hình, **0 người toàn bộ** ✅ |
| B — canh vùng ngoài đời | `people-detection.mp4 --vung vung.txt --vung-max 2 --canh-lau 2` | Vùng 153,64→614,410 · tối đa 3 người trong vùng · 8 lần có người vào vùng · vượt ngưỡng 2 lần · đứng lâu 4 lần ✅ |
| C — nhận diện mặt thật | `head-pose-face-detection-female.mp4` (có nhận diện) | `detection/genderage/recognition = CUDA` · 1520 nữ vs 95 nam · tuổi TB 36 — **video của nữ thì đo ra nữ, đúng** ✅ |

### Ghi chú quan trọng

- Test C chạy trên **mặt thật** (không phải ảnh mẫu giả lập như `video_test.mp4`) và cho kết quả
  giới tính khớp với nội dung video → **bộ đo tuổi/giới tính hoạt động đúng trên người thật**.
- `worker-zone-detection.mp4` (công nhân trong khu vực làm việc) là case khớp nhất với
  tính năng canh vùng, nhưng dài 4548 khung hình 1080p nên chưa chạy full — dùng `--buoc` hoặc
  `--face-every` để chạy nhanh hơn.
- `app.py` **không đổi logic**, chỉ bump `VERSION` 2.1 → 2.2.

---

## v2.1 (2026-10-18) - Thêm tính năng canh vùng

Anh muốn "vẽ 1 khu vực, có người đi vào thì báo". Làm xong, kèm 3 tính năng
đi kèm lấy từ phần toán học sẵn có — **không cần huấn luyện model nào thêm**.

### Tính năng mới

| Tính năng | Cách dùng | Ghi chú |
|---|---|---|
| **Khoanh vùng bằng chuột** | `ve_vung.py --input video.mp4` | Kéo chuột vẽ hcnh, Enter xong, lưu `vung.txt` |
| **Báo có người vào vùng** | `app.py --input video.mp4 --vung vung.txt` | Vẽ khung đỏ + đếm trên đầu video |
| **Chế độ nhạy** | thêm `--vung-nhay` | Chỉ cần 1 phần thân chạm vùng là báo (mặc định: chặt) |
| **Cảnh báo chỗ đông** | thêm `--vung-max 5` | Báo khi số người trong vùng vượt ngưỡng |
| **Cảnh báo đứng lâu** | thêm `--canh-lau 30` | Báo khi có người đứng trong vùng quá 30 giây |

### Kết quả đo thật (`video_test.mp4`, 250 khung hình)

| Cách chạy | Kết quả |
|---|---|
| Chế độ chặt | 2 người trong vùng, đỏ **1 lần**, đứng lâu **1 lần** (3.0s) |
| Chế độ nhạy | 2 người trong vùng, đỏ **1 lần** |
| Chạy không có `--vung` | Không đổi so với v2.0, không lỗi |

### CSV thêm 3 cột

`trong_vung` (số người trong vùng lúc đó) · `vi_pham` (1 = có người trong vùng) ·
`canh_lau` (số người bị cảnh báo đứng lâu)

### Ghi chú kỹ thuật

- Vùng lưu **tương đối 0.0–1.0** nên khoanh 1 lần dùng được cho mọi video,
  kể cả video quay góc khác nhưng cùng khu vực cần canh.
- `ve_vung.py` có đường lùi `--manual` nhập tọa độ bằng số, phòng khi máy
  không mở được cửa sổ OpenCV.
- So sánh vùng là toán học thuần trên bounding box YOLO — **không cần model mới**.

## v2.0 (2026-10-16) - Nâng cấp nhận diện khuôn mặt sang ArcFace

### Đã thay đổi

| Mục | Trước (v1.x) | Sau (v2.0) |
|---|---|---|
| Bộ dò khuôn mặt | MTCNN (facenet-pytorch) | SCRFD 10G (insightface) |
| Bộ nhận diện | InceptionResnetV1 / vggface2 | ArcFace w600k_r50 |
| Tuổi / giới tính | Không có | Có (ước lượng) |
| Chạy trên | CPU (onnx) | GPU tự động (onnxruntime-gpu) |
| Tốc độ | 226 ms/khung hình | **39 ms/khung hình** (nhanh gấp 5,8 lần) |

### Kết quả đo thật trên video mẫu (`video_test.mp4`, 250 khung hình)

| Chỉ số | v1.x | v2.0 |
|---|---|---|
| Tổng số mặt tìm thấy | 463 | 500 |
| Số lần rút đúng tên | 43 | **500** |
| Người nhận đúng | An (Bình bị bỏ sót) | **An + Bình** |

Nguyên nhân bản cũ bỏ sót: MTCNN nhận được mặt nhỏ nhưng vector vggface2 không đủ phân biệt; ArcFace chuẩn hóa tốt hơn nên khớp cả hai.

### Mới thêm

- `face_engine.py` — lớp nhận diện mặt mới, tự bật GPU nếu có card NVIDIA.
- `dang_ky_anh.py` — đăng ký ảnh người quen tự động từ video (thay vì chụp tay).
- `tai_tao_model.py` — tải lại bộ model khi bị xoá.
- `kiem_tra_nhan_dien.py` — đo nhanh khả năng nhận diện trên một video.
- Báo cáo CSV thêm cột `nam`, `nu`, `tuoi_tb`.
- `app.py` thêm `--face-threshold`, `--min-face`.
- `models/face_core/` — chỉ giữ 3 model cần dùng (183MB thay vì 325MB, tiết kiệm 142MB).

### Gỡ bỏ

- `facenet-pytorch` (không còn dùng).
- `app.py` không còn tự tải model nhận diện mặt cũ.

### Ghi chú kỹ thuật quan trọng

- **insightface 2.1 ép CPU khi `prepare(ctx_id=-1)`.** Muốn chạy GPU phải dùng `ctx_id=0`. Đây là lý do mã ban đầu rơi về CPU dù đã truyền đúng provider.
- Phải nạp thư viện CUDA của torch (`os.add_dll_directory(torch/lib)`) **trước khi** onnxruntime được import, nếu không CUDAExecutionProvider không tìm thấy cuDNN và im lặng rơi về CPU.
- `provider_options={}` rỗng cũng làm GPU rơi về CPU — phải truyền `None`.
- Ảnh mẫu cũ trong `known_faces/` quá tệ (160×160, cận mặt, đeo kính râm) nên bộ dò mặt mới **không tìm thấy mặt** và báo đúng: "bo dien dan khong tim thay mat". Đã tạo lại ảnh mẫu từ video bằng `dang_ky_anh.py`.

## v1.0

- Phát hiện người bằng YOLO11n, đếm người bằng ByteTrack.
- Đếm ra/vào bằng LineZone.
- Nhận diện khuôn mặt bằng facenet-pytorch (MTCNN + InceptionResnetV1).
- Làm mờ nền (`--pixelate`).