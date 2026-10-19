# AGENT_CHAT — CamAI · Nhật ký điều phối

> Nhật ký 15/10/2026 → 18/10/2026: ngày nào làm gì, ai giữ file nào, kết quả kiểm chứng,
> và **những quyết định đã chốt — KHÔNG mở lại**.
>
> Người đọc file này: phiên làm việc SAU ĐÓ, và cả các agent chạy song song.

---

## 0. Cách đọc file này

| Bạn là | Đọc mục nào |
|---|---|
| Phiên làm việc mới | Mục 2 (quyết định đã chốt) → mục 5 (file đang bị khoá) → `PROJECT_STATE.md` |
| Agent mới nhận việc | Mục 5 để biết file nào **đã có người giữ**, **đừng sửa** |
| Ai đó đang nghi ngờ phá vỡ thứ gì | Mục 2 — có thể hỏi lại quyết định này không |

**Nguyên tắc phối hợp:** mỗi agent **giữ riêng một nhóm file**. Không sửa file của agent khác,
kể cả khi thấy sai — hãy ghi vào `ISSUE_LOG.md` rồi báo lại.

---

## 1. Nhật ký theo ngày

### 15/10/2026 — Ngày 1 · Dựng nền

**Làm gì**
- Viết `app.py` đầu tiên: YOLO11n phát hiện người → đếm người (ByteTrack) → đếm ra/vào (LineZone).
- Viết `make_test_data.py` sinh `video_test.mp4` + ảnh mặt giả cho 2 người "An", "Bình".

**Quyết định**
- Không deploy Internet, mọi thứ chạy local.
- Làm CLI trước để nghiệm thu được bằng số, GUI làm sau.

**Kết quả**
`app.py --input video_test.mp4` chạy được, ra video có khung + file CSV.

---

### 16/10/2026 — Ngày 2 · Nâng nhận diện mặt lên ArcFace

**Vấn đề phát hiện**
Bộ cũ (facenet-pytorch: MTCNN + InceptionResnetV1) **rất kém**:
463 mặt tìm thấy nhưng chỉ rút đúng tên **43** lần, và **bỏ sót** 1 người trong 2 người quen.

**Quyết định**
- Thay bằng **ArcFace** của insightface 2.1: SCRFD 10G (dò mặt) + w600k_r50 (nhận diện) + genderage.
- Gỡ `facenet-pytorch`.

**Kết quả đo thật**

| Chỉ số | Bộ cũ | ArcFace |
|---|---|---|
| Tổng số mặt | 463 | 500 |
| Rút đúng tên | 43 | **500** |
| Người nhận đúng | An (bỏ sót Bình) | **An + Bình** |
| Tốc độ | 226 ms/khung hình | **39 ms/khung hình** |

**3 bẫy ArcFace đã mắc phải** → ghi đầy đủ ở `ISSUE_LOG.md` #4.
Tóm tắt: `ctx_id=0` (không phải -1) · nạp DLL CUDA của torch **trước** khi onnxruntime được import ·
`provider_options` phải là `None` chứ không phải `{}`.

**Người hỏi nhầm:** chủ sở hữu hỏi "insightface là model gì?". Đã giải thích:
insightface là **bộ** model gồm nhiều file, không phải 1 model. Ghi lại trong `PROJECT_STATE.md` mục 7.

---

### 17/10/2026 — Ngày 3 · Tách lõi + làm GUI + cảnh vùng

**Tách lõi `cam_ai_core.py`**
Trước đó toàn bộ pipeline nằm trong `app.py`. GUI cần gọi lại pipeline đó nhưng
không được sửa logic → tách ra `cam_ai_core.py`.

Hệ quả bắt buộc: **mọi thay đổi phải qua 4 lệnh hồi quy** (xem `PROJECT_STATE.md` mục 4).

**Giao diện GUI**
- Dùng **CustomTkinter** — đã có sẵn trong môi trường, **không cài thêm**.
- `chay_gui.bat` để anh double-click.
- Pipeline chạy ở thread riêng, GUI không bị treo.

**Cảnh vùng**
- `ve_vung.py` vẽ vùng bằng chuột.
- Lưu **toạ độ tương đối 0.0–1.0** để dùng lại cho mọi độ phân giải.
- 2 chế độ: **chặt** (tâm người nằm trong vùng) và **nhạy** (chỉ cần chạm).
- Thêm `--vung-max` (đông) và `--canh-lau` (đứng lâu).

**Chốt:** vạch đếm ra/vào cố ý **ở giữa khung hình**. Sau này có thể đổi thành vạch theo cửa.

---

### 18/10/2026 — Ngày 4 · Bổ sung bộ kiểm thử + chia việc cho 4 agent

**Sáng — bổ sung năng lực kiểm thử**
- Thêm **9 video mẫu Intel** vào `video_mau/` (chỉ đủ tình huống) + công cụ `kiem_tra_video_mau.py`.
- Viết `DE_XUAT_CONG_NGHE.md` — báo cáo nghiên cứu, viết cho anh Tuấn.
- Viết `bao_cao_tong_ket.py` — Excel 3 sheet + trang HTML xem lại.

**Chiều — chia việc cho 4 agent chạy nền**

| Agent | Giữ file | Việc |
|---|---|---|
| **A** | `cam_ai_core.py`, `app.py`, `gui.py` | Sửa bug "đứng lâu" · tự lưu clip · nhận diện vật thể |
| **C** | `canh_bao.py` + `HUONG_DAN_CANH_BAO.md` | Cảnh báo Telegram (chỉ gửi chữ) + chuông Windows |
| **D** | `model_info.py` | Sổ đăng ký 4 model tiếng Việt cho giao diện |
| **Tài liệu** | 5 file `.md` | Viết lại toàn bộ tài liệu bàn giao (chính là file này) |

**Agent A tiến triển trong ngày** — code đã có trên đĩa:
- Lớp `ClipRecorder` + cờ `--tu-luu-clip`, `--clip-giay`, `--clip-ghi-tat-ca`
- Cờ `--nhan-vat-the`, `--lop`
- Bug "đứng lâu" **đã sửa** (`cam_ai_core.py:635-636`)

**Kiểm chứng lại ngày 18/10 (4 lệnh hồi quy):**

| Kiểm tra | Kết quả |
|---|---|
| Lệnh 1 — chặt + đông + đứng lâu | `[vung] 192,81 -> 768,513 \| che do chac \| toi da 2 nguoi \| canh dung lau 3.0s` ✅ |
| Số người nhiều nhất trong vung | `2` ✅ |
| Số lần có người vào vùng | `1` ✅ |
| Cảnh báo đứng lâu | `Dung lau hon 3.0s: 1 lan, lan dai nhat 10.0s` — **10.0s là đo thật, bug đã hết** ✅ |
| MD5 `base1` vs `new1` | **trùng** ✅ |
| MD5 `base2` vs `new2` | **trùng** ✅ |
| MD5 `base3` vs `new3` | **trùng** ✅ |
| CSV | đúng **10 cột** ✅ |

⚠️ **Nhưng chưa ai báo xong chính thức.** Phải hỏi Agent A rồi chạy lại hồi quy một lần nữa.

**Tối (22:30) — Định hướng & Khởi tạo SPEC Nhận diện vật thể (Object Detection)**
- **Yêu cầu từ anh Tuấn:** Tạm thời tập trung vào xử lý **File video** hoặc **Stream camera đơn (Webcam / RTSP)** để nhận diện vật thể mượt mà, **chưa cần** kết nối hệ thống camera chuyên nghiệp (NVR nhiều kênh).
- **Hành động:** Tạo tài liệu đặc tả chuẩn `SPEC_OBJECT_DETECTION.md` phân công rõ ràng trách nhiệm cho Agent Lõi (Core), Agent Giao diện (UI) và Agent Dữ liệu (Export).

---

## 2. QUYẾT ĐỊNH ĐÃ CHỐT — KHÔNG MỞ LẠI

> 10 quyết định dưới đây đã bàn rồi và chốt. Đừng mở lại trừ khi anh Tuấn nói rõ.

### Q1 · Giữ nguyên đúng 10 cột CSV

CSV là **hợp đồng dữ liệu**. Không thêm cột, không đổi tên, không đổi thứ tự.
Lý do: mọi báo cáo cũ và mọi công cụ đọc CSV đều dựa trên đúng 10 cột này.

```
giay,so_nguoi,so_mat,nguoi_quen,nam,nu,tuoi_tb,trong_vung,vi_pham,canh_lau
```

Hệ quả **chấp nhận được**: CSV không lưu ngưỡng đông → phải truyền `--nguong-dong` khi làm báo cáo.
Đây là giới hạn được biết, không phải lỗi cần sửa (`ISSUE_LOG.md` #12).

### Q2 · Tách lõi `cam_ai_core.py` — CLI và GUI dùng chung một pipeline

Lý do: GUI và CLI phải cho ra **cùng một kết quả**. Nếu mỗi bên có pipeline riêng,
sẽ có lúc chúng lệch nhau mà không ai biết.

Hệ quả bắt buộc: **4 lệnh hồi quy** phải chạy sau mọi thay đổi (`PROJECT_STATE.md` mục 4).

### Q3 · Chuyển từ web sang GUI Windows, dùng CustomTkinter

Đã cân nhắc làm web app nhưng **bỏ**. Lý do:
- Anh Tuấn không rành công nghệ, mở trình duyệt + địa chỉ web làm khó dùng
- Chạy local thì web vẫn cần server → thêm phần phải bảo trì
- CustomTkinter **đã có sẵn** trong môi trường → không cài gì thêm

### Q4 · KHÔNG làm app điện thoại

Đã hỏi và được trả lời: **không làm**.

### Q5 · KHÔNG làm camera điện thoại qua browser

Lý do kỹ thuật: truy cập camera qua trình duyệt **bắt buộc phải có HTTPS**.
Không chạy server Internet → không làm được. Anh Tuấn đã đồng ý bỏ.

### Q6 · Cảnh báo Telegram CHỈ gửi chữ, tuyệt đối không gửi hình/video lên cloud

Không phải sở thích — đây là **ranh giới dữ liệu** của dự án.
Gửi hình/video lên cloud là vi phạm nguyên tắc "không đưa dữ liệu ra ngoài máy".

Kênh phụ: chuông + hộp thoại ngay trên máy thì không cần Internet.

### Q7 · Trang xem lại HTML phải chạy offline 100% (`file://`)

Đã kiểm chứng: **0** tham chiếu `https://`, **0** tham chiếu `http://`, **0** lệnh `fetch`.
Biểu đồ vẽ bằng **Canvas thuần** — không dùng thư viện vẽ ngoài.

Video nhúng bằng **đường dẫn tương đối** → phải giữ video cùng thư mục với file HTML.

### Q8 · Vùng lưu toạ độ tương đối 0.0–1.0

Khoanh 1 lần, dùng lại được cho video khác độ phân giải và khác góc quay
(chỉ cần cùng khu vực cần canh). Nhân với kích thước khung hình để ra pixel.

**Không bao giờ lưu pixel thật vào `vung.txt`.**

### Q9 · Ưu tiên thứ máy đã có sẵn trước khi cân nhắc cài mới

Máy đã có sẵn: 6 tracker của ultralytics · `PolygonZone` · `CLAHE`.
Và **không được `pip install` thêm** (`ISSUE_LOG.md` #5) — cài `basicsr`/`realesrgan`/`torchreid`
sẽ phá Python 3.13 + NumPy 2.5.4.

### Q10 · Chỉ gọi tính năng là "xong" khi có bằng chứng chạy thật

Không tính là xong khi mới chỉ đọc code.
Ba mức phải phân biệt rõ: *chạy được* → *kiểm tự động pass* → *đã xem bằng mắt*.

**Không vẽ vời.** Nếu chưa kiểm chứng bằng mắt thì phải ghi rõ là chưa kiểm chứng bằng mắt.

### Q11 · Tập trung nhận diện vật thể File Video & Stream Camera đơn (Webcam/RTSP đơn), KHÔNG làm NVR chuyên nghiệp

Quyết định theo yêu cầu của anh Tuấn (18/10/2026):
- Ưu tiên trải nghiệm mượt mà, trực quan khi nhận diện vật thể từ video file hoặc camera/RTSP stream đơn.
- Không kết nối hệ thống NVR camera chuyên nghiệp đa kênh (8-16-32 cam), không quản lý hạ tầng phức tạp.
- Chi tiết xem tại `SPEC_OBJECT_DETECTION.md`.

---

## 3. Những gì đã bị loại khỏi kế hoạch

| Ý tưởng | Vì sao bị loại |
|---|---|
| App điện thoại | Anh Tuấn không cần |
| Camera điện thoại qua browser | Bắt buộc phải có HTTPS → không làm được local |
| Web app chạy trên trình duyệt | Khó dùng với người không rành công nghệ + cần server |
| Thêm cột "ngưỡng" vào CSV | Phá quyết định Q1 |
| Cài `tkinterdnd2` để kéo-thả file | Không được `pip install` thêm (Q9) |
| Nhận diện hút thuốc / rút súng / đeo mặt nạ | Không có model offline. Cần model chuyên dụng hoặc tự huấn luyện |
| Làm nét ảnh ban đêm | Tương tự — chưa có model |

---

## 4. Bài học rút ra trong 4 ngày

1. **Phân biệt "chạy được" với "đúng"**: nhiều lỗi chỉ lộ ra khi đo số (bug đứng lâu in ra
   đúng bằng ngưỡng — nhìn bằng mắt thì tưởng đúng vì nó là một con số hợp lý).
2. **Số liệu nền phải lưu lại**: 3 file `base*.csv` trong `_t/` là chuẩn so sánh.
   Không có chúng thì "không phá gì" chỉ là cảm giác.
3. **Một quyết định kiến trúc tiết kiệm hàng giờ**: tách `cam_ai_core.py` sớm đã giữ
   cho GUI và CLI không lệch nhau suốt 4 ngày.
4. **Đừng sửa file bằng PowerShell** (`ISSUE_LOG.md` #3) — hỏng 3 thứ cùng lúc.
5. **Đừng coi giới hạn là bug**: CSV không có ngưỡng là quyết định Q1, sửa nó sẽ phá nhiều thứ hơn nó giúp.

---

## 5. File đang bị KHOÁ — không sửa khi chưa bàn giao

Kiểm tra ngày **18/10/2026**.

| Agent | Giữ file | Trạng thái |
|---|---|---|
| **A** | `cam_ai_core.py` · `app.py` · `gui.py` | Code đã trên đĩa, hồi quy pass. **Chưa báo xong** |
| **C** | `canh_bao.py` · `HUONG_DAN_CANH_BAO.md` | Có trên đĩa. Chưa nối vào GUI |
| **D** | `model_info.py` | Có trên đĩa, chạy được. Chưa nối vào GUI |

**Không ai giữ — ai cũng sửa được:**

`face_engine.py` · `bao_cao_tong_ket.py` · `ve_vung.py` · `dang_ky_anh.py` · `tai_tao_model.py` ·
`setup_models.py` · `kiem_tra_nhan_dien.py` · `kiem_tra_video_mau.py` ·
`chay_gui.bat` · `run.bat` · `vung.txt` · `README.md` · toàn bộ file `.md`

**Tuyệt đối không sửa (dữ liệu):** mọi thứ trong `models/`, `known_faces/`, `video_mau/`

**File tạm của agent khác — đừng xoá:**

| File | Của ai |
|---|---|
| `_t_canh_bao_thu.py` | Agent C |
| `_t_canh_bao.ini` | Agent C |

**Thư mục `_t/`** chứa ảnh chụp hồi quy `base1-3` — **nên giữ lại**, đó là chuẩn so sánh.

---

## 6. Việc chưa ai làm

| Việc | File sẽ bị đụng |
|---|---|
| Nâng `VERSION` lên `"2.3"` (`cam_ai_core.py:41` vẫn là `"2.2"`) | `cam_ai_core.py` ⚠️ Agent A |
| Hỏi Agent A xong chưa, chạy lại 4 lệnh hồi quy | không sửa file |
| **Xem bằng mắt trang HTML xem lại** | không sửa file |
| Xác nhận clip tự lưu đúng 10s, đúng quanh sự kiện | không sửa file |
| Sửa hiển thị version onnxruntime (`ISSUE_LOG.md` #8) | `model_info.py` ⚠️ Agent D |
| Nối báo cáo + cảnh báo + thông tin model vào GUI | `gui.py` ⚠️ Agent A |
| Làm lại GUI cho người không rành công nghệ | `gui.py` ⚠️ Agent A |
| Cập nhật `README.md` (đang ghi v2.1, thực tế đã v2.3) | `README.md` |
| Xoá `known_faces/An` + `known_faces/Binh` khi dùng thật | `known_faces/` |
| Viết lại `smoke_test.py` (`ISSUE_LOG.md` #10) | `smoke_test.py` |
| Đổi `chay_gui.bat` sang `pythonw.exe` (`ISSUE_LOG.md` #6) | `chay_gui.bat` |
| Test trên **video thật** của chủ sở hữu (`ISSUE_LOG.md` #9) | không sửa file |

---

## 7. Bàn giao

Phiên làm việc sau bắt đầu bằng:

1. Đọc `PROJECT_STATE.md` (bắt buộc, dòng đầu tiên ghi rõ điều này)
2. Đọc mục 5 ở trên để biết file nào đang bị khoá
3. Đọc `ISSUE_LOG.md` mục 9 và 11 — 2 giới hạn thật cần nói với anh Tuấn
4. Chạy 4 lệnh hồi quy (`PROJECT_STATE.md` mục 4) để xác nhận nền vẫn vững **trước khi** sửa gì
5. Làm việc, rồi cập nhật `CHANGELOG.md` + `PROJECT_STATE.md` + `ROADMAP.md` + `ISSUE_LOG.md`