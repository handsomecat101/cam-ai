# AGENT_TEAM.md — đội agent cứng của CamAI

> **Đây là bộ nhớ làm việc của CẢ ĐỘI.** Đọc file này **trước khi nhận việc**.
> Mọi thứ ở đây đã được **đo thật**, không phải phỏng đoán.
> Ngày cập nhật: **2026-10-23** · Bản đang làm: **v3.10**

**CamAI v3.10** · `VERSION` nằm trong `cam_ai_core.py` · nhánh `master`
Repo **public**: `https://github.com/handsomecat101/cam-ai` · địa chỉ: `H:\AI Project\cam-ai`

---

## 1. CamAI là gì

App **detect đa thể loại**, chạy **100% local** (không cloud, không tunnel, không gửi ảnh ra
ngoài). Nhận 3 loại nguồn: **file video** · **ảnh tĩnh** · **quay video/camera** (webcam `0`
hoặc camera IP `rtsp://`). Trả về **ảnh đã vẽ khung** + **báo cáo CSV** + số đếm.

### Kiến trúc: **web-first** (đã chốt từ bản 3.9)

**MỘT bộ HTML/CSS/JS duy nhất** phục vụ CẢ **desktop** (PySide6 + QWebEngineView) LẨN **điện
thoại** (trình duyệt, cùng Wi-Fi). **TUYỆT ĐỐI không viết UI hai lần.**

| Tầng | File | Ghi chú |
|---|---|---|
| UI (duy nhất) | `giao_dien_web/index.html` | 12 nhóm tính năng / 56 control, responsive 1440/820/390, **không tải tài nguyên ngoài** |
| Server | `web_server.py` | FastAPI, bind **0.0.0.0** (LAN), có cảnh báo "cùng Wi-Fi / không mở ra Internet" |
| Vỏ desktop | `app_qt.py` | PySide6 + QWebEngineView, tự sinh mật khẩu + tự đăng nhập + hộp thoại URL LAN |
| Lõi xử lý | `cam_ai_core.py` | `VERSION` ở dòng ~57 · **không đổi khi làm GUI** |
| Tăng tốc | `nhan_dien_nhanh.py` | CUDA Graph |
| Lớp tiếng Việt | `lop_viet.py` | 80 lớp COCO + ~200 từ đồng nghĩa |
| Nhận diện mặt | `face_engine.py` | dùng chung với app chấm công (app riêng, chưa làm) |
| Biển số | `bien_so.py` | OCR |
| Cảnh báo | `canh_bao.py` | gửi tin ra ngoài (Telegram/email/webhook) |

Bản Tkinter cũ (`gui.py` ~5.200 dòng, `gui_khung.py`, `giao_dien.py`, `ve_vung_gui.py`) được **giữ
làm dự phòng** — đừng sửa, đừng xoá. Launcher: `Mo CamAI Qt.vbs` (web, mới) · `Mo CamAI.vbs`
(Tkinter, cũ). Shortcut desktop: `C:\Users\TTC\Desktop\CamAI.lnk`.

---

## 2. Ba agent cứng — vai trò và sở hữu file

| Agent | Thư mục cấu hình | SỞ HỮU DUY NHẤT |
|---|---|---|
| **camai-ui** | `C:\Users\TTC\.minimax\agents\camai-ui\` | `giao_dien_web/index.html` (+ mọi file trong `giao_dien_web/`), `app_qt.py`, `mau_gui_web.py`, `mau_gui_web/`, `mau_gui_qt.py`, `_kk_kiem_ui_web.py`, `_kk_kiem_app_qt.py` |
| **camai-server** | `C:\Users\TTC\.minimax\agents\camai-server\` | `web_server.py`, `cam_ai_core.py`, `nhan_dien_nhanh.py`, `lop_viet.py`, `face_engine.py`, `bien_so.py`, `canh_bao.py`, `_kk_kiem_web_server.py`, `_kk_kiem_chuc_nang.py`, `_kk_kiem_nguon_viet.py`, `_kk_kiem_lop_viet.py` |
| **camai-qa** | `C:\Users\TTC\.minimax\agents\camai-qa\` | Script `_kk_qa_*` (tiền tố riêng) + ảnh trong `_kk_out/qa/` + báo cáo nghiệm thu. **KHÔNG sửa file nguồn.** |

**Không có file nào thuộc cả hai agent.** Cần đụng file của agent khác ⇒ **BÁO LẠI**, đừng tự sửa.

### Quy trình làm việc — BẮT BUỘC

1. **Dùng `task_append` để giao việc tiếp theo cho CÙNG một agent**, đừng spawn agent mới mỗi
   vòng. Agent mới phải đọc lại `AGENTS.md` + dò lại code ⇒ chậm, tốn token, và đã có tiền lệ
   **2 agent chết vì timeout 300 s** do đọc quá nhiều trước lượt đầu.
2. **Prompt phải tự chứa dữ liệu**: id/bảng số thật, chữ ký hàm, giá trị hằng số cụ thể —
   đừng bắt agent đi tìm bằng cách đọc file lớn.
3. **Tách task lớn thành nhiều task nhỏ theo file** để mất 1 phần vẫn còn phần khác.
4. **Coordinator (MCode) không tự viết/sửa code nguồn.** Coordinator tự chạy lại mọi bộ kiểm
   chứng, tự xem ảnh bằng mắt, tự commit. **Không tin báo cáo của agent.**
5. **Mỗi nhóm code xong:** bump `VERSION` trong `cam_ai_core.py` + cập nhật `PROJECT_STATE.md`,
   `CHANGELOG.md`, `ISSUE_LOG.md`, `ROADMAP.md`.

---

## 3. BẤT BIẾN — đo được, đừng phá

| Bất biến | Giá trị | Kiểm bằng |
|---|---|---|
| Số checkbox trong GUI | **20** | `_kk_kiem_khong_mat_tinh_nang.py` |
| Số nhóm con | **12** | idem |
| Thẻ video mẫu | **13** | idem |
| CSV (chưa bật tính năng mới) | **10 cột** | `_kk_kiem_nguon_viet.py` |
| CSV (bật đếm phương tiện) | **14 cột**, cột mới **LUÔN Ở CUỐI** | idem |
| SHA256 CSV khi tắt tính năng | phải **khớp gốc**: `bf97d113fdac39fb…` | idem (`Get-FileHash`) |
| Lớp COCO | **80 lớp, khớp 100% model** | `_kk_kiem_lop_viet.py` |
| Bit-exact | **200/200 khung** (2 video) | `_kk_kiem_bit_exact.py` |
| Tốc độ YOLO | **6,09–6,33 ms/khung** (~151 khung/s) | `_kk_kiem_toc_do.py` |
| Đếm phương tiện | 21 khớp 21 | `_kk_kiem_toc_do.py` |
| Tài nguyên ngoài trong HTML | **0** (không CDN/font/ảnh ngoài) | grep `http(s)://`, `<script src=>`, `<link href=>` |

**Quy tắc đặc biệt:** CSV khi tắt tính năng phải **GIỐNG HỆT** bản gốc — đây là bất biến
khó nhất, đừng đụng vào cột/header/thứ tự trường.

---

## 4. Bản 3.10 — đã làm gì, đo ra sao

### 4.1. Khoá bootstrap — bỏ form mật khẩu trên trình duyệt
- `web_server.py`: `KHOA_TRUY_CAP = secrets.token_urlsafe(32)` — sinh 1 lần lúc nạp module
  (43 ký tự, **đổi mỗi lần khởi động**). `_khop_khoa_truy_cap()` so sánh `secrets.compare_digest`
  (constant-time, chuẩn hoá UTF-8 bytes). `url_san_dung(ip_lan, cong)` → `http://<IP>:<port>/?k=<khoá>`.
- `GET /` có `?k=` khớp ⇒ `PHIEN.cap_phien()` + `set_cookie("camai_phien", httponly=True,
  samesite="lax", max_age=12h)` ⇒ vào thẳng, **không form mật khẩu**. Không khoá / khoá sai ⇒
  vẫn 200 nhưng UI hiện màn hướng dẫn; **API vẫn 401**.
- Route mới `GET /api/phien` (UI tự biết đã đăng nhập) · `GET /api/ping` (safety net).
- `POST /api/dang-nhap` **không đụng**; `CAMAI_PASSWORD` vẫn fail-closed.
- Khoá **KHÔNG ghi file**, **KHÔNG in console** (chỉ khi `CAMAI_DEBUG_KHOA=1`).
- `app_qt.py`: hộp thoại "Mở trên điện thoại" hiện **URL sẵn dùng** có `?k=` + nút "Sao chép";
  bỏ dòng mật khẩu + nút "Sao chép mật khẩu".

### 4.2. Khung video LUÔN Ở TRÊN (sticky)
- Video ở **đầu cột giữa**, `.the-video-stick{position:sticky;top:calc(var(--h-dau) - 15px)}`.
- `--h-dau` **đo runtime** bằng ResizeObserver ⇒ đúng ở mọi bề rộng.
- Giữ 16/9: `aspect-ratio:16/9` + `width:min(100%, calc(46vh * 16 / 9))` ⇒ cao ≤ 46vh.
- **Đo thật (sau khi cuộn thật, `scrollY > 0`):** 1440×900 → top **56px** (header 56) ·
  820×1180 → **56px** · 390×844 → **61px** (header 61). Yêu cầu ≤ header+2px ⇒ **đạt cả 3**.

### 4.3. Không treo + có indicator
- `web_server.py` có trường `giai_doan` trong `/api/trang-thai`: "Đang chuẩn bị" → "Đang nạp
  model nhận diện" → "Đang mở video" → "Đang phân tích" → "Xong" (+ "Lỗi").
- UI: spinner CSS thuần (`@keyframes quay`, **không emoji**) + overlay trên khung video + tên
  giai đoạn + gợi ý "Lần đầu mất khoảng 10–20 giây. Phần mềm vẫn phản hồi, khoan đợi."; badge
  "● Nạp model 0%" ở thanh đầu. Overlay hiện **0,074–0,8 s** sau khi bấm BẮT ĐẦU.

### 4.4. Kiến trúc: process con giữ sống (warm worker)
- Phần phân tích chuyển sang **tiến trình con `multiprocessing` (spawn)** giữ torch + YOLO +
  ArcFace. **Server không bao giờ import torch/cv2.**
- Lần chạy 2+ **không phải nạp lại model**: đo thật lần 1 = 27,8 s (cold) → lần 2 = **8,8 s**
  (warm, đo lần 2 của `camai-qa`: 44,7 s → 28,6 s, nhanh hơn 16,1 s).
- Tiến trình con resize ảnh nền ngay ⇒ server không cần `import cv2` trong đường gọi.
- Dừng có tín hiệu `dung`; watchdog 20 s huỷ worker không phản hồi. Worker chết ⇒ lần chạy sau
  **tự hồi sinh** (đo thật: PID 31256 → 53676).

### 4.5. ĐO ĐƯỢC ĐẦU VÀO — đọc để không phát minh lại
- **Giả thuyết "GIL starvation" BỊ BÁC BỎ BẰNG ĐO**: stall tối đa **0,055 s** khi import
  `cam_ai_core` (5,26 s) ⇒ GIL không hề bị chiếm.
- `/api/trang-thai` poll trong suốt lần chạy lạnh 75 s: **144/144 OK**, khoảng cách lớn nhất
  **0,502 s** ⇒ event loop FastAPI không bao giờ đứng.
- Browser main-thread rAF: khoảng cách lớn nhất **0,035 s** ⇒ trang không đứng hình.
- **NGUYÊN NHÂN THẬT:** lúc nạp model 11–27 s **không có gì hiển thị** (overlay không hiện,
  tiến trình đứng 0%, chip ghi "Đang chạy 0%") ⇒ *cảm giác* như treo. Kèm lỗi thật thứ hai:
  việc nặng chạy **cùng process** với server và với event loop Qt ⇒ một lần stall C-extension/CUDA
  làm đứng cả app desktop, và core crash làm chết app.
- **Nói thẳng trong tài liệu:** server/browser **không hề đứng đo được trước khi sửa** — giá
  trị thật của bản 3.10 là **gỡ bỏ rủi ro treo + có phản hồi trực quan**, không phải "đã sửa
  một lần đứng đo được".

### 4.6. BẰNG CHỨNG — coordinator TỰ chạy lại, không tin báo cáo agent

| Bộ kiểm chứng | Kết quả |
|---|---|
| `_kk_kiem_web_server.py` | **64/64 PASS** |
| `_kk_kiem_ui_web.py` | **49/49 PASS** |
| `_kk_kiem_app_qt.py` | **30/30 PASS** |
| `_kk_kiem_khoa_truy_cap.py` (mới) | **26/26 PASS** |
| `_kk_kiem_chuc_nang.py` | **73 PASS / 0 FAIL** |
| `_kk_kiem_nguon_viet.py` | **35/35 PASS** — SHA256 CSV khớp gốc |
| `_kk_kiem_lop_viet.py` | **53 PASS / 0 FAIL** |
| `_kk_kiem_gui_chay_thuc.py` | **PASS (7/7)** — bản Tkinter cũ |
| `_kk_kiem_khong_mat_tinh_nang.py` | **PASS** — 24 lệnh, không mất nút nào |

**Nghiệm thu độc lập của `camai-qa`:** **KẾT LUẬN PASS** (9/9 script PASS, 464/464 mục; khoá
32/32; sticky 32/32; không-treo 16/16). Báo cáo đầy đủ:
`_kk_out/qa/BAO_CAO_NGHIEM_THU_v3.10.md`.

---

## 5. VIỆC CÒN LẠI — phân công rõ

### 5.1. Lỗi thị giác do `camai-qa` phát hiện (báo cáo mục 4.2 / 4.3 / 4.4 / 4.6) → **camai-ui**

| # | Mức | Vấn đề | Bằng chứng |
|---|---|---|---|
| **4.2** | **TRUNG BÌNH** | Tiêu đề **"2. Chạy" bị CẮT ĐÔI** bởi mép dưới panel sticky (1440 mất 8/18px ≈ 44% chữ; 820 gần như hết chữ) | `qa_zoom_chay_1440.png`, `qa_zoom_chay_820.png` |
| **4.4** | NHẸ | Badge thanh đầu còn ghi "Xong" ~0,4 s sau khi bấm BẮT ĐẦU (overlay đã ghi "Đang nạp model") | `qa_overlay_1440x900.png` |
| **4.3** | NHẸ | Badge rút gọn "Nạp model" còn overlay "Đang nạp model nhận diện" ⇒ không nhất quán | `index.html:962-967` (`rutGonGiaiDoan`) |
| **4.6** | NHẸ | 404 `/favicon.ico` ⇒ mỗi lần tải trang 1 dòng log 404, tab trình duyệt không có logo | log server |

**Nguyên nhân 4.2:** `.the-video-stick` có `background:var(--panel)` **đục** + `z-index:5` ⇒ nội
dung trôi qua mép dưới bị cắt ngang. Hướng sửa: gradient mờ dần ở đáy panel (`: ::after`) và/hoặc
`scroll-margin-top` cho `.the`.
**Ràng buộc cứng:** sửa 4.2 **KHÔNG ĐƯỢC** phá yêu cầu (B) — video top vẫn ≤ header + 2px ở
1440/820/390; và **đừng làm hỏng** layout 390 (hiện 390 không bị cắt).

### 5.2. Sửa docstring sai kiến trúc → **camai-server**
- **4.5 [NHẸ]:** `web_server.py:33` và docstring route `/api/phan-tich` (~dòng 3733) vẫn ghi
  *"Pipeline chạy trong THREAD NỒN"* / *"chạy ở thread nền"* — nhưng mã đã chuyển sang
  `multiprocessing` spawn (`web_server.py:1910`). Sửa 2 dòng docstring cho khớp thực tế.

### 5.3. Việc chờ anh Tuấn — KHÔNG tự kết luận đạt
- **Mục 7** (kéo cửa sổ) — chờ anh xác nhận.
- **Mục 8** (video thật) — chờ anh xác nhận.
- **Ảnh biển số VN thật** — chờ anh gửi để test OCR.
- **Thử trên điện thoại thật** — cùng Wi-Fi + cho phép Python trong Windows Defender Firewall
  (Private network).

### 5.4. Hạn chế đã biết (đừng hứa là đã làm)
- Bản web **chỉ phân tích file video** — camera/webcam trực tiếp dùng trong bản desktop. Nút
  "Quét camera" ở bản web đang hướng dẫn về bản desktop.
- OCR biển số chưa chạy hết vòng với dữ liệu VN thật.
- Nhận diện mặt trên video xa yếu (1%–62%).
- Ô tick chọn 80 lớp trong GUI chưa làm (đang gõ tay, đã nhận tiếng Việt).
- Máy phát triển **không có camera**.
- Warm worker sống trong 1 phiên server ⇒ khởi động lại app là lại cold (~27,8 s).

---

## 6. QUY TẮC BẤT BIẾN KHI SỬA CODE

- **Tiếng Việt CÓ DẤU** trong mọi chuỗi hiển thị. **Comment code KHÔNG dấu.**
- File UTF-8 **KHÔNG BOM**, xuống dòng **LF**. Dùng tool `edit`/`write` —
  **TUYỆT ĐỐI KHÔNG `Get-Content | Set-Content`** (PowerShell 5.1 làm hỏng UTF-8).
- **KHÔNG** thêm dependency ngoài `requirements.txt` đã có.
- **KHÔNG** hardcode token/mật khẩu. **KHÔNG** log khoá.
- **KHÔNG** commit (coordinator commit). **KHÔNG** tự bump VERSION trừ khi được giao.
- **KHÔNG** dùng `/api/phan-tich` trả về đồng bộ (phần nặng phải chạy nền).
- `/api/cau-hinh` phải trả **37 field tự sinh từ dataclass bằng `ast`** — KHÔNG import thật.
- Chặn path traversal **3 lớp**.
- `vung.txt` lưu tọa độ **tương đối 0..1** (`cam_ai_core.py:1168-1186` đọc, 1862-1865 quy đổi pixel).
- `cv2.putText` **mất dấu** — nhãn khung không dấu, báo cáo thì có dấu.
- Khoá dịch có tham số phải gọi `dich().format()`.
- `rapidocr-onnxruntime` ghi đè `onnxruntime-gpu` (script cài đã xử lý).
- Crash `0xC0000005` lúc thoát do thiếu `openh264-2.5.0-win64.dll` ⇒ phải có
  `_nap_dll_openh264()` + `_fourcc_ket_qua()` probe thật rồi mới chọn `avc1`, lỗi thì lùi `mp4v`.
- **3 hướng tối ưu đã bị loại có lý do, đừng thử lại mù:** batching (lệch số đếm 0,497559) ·
  FP16 (không tăng tốc) · ONNX (export cứng 480×480).

---

## 7. LỆNH KIỂM CHỨNG (copy-paste)

```powershell
$env:PYTHONIOENCODING='utf-8'
$py='H:\AI Project\cam-ai\.venv\Scripts\python.exe'
$app='H:\AI Project\cam-ai'
& $py -W ignore "$app\_kk_kiem_web_server.py"     # 64/64
& $py -W ignore "$app\_kk_kiem_ui_web.py"        # 49/49
& $py -W ignore "$app\_kk_kiem_app_qt.py"        # 30/30
& $py -W ignore "$app\_kk_kiem_khoa_truy_cap.py" # 26/26
& $py -W ignore "$app\_kk_kiem_chuc_nang.py"     # 73/73
& $py -W ignore "$app\_kk_kiem_nguon_viet.py"     # 35/35
& $py -W ignore "$app\_kk_kiem_lop_viet.py"      # 53/53
& $py -W ignore "$app\_kk_kiem_gui_chay_thuc.py"  # Tkinter cũ
& $py -W ignore "$app\_kk_kiem_khong_mat_tinh_nang.py" --so "$app\_kk_out\agent_a_nguon\sau_khong_mat.json" "$app\_kk_out\agent_c_vong3\sau_khong_mat.json"
```

Chạy python **CHỈ** bằng `H:\AI Project\cam-ai\.venv\Scripts\python.exe`.

### Quy tắc cổng & dọn tiến trình (rất quan trọng)
- App của anh Tuấn chạy ở **cổng 8765** — **TUYỆT ĐỐI không chạm 8765, không kill tiến trình
  của anh.**
- Mỗi agent dùng **cổng riêng**: `camai-ui` 8815+ · `camai-server` 8825+ · `camai-qa` 8835+.
- Dọn dẹp: **chỉ** kill tiến trình BẠN sinh, dùng `taskkill /PID <pid> /T /F` (**giết cả cây**).
- Sweep headless Edge/Chrome cũ theo `--user-data-dir` — nếu không, tiến trình GPU mồ côi có
  thể ăn **hàng chục ngày CPU** (đã xảy ra: 1 tiến trình Edge mồ côi ăn 74% CPU máy).
- **`.venv\Scripts\python.exe` là LAUNCHER STUB** — tiến trình thật là tiến trình **CON**. Khi tìm
  cửa sổ Qt phải lọc theo PID con (xem `_pid_app()` trong `_kk_kiem_app_qt.py`).
- `_kk_kiem_app_qt.py` quét **cả `_kk_out/`** để tìm mật khẩu bị lộ ⇒ **đừng** để stdout của app
  lọt vào file trong thư mục dự án, nếu không mục "6. Mật khẩu KHÔNG bị ghi ra file" sẽ FAIL
  (lỗi của script, không phải lỗi app).

### Xem ảnh bằng mắt (bắt buộc khi có lỗi thị giác)
- Chụp GUI theo mẫu: `attributes("-topmost",True)` → `lift()` → `GetAncestor(id,2)` →
  `GetWindowRect` → `ImageGrab.grab(bbox, all_screens=True)`.
- Lỗi thị giác phải soi ảnh **phóng 3×**: `& $py "$app\_kk_phong_to.py" "<ảnh gốc>" "<ảnh phóng>"
  <x> <y> <w> <h>`.
- Ảnh của đội: `_kk_out/ui_web/` (UI) · `_kk_out/qa/` (nghiệm thu) · `_kk_out/app_qt/` (desktop).

---

## 8. Những điều TUYỆT ĐỐI KHÔNG được kết luận khi chưa có bằng chứng

- **KHÔNG** nói "chạy tốt trên điện thoại thật" — mới chỉ có viewport mô phỏng 390/820 + localhost.
- **KHÔNG** nói OCR biển số hoạt động — chưa có ảnh biển số VN thật.
- **KHÔNG** nói mục 7 / mục 8 đạt — đang **chờ anh xác nhận**.
- **KHÔNG** nói camera/webcam chạy được trên bản web — tính năng đó không tồn tại trên bản web.
- **KHÔNG** nói "đã sửa lỗi treo" nếu chưa đo — điểm mấu chốt của bản 3.10 là đo được trước
  và sau.

---

## 9. File tài liệu khác (đọc theo thứ tự)

| # | File | Vì sao |
|---|---|---|
| 1 | `AGENTS.md` | quy tắc + bất biến + lệnh (**cần cập nhật version**) |
| 2 | `AGENT_TEAM.md` (file này) | đội agent + trạng thái v3.10 + việc còn lại |
| 3 | `PROJECT_STATE.md` mục 0, 2, 3, 4, 6, 9 | bộ nhớ dài hạn của dự án |
| 4 | `ISSUE_LOG.md` | lỗi đã biết — đọc trước khi sửa |
| 5 | `CHANGELOG.md` | thay đổi gì, bằng chứng ra sao |
| 6 | `ROADMAP.md` | việc đã xong / còn lại / chờ anh |
| 7 | `_kk_out/qa/BAO_CAO_NGHIEM_THU_v3.10.md` | nghiệm thu độc lập (PASS) |
