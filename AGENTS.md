# AGENTS.md — làm việc trong repo CamAI

> Đọc file này **trước khi sửa bất cứ thứ gì**. Nó là "bộ nhớ làm việc" của dự án.
> Mọi thứ ở đây đã được **kiểm chứng bằng số đo thật** — đừng phải đoán lại.

**CamAI v3.7** · `VERSION` nằm trong `cam_ai_core.py` · nhánh `master` · repo **public**
`https://github.com/handsomecat101/cam-ai`

---

## 1. Dự án này là gì

App **detect đa thể loại**, chạy **100% local** (không cloud, không tunnel, không gửi ảnh ra
ngoài). Nhận 3 loại nguồn: **file video** · **ảnh tĩnh** · **quay video/camera** (webcam `0`
hoặc camera IP `rtsp://`). Trả về **ảnh đã vẽ khung** + **báo cáo CSV** + số đếm.

### 3 nguyên tắc sản phẩm đã chốt — KHÔNG MỞ LẠI
1. **CamAI = máy detect đa thể loại** — mục tiêu: detect được **càng nhiều thể loại càng tốt**.
2. **Ứng dụng chấm công → TÁCH RA APP RIÊNG** (dùng chung `face_engine.py` + `known_faces/`).
   CamAI lo **DETECT**, app kia lo **nghiệp vụ + dữ liệu**.
3. **Đổi nền tảng GUI (PySide6/Qt) → LÀM SAU**, khi đã chốt phạm vi tính năng, để viết lại
   **một lần cho đủ**. Nếu làm thì dựng **song song**, giữ bản cũ dự phòng.

Chi tiết: `PROJECT_STATE.md` mục 0 + mục 3, `USE_CASE.md` mục 0 + 3.1.

---

## 2. Đọc gì, theo thứ tự

| # | File | Vì sao |
|---|---|---|
| 1 | `AGENTS.md` (file này) | quy tắc + bất biến + lệnh |
| 2 | `PROJECT_STATE.md` mục **0** (định hướng), **2** (ĐÃ ĐẠT / CHƯA ĐẠT), **3** (quyết định đã chốt), **4** (cách chạy + kiểm chứng), **6** (gotcha), **9** (lịch sử) | bộ nhớ dài hạn của dự án |
| 3 | `ISSUE_LOG.md` | lỗi đã biết — **đọc trước khi sửa** để không phát minh lại |
| 4 | `CHANGELOG.md` | thay đổi gì, bằng chứng ra sao |
| 5 | `ROADMAP.md` | việc đã xong / việc tiếp theo / việc chờ anh |

---

## 3. BẤT BIẾN — đo được, đừng phá

| Bất biến | Giá trị | Kiểm bằng |
|---|---|---|
| **Số checkbox trong GUI** | **20** | `_kk_kiem_khong_mat_tinh_nang.py` |
| **Số nhóm con** | **12** | idem |
| **Số thẻ "Video mẫu dùng thử"** | **13** | idem |
| **Cột CSV khi tính năng mới TẮT** | **10 cột**, đúng tên cũ | `_kk_kiem_chuc_nang.py` |
| **Cột CSV khi bật đếm phương tiện** | **14 cột** (10 cũ + 4 mới **ở CUỐI**) | idem |
| **Dòng CSV khi tắt tính năng mới** | **251 dòng**, SHA256 **giống hệt** bản gốc | `_kk_kiem_nguon_viet.py` |
| **Bảng lớp COCO ↔ tiếng Việt** | **80 lớp**, khớp **100%** `detector.names` | `_kk_kiem_lop_viet.py` |
| **Chuỗi hiển thị mới** | phải có **bản dịch Anh** trong `DICH_VI_EN` (trong `gui.py`) | `_kk_kiem_ngon_ngu_v3_3.py` |
| **File tiếng Việt** | **UTF-8 không BOM**, **LF** (CR = 0) | mục 4.5 của `PROJECT_STATE.md` |

> Cột CSV **chỉ thêm ở CUỐI**, không thêm xen giữa — đã dùng ở nhiều nơi, đổi là vỡ tương thích.

---

## 4. Quy tắc bắt buộc khi sửa code

1. **Chạy Python CHỈ bằng** `H:\AI Project\cam-ai\.venv\Scripts\python.exe` (hoặc `.venv\Scripts\python.exe`
   tương đối). **TUYỆT ĐỐI KHÔNG** dùng `python` trong PATH — sẽ thiếu module.
2. **Encoding**: file tiếng Việt = **UTF-8 không BOM + LF**. Dùng tool sửa file (`edit`/`write`).
   **KHÔNG** dùng `Get-Content | Set-Content` (thêm BOM, đổi CRLF, phá tiếng Việt).
3. **Tiếng Việt**: chuỗi **hiển thị** cho người dùng → **có dấu**. **Comment / docstring trong code**
   → **KHÔNG dấu**. Mọi chuỗi hiển thị mới → **kèm bản dịch Anh** trong `DICH_VI_EN`.
4. **Không thêm dependency** ngoài: `rapidocr-onnxruntime`, `easyocr`, `pillow`, `opencv`,
   `numpy`, `ultralytics`, `onnxruntime`, `customtkinter`, `torch`, `insightface`, `supervision`,
   `openpyxl`, `pywin32`.
5. **Không hardcode token / mật khẩu.**
6. **Mỗi tính năng mới mặc định TẮT** → hành vi cũ không đổi khi không bật.
7. **1 nguồn sự thật cho mỗi quy tắc.** Không copy logic chọn lớp / dịch chuỗi vào nhiều nơi —
   đã xảy ra 1 lần: GUI viết lại logic chọn lớp ⇒ gõ "ô tô" thì báo cáo có nhưng khung xem
   trực tiếp **không vẽ khung nào**.
8. **Không sửa lõi chỉ để phục vụ wrapper.** Nếu bottleneck ở lõi thì **báo rõ**, không lách.
9. **Sửa file GUI**: giữ nguyên số widget/bất biến ở mục 3. Chụp ảnh kiểm chứng theo mẫu:
   `attributes("-topmost", True)` → `lift()` → `GetAncestor(id, 2)` → `GetWindowRect` →
   `ImageGrab.grab(bbox, all_screens=True)` (xem `_kk_chup_cua_so.py`).
10. **Kiểm tra lỗi thị giác bằng ảnh phóng to 3×** (`_kk_phong_to.py`). Nhìn ở 100% sẽ bỏ sót.
    → Đã bỏ sót 1 lỗi: mũi tên mục lớn sai trạng thái (có từ bản 3.6).

### Khi làm việc với nhiều agent (sub-agent)
- **Mỗi agent sở hữu file riêng, không sửa chồng.**
  - agent GUI → `gui.py`, `gui_khung.py`, `ve_vung_gui.py`
  - agent lõi → `cam_ai_core.py`, `app.py`, `canh_bao.py`, `lop_viet.py`, `face_engine.py`
  - coordinator → `.md` + script `_kk_*`
- **Coordinator KHÔNG tự viết/sửa code nguồn** — giao sub-agent, rồi **tự chạy lại lệnh kiểm
  chứng** và **tự xem ảnh bằng mắt**. **Không tin báo cáo của agent.**
- Agent nào báo *"tôi không sửa được file X vì agent khác đang giữ"* → đó là tín hiệu **phải
  giao vòng sửa tiếp**, không được bỏ qua.

---

## 5. Lệnh kiểm chứng (copy-paste được)

```powershell
$env:PYTHONIOENCODING='utf-8'
$py='H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$app='H:\AI Project\cam-ai'

& $py -W ignore "$app\_kk_kiem_nguon_viet.py"        # 35/35 - lop tieng Viet + dem phuong tien + nguon moi
& $py -W ignore "$app\_kk_kiem_lop_viet.py"          # 53/53 - 80 lop COCO khop model
& $py -W ignore "$app\_kk_kiem_chuc_nang.py"         # 73/73 - 10 cot CSV cu giong het
& $py -W ignore "$app\_kk_kiem_nguon_gui.py"         # 35/35 - GUI 3 nguon
& $py -W ignore "$app\_kk_kiem_chevron_lop_viet.py"  # 23/23 - mui ten + GUI==CLI khi chon lop
& $py -W ignore "$app\_kk_kiem_gui_chay_thuc.py"     # 7/7  - e2e GUI
& $py -W ignore "$app\_kk_kiem_gui_b3.py"            # 4/4  - 3 tinh nang dung tay
& $py -W ignore "$app\_kk_kiem_giao_dien.py"         # 7/7  - tham my
& $py -W ignore "$app\_kk_kiem_ngon_ngu_v3_3.py"     # 5/5  - song ngu
& $py -W ignore "$app\_kk_kiem_canvas_vung.py"       # PASS - sai so 0.0000
& $py -W ignore "$app\_kk_kiem_khong_mat_tinh_nang.py" --so "$app\_kk_out\A.json" "$app\_kk_out\B.json"
```

Lệnh CLI kiểm tra nhanh:
```powershell
& $py -W ignore "$app\app.py" --list-lop          # 80 lop COCO (Anh + Viet)
& $py -W ignore "$app\app.py" --list-camera       # camera tren may (may nay KHONG co camera)
& $py -W ignore "$app\app.py" --input "$app\video_mau\car-detection.mp4" --lop "ô tô,xe máy"
```

**Sau MỌI lần sửa code**: chạy tối thiểu `kiem_chuc_nang` + `kiem_gui_chay_thuc` +
`kiem_khong_mat_tinh_nang` + `kiem_ngon_ngu_v3_3` + kiểm tra encoding. Nếu sửa `gui.py` →
thêm `kiem_giao_dien` + chụp ảnh tự xem.

---

## 6. Bản đồ file

| File | Vai trò |
|---|---|
| `cam_ai_core.py` | **lõi**: pipeline phân tích, `AnalysisConfig`, `AnalysisResult`, `run_analysis`, chế độ ảnh/camera, đếm phương tiện |
| `lop_viet.py` | bảng **80 lớp COCO ↔ tiếng Việt** + tra cứu + gợi ý. **Không import torch** (import rẻ) |
| `face_engine.py` | ArcFace (SCRFD + w600k_r50) — dùng chung với app chấm công sau này |
| `bien_so.py` | OCR biển số (RapidOCR) — chạy 100% local |
| `app.py` | CLI. Mọi tính năng phải có cờ CLI tương ứng |
| `gui.py` | GUI CustomTkinter (~5.200 dòng). 4 mục lớn, 12 nhóm con |
| `giao_dien.py` | **hằng số màu + font + spacing** — nguồn sự thật cho giao diện |
| `design-system/camai/MASTER.md` | design system (nguồn sự thật cho màu/spacing) |
| `ve_vung_gui.py` | vẽ vùng bằng PIL |
| `canh_bao.py` | gửi cảnh báo ra ngoài (mặc định **chỉ thử**, không gửi thật) |
| `lop_viet.py` → `DICH_VI_EN` | bản dịch Anh **nằm trong `gui.py`** |
| `*.md` | tài liệu — coordinator giữ |
| `_kk_*` | script kiểm chứng (coordinator giữ) |

---

## 7. Gotcha hay gặp (rút gọn — chi tiết ở `ISSUE_LOG.md`)

- **`cv2.putText` không có glyph dấu tiếng Việt** → nhãn trên khung hình **không dấu**
  ("xe o to"); **log/báo cáo/CSV thì có dấu** ("ô tô"). Vẽ chữ có dấu phải dùng **PIL**.
- **Khoá dịch có tham số** phải dùng `self.dich("... {n} ...").format(...)` — dùng f-string thì
  khoá dịch **chết lặng lẽ** ⇒ bật tiếng Anh vẫn hiện tiếng Việt.
- **`customtkinter 5.2.2` không hiện placeholder** khi `CTkEntry` có `textvariable` (vì
  `StringVar` không định nghĩa `__eq__`). Ô gợi ý = **nhãn `CTkLabel` phủ lên ô**.
- **Đọc `StringVar` từ thread nền** → `main thread is not in main loop`. Mọi cập nhật UI từ
  thread → đẩy qua hàng đợi `self.queue`.
- **`CTkScrollbar._draw()` gọi `update_idletasks()`** → xả hết hàng đợi idle của **cả app** →
  tre 600–900 ms ở lần kéo cửa sổ **đầu tiên**. Đã vá.
- **Tìm vùng biển phải chạy ở luồng nền daemon** (khựng pipeline 680–1916 ms/khung).
- **RapidOCR không thread-safe** → mỗi engine OCR phải có `threading.Lock` riêng.
- **`chuan_hoa_bien_so` tuyệt đối không bịa ký tự** — thiếu biển còn hơn báo sai.
- **`rapidocr-onnxruntime` kéo bản CPU `onnxruntime` ghi đè bản GPU** → phải cài lại
  `onnxruntime-gpu` sau.
- **App mở mất ~12,5 s** (import 6,8 s + dựng GUI 2,7 s) — chưa tối ưu.
- **Log đỏ `libopenh264`** mỗi lần chạy — file video **vẫn H.264 hợp lệ**, không sao.
- **Nhận diện mặt trên video quay xa yếu** (1%–62%) → bật "Nhận người ở xa" (chậm ~5,3 lần).

---

## 8. Sau khi sửa xong — CHECKLIST (không làm thì lần sau không ai nhớ)

1. **Bump `VERSION`** trong `cam_ai_core.py` (patch/minor theo mức độ thay đổi).
2. Cập nhật **4 file tài liệu**:
   - `PROJECT_STATE.md` — mục mới trong 2.1x (bằng chứng) + dòng lịch sử ở mục 9 + header
   - `CHANGELOG.md` — mục phiên bản mới
   - `ISSUE_LOG.md` — lỗi mới gặp (triệu chứng · nguyên nhân · cách tránh lặp)
   - `ROADMAP.md` — tick việc đã xong, thêm việc mới
3. **Commit** với message tiếng Việt **không dấu** (để `git log` đọc được trên mọi font).
4. Kiểm tra encoding: **BOM=False, CR=0** cho mọi file đã sửa.
5. `git push`.

---

## 9. Việc chưa làm / chờ anh

| Việc | Trạng thái |
|---|---|
| **Ô tick chọn 80 lớp trong GUI** | Chưa có — hiện vẫn gõ tay vào ô lớp (đã nhận tiếng Việt). Đọc `lop_viet.DANH_SACH_LOP_VIET()` |
| **Tối ưu 12,5 s mở app** | Chưa làm — nạp model OCR/YOLO **trễ** lúc bấm BẮT ĐẦU thay vì lúc mở |
| **Camera thật** | **Chưa kiểm chứng được** — máy dùng để phát triển **không có camera**. Đã kiểm chứng đường đi live qua **camera IP giả** (HTTP MJPEG) + đường lỗi |
| **Mục 7 (kéo cửa sổ)** | Chờ **anh** tự xác nhận. Số đo đã sạch (lần kéo đầu 19,4 ms) nhưng cần cảm nhận thật |
| **Mục 8 (độ nhận diện)** | Chờ **anh** gửi video camera thật. Xem `PROJECT_STATE.md` mục 2.3 — có hạn chế lớn, cần nói rõ với anh |
| **Ảnh biển số VN thật** | Chờ **anh**. Hiện mới kiểm chứng bằng ảnh giả 10/10. Bản 3.3 có nút **"Đọc biển số thử…"** |

> **Nguyên tắc:** **KHÔNG** tự tuyên bố mục 7 / mục 8 là đạt khi chưa có xác nhận của anh.

---

## 10. Máy mới

Đọc **`TAI-MAY-MOI.md`**. Tóm tắt: `git clone` → `cai_dat_may_moi.bat` → `Mo CamAI.vbs`.
Model (784 MB) và video mẫu (507 MB) **cố ý không có trong git** — xem bảng trong file đó.
