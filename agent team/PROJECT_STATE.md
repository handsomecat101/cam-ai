> **ĐỌC FILE NÀY ĐẦU TIÊN KHI QUAY LẠI LÀM TIẾP** — cập nhật lần cuối: 18/10/2026 · trạng thái: v2.3 đang hoàn thiện

# PROJECT_STATE — CamAI

Phiên bản mã nguồn: **v2.2** (xem mục 13 — số version trong code **chưa** được nâng lên 2.3).
Ngày viết lại tài liệu này: **18/10/2026**.

---

## 1. Dự án này là gì

**CamAI** là phần mềm giám sát video camera chạy **100% trên máy tính của anh Tuấn**.

Nó làm được những việc sau:

| Việc | Mô tả cho người không rành công nghệ |
|---|---|
| Đếm người | Xem video, tự động đếm có bao nhiêu người trong khung hình |
| Đếm ra / vào | Đếm người đi vào và đi ra qua 1 vạch ở giữa khung hình |
| Nhận diện người quen | Biết đây là An hay Bình; người lạ ghi là "Nguoi la" |
| Ước lượng tuổi / giới tính | Đoán tuổi và nam/nữ từ khuôn mặt (chỉ là ước lượng) |
| Cảnh vùng | Vẽ 1 khu vực cần canh giữ. Có người bước vào là báo |
| Cảnh báo | Có người đứng lâu, hoặc vượt quá số người cho phép |
| Báo cáo | Xuất Excel + 1 trang web xem lại, mở offline |

**Ba nguyên tắc không được phá:**

1. **KHÔNG deploy Internet.** Phần mềm này chạy local, không có máy chủ, không có tài khoản.
2. **KHÔNG gửi hình / video ra ngoài máy.** Ảnh và video chỉ nằm trên ổ cứng của máy này.
   (Cảnh báo Telegram là ngoại lệ: nó gửi **chữ** qua Internet, không gửi hình — xem `canh_bao.py`.)
3. **Giao diện phải dùng được với người KHÔNG rành công nghệ.** Đây là yêu cầu cốt lõi của anh Tuấn.

---

## 2. Môi trường máy

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3090, 24GB |
| Python | 3.13.7 — `C:\Program Files\Python313` |
| Venv | `.venv` (tạo bằng `python -m venv .venv --system-site-packages` để dùng lại torch CUDA có sẵn) |
| Thư viện chính | ultralytics 8.4.177 · insightface 2.1 · onnxruntime-gpu 1.23.2 · supervision 0.30.9 · opencv-python 5.0.0.93 · numpy 2.5.4 |
| Thư mục dự án | `H:\AI Project\cam-ai` |

**Luôn chạy bằng `.venv\Scripts\python.exe`.** Dùng `python` hệ thống là sai môi trường, sẽ thiếu thư viện.

> `.venv\Lib\site-packages\` có **không có git**. Nếu máy này từng có `.git` thì nó đã bị mất — xem ISSUE_LOG #2.

---

## 3. Cách chạy (viết cho người không rành kỹ thuật)

Mở cửa sổ PowerShell, gõ `cd 'H:\AI Project\cam-ai'` rồi Enter, rồi gõ các lệnh dưới đây.

### 3.1 Mở giao diện đồ hoạ (CÁCH ANH DÙNG NHIỀU NHẤT)

Double-click vào file `chay_gui.bat` trong thư mục dự án. Xong.

Nếu muốn chạy bằng lệnh:

```
.venv\Scripts\python.exe gui.py
```

### 3.2 Xử lý 1 video

```
.venv\Scripts\python.exe app.py --input ten_video.mp4
```

Kết quả sinh ra 2 file cạnh video đó:

- `ten_video_ket_qua.mp4` — video đã vẽ khung, khung người, nét đếm
- `ten_video_bao_cao.csv` — bảng số liệu **10 cột** (xem mục 5)

Muốn quay webcam thay vì đọc file: `--input 0`

### 3.3 Vẽ vùng canh (chạy 1 lần, dùng lại được cho mọi video)

```
.venv\Scripts\python.exe ve_vung.py --input ten_video.mp4
```

Dùng chuột kéo 1 khung, rồi gõ tên file (mặc định `vung.txt`) và Enter.
Sau đó chạy `app.py` với cờ `--vung vung.txt`.

### 3.4 Làm báo cáo Excel + trang xem lại

```
.venv\Scripts\python.exe bao_cao_tong_ket.py --csv ten_file_bao_cao.csv --video ten_video_ket_qua.mp4
```

Đã kiểm chứng bằng `--help` ngày 18/10/2026, đúng **4 cờ** sau:

| Cờ | Bắt buộc? | Ý nghĩa |
|---|---|---|
| `--csv DUONG_DAN` | **CÓ** | File CSV 10 cột do `app.py` xuất ra |
| `--video DUONG_DAN` | không | File mp4 kết quả, để trang HTML có video để xem lại |
| `--xuat THU_MUC` | không | Nơi ghi kết quả. Mặc định = cùng thư mục với CSV |
| `--nguong-dong N` | không | Người tối đa trong vùng. Mặc định tự lấy = số người nhiều nhất quan sát được |

Xuất ra 2 file: `<ten>_tong_ket.xlsx` và `<ten>_xem_lai.html`.
Mở file `.html` bằng trình duyệt (double-click) là xem được, **không cần Internet**.

### 3.5 Cảnh báo Telegram / chuông Windows

```
.venv\Scripts\python.exe canh_bao.py --kiem-tra
```

Cách cài đặt viết cho người chưa dùng Telegram Bot: xem `HUONG_DAN_CANH_BAO.md`.

### 3.6 Các lệnh khác

| Lệnh | Việc |
|---|---|
| `dang_ky_anh.py --input video.mp4 --names An,Binh` | Lấy ảnh mặt từ video, lưu vào `known_faces/<Ten>/` |
| `kiem_tra_nhan_dien.py video.mp4` | Kiểm tra nhận diện mặt có chạy không |
| `kiem_tra_video_mau.py --buoc 30` | Quét 9 video mẫu, đo số người từng video |
| `tai_tao_model.py` | Tải lại bộ model nhận diện mặt nếu bị xoá |
| `model_info.py` | In ra bảng 4 model đang dùng (tiếng Việt) |
| `run.bat` | Chạy nhanh `app.py` (có thể kéo file .mp4 vào) |

---

## 4. BỐN LỆNH HỒI QUY — LUẬT NGHIỆM THU

Sau **mọi** thay đổi code, phải chạy đủ 4 lệnh này. Kết quả phải **y hệt** bản gốc, nếu lệch thì tính là phá vỡ.

```powershell
cd 'H:\AI Project\cam-ai'
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-max 2 --canh-lau 3 --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-nhay --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --no-face
.venv\Scripts\python.exe app.py --help
```

### Kết quả ĐÚNG MONG ĐỢI (đã chạy thật ngày 18/10/2026)

**Lệnh 1** — canh vùng chặt + cảnh báo đông + cảnh báo đứng lâu:

```
[vung] 192,81 -> 768,513 | che do chac | toi da 2 nguoi | canh dung lau 3.0s
So nguoi nhieu nhat trong vung: 2
So lan co nguoi vao vung: 1
Nguong 2 nguoi: vuot 0 lan
Dung lau hon 3.0s: 1 lan, lan dai nhat 10.0s
Nguoi dung lao nhat: 10.0s
```

**Lệnh 2** — canh vùng nhạy:

```
[vung] 192,81 -> 768,513 | che do nhay
So nguoi nhieu nhat trong vung: 2
So lan co nguoi vao vung: 1
```

**Lệnh 3** — không dùng vùng:

```
[video] 960x540 @ 25fps, 250 frame
Bao cao       : output_bao_cao.csv
Do dai        : 0:00:10
Nguoi nhieu nhat trong 1 khung hinh: 4
```

**Lệnh 4** — in danh sách cờ, phải có đủ 4 nhóm: `canh vung`, `tu luu clip`, `nhan vat the`.

### Cách kiểm tra CSV đúng 10 cột (nhanh nhất)

Mỗi lần đổi code, so 3 file CSV nền với 3 file mới bằng **MD5**:

```powershell
cd 'H:\AI Project\cam-ai\_t'
Get-FileHash base1_bao_cao.csv,new1_bao_cao.csv,base2_bao_cao.csv,new2_bao_cao.csv,base3_bao_cao.csv,new3_bao_cao.csv -Algorithm MD5
```

MD5 phải **trùng cặp** `base1 = new1`, `base2 = new2`, `base3 = new3`.
Ngày 18/10/2026 đã kiểm: cả 3 cặp đều trùng.

- `base1` = lệnh 1 · `base2` = lệnh 2 · `base3` = lệnh 3 (mỗi cái 251 dòng = 1 dòng tiêu đề + 250 khung hình)
- Dòng tiêu đề chuẩn, **đúng 10 cột, đúng thứ tự**:
  `giay,so_nguoi,so_mat,nguoi_quen,nam,nu,tuoi_tb,trong_vung,vi_pham,canh_lau`

---

## 5. CSV 10 cột — hợp đồng dữ liệu

| # | Tên cột | Ý nghĩa |
|---|---|---|
| 1 | `giay` | Giây thứ mấy trong video |
| 2 | `so_nguoi` | Số người trong khung hình này |
| 3 | `so_mat` | Số khuôn mặt tìm được |
| 4 | `nguoi_quen` | Tên người quen, nhiều người nối bằng ` | ` |
| 5 | `nam` | Số khuôn mặt đo là nam |
| 6 | `nu` | Số khuôn mặt đo là nữ |
| 7 | `tuoi_tb` | Tuổi trung bình trong khung hình này (rỗng nếu không đo được) |
| 8 | `trong_vung` | Số người đang ở trong vùng canh |
| 9 | `vi_pham` | 1 = có người trong vùng, 0 = không |
| 10 | `canh_lau` | Số người đứng lâu quá ngưỡng trong khung hình này |

**Mỗi dòng = 1 khung hình.** Không đổi. Không thêm cột. Không đổi tên cột. Không đổi thứ tự.
Nguồn chốt: `cam_ai_core.py:43-46` (`CSV_FIELDS`) và `cam_ai_core.py:784-787` (ghi file).

File được ghi bằng `encoding="utf-8-sig"` — tức là **có BOM**, để Excel mở tiếng Việt không lỗi. Đây là chủ ý.

---

## 6. Cấu trúc thư mục

### File mã nguồn

| File | Làm gì | Được sửa? |
|---|---|---|
| `cam_ai_core.py` | **Lõi xử lý video.** Chứa toàn bộ pipeline. Cả CLI lẫn GUI đều gọi file này | ⚠️ Agent A đang giữ |
| `app.py` | Lớp vỏ dòng lệnh — chỉ khai báo cờ rồi gọi `run_analysis()` | ⚠️ Agent A đang giữ |
| `gui.py` | Giao diện đồ hoạ (CustomTkinter) | ⚠️ Agent A đang giữ |
| `face_engine.py` | Nhận diện khuôn mặt ArcFace + bật CUDA | Không ai giữ — sửa được khi cần |
| `bao_cao_tong_ket.py` | Sinh Excel + trang HTML xem lại | Đã xong, chưa nối vào GUI |
| `canh_bao.py` | Cảnh báo Telegram + chuông Windows | ⚠️ Agent C đang giữ |
| `model_info.py` | Sổ đăng ký 4 model, tiếng Việt, cho giao diện | ✅ Xong 18/10 — **sẵn sàng nối vào GUI** |
| `ve_vung.py` | Công cụ vẽ vùng bằng chuột | Sửa được |
| `dang_ky_anh.py` | Lấy ảnh mặt từ video để đăng ký người quen | Sửa được |
| `tai_tao_model.py` | Tải lại bộ model ArcFace | Sửa được |
| `setup_models.py` | Kiểm tra GPU + tải model cơ bản | Sửa được |
| `smoke_test.py` | Kiểm tra nhanh model + GPU | ⚠️ Còn import `facenet_pytorch` cũ, xem ISSUE_LOG #10 |
| `make_test_data.py` | Tạo video test + ảnh mẫu giả | ⚠️ Tạo dữ liệu GIẢ, xem mục 8 |
| `kiem_tra_nhan_dien.py` | Đo tốc độ + độ chính xác nhận diện | Sửa được |
| `kiem_tra_video_mau.py` | Quét 9 video mẫu, đo số người | Sửa được |
| `chay_gui.bat` | Double-click mở GUI | Sửa được — xem ISSUE_LOG #6 |
| `run.bat` | Double-click chạy CLI | Sửa được |

### Thư mục

| Thư mục | Chứa gì |
|---|---|
| `.venv/` | Môi trường Python. **Không sửa, không cài thêm** |
| `models/face_core/` | 3 file `.onnx` CamAI thực sự dùng |
| `models/buffalo_l/` | Bộ model ArcFace đầy đủ (5 file). `face_core` là hardlink sang đây nên không tốn thêm dung lượng |
| `known_faces/<Tên>/*.jpg` | Ảnh mặt đã học. **Hiện chứa dữ liệu GIẢ LẬP** — xem mục 8 |
| `video_mau/` | 9 video mẫu của Intel + `_ket_qua/` kết quả chạy thử |
| `_t/` | **Thư mục tạm của agent.** Chứa ảnh chụp hồi quy `base1-3`, kết quả mới `new1-3`, thư mục clip thử |

### Tài liệu

| File | Dành cho |
|---|---|
| `PROJECT_STATE.md` | File này — **đọc đầu tiên** |
| `AGENT_CHAT.md` | Nhật ký điều phối 15/10 → 18/10, ai giữ file nào, quyết định đã chốt |
| `ISSUE_LOG.md` | Lỗi đã gặp, nguyên nhân thật, cách tránh lặp |
| `CHANGELOG.md` | Thay đổi theo phiên bản |
| `ROADMAP.md` | Chương nghiệm thu — cái nào xong, cái nào chưa |
| `README.md` | Hướng dẫn rút gọn. **Đang ghi v2.1, cũ hơn thực tế** |
| `DE_XUAT_CONG_NGHE.md` | Báo cáo nghiên cứu công nghệ, viết cho anh Tuấn |
| `HUONG_DAN_CANH_BAO.md` | Hướng dẫn cài cảnh báo Telegram, cho người chưa dùng bot |

---

## 7. Bốn model AI đang dùng

| Việc | Model | Thư viện | File | Dung lượng |
|---|---|---|---|---|
| Phát hiện người & 80 vật thể | **YOLO11n** | ultralytics 8.4.177 | `yolo11n.pt` | 5,4 MB |
| Tìm khuôn mặt | **SCRFD 10G** | insightface 2.1 | `models/face_core/det_10g.onnx` | 16,1 MB |
| **Nhận diện người quen** | **ArcFace w600k_r50** | insightface 2.1 | `models/face_core/w600k_r50.onnx` | 166,3 MB |
| Ước lượng tuổi/giới tính | **genderage** | insightface 2.1 | `models/face_core/genderage.onnx` | 1,3 MB |

Đã đo trên đúng máy này ngày 18/10/2026 (lệnh `model_info.py`) — khớp bảng.

**Cách gộp:** `face_engine.py:126-131` dùng `FaceAnalysis` của insightface 2.1 với
`allowed_modules=["detection", "recognition", "genderage"]`.
Cố ý **bỏ 2 model toạ độ 3D** (`1k3d68.onnx` 137 MB + `2d106det.onnx` 4,8 MB) vì không dùng, bỏ đi nhanh hơn nhiều.

**Ngưỡng khớp mặt mặc định: 0.40** (`face_engine.py:29`). Cao hơn = dễ nhận nhầm, thấp hơn = dễ không nhận ra.

### ⚠️ Ghi chú quan trọng: "insightface" là **BỘ** model, không phải 1 model

Chủ sở hữu đã hỏi nhầm chỗ này. `insightface` là **thư viện**; nó gói 3 file `.onnx` mà CamAI dùng.
Nói "insightface" mà không nói tên file là chưa đủ thông tin.

### ⚠️ Số version onnxruntime — máy cài SONG SONG 2 gói (không phải in sai)

`model_info.py` trước đây in ra **hai** dòng:

```
  onnxruntime          : 1.20.1
  onnxruntime-gpu      : 1.23.2
```

**Người viết tài liệu trước tưởng `model_info.py` in sai — hoá ra in ĐÚNG**, vì máy thật sự có 2 gói:

| Gói | Bản | Nằm ở đâu |
|---|---|---|
| `onnxruntime` (CPU) | 1.20.1 | `C:\Users\TTC\AppData\Roaming\Python\Python313\site-packages\onnxruntime` |
| `onnxruntime-gpu` (GPU) | **1.23.2 ← đang chạy** | `H:\AI Project\cam-ai\.venv\Lib\site-packages\onnxruntime` |

`onnxruntime.__version__` = **1.23.2**. Venv đứng trước user site trong `sys.path` nên bản GPU được nạp.
Hai gói **không chung thư mục** → hiện tại không ghi đè nhau.

Đã kiểm chứng ngày 18/10/2026. Xem ISSUE_LOG #8 (có lệnh đo và cách xử lý nếu sau này GPU chậm bất thường).

---

## 8. Dữ liệu giả lập — phải xoá trước khi dùng thật

`known_faces/An/` và `known_faces/Binh/` (mỗi người 5 ảnh `.jpg`) là **người GIẢ LẬP**,
sinh ra bởi `make_test_data.py` từ ảnh mẫu `sample_bus.jpg`.

**Phải xoá cả 2 thư mục trước khi thêm người thật.** Nếu không xoá, phần mềm sẽ nhận nhầm
người thật thành "An" hoặc "Bình".

`model_info.py` đã tự in cảnh báo này ở phần thống số, nhưng **vẫn phải xoá thật**.

---

## 9. NHỮNG CÁI BẪY KỸ THUẬT DỄ SAI NHẤT

> Đây là phần quan trọng nhất của file này. Đọc trước khi sửa bất cứ thứ gì.

### 9.1 Ba bẫy ArcFace — rơi về CPU im lặng

Trong `face_engine.py`:

| # | Bẫy | Sửa | Chỗ |
|---|---|---|---|
| 1 | `ctx_id=-1` ép CPU | Phải `prepare(ctx_id=0)` | `face_engine.py:131` |
| 2 | Nạp DLL CUDA của torch **sau** khi onnxruntime đã import | Phải nạp **trước** → hàm `_enable_cuda()` chạy ở `face_engine.py:63`, ngay khi module được import | `face_engine.py:36-67` |
| 3 | `provider_options` truyền `{}` | Phải truyền `None` | **Hiện KHÔNG có trong code** |

**Đo thật trên RTX 3090:** `ctx_id=-1` → **226 ms/khung hình** (CPU) · `ctx_id=0` → **39 ms/khung hình** (CUDA).
Nhanh gấp **5,8 lần**.

**Về bẫy số 3:** code hiện tại **không** truyền `provider_options` cho `FaceAnalysis` — chỉ truyền
`providers=self.providers` (`face_engine.py:126-130`). Có thể insightface 2.1 đã tự xử lý,
hoặc bẫy này thuộc phiên bản khác. **Cần người sau xác nhận lại** trước khi dựa vào.

**Cách kiểm tra nhanh xem đang chạy GPU hay CPU** (dán vào lệnh, in ra dòng `[model]`):

```
[model] models/face_core | GPU | detection:CUDAExecutionProvider | ...
```

Chữ `GPU` và `CUDA` là đúng. Nếu thấy `CPU` là rơi về CPU — kiểm tra lại 3 bẫy trên.

⚠️ **Thứ tự import rất dễ sai:** `cam_ai_core.py:441` cố ý import `face_engine` **trong hàm**,
không phải ở đầu file. Comment tại `cam_ai_core.py:443-445` giải thích: chuyển import lên đầu file
sẽ làm GPU chạy sai. **Đừng "tối ưu" chỗ này.**

### 9.2 PowerShell 5.1 phá file nguồn — hỏng 3 thứ cùng lúc

**TUYỆT ĐỐI KHÔNG** dùng `Get-Content ... | Set-Content` để sửa file nguồn. Nó hỏng:

1. Chèn BOM vào đầu file
2. Phá ký tự tiếng Việt: `Anh Tuấn` → `Anh Tuáº¥n`
3. Đổi CRLF → LF

⚠️ **Lưu ý về "cứu bằng git":** thư mục này **KHÔNG có `.git`** (đã kiểm 18/10/2026).
Nên câu lệnh `git checkout -- <file>` **không dùng được ở đây**. Cách cứu thật:
dùng tool `edit` / `write` để viết lại đúng nội dung UTF-8. Nếu file đã hỏng nặng
và không còn bản nào để đối chiếu → phải dựng lại từ `PROJECT_STATE.md` mục 3 + 6.

### 9.3 Quy tắc encoding và xuống dòng

| Mục | Quy tắc đúng của dự án này |
|---|---|
| Encoding | UTF-8 **có dấu**, **KHÔNG BOM** |
| Xuống dòng | **LF** (`\n`) |

Đã đo byte thật ngày 18/10/2026 trên `PROJECT_STATE.md`, `CHANGELOG.md`, `ROADMAP.md`, `README.md`,
`gui.py`, `cam_ai_core.py`, `app.py`, `face_engine.py`: **tất cả đều LF, không BOM**.

> Ghi chú: có tài liệu cũ nói quy ước là CRLF. **Không đúng với dự án này** — code thật đang dùng LF.
> Hãy làm theo LF để không tạo file lạc lõi trong repo.

Ngoại lệ duy nhất: file CSV do `cam_ai_core.py` ghi bằng `utf-8-sig` (**có BOM**) — cố ý, để Excel đọc tiếng Việt.

### 9.4 CSV phải giữ đúng 10 cột

Không thêm cột, không đổi tên, không đổi thứ tự. Xem mục 5 và `cam_ai_core.py:43-46`.

### 9.5 Vùng lưu toạ độ **tương đối 0.0–1.0**

`vung.txt` chứa 4 số thập phân. Nhân với kích thước khung hình để ra pixel.
Nhờ vậy cùng 1 file vùng dùng được cho video khác độ phân giải.

File `vung.txt` hiện tại:
```
# CamAI - vung canh (tao thu cong de test, khong dung chuot)
# Toa do tuong doi 0.0 - 1.0, dung chung cho moi video
0.2000 0.1500 0.8000 0.9500
```

Chuyển đổi xảy ra ở `cam_ai_core.py:474-477`. Hàm đọc: `load_zone()` (`cam_ai_core.py:322`).
**Đừng bao giờ lưu pixel thật vào `vung.txt`.**

### 9.6 Logic nghiệp vụ chỉ áp cho class `person`

`PERSON_CLASS_ID = 0` (`cam_ai_core.py:40`). Ở `cam_ai_core.py:542`:

```python
detections = tat_ca[tat_ca.class_id == PERSON_CLASS_ID]
```

Các logic đếm ra/vào, canh vùng, nhận diện mặt chỉ chạy trên `detections` này.

Vật thể khác (xe, chó, mèo…) nằm ở biến riêng `vat_the` (`cam_ai_core.py:549-561`) —
**chỉ vẽ khung + ghi nhãn + đếm**, không vào canh vùng.
→ **Xe chạm vùng không được tính là "người vào vùng".** Giữ nguyên nguyên tắc này.

### 9.7 Mọi module phải resolve đường dẫn theo thư mục chứa file

Dùng `pathlib.Path(__file__).resolve().parent` — mẫu đúng nằm ở `model_info.py:35`.

Không được phụ thuộc thư mục làm việc. Nếu không, chạy từ `H:\` sẽ không tìm thấy model.

### 9.8 Không được `pip install` thêm

Cấm cài `basicsr`, `realesrgan`, `torchreid` — chúng kéo NumPy/ABI cũ về và phá
Python 3.13 + NumPy 2.5.4.

**Trước khi muốn cài gì: kiểm tra đã có sẵn chưa.** Máy này đã có sẵn
6 tracker của ultralytics, `PolygonZone`, `CLAHE`. Ưu tiên cái có sẵn.

### 9.9 `onnxruntime-gpu==1.20.1` không có trên PyPI

Phải dùng **1.23.2** (đang ghim trong `requirements.txt`). Bản 1.20.1 không tồn tại trên PyPI.

### 9.10 Cảnh báo vô hại — bỏ qua được

```
FutureWarning: estimate is deprecated
Skip loading CUDA and cuDNN DLLs since torch is imported.
```

Không phải lỗi. Dòng thứ 2 là hệ quả của bẫy 9.1 số 2 (nạp DLL trước) — đang hoạt động đúng.

### 9.11 CSV KHÔNG chứa ngưỡng đông người — đây là giới hạn thật

`cam_ai_core.py` **không** ghi ngưỡng đông xuống CSV. CSV chỉ có `trong_vung` (số người trong vùng).

Hệ quả: khi đọc lại CSV, **không biết** lúc chạy anh đã đặt ngưỡng mấy.
Muốn báo cáo "số lần vượt ngưỡng" thì phải truyền thủ công:

```
.venv\Scripts\python.exe bao_cao_tong_ket.py --csv ten.csv --nguong-dong 3
```

Bỏ trống thì `bao_cao_tong_ket.py` tự lấy = **số người nhiều nhất quan sát được trong vùng**
(`max_trong_vung`). Trang HTML có ghi rõ là ngưỡng tự động.

**Đây là giới hạn thật của dữ liệu CSV, KHÔNG phải lỗi.** Muốn sửa thật thì phải đổi CSV → vi phạm mục 9.4.

### 9.12 Máy cài SONG SONG 2 gói onnxruntime — CPU 1.20.1 + GPU 1.23.2

Máy này có **2 gói onnxruntime** cùng tồn tại, nhưng **chỉ 1 cái được chạy**:

| Gói | Bản | Thư mục |
|---|---|---|
| `onnxruntime` (CPU) | 1.20.1 | user site-packages (ngoài `.venv`) |
| `onnxruntime-gpu` (GPU) | **1.23.2 ← đang chạy** | `.venv\Lib\site-packages\onnxruntime` |

- `.venv` tạo bằng `--system-site-packages` nên **nhìn thấy** gói user; venv đứng trước trong `sys.path` nên GPU thắng.
- Hai gói **không chung thư mục** → hiện tại **không** ghi đè nhau.
- Rủi ro thật: ai đó chạy `pip install onnxruntime` **trong khi `.venv` đang bật** → nó sẽ cài
  đè đúng thư mục của bản GPU, làm phần mềm **chậm lại mà không báo lỗi**.
- Muốn hiển thị "đang chạy cái gì" cho người dùng: đọc **`onnxruntime.__version__`** (module đang chạy),
  **không** đọc `importlib.metadata` — metadata chỉ nói gói có cài không.
- Nếu thấy phần mềm chậm bất thường: đo lại bằng lệnh trong ISSUE_LOG #8, rồi kiểm tra 3 bẫy ở 9.1.

---

## 10. Trạng thái công việc tại thời điểm viết

### 10.1 ĐÃ XONG & ĐÃ KIỂM CHỨNG

| Tính năng | Bằng chứng |
|---|---|
| Phát hiện & đếm người | 4 lệnh hồi quy chạy đúng |
| Nhận diện khuôn mặt + người quen | `kiem_tra_nhan_dien.py` → 500/500 mặt đúng tên |
| Ước lượng tuổi / giới tính | Video nữ → 1520 nữ / 95 nam, tuổi TB 36 |
| Cảnh báo đông người | `--vung-max 2` → `vuot 0 lan` trên video mẫu |
| Cảnh báo đứng lâu | `--canh-lau 3` → `1 lan, lan dai nhat 10.0s` |
| Canh vùng chặt + nhạy | `[vung] ... che do chac` / `che do nhay` |
| CSV 10 cột | MD5 `base1=new1`, `base2=new2`, `base3=new3` |
| Video có vẽ vùng | Mở `video_test_ket_qua.mp4` xem được |
| Làm mờ nền `--pixelate` | `cam_ai_core.py:586-595` |
| Giao diện GUI | Mở được bằng `chay_gui.bat` |
| 9 video mẫu Intel | Quét đủ 9 bằng `kiem_tra_video_mau.py` |
| Công cụ quét video mẫu | `kiem_tra_video_mau.py` |
| Báo cáo nghiên cứu công nghệ | `DE_XUAT_CONG_NGHE.md` |
| Tự lưu clip khi có sự kiện | Đã sinh 4 file clip thử ngày 18/10 17:09 trong `_t/clip/` |
| Nhận diện vật thể khác | `--nhan-vat-the` có trong `app.py --help` |
| **Báo cáo Excel + trang xem lại** | Đã chạy thật 18/10 — xem mục 11 |

### 10.2 ĐÃ XONG nhưng **CHƯA KIỂM CHỨNG BẰNG MẮT**

- **Trang HTML xem lại** — xem mục 11. Chưa ai xem bằng mắt bản render thật.
- **Tự lưu clip** — file clip đã sinh ra, nhưng chưa xác nhận thời lượng/nội dung clip có đúng 10s và đúng khoảng thời điểm sự kiện.
- **Nhận diện vật thể** — cờ có trong `--help`, nhưng chưa có ảnh chụp màn hình xác nhận khung/label đúng.

### 10.3 ĐANG CHẠY NỀN — **FILE ĐANG BỊ KHOÁ**

| Agent | Giữ file | Việc |
|---|---|---|
| **Agent A** | `cam_ai_core.py`, `app.py`, `gui.py` | (1) sửa bug "đứng lâu" (2) tự lưu clip (3) nhận diện vật thể khác |
| **Agent C** | `canh_bao.py` + `HUONG_DAN_CANH_BAO.md` | Cảnh báo Telegram (chỉ gửi chữ) + chuông Windows |
| **Agent D** | `model_info.py` | ✅ **XONG (18/10)** — sổ đăng ký 4 model + sửa hiển thị onnxruntime. **Sẵn sàng để Agent A gắn vào GUI** |

**Tính đến 18/10/2026, code trên đĩa đã thấy dấu hiệu Agent A xong phần lớn:**
`cam_ai_core.py` đã có lớp `ClipRecorder`, cờ `--tu-luu-clip` / `--nhan-vat-the`, và
bug đứng lâu **đã được sửa** (`cam_ai_core.py:635-636` gán `longest_loiter = held` — thời gian đo thật,
không còn bằng ngưỡng). 4 lệnh hồi quy đã chạy lại và **vẫn đúng**.

⚠️ Nhưng **chưa ai báo xong chính thức**. Phải hỏi Agent A rồi chạy lại 4 lệnh hồi quy
trước khi coi là nghiệm thu.

⚠️ `cam_ai_core.py:41` vẫn là `VERSION = "2.2"` — **chưa nâng lên 2.3**. Cần Agent A sửa.

### 10.4 CHƯA LÀM

| Việc | File sẽ bị đụng |
|---|---|
| Giao diện rút gọn cho người thường | `gui.py` ⚠️ Agent A |
| Panel "Thông tin model" trong GUI | `gui.py` ⚠️ Agent A | `model_info.py` đã xong — Agent A chỉ cần gọi `bang_tt_tong_hop()` |
| Nối báo cáo vào GUI (nút "Xem báo cáo") | `gui.py` ⚠️ Agent A |
| Nối cảnh báo Telegram vào GUI | `gui.py` ⚠️ Agent A, `canh_bao.py` ⚠️ Agent C |
| Nhiều vùng cùng lúc | `cam_ai_core.py` ⚠️ Agent A |
| Vạch đếm theo cửa (thay vì cứ giữa khung hình) | `cam_ai_core.py` ⚠️ Agent A |
| Giờ vàng / giờ đen | `cam_ai_core.py` ⚠️ Agent A |
| Theo dõi 1 người cụ thể | `cam_ai_core.py` ⚠️ Agent A |

### 10.5 KHÔNG LÀM ĐƯỢC / CHƯA CÓ MODEL OFFLINE

Đã tìm rất nhiều, không có model nào chạy offline tốt. Đây là **giới hạn thật**, không phải thiếu cố gắng:

| Tính năng | Vì sao không làm được |
|---|---|
| Hút thuốc | YOLO11 chỉ biết "người", không biết hành động |
| Rút súng | Cần model chuyên dụng hoặc tự huấn luyện |
| Đeo mặt nạ | Tương tự |
| Nhận dạng hành vi theo video | Cần model hành vi + ReID |
| Làm nét ảnh ban đêm | Cần model khử nhiễu, chưa có sẵn và không cài được |

Cần model chuyên dụng hoặc tự huấn luyện. **Không hứa với anh là sẽ làm được.**

---

## 11. Báo cáo Excel + trang xem lại video (`bao_cao_tong_ket.py`)

Phiên bản nội bộ: `PHIEN_BAN = "1.0"` (`bao_cao_tong_ket.py:52`).

### 11.1 File 1 — Excel `.xlsx`, 3 sheet

Tên sheet (tiếng Việt không dấu để mọi Windows mở được), `bao_cao_tong_ket.py:64-66`:

| Sheet | Nội dung |
|---|---|
| `Tong ket` | Chỉ số tổng: số khung hình, giây đông nhất, TB/max/min người, số lần sự kiện |
| `Theo gio` | Gom nhóm theo **phút** (60 giây) — xem nhanh theo từng đoạn |
| `Cu theo giay` | Từng giây một dòng, để anh tự vẽ đồ thị |

Cả 3 sheet đều có `freeze_panes = 'A5'` (đóng băng 4 dòng tiêu đề) và `autofilter`.
Đã kiểm chứng bằng openpyxl ngày 18/10/2026:

```
sheet=Tong ket         dims=A1:D23  freeze=A5  autofilter=A4:D23
sheet=Theo gio         dims=A1:F5   freeze=A5  autofilter=A4:F5
sheet=Cu theo giay    dims=A1:H14  freeze=A5  autofilter=A4:H14
```

Có màu: tiêu đề nền xanh đậm `1F4E79` chữ trắng, dòng nhóm mục `DDEBF7`, dòng ghi chú `F2F7FC` (`bao_cao_tong_ket.py:73-77`).

Chỉ cần thêm 1 thư viện: `openpyxl` (đã cài, bản 3.1.5). **Không cần matplotlib, không cần Internet.**

### 11.2 File 2 — 1 trang HTML xem lại, offline 100%

Đã kiểm chứng ngày 18/10/2026 bằng cách đếm trong file sinh ra:

| Kiểm tra | Kết quả | Ý nghĩa |
|---|---|---|
| Số tham chiếu `https://` | **0** | Không gọi Internet |
| Số tham chiếu `http://` | **0** | Không gọi Internet |
| `fetch(` hoặc `XMLHttpRequest` | **0** | Không gọi API nào |
| Thẻ `<canvas>` | 1 | Biểu đồ vẽ bằng Canvas thuần |

Cách nó hoạt động:

- Video được nhúng bằng **đường dẫn tương đối** tính từ thư mục chứa file HTML
  (`bao_cao_tong_ket.py:963-980`). Nếu video ở ổ đĩa khác thì mới dùng `file:///`.
  → **Phải giữ video cùng thư mục với file HTML**, nếu không sẽ không mở được video.
- Biểu đồ vẽ bằng Canvas thuần, bấm vào điểm nào thì nhảy video tới giây đó.
- Nút lớn nhảy tới giây đông nhất.
- Danh sách sự kiện bấm được.
- Có dải "thẻ số liệu" ở đầu trang.

Giới hạn an toàn: `TOI_DA_DONG_HTML = 400` sự kiện, `TOI_DA_GIAY_CHI_TIET = 20000` dòng
(`bao_cao_tong_ket.py:80-81`) — tránh làm treo máy.

### 11.3 Ý nghĩa số liệm — đọc kỹ trước khi báo cáo cho anh

`vi_pham` và `canh_lau` trong CSV là **cờ 0/1 trên từng khung hình**.
"Số lần" trong báo cáo = **số lần LIÊN TIẾP** — một lần vào vùng tính 1 lần,
đứng yên 5 giây vẫn chỉ là 1 lần. Đúng y như `app.py` đếm.

### 11.4 ⚠️ ĐIỂM CHƯA KIỂM CHỨNG

**Chưa ai xem bằng mắt bản render thật của trang HTML.**
Agent trước kiểm bằng `node --check` + `html.parser` + mở trình duyệt thật.
Phần này em cũng chỉ kiểm được mức "file tự chứa, không gọi Internet".

→ **Việc cần người sau làm: mở `video_test_xem_lai.html` bằng trình duyệt và xác nhận
bấm vào biểu đồ có nhảy video, nút lớn có nhảy đúng giây, danh sách sự kiện bấm được.**

Cũng chưa xác nhận: nút lớn, màu sắc, độ dễ đọc với người không rành công nghệ.

### 11.5 Lệnh đã chạy thật ngày 18/10/2026

```powershell
.venv\Scripts\python.exe bao_cao_tong_ket.py --csv video_test_bao_cao.csv --video video_test_ket_qua.mp4 --xuat _t\kt
```

Ra đủ 2 file:
```
_t\kt\video_test_tong_ket.xlsx     (3 sheet: Tong ket, Theo gio, Cu theo giay)
_t\kt\video_test_xem_lai.html
```

---

## 12. Việc tiếp theo (checklist)

Ưu tiên cao trước.

| # | Việc | File sẽ bị đụng | Ghi chú |
|---|---|---|---|
| 1 | **Hỏi Agent A xong chưa, chạy lại 4 lệnh hồi quy** | không sửa file | Chạy lệnh ở mục 4 + so MD5 `base` với `new` |
| 2 | Nâng `VERSION` trong `cam_ai_core.py` lên `"2.3"` | `cam_ai_core.py` ⚠️ Agent A | Hiện vẫn là `"2.2"` |
| 3 | Làm lại GUI cho người thường + panel "Thông tin model" | `gui.py` ⚠️ Agent A, `model_info.py` ⚠️ Agent D | Đọc `model_info.py:250` `bang_tt_tong_hop()` |
| 4 | Nối `bao_cao_tong_ket.py` vào GUI (nút "Xem báo cáo") | `gui.py` ⚠️ Agent A | Chạy như subprocess, xem `gui.py:643` cách gọi `ve_vung.py` |
| 5 | Nối `canh_bao.py` vào GUI | `gui.py` ⚠️ Agent A, `canh_bao.py` ⚠️ Agent C | Chỉ gửi chữ |
| 6 | Xem bằng mắt trang HTML xem lại | không sửa file | Mục 11.4 |
| 7 | Xoá `known_faces/An` và `known_faces/Binh` khi dùng thật | `known_faces/` | Mục 8 |
| 8 | ~~Sửa hiển thị version onnxruntime trong `model_info.py`~~ | — | ✅ **XONG 18/10** — in 1 dòng `onnxruntime-gpu` đang chạy thật. Xem ISSUE_LOG #8 |
| 9 | Dọn file tạm | `_t/`, `_t_canh_bao_thu.py`, `_t_canh_bao.ini` | Xem ghi chú bên dưới |
| 10 | Cập nhật `README.md` (đang ghi v2.1) | `README.md` | Không ai giữ |
| 11 | Roadmap còn lại | xem `ROADMAP.md` | |

### Ghi chú về file tạm — đã kiểm tra ngày 18/10/2026

| File | Trạng thái |
|---|---|
| `_bt` | **KHÔNG còn** (đã xoá) |
| `_t_canh_bao_thu.py` | **CÒN** — 9.455 byte, file thử của Agent C |
| `_t_canh_bao.ini` | **CÒN** — 74 byte, file cấu hình thử |
| `_t/` | **CÒN** — 22 file + 4 clip thử. Có `base1-3` (ảnh chụp hồi quy) **nên giữ lại** |
| `_t/kt/` | **CÒN** — do em tạo lúc kiểm chứng mục 11. Có thể xoá |

⚠️ **Không tự ý xoá `_t_canh_bao.*`** — thuộc Agent C.

⚠️ `smoke_test.py` vẫn còn import `facenet_pytorch` (thư viện đã bị thay bằng ArcFace) và
`urllib.request` tải ảnh từ Internet. File này **gần như chắc chắn sẽ lỗi** nếu chạy.
Xem ISSUE_LOG #10.

---

## 13. Lịch sử thay đổi theo ngày

| Ngày | Việc | Kết quả |
|---|---|---|
| 15/10/2026 | Dựng nền: `app.py` phát hiện người + đếm người + đếm ra/vào bằng YOLO11n + LineZone | Chạy được trên `video_test.mp4` |
| 15/10/2026 | Tạo video test + 2 người giả lập (An, Binh) bằng `make_test_data.py` | Có dữ liệu để thử nhận diện |
| 16/10/2026 | Nhận diện mặt chuyển từ facenet-pytorch → **ArcFace (SCRFD + w600k_r50)** | 500/500 mặt đúng tên (bản cũ chỉ 43/463) |
| 16/10/2026 | Sửa 3 bẫy ArcFace, bật được CUDA | 226 ms → 39 ms/khung hình, nhanh gấp 5,8 lần |
| 16/10/2026 | Thêm ước lượng tuổi/giới tính (genderage) | Video nữ → 1520 nữ / 95 nam, tuổi TB 36 |
| 17/10/2026 | Tách lõi `cam_ai_core.py` ra khỏi `app.py` | CLI và GUI dùng chung một pipeline |
| 17/10/2026 | Làm giao diện GUI bằng CustomTkinter + `chay_gui.bat` | Mở được, không cần gõ lệnh |
| 17/10/2026 | Vẽ vùng `ve_vung.py`, lưu toạ độ tương đối 0.0–1.0 | Vùng dùng lại được cho video khác độ phân giải |
| 17/10/2026 | Cảnh báo vào vùng (chặt + nhạy), `--vung-max`, `--canh-lau` | Dòng chuẩn `[vung] 192,81 -> 768,513 \| che do chac` |
| 18/10/2026 | Thêm 9 video mẫu Intel + `kiem_tra_video_mau.py` | Quét đủ 9 video, đo được số người từng video |
| 18/10/2026 | Báo cáo nghiên cứu công nghệ `DE_XUAT_CONG_NGHE.md` | Xong |
| 18/10/2026 | Viết `bao_cao_tong_ket.py` — Excel 3 sheet + trang HTML offline | Chạy thật, ra đủ 2 file. **Chưa xem bằng mắt** |
| 18/10/2026 | Agent C: `canh_bao.py` + `HUONG_DAN_CANH_BAO.md` | Telegram (chỉ gữi chữ) + chuông Windows |
| 18/10/2026 | Agent D: `model_info.py` — sổ đăng ký 4 model tiếng Việt | In ra bảng 4 model, có cảnh báo dữ liệu giả lập |
| 18/10/2026 | Agent A: sửa bug đứng lâu + tự lưu clip + nhận diện vật thể | Code đã trên đĩa, 4 lệnh hồi quy vẫn đúng. **Chưa báo xong** |
| 18/10/2026 | Viết lại toàn bộ tài liệu bàn giao (file này + 4 file kia) | Hoàn tất |
| 18/10/2026 | Sửa `model_info.py` + đính chính ISSUE_LOG #8 + thêm bẫy 9.12 | Chẩn đoán cũ "in sai" **sai** — thật ra máy cài song song CPU 1.20.1 + GPU 1.23.2. `model_info.py` nay in **1 dòng** + ghi chú |

---

## 14. Số version trong code — CẦN SỬA

`cam_ai_core.py:41` → `VERSION = "2.2"`
`README.md` → ghi **v2.1**
`ROADMAP.md` → ghi **v2.2**

Thực tế đã có code v2.3 (tự lưu clip, nhận diện vật thể) nhưng **số version chưa được nâng**.
Người sau làm việc: **nâng `VERSION` lên `"2.3"` trước**, rồi cập nhật `README.md`.