# Nhật ký thay đổi CamAI

Định dạng: Keep a Changelog. Phiên bản theo Semantic Versioning.

## [3.7] — 2026-10-20 (sau 17:00)

`VERSION` trong `cam_ai_core.py` = **3.7**.

Bản này **hoàn tất** mục tiêu anh chốt: *CamAI = app detect đa thể loại, chạy được trên
**file video + ảnh + quay video**, và **chọn được lớp vật thể bằng tiếng Việt***.

### Đã thêm

| # | Hạng mục | Chi tiết |
|---|---|---|
| 1 | **GUI nối 2 nguồn mới** | Nhóm "NGUỒN" nay là chọn nguồn tổng quát: label **"Nguồn"**, nhãn trạng thái tự cập nhật (**"Loại nguồn: Video / Ảnh tĩnh / Camera máy / Camera IP"**), 4 nút: **Chọn video… / Chọn ảnh… / Chọn camera… / Danh sách camera** |
| 2 | **Hộp thoại chọn camera** | Quét camera (chạy **nền**, có nút Huỷ, **không treo**), hiện danh sách (index, tên, độ phân giải, mở được không), ô nhập **địa chỉ camera IP** (`rtsp://` / `rtmp://` / `http://` / `https://`) có kiểm tra định dạng. Máy không có camera → báo rõ, **không crash** |
| 3 | **Thanh tiến trình "không xác định"** khi quay camera | `total_frames = 0` ⇒ dùng `mode="indeterminate"`; nút **DỪNG** dừng được vòng lặp live (`stopped=True`) |
| 4 | **Nguồn ảnh trong GUI** | Phân tích 1 ảnh → xuất **ảnh kết quả `.jpg`** + CSV; mở kết quả / xem báo cáo xử lý đúng cả ảnh lẫn video; vẽ vùng chỉ cho nguồn video |
| 5 | **`lop_viet.py` — bảng 80 lớp COCO ↔ tiếng Việt** | Module độc lập, **không import torch/ultralytics** (import rẻ). `TEN_LOP_VIET` (80 lớp → tiếng Việt có dấu), `DANH_SACH_LOP_VIET()` (id + Anh + Việt, đúng thứ tự model), `TRA_CUU_LOP_VIET()`, `GOI_Y_LOP_VIET()`, `XE_PHUONG_TIEN` |
| 6 | **`--lop` nhận tiếng Việt** | Gõ được **"ô tô,xe máy"** (có dấu), **"o to,xe may"** (không dấu) hoặc **"car,motorcycle"** (tiếng Anh) → cùng kết quả. Gõ sai → báo lỗi rõ **kèm gợi ý** + liệt kê 80 lớp |
| 7 | **`--list-lop`** | In đủ **80 lớp** (id, tiếng Anh, tiếng Việt) rồi thoát `exit 0`, **không cần `--input`** |
| 8 | **Đếm phương tiện** | `--dem-phuong-tien`: đếm theo từng lớp + tổng lượt + số xe nhiều nhất cùng lúc; **4 cột CSV mới ở CUỐI** (`phuong_tien`, `so_phuong_tien`, `tong_phuong_tien`, `max_phuong_tien`), 10 cột cũ **không đổi** |
| 9 | **~200 từ đồng nghĩa tiếng Việt** | "ô tô" = "xe hơi" = "xe ô tô" · "xe máy" = "mô tô" = "xe gắn máy" · "xe khách" = "xe buýt" = "xe đò" · "xe tải" = "xe hàng" · "thuyền" = "tàu thuyền" · "tàu hỏa" = "tàu lửa" · "điện thoại" = "smartphone" · "gấu bông" = "thú bông" … |
| 10 | **Bộ cài đặt 1 lệnh cho máy mới** | `cai_dat_may_moi.bat` (double-click) → `cai_dat_may_moi.py`: tạo `.venv`, cài thư viện, tải `yolo11n.pt`, tải model ArcFace (`tai_tao_model.py`), in tổng kết. **Không chết khi 1 bước fail** — bỏ qua bước đó và đi tiếp; exit 0 chỉ khi venv + 2 model đều có |
| 11 | **`requirements.txt` đầy đủ + đúng** | Bổ sung 5 gói đang thiếu: `customtkinter` (GUI), `pillow` (vẽ nhãn tiếng Việt), `rapidocr-onnxruntime` (OCR biển số), `openpyxl` (báo cáo .xlsx), `pywin32` (script chụp màn hình). Dòng `torch` **cố ý comment** vì bản `+cu126` không có trên PyPI — script cài riêng từ index pytorch.org |
| 12 | **`TAI-MAY-MOI.md`** | Hướng dẫn đầy đủ cho máy mới: yêu cầu hệ thống, clone (kèm cách dùng PAT), cài đặt, mở app, **bảng "những thứ KHÔNG có trong git"** (models 784 MB, video_mau 507 MB, known_faces) và cách lấy lại từng thứ, quy trình `git pull/push`, gotcha đã biết |

### BỔ SUNG SAU KHI CHỐT 3.7 — ĐẨY LÊN GITHUB (anh chuyển sang máy khác)

| Hạng mục | Chi tiết |
|---|---|
| **Repo GitHub** | `https://github.com/handsomecat101/cam-ai` — **private**, nhánh `master`, **toàn bộ lịch sử commit** (từ `bb52c18` bản 3.5 → `7ebe43b`) đã lên. Kích thước repo **~3 MB** (chỉ code + tài liệu) |
| **Cố ý KHÔNG commit** | `models/` (784 MB) · `video_mau/` (507 MB) · `.venv/` · `known_faces/` (ảnh khuôn mặt) · `*.pt` / `*.onnx` · file kết quả chạy. Lý do: GitHub giới hạn 100 MB/file, repo 1,3 GB sẽ clone chậm; model tải lại được bằng 1 lệnh |
| **Giữ lại file giấy phép** | `video_mau/moi/NGUON_LICENSE_NGUOI.md` **vẫn được commit** — là attribution CC BY / CC BY-SA cho 5 video Wikimedia, bắt buộc phải có |
| **`known_faces_mau.zip`** (41 KB, **không commit**) | Gói 10 ảnh "An"/"Binh" để anh chuyển sang máy mới bằng USB. Ảnh khuôn mặt **cố ý không đưa vào git** (biometric data + git history không xoá được) |
| **Xung đột thật do agent phát hiện khi làm bộ cài** | `rapidocr-onnxruntime` kéo theo bản **CPU** của `onnxruntime` và **ghi đè** bản GPU. Script cài đặt phát hiện (chỉ khi cả 2 dist-info nằm trong `.venv`) và cài lại `onnxruntime-gpu==1.23.2` |
| **Xác minh** | `pip install --dry-run -r requirements.txt` → **exit 0**, cả 11 dòng đang hoạt động đều resolve; `torch==2.14.0` trên index cu126 → `torch-2.14.0+cu126` (cp313 win_amd64) resolve được; `insightface==2.1` có sẵn wheel (không cần trình biên dịch); chạy thật `cai_dat_may_moi.py` → **exit 0**, chạy từ số 0 (xoá `.venv` trước) → tạo venv + thông báo tiếng Việt có dấu đúng |

### Đã sửa

| Mục | Chi tiết |
|---|---|
| **Mũi tên mục lớn sai trạng thái** | Mục **NGUỒN đang mở** nhưng mũi tên vẫn chỉ sang phải ⇒ cả 4 mục trông giống nhau. Lỗi có từ bản 3.6 (đã kiểm lại bằng `git show 35250e5:gui.py`). Sửa: mũi tên khởi tạo đúng trạng thái (mở ⇒ ChevronDown). Phát hiện bởi coordinator khi **phóng to 3×** ảnh chụp |
| **GUI "xem trực tiếp" không hiểu lớp tiếng Việt** | `_vong_xem()` tự viết lại logic chọn lớp (chỉ tiếng Anh) ⇒ gõ "ô tô" thì **khung xem trực tiếp không vẽ khung nào** dù báo cáo có. Sửa: dùng **cùng hàm** của `cam_ai_core` → GUI và CLI luôn cho kết quả giống nhau |
| **Lỗi hiển thị khi nhóm cha đang thu gọn** | `_hang()` cho cột điều khiển `minsize=140` — nếu không, các nút rộng bị Tk bóp còn 124px ⇒ **chữ bị cắt** |
| **Log "Đang nhận N lớp" không dịch được** + lỗi chính tả | Khoá dịch là **mẫu có tham số** (`"...{n} lớp: {ds}"`) nhưng chuỗi thật đã f-string → khoá dịch **chết lặng lẽ** ⇒ bật tiếng Anh vẫn hiện tiếng Việt. Sửa: `self.dich(...).format(...)`. Kèm sửa chính tả `"Bỏ qua l không có:"` → `"Bỏ qua lớp không có:"` |

### BẰNG CHỨNG — coordinator tự chạy lại trên code cuối

| Bộ | Kết quả |
|---|---|
| `_kk_kiem_nguon_viet.py` (coordinator, mới) | **35/35 PASS** — 80 lớp khớp 100% model, 13/13 tra cứu tiếng Việt, CLI `--list-lop` đủ 80 dòng, CSV 14 cột, hồi quy SHA256 giống bản gốc |
| `_kk_kiem_lop_viet.py` | **53/53 PASS** |
| `_kk_kiem_chuc_nang.py` | **73/73 PASS** — 10 cột CSV cũ giống hệt từng giá trị, 4 cột mới ở cuối |
| `_kk_kiem_nguon_gui.py` | **35/35 PASS** |
| `_kk_kiem_gui_chay_thuc.py` (e2e) | **7/7 PASS** — 39,1 s |
| `_kk_kiem_gui_b3.py` | **4/4 PASS** |
| `_kk_kiem_giao_dien.py` | **7/7 PASS** |
| `_kk_kiem_ngon_ngu_v3_3.py` | **5/5 PASS** |
| `_kk_kiem_canvas_vung.py` | **PASS** — sai số 0,0000 |
| `_kk_kiem_khong_mat_tinh_nang.py` | **PASS** — 20 checkbox + 12 nhóm con + 13 thẻ video mẫu **giống hệt**; 21 lệnh nút **không mất nút nào** (3 nút mới + 1 đổi nhãn) |
| Hồi quy video (baseline từ git HEAD) | CSV **SHA256 giống hệt**, thời gian **−0,43%** (nhiễu) |
| Encoding mọi file đã sửa | **BOM=False, CR=0** |

### CHƯA ĐẠT ở bản 3.7

- **Camera thật chưa kiểm chứng được** — máy này **không có camera**. Đã kiểm chứng đường
  đi live qua **camera IP giả** (HTTP MJPEG) và đường lỗi (rõ ràng, không treo).
- **Chưa có ô tick chọn 80 lớp** trong GUI — hiện vẫn gõ tay vào ô lớp (đã nhận tiếng Việt).
- **Mục 7 / mục 8** — vẫn chờ **anh** xác nhận.

## [3.6] — 2026-10-20 (sau 15:30)

`VERSION` trong `cam_ai_core.py` = **3.6**.

Bản đầu tiên làm theo **định hướng mới anh chốt**: *CamAI = app detect đa thể loại, chạy
được trên **file video + ảnh + quay video**; ứng dụng chấm công tách ra app riêng; đổi nền
tảng để sau.* Chi tiết định hướng: `USE_CASE.md` mục 0, `PROJECT_STATE.md` mục 0.

### Đã thêm

| # | Hạng mục | Chi tiết |
|---|---|---|
| 1 | **4 mục cấu hình lớn** thay cho 12 mục rời rạc | NGUỒN (mở sẵn) · PHÂN TÍCH · BIỂN SỐ & ẢNH · CẢNH BÁO & MÔ HÌNH. Mỗi mục có 1 dòng mô tả, chỉ 1 mục mở tại một lúc, mũi tên Segoe MDL2 xoay thật (E76C ↔ E70D). Mở mục con sẽ mở luôn mục lớn cha |
| 2 | **Dải "Video mẫu dùng thử" gọn lại** | Thẻ bố cục ngang (ảnh 84×47 + tên + mô tả) → 1 thẻ cao 55px thay vì 137px; cả khối **212px → 125px** (đo thật) |
| 3 | **Nguồn ẢNH tĩnh** | `--input <ảnh>` → phân tích 1 khung hình qua **cùng một đường pipeline**; xuất **ảnh đã vẽ khung** (người + mặt + tên + biển số) + CSV; tiến trình `frame 0/1`, `percent=100` |
| 4 | **Nguồn CAMERA** | webcam `0` + camera IP `rtsp://`/`http://`; có **ngân sách thời gian** nên không treo; **nhấn `q` để dừng**; thanh tiến trình kiểu **không xác định** khi không biết tổng số khung |
| 5 | **Lệnh `--list-camera`** | Quét và in danh sách camera (index, độ phân giải, tên, mở được hay không); không có camera → in rõ + hướng dẫn, **exit 0** |
| 6 | **`loai_nguon()` / `la_live()`** trong `cam_ai_core` | Hàm dùng chung cho CLI và GUI, để GUI nối vào 2 nguồn mới sau |
| 7 | **`_chuan_hoa_console()` được gọi thật** trong `app.py` | Trước đó hàm có sẵn nhưng chưa ai gọi → thông báo lỗi tiếng Việt bị escape thành `\u1ed7i` |

### Đã sửa

| Mục | Chi tiết |
|---|---|
| **`gui_ngon_ngu.json` bị git theo dõi** | File này lưu **lựa chọn ngôn ngữ của người dùng**. Một script kiểm chứng để lại "en" → app của anh **tự mở bằng tiếng Anh**; bộ e2e **FAIL** vì chỉ tìm chuỗi tiếng Việt. → `git rm --cached` + thêm `.gitignore`, reset về `"vi"`, và bộ e2e **không còn phụ thuộc ngôn ngữ** |
| Lỗi bố cục lộ ra khi gom nhóm | `_hang()` cho cột điều khiển `minsize=140` — nếu không, các nút rộng 260px bị Tk bóp còn 124px khi mục lớn cha đang thu gọn ⇒ **chữ bị cắt** |

### BẰNG CHỨNG — coordinator tự chạy lại

| Bộ | Kết quả |
|---|---|
| `_kk_kiem_gui_chay_thuc.py` | **7/7 PASS** — 37,9 s |
| `_kk_kiem_gui_b3.py` | **4/4 PASS** |
| `_kk_kiem_giao_dien.py` | **7/7 PASS** |
| `_kk_kiem_ngon_ngu_v3_3.py` | **5/5 PASS** |
| `_kk_kiem_canvas_vung.py` | **PASS** — sai số 0,0000 |
| Chế độ ảnh (chạy tay) | **EXIT=0** — 4 người, 2 mặt, nhận "An"/"Binh", ảnh kết quả 199.956 B |
| `--list-camera` | **EXIT=0** — máy này không có camera → thông báo rõ |
| Hồi quy video | CSV **251 dòng**, SHA256 **giống hệt** bản gốc, thời gian −5,4%…+0,1% |

### CHƯA ĐẠT ở bản 3.6

- **GUI chưa nối vào 2 nguồn mới** (chọn ảnh / chọn camera) — phần lõi đã xong, còn lớp vỏ.
- **Camera thật chưa kiểm chứng** (máy này không có camera) — đã kiểm chứng đường đi live
  qua **camera IP giả** (HTTP MJPEG).
- **Mục 7 / mục 8** — vẫn chờ **anh** xác nhận.

## [3.5] — 2026-10-20 (sau 08:40)

`VERSION` trong `cam_ai_core.py` = **3.5**.

Bản này sinh ra từ **anh dùng thật và báo: "kéo cửa sổ vẫn bị giật lắm"** — đây là **mục 7**
của bảng nghiệm thu, lần đầu có **xác nhận của người dùng** (trước đó chỉ có số đo của
coordinator, và đó là điều sai — em đã ghi nhận lỗi này).

### Đã thêm

| # | Hạng mục | Chi tiết |
|---|---|---|
| 1 | **Launcher 1-click cho người dùng** | `Mo CamAI.vbs` (không hiện cửa sổ đen) + `Mo CamAI.bat` (có cửa sổ đen để xem lỗi) — trước đó **chưa có cách nào mở app cho người không rành kỹ thuật**. Kèm `HUONG-DAN-MO-APP.md` |
| 2 | **Sửa tooltip** (giảm tạo/huỷ cửa sổ native) | Tái sử dụng **1 cửa sổ tooltip duy nhất**, **trì hoãn 450 ms** (chuẩn Windows), đóng cửa sổ tooltip khi app đóng |
| 3 | **Sửa giật lần kéo đầu tiên** | Xem mục "Đã sửa" bên dưới |

### Đã sửa — vấn đề anh báo: kéo cửa sổ bị giật

**Quy trình:** coordinator **đo**, không đoán. 4 phép đo độc lập đã loại trừ 3 giả thuyết sai:

| Giả thuyết bị loại | Bằng chứng |
|---|---|
| "Do tooltip tạo/huỷ cửa sổ" | Trong lúc kéo, con trỏ **không nằm trên app** → `Enter=0`, `Leave=0`, **tooltip tạo 0 cửa sổ** |
| "Do vẽ lại nhiều" | Đo riêng thời gian vẽ lại toàn bộ cửa sổ = **0,5 ms** |
| "Do app chạy nền" | **CPU idle = 0 ms** trong 3 s |

**Cái thật sự (đo được):** giật **chỉ xảy ra ở lần kéo ĐẦU TIÊN** — lần 1 = **859 ms**,
lần 2 = 20,2 ms, lần 3 = 20,9 ms. Cửa sổ Tk/CTk **rỗng** không bị (21 ms) nhưng app đầy đủ
bị (**984 ms**). **Bỏ hết scrollbar → còn 144 ms** ⇒ **5 scrollbar chiếm ~85% chi phí**.
Stack lúc đang tre cho thấy vòng `CTkScrollbar._draw` → `update_idletasks` → `<Configure>`.

> **Bài học quan trọng:** phép đo A/B đầu tiên của em **ra kết luận sai** vì lần đo đầu
> luôn dính "phí khởi tạo hiển thị". Phải **đo lần kéo thứ 2, thứ 3** mới thấy ra sự thật.

**Cách sửa:** làm scrollbar nhẹ hơn + **khởi động ấm** (ép cây widget vẽ xong **trước khi
cửa sổ hiện ra**) để lần kéo đầu tiên của người dùng không phải chịu chi phí này.

### CHƯA ĐẠT ở bản 3.5

- **Mục 7 (kéo cửa sổ không giật)** — đã sửa theo số đo, nhưng **cần anh tự xác nhận** vì
  chỉ có đo máy, chưa có xác nhận của người dùng.
- **Mục 8 (độ nhận diện video thật)** — vẫn chờ **anh** (cần video thật của anh).
- **OCR biển số trên ảnh THẬT** — vẫn chờ ảnh biển số VN thật của anh.

## [3.4] — 2026-10-20 (sau 06:40)

`VERSION` trong `cam_ai_core.py` = **3.4**.

Bản này **KHÔNG thêm tính năng mới** — nó **thiết kế lại toàn bộ giao diện** theo yêu cầu
*"cái app này nhìn cứ phèn phèn"*, đồng thời **làm lại icon app bằng ảnh AI**.

### Nguồn thiết kế

| Tài liệu | Vai trò |
|---|---|
| `design-system/camai/MASTER.md` | **Nguồn sự thật** cho toàn bộ giao diện: bảng màu, typography, lưới khoảng cách, layout, component, checklist. Sinh từ skill `ui-ux-pro-max` (`--design-system` + domain `color`/`typography`/`ux`) rồi **chỉnh cho đúng bản chất sản phẩm** (app desktop nền tối, người dùng không rành kỹ thuật) |
| `giao_dien.py` (file mới) | Hằng số thiết kế + hàm trợ giúp: màu, font, khoảng cách, bo góc, kích thước, biểu tượng Windows. Tách ra để `gui.py` không còn chôn vùi số hex |

**3 quyết định sửa so với output gốc của skill** (đều ghi rõ lý do ở MASTER.md mục 0):
1. Skill trả pattern **"Enterprise Gateway"** (landing page bán hàng, có CTA "Contact Sales")
   → **bỏ**, giữ style **Data-Dense Dashboard**. CamAI là công cụ desktop local, không bán hàng.
2. Query "desktop … dark mode" của skill trả **Cyberpunk UI** (đen + xanh neon + glitch)
   → **bỏ**, dùng **dark slate + xanh trạng thái**. Neon trông như tool hacker, tương phản kém.
3. Skill gợi ý font **Fira Sans / Fira Code / Inter** (Google Fonts) → dùng **font có sẵn trên
   Windows** (`Segoe UI`, `Segoe UI Semibold`, `Segoe UI Black`, `Cascadia Mono`) vì app chạy
   **100% offline**, không được phụ thuộc tải font ngoài.

### Đã thay đổi

| # | Hạng mục | Chi tiết |
|---|---|---|
| 1 | **Thanh đầu mới (64px)** | Icon app + "CamAI v3.3" + phiên bản nhỏ + nút ngôn ngữ + nút **DỪNG** / **BẮT ĐẦU**. Nút chính xanh `nut`, nút phụ có viền |
| 2 | **Icon app do AI vẽ** | `assets/camai.png` (512px) + `assets/camai.ico` (16/24/32/48/64/128/256). Vẽ bằng **Nano Banana Pro (Gemini 3 Pro Image)**: 4 biến thể, chọn bản "đầu người + ống kính + khung nhận dạng" vì **3 hình đơn giản → vẫn rõ ở 16×16px**. Icon hiện ở thanh đầu **và** trên thanh tiêu đề cửa sổ Windows |
| 3 | **Bỏ ký hiệu emoji làm icon** | `▶ ● ✔ ✖ ■` → **font biểu tượng Windows `Segoe MDL2 Assets`** (Play / Pause / Stop / CheckMark / Error / Chevron…). Font có sẵn ở `C:\Windows\Fonts\segmdl2.ttf`, không cần tải gì |
| 4 | **Typography** | Segoe UI (thường/Semibold/Black) + Cascadia Mono cho số & mã. Tiêu đề 23px, tiêu đề khu vực 14–15, nhãn 13, ghi chú 12, số liệu 28 — **không còn chữ < 12px** |
| 5 | **Màu** | Tách hết sang `giao_dien.py`; **bổ sung màu cảnh báo `#F59E0B`** (skill yêu cầu trạng thái xanh / hổ phách / đỏ — bản 3.3 thiếu hổ phách) |
| 6 | **Component** | Bo góc thống nhất (nút 8 / ô nhập 6 / thẻ 10), nút cao 36px, ô nhập cao 32px, viền 1px, 6 ô số liệu có màu theo trạng thái, checkbox có **ghi chú riêng dưới từng ô** |
| 7 | **Lưới khoảng cách** | 4 / 8 / 12 / 16 / 24 / 32 px — cùng vai trò luôn dùng đúng một giá trị; bỏ viền/đường kẻ thừa |

### BUG THẬT — coordinator phát hiện khi tự mở ảnh xem

| # | Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | Ô checkbox đã tick hiện là **một ô xanh đặc, không thấy dấu ✓** | CustomTkinter 5.2.2 (`ctk_checkbox.py` dòng 196–207): khi tick, **ô được tô bằng `fg_color`**, **dấu ✓ được vẽ bằng `checkmark_color`**. Đặt cả hai cùng xanh → dấu ✓ biến mất | `checkmark_color = MAU["nen"]` (#0F172A, tương phản ≈ 7,7:1 trên nền xanh) |
| 2 | Nút **DỪNG** hiện `▯ DỪNG` — trông **y như ô vuông thiếu glyph** | Dùng icon **Stop (U+E71A)** = hình vuông đặc, đọc nhầm là tofu | Đổi sang **Pause (U+E769)** = hai thanh dọc |

### CHƯA ĐẠT ở bản 3.4

- **Mục 7** (kéo cửa sổ không giật) và **mục 8** (độ nhận diện trên video thật) — vẫn chờ **anh** xác nhận.
- **OCR biển số trên ảnh THẬT** — vẫn chưa có ảnh biển số VN thật (bản 3.3 đã có nút "Đọc biển số thử…").
- **Đăng ký nhiều người cùng lúc** và **nhiều vùng** trong 1 file — bản 3.3 mới làm 1 người / 1 vùng.

## [3.3] — 2026-10-20 (sau 04:50)

`VERSION` trong `cam_ai_core.py` = **3.3**.

Bản này **thêm 3 tính năng** và **sửa 1 lỗi thật**. Cả hai đều do **anh chốt**:
tách 2 ô xem video, và đi theo hướng **"(A) bộ công cụ AI dùng tay"** — đẩy những thứ
đã có sẵn ở CLI vào **GUI** để anh không phải mở cửa sổ lệnh.

### Đã thêm

| # | Tính năng | Chi tiết |
|---|---|---|
| 1 | **Tách 2 ô xem video** | `chk_xem_video` → nhãn **"Xem trực tiếp"**; thêm `chk_xem_ket_qua` → **"Xem khung hình kết quả"** (mặc định BẬT). Trước đó 1 ô mang 2 nghĩa. Bật cả 2 → log giải thích "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' tạm không dùng (tránh 2 nguồn hình đè nhau)". `frame_cb` chỉ bật khi TẮT "Xem trực tiếp" |
| 2 | **Nút "Đăng ký người quen…"** | Chọn ảnh/video → nhập tên → lưu vào `known_faces/<Tên>/`. Dùng lại `dang_ky_anh.collect_faces` + `cluster` + `save_group`. Hỏi xác nhận trước khi ghi đè thư mục đã có (`save_group` xoá thư mục cũ). Chạy ở thread nền; chỉ khoá nút, **không khoá cả app** |
| 3 | **Nút "Vẽ vùng ngay tại đây"** | Kéo chuột **ngay trong cửa sổ** để khoanh vùng → ghi file vùng `.txt` → điền vào ô "File vùng". Dùng module mới `ve_vung_gui.py`. Nút cũ "Vẽ vùng trên video này" (mở cửa sổ CLI) **giữ nguyên** |
| 4 | **Nút "Đọc biển số thử…"** | Đọc **1 ảnh** → trả chuỗi biển + tin cậy + số hàng + ảnh crop đã lưu. Dùng `tim_vung()` + `doc_vung()` — **KHÔNG dùng `doc()`** vì `doc()` chỉ trả về biển đã xác nhận qua ≥2 khung hình nên 1 ảnh sẽ không ra kết quả. Ghi rõ trong UI: đây là chế độ thử 1 ảnh, chưa qua xác nhận đa khung hình |
| 5 | **Module mới `ve_vung_gui.py`** | Hộp thoại `CTkToplevel`: ảnh nền co vừa khung, **kéo chuột trái** để khoanh (hình chữ nhật xanh realtime), nút **Lưu vùng / Chọn lại / Bỏ**, dòng tọa độ tương đối 4 số hiện realtime, `Esc` = hủy, `grab_set()` + `wait_window()` (modal). Chuyển pixel→tương đối theo kích thước **ảnh gốc** |

### Đã sửa — lỗi thật do coordinator phát hiện khi tự chạy

- **Triệu chứng:** sau khi đăng ký người quen xong, nhật ký GUI hiện
  `[LỖI] Lỗi khi đăng ký người quen: main thread is not in main loop`
  và **không** có dòng `> Đã học được: ...` (danh sách người quen không được nạp lại).
- **Nguyên nhân:** `_chay_dang_ky_nguoi_quen` chạy ở **thread nền** nhưng gọi
  `_nap_lai_danh_sach_nguoi_quen()`, mà hàm đó đọc `self.v_faces_dir` — một
  `tkinter.StringVar` → **gọi Tk từ thread không phải thread chính** → Tcl ném
  `RuntimeError`.
- **Cách sửa:** thread nền **không** gọi hàm đó nữa mà đẩy
  `("nap_lai_danh_sach", (faces_dir, threshold))` vào hàng đợi; `_hut_hang_doi()`
  (UI thread) nhận rồi mới gọi. `faces_dir`/`threshold` đã đọc sẵn ở UI thread nên
  không còn đọc biến Tk ở thread nền.
- **Kiểm chứng độ nhạy:** cố tình vô hiệu hóa fix → lỗi **tái hiện đúng** → bật lại fix
  → PASS. Đồng thời rà toàn bộ code v3.3: không còn chỗ nào khác gọi Tk từ thread nền.

### Bằng chứng — coordinator tự chạy + tự xem ảnh bằng mắt

> Bộ script kiểm chứng **của coordinator** (`_kk_kiem_gui_b3.py`, `_kk_kiem_canvas_vung.py`),
> không dùng script của agent.

| Bước | Kết quả |
|---|---|
| `_kk_kiem_canvas_vung.py` | **PASS** — kéo chuột giả lập (120,90)→(330,210) trên canvas 640×480 → hàm trả `(0.1875, 0.1875, 0.515625, 0.4375)`, **sai số 0.0000** |
| Ảnh `_kk_out/kiem_canvas/canvas_vung.png` (coordinator **tự mở xem**) | Hộp thoại "Vẽ vùng canh — kéo chuột rồi bấm Lưu", **hình chữ nhật xanh** đúng chỗ kéo, dòng `0.1875 0.1875 0.5156 0.4375`, 3 nút Lưu vùng / Chọn lại / Bỏ, chữ tiếng Việt **có dấu** không bị cắt |
| `_kk_kiem_gui_b3.py` mục [1] (2 ô xem video) | **PASS** — nhãn đúng, mặc định đúng |
| `_kk_kiem_gui_b3.py` mục [2] (đăng ký người quen) | **PASS** — tạo thật `known_faces_test/KiemThuV33/01.jpg`; log `> Tìm thấy 1 khuôn mặt`, `> Số ảnh đã lưu: 1`, `> Đã học được: KiemThuV33` |
| `_kk_kiem_gui_b3.py` mục [3] (đọc biển số thử) | **PASS** — log `Biển số: 30A-12345 \| tin cậy 0.67 \| số hàng: 2`, ảnh crop đã lưu |
| `_kk_kiem_gui_b3.py` mục [4] (vẽ vùng) | **PASS** — file vùng ghi đúng `0.2000 0.1500 0.8000 0.9500` |
| Chạy lại sau khi sửa lỗi Tk | **4/4 PASS** và **không còn** dòng `main thread is not in main loop`; có lại dòng `> Đã học được: KiemThuV33` |
| Ảnh `_kk_out/kiem_gui_b3/b3_full.png` (coordinator **tự mở xem**) | 3 checkbox dưới khung video — **"Xem trực tiếp"**, **"Xem khung hình kết quả"**, **"Nhận diện tên trên ảnh"** — đều hiện đủ chữ, không chồm nhau |
| Hồi quy `_kk_kiem_gui_batch_preview.py` | **PASS** — khung hình hiện panel **79 lần**, vùng panel **107.129 màu / sáng TB 68,57** → không đen |
| Hồi quy `_kk_kiem_gui_chay_thuc.py` (e2e) | **7/7 PASS** — thời gian chạy 28,3 s |

### CHƯA ĐẠT ở bản 3.3

- **OCR biển số trên ảnh THẬT** — bản này chỉ rút ngắn đường đi (1 nút, vài giây);
  vẫn **chưa có ảnh biển số VN thật** để nghiệm thu.
- **Đăng ký nhiều người cùng lúc** — hiện `cluster(max_people=1)` → 1 người / 1 lần.
- **Nhiều vùng** trong 1 file — hiện 1 vùng (đúng như CLI cũ).
- **Mục 7 (kéo cửa sổ)** và **mục 8 (độ nhận diện video thật)** — vẫn chờ **anh** xác nhận.

## [3.2] — 2026-10-20 (sau 01:30)

`VERSION` trong `cam_ai_core.py` = **3.2**.

Bản này **không thêm tính năng mới**. Đây là bản **sửa 1 lỗi hiển thị** — lỗi mà
coordinator phát hiện khi rà bản PC: panel **"Xem video"** (panel lớn nhất của GUI)
**đen suốt** khi chạy phân tích theo lô.

### Đã sửa — panel "Xem video" đen khi chạy theo lô

- **Triệu chứng:** bấm "Chạy" trên file video → panel lớn nhất bên giữa **đen suốt**,
  không hiện khung hình nào, dù mọi thứ khác chạy đúng (tiến trình chạy, số liệu
  `2 Người / 2 Mặt / 2 Người quen` có giá trị, file `.mp4` + `.csv` vẫn sinh ra).
  Ngoài ra nút **"Tạm dừng"** (thuộc chế độ xem trực tiếp) vẫn hiện ở chế độ lô →
  bấm không có tác dụng nhưng trông như có.
- **Nguyên nhân:** `run_analysis()` chỉ có `progress_cb` + `log`, **không có callback
  khung hình**. GUI chỉ đẩy `("frame", ...)` ở chế độ **xem trực tiếp**.
- **Cách sửa:**
  1. `cam_ai_core.py`: thêm `frame_cb` + `frame_cb_interval` vào `run_analysis()`.
     Khung hình gửi ra là **khung ĐÃ vẽ overlay** (khung người, nhãn tên, vùng canh,
     badge) → hiển thị **y hình pipeline**, khác ảnh thô. `frame_cb is None` →
     **không encode, chi phí = 0** (CLI không bị ảnh hưởng). Callback ném lỗi →
     **không làm chết pipeline**, chỉ báo 1 lần.
  2. `gui.py`: hộp thư **1 ô** (`_khung_hinh_moi` + `threading.Lock` + `_khung_hinh_seq`)
     thay vì `self.queue` — queue không giới hạn sẽ **phình bộ nhớ** khi quét video
     dài (~100 KB/khung × hàng chục nghìn khung).
  3. `gui.py`: giới hạn **10 fps** (`KHOUNG_HINH_FPS = 10`).
  4. `gui.py`: nút "Tạm dừng" **ẩn** ở chế độ lô (`_cap_nhat_nut_tam_dung_xem()`).

### Bằng chứng — coordinator tự chạy + tự xem ảnh bằng mắt

| Bước | Kết quả |
|---|---|
| `_kk_kiem_gui_batch_preview.py` (GUI chế độ lô, `v_xem_video="0"`) | **PASS** — khung hình hiện lên panel **82 lần**; vùng panel đo được **118.735 màu đơn sắc**, sáng TB **73,95**, max 255 / min 0 → **KHÔNG đen** |
| Ảnh `v5_dang_chay.png` (coordinator **tự mở xem**) | Khung hình thật + khung tím `Người 1..4`, khung xanh mặt với nhãn **An** / **Binh**, badge `Người: 4 \| Mặt: 2 \| Vào: 0 \| Ra: 0` |
| Vùng panel cắt riêng `v5_vung_khung_hinh.png` | Ảnh thật, **không có vùng đen nào** |
| Nút "Tạm dừng" trong chế độ lô | `hien_thi = False` → đã ẩn |
| `_kk_kiem_gui_chay_thuc.py` (bộ e2e đầy đủ) | **7/7 PASS** (thêm mục [7] đo vùng panel) — video `h264,960,540`, CSV 251 dòng, 250 frame đọc được |
| Callback ném lỗi | Pipeline **vẫn chạy hết 250 khung**, không chết |

### Chi phí — đo thật (video 960×540, yolo11n + ArcFace, RTX 3090)

> Số đo lấy từ `_kk_do_chi_phi_frame_cb.py`: có **warm-up** (nạp model + mở CUDA) rồi
> chạy **2 vòng**, lấy **vòng 2** (máy đã nóng). Bản đầu tiên của script đo bị sai
> (lỗi của script, không phải của app) → đã sửa và đo lại.

| Cấu hình | Thời gian | Khung/s | Callback gọi | Ghi chú |
|---|---|---|---|---|
| Không `frame_cb` (CLI) | 27,01 s | **9,26** | 0 | không encode → không tốn thêm |
| `frame_cb` mỗi khung | 28,63 s | **8,73** | 250 / 250 | −5,7% so với CLI |
| `frame_cb` giới hạn 10 fps | 29,27 s | **8,54** | 147 / 250 (~59%) | −7,7% so với CLI — **mức GUI thật dùng** |

**CẢNH BÁO về độ chính xác:** nhiễu đo giữa hai lần chạy **cùng cấu hình** là
~3–4% (vòng 1 của chính lần đo này cho 8,79 / 8,41 / 8,05 khung/s). Vì vậy:
- Chênh lệch **5,7%–7,7%** so với CLI là **con số đo thật nhưng nằm gần ngưỡng nhiễu**
  → **hao tổn thực tế nằm trong khoảng 3–8%**.
- Chênh lệch giữa "mỗi khung" và "giới hạn 10 fps" **nằm trong nhiễu** → không khẳng
  định được 10 fps nhanh hơn bao nhiêu.
- Con số **chắc chắn** là chi phí encode đo riêng: **2,80 ms/khung** (JPEG q=80,
  117 KB/khung) → 250 khung = **0,7 s**.

Vì `frame_cb is None` ở CLI nên **lệnh `app.py` không bị ảnh hưởng gì cả** — phần
chi phí nằm ở đúng chế độ GUI là chế độ cần nó.

### CHƯA ĐẠT (không thay đổi so với 3.1)

- **Mục 7** — cảm giác kéo cửa sổ: chỉ có số đo, **anh phải tự xác nhận**.
- **Mục 8** — độ nhận diện trên video thật: cần video thật của anh (xem `PROJECT_STATE.md` mục 2.3).
- **OCR biển số Việt Nam**: cần ảnh biển số VN thật (10 ảnh kiểm chứng hiện là **ảnh giả**).

## [3.1] — 2026-10-20 (sau 00:40)

`VERSION` trong `cam_ai_core.py` = **3.1**.

Bản này **không thêm tính năng mới**. Đây là bản **sửa 3 lỗi chết app** mà coordinator
tìm được khi **rà toàn bộ bản PC** theo đúng yêu cầu của anh: *"chuẩn xem bản PC có
tính năng nào chạy được là được rồi"*.

### Rà bản PC — coordinator tự chạy, không tin báo cáo agent

| Vòng | Nội dung | Kết quả |
|---|---|---|
| Batch A | 14 lệnh lõi & vùng (`--no-face`, `--vung`, `--vung-nhay`, `--lop`, `--tach-o`, `--doc-bien-so`, `--tu-chup`, `--tu-luu-clip`, `--bat-canh-bao`, `--pixelate`, `--thiet-bi cpu`, `--model`, + chạy có nhận diện mặt) | **14/14 EXIT=0** |
| Batch B | 12 lệnh còn lại (`--nhan-vat-the`, `--lop` nhiều lớp, `--clip-giay`, `--clip-ghi-tat-ca`, `--canh-bao-*`, `--face-every`, `--min-face`, `--vung-bien-so`, `--tu-chup-dir`, `--bien-so-tin-cay`, `--pixelate --vung`) | **12/12 EXIT=0** |
| Batch OCR | 6 script kiểm chứng OCR | **6/6 PASS** (10/10, 16/16, 0/6 sai, ROI 2,5 vs 7,5 ms/khung) |
| GUI | Bấm nút "Chạy" thật trên GUI, chụp ảnh, **coordinator tự xem bằng mắt** | `▶ Đang chạy` → `✔ Xong`, `247/250 · 99%`, `2 Người / 2 Mặt / 2 Người quen`, file `.mp4` 16.247.979 B + `.csv` sinh ra |

Mọi video kết quả đều **H.264 960×540** (`ffprobe`), CSV đều **251 dòng × 10 cột**.

### Đã sửa — 3 lỗi chết app

#### 1. Đường dẫn tương đối bị phân giải theo thư mục đang chạy

- **Triệu chứng:** chạy `app.py` từ thư mục khác (double-click từ Explorer, shortcut,
  service/CI) → **exit 1** với `[loi] khong thay bo model ArcFace`, dù model đã có
  đủ trên đĩa. `known_faces`, `models/...`, `yolo11n.pt`, `vung.txt` đều bị ảnh hưởng.
- **Nguyên nhân:** `face_engine.py` có `MODEL_DIRS = ("models/face_core", ...)` và
  `resolve_model_dir()` kiểm tra bằng `os.path.isdir()` → theo **CWD**.
- **Cách sửa:** thêm file mới **`duong_dan.py`** làm nguồn sự thật duy nhất:
  - `APP_DIR` = thư mục gốc dự án (không phụ thuộc CWD).
  - `chuan_hoa_duong_dan(path)` — đường dẫn **tuyệt đối giữ nguyên**; đường dẫn
    **tương đối** ưu tiên bản trong CWD → không có thì bản trong `APP_DIR` → không có
    ở đâu cả thì **giữ nguyên** để lỗi báo đúng chỗ người dùng trỏ tới (không tự bịa).
  - `duong_dan_app(path)` — luôn nối với `APP_DIR` cho tài nguyên nội bộ.
  - `face_engine.py`: `MODEL_DIRS` thành đường dẫn tuyệt đối theo `APP_DIR`;
    `resolve_model_dir()` **in ra các đường dẫn đã thử** khi không tìm thấy.
  - `app.py`: thêm `_chuan_hoa_input()` / `_chuan_hoa_output()`; `--output` mặc định
    `None` → `APP_DIR\output.mp4`; chuẩn hoá `--input/--faces/--model/--vung`.
  - `cam_ai_core.py`: `AnalysisConfig.__post_init__` chuẩn hoá `faces_dir` + `model`.
  - `dang_ky_anh.py`, `ve_vung.py`, `model_info.py`, `gui.py` dùng chung `APP_DIR`.
- **Kiểm chứng:** CWD = `C:\Windows` **có nhận diện mặt** → **EXIT=0**,
  `[model] H:\AI Project\cam-ai\models\face_core | GPU | detection:CUDA | genderage:CUDA
  | recognition:CUDA`, CSV 250 dòng, cột `nguoi_quen` = **"An | Binh"**.

#### 2. App không tự tạo thư mục output

- **Triệu chứng:** `--output` trỏ vào thư mục chưa tồn tại → `[loi] khong gia duoc
  file video ket qua: ...` — không nói nguyên nhân là thiếu thư mục.
- **Nguyên nhân:** `cv2.VideoWriter` **không tự tạo thư mục**.
- **Cách sửa:** `cam_ai_core.py` thêm `tao_thu_muc_cha()`, gọi **trước** khi mở
  `VideoWriter` và **trước** khi ghi CSV; lỗi writer/CSV giờ **nêu rõ thư mục cha**
  và bọc trong `CamAIError` có thông điệp rõ ràng.
- **Kiểm chứng:** CWD = `C:\Windows` + thư mục output chưa tồn tại → **EXIT=0**,
  thư mục được tạo, có cả `.mp4` + `.csv`.

#### 3. `--tu-luu-clip` xoá mất video kết quả (nhưng exit 0)

- **Triệu chứng:** `--tu-luu-clip DIR` mà `DIR` **trùng** thư mục ghi video kết quả →
  log `[clip] da don 1 file .part.mp4 con sot lai` + `[video] ⚠ không ghi được video
  kết quả`; **exit 0 nhưng file video kết quả biến mất**.
- **Nguyên nhân:** `don_file_tam_trong_thu_muc()` xoá **mọi** `*.part.mp4` trong thư mục,
  kể cả file tạm của video kết quả đang được `VideoWriter` giữ.
- **Cách sửa:**
  - Tham số mới `giu=(...)` — danh sách đường dẫn tuyệt đối **không được xoá**;
    so sánh bằng `os.path.abspath` + `os.path.normcase` (Windows không phân biệt
    hoa/thường).
  - **Lớp bảo vệ thứ hai:** registry `_FILE_DANG_GHI` — mọi `VideoWriter` đang ghi trong
    tiến trình đều đăng ký file `.part.mp4` của mình, nên **không cleanup path nào**
    xoá được file đang được ghi, kể cả khi sau này có chỗ gọi quên truyền `giu`.
  - Vòng dọn bọc `try/except` từng file (trước đó 1 file xoá lỗi làm hỏng cả vòng dọn).
- **Kiểm chứng:** chạy lại B3 (CWD = `C:\Windows`) → file rác `rac_gi_20250101.part.mp4`
  **bị xoá** (`da don 1 file .part.mp4 con sot lai`) **và** `ket_qua_ket_qua.mp4`
  **16.253.729 B vẫn còn**, `ffprobe` → `h264,960,540`.

### Sửa nhỏ

- `_kk_kiem_bien_so.py`: ép UTF-8 cho stdout/stderr (script chạy xong exit 0).
  Đây là lỗi **của script kiểm chứng**, không phải của app — `app.py` đã có
  `_chuan_hoa_console()` từ trước.

### CHƯA ĐẠT / việc còn mở

- **Panel "Xem video" trong GUI đen khi chạy phân tích theo lô.** Tìm ra khi rà bản PC
  2026-10-20: `run_analysis()` chỉ có `progress_cb` + `log`, **không có callback khung
  hình**; GUI chỉ đẩy `("frame", ...)` ở chế độ **xem trực tiếp** (`gui.py:3631`).
  Ngoài ra nút "Tạm dừng" (thuộc chế độ trực tiếp) vẫn hiện ở chế độ lô.
  → Cần thêm callback khung hình + đẩy vào GUI. **Chưa sửa** (xem `PROJECT_STATE.md`
  mục 2.1e mục E và mục 8).
- Mục 7 (kéo cửa sổ) + mục 8 (độ nhận diện video thật) + OCR biển số trên **ảnh thật**
  vẫn **chờ anh xác nhận / chờ ảnh thật**.

## [3.0] — 2026-10-19 (sau 18:00)

`VERSION` trong `cam_ai_core.py` = **3.0**.

Bản này thêm **2 nhóm tính năng lớn** (đọc biển số xe Việt Nam + tự chụp ảnh sự
kiện) và **sửa 3 lỗi nghiêm trọng** trong pipeline OCR biển số mà coordinator phát
hiện bằng **đo thật**, không phải bằng đọc code.

### Đã thêm — đọc biển số xe Việt Nam (mặc định TẮT)

- Module mới `bien_so.py` (~41 KB):
  - `BoDocBienSo` — nạp 2 engine OCR, tìm vùng biển, đọc, chuẩn hoá, lưu ảnh crop.
  - `KetQuaBienSo` — `chuoi`, `chuoi_goc`, `tin_cay`, `khung`, `duong_dan`, `so_hang`, `nguon`.
  - `chuan_hoa_bien_so()` — chuẩn hoá về mẫu VN `2 số + 1 chữ + 4/5 số`.
  - `ve_khung_bien_so()` — vẽ khung + nhãn bằng **PIL** (KHÔNG `cv2.putText`),
    chữ tiếng Việt **có dấu**.
  - `tach_hang()` — gom mảnh chữ OCR về đúng thứ tự đọc (biển 1 hàng / 2 hàng).
- Lõi `cam_ai_core.py`:
  - `AnalysisConfig` (đặt **cuối** dataclass để không đổi thứ tự vị trí cũ):
    `doc_bien_so`, `bien_so_dir`, `bien_so_tin_cay`, `bien_so_nhoan_lai_giay`,
    `vung_bien_so`, `tu_chup_dir`, `tu_chup_nhoan_lai_giay`.
  - `AnalysisResult.bien_so` + `AnalysisResult.anh_su_kien`.
  - `CSV_FIELDS_BIEN_SO = ["bien_so", "so_bien_so"]` — thêm **2 cột ở CUỐI**, chỉ khi bật.
  - Nối `BoDocBienSo` + `TuChupAnh` trong `try/except` **fail-safe**: `bien_so.py` hỏng
    thì phân tích vẫn chạy, chỉ mất tính năng đọc biển số.
  - **Mặc định TẮT** → CSV vẫn đúng **251 dòng × 10 cột** như bản 2.8.
- Module mới `tu_chup.py` — `TuChupAnh(thu_muc, nhoan_lai_giay=10.0, log=...)`:
  tự lưu ảnh khi có sự kiện, mỗi loại sự kiện chụp 1 lần, kèm file
  `_bang_ke_chup.csv` ghi lại lúc chụp.
- CLI `app.py` — **8 cờ mới**, mặc định TẮT, tiếng Việt có dấu:
  `--doc-bien-so`, `--bien-so-dir`, `--bien-so-tin-cay`, `--bien-so-nhoan-lai-giay`,
  `--vung-bien-so`, `--tu-chup`, `--tu-chup-dir`, `--tu-chup-nhoan-lai-giay`.
- GUI `gui.py` — 2 nhóm mới: **"Đọc biển số xe"** và **"Tự chụp ảnh khi có sự kiện"**,
  kèm bản dịch Anh trong `DICH_VI_EN`.

### Sửa 3 lỗi nghiêm trọng trong pipeline OCR (đều do coordinator đo thật)

1. **Dùng nhầm engine OCR → chậm ~100 lần.** `nap()` dùng `RapidOCR()` (có tìm
   chữ) cho crop **đã định vị sẵn**. Đo thật: **1473 ms → 10.5 ms/crop**.
   RapidOCR 1.2.3 chỉ đọc `use_text_det` **lúc khởi tạo**, lúc gọi thì bỏ qua →
   phải có **2 engine riêng** (chỉ-đọc + có-tìm-chữ).
2. **`chuan_hoa_bien_so` BỊA biển số.** Biển Đức `"MS WL 345"` bị trả về
   `"50W-1345"` — hợp lệ về hình thức biển VN nhưng là bịa. Nay **tuyệt đối không
   thêm/bớt ký tự**, chỉ sửa `O/I/L` **tại vị trí bắt buộc** và **chỉ khi phần còn
   lại khớp mẫu**; không khớp mẫu → trả `""`.
3. **`app.py --help` crash.** Dấu `%` trong help string của argparse phải escape
   thành `%%` → `ValueError: unsupported format character 't'`. Đã sửa.

### Đo thật — OCR biển số Việt Nam

Chưa có **ảnh biển số VN thật** từ anh, nên coordinator tạo **10 ảnh biển số VN
giả** (`_kk_lam_bien_so_gia.py`, PIL, font Arial Bold) để kiểm chứng logic:

| Ảnh | Kết quả |
|---|---|
| 2 hàng `30A`/`12345` | PASS `30A-12345` (tc 0.67) |
| 2 hàng `51H`/`98765` | PASS `51H-98765` (tc 0.74) |
| 2 hàng `30A`/`1234` | PASS `30A-1234` (tc 0.67) |
| 2 hàng `29B`/`45678` | PASS `29B-45678` (tc 0.72) |
| 1 hàng `30A 12345` | PASS `30A-12345` (tc 0.80) |
| 1 hàng `51H 98765` | PASS `51H-98765` (tc 0.83) |
| có nhiễu | PASS `30A-12345` (tc 0.76) |
| **xoay 6°** | PASS `30A-12345` (tc 0.68) |
| nhỏ 218×46 | PASS `30A-12345` (tc 0.72) |
| phóng 1.6× | PASS `30A-12345` (tc 0.75) |

**Kết quả: 10/10 đúng chuỗi, 0 ảnh nào bị thêm ký tự.**
Bằng chứng: `_kiem_chung/kiem_bien_so_gia.txt`.

> Ảnh giả **không đại diện** ảnh biển số thật (ánh sáng, nhiễu, góc nghiêng, độ nét
> của camera). Vẫn **cần ảnh thật từ anh** để chốt.

### Mở rộng: ảnh biển số xoay

- Xoay ≤ ~7° → đọc đúng (đã đo: ±4°, +7° PASS).
- Xoay ~11° → OCR đọc **sai 1 số** nhưng chuỗi sai **vẫn khớp mẫu VN**
  (`"30A 12346"` → `"30A-12346"`) → nguy cơ **ghi sai biển số** vào báo cáo.
  Bằng chứng: `_kiem_chung/plate_gia/ket_qua_xoay_vn_1hang_30A_12345_+11do.png`.
- Vì vậy đã thêm cơ chế **xác nhận đa khung hình**: chỉ chuỗi xuất hiện ở
  **≥ 2 khung hình liên tiếp** mới coi là đọc chắc và mới ghi vào CSV.

### Đính chính — con số "9.4 ms/ảnh" từng báo trước đây

Con số đó là của engine **chỉ đọc**. Pipeline cũ dùng engine **có tìm chữ** →
thực tế **1–5 giây/crop**. Số đo phải đo trên **đúng đường code sản phẩm**.

### Đọc biển số KHÔNG làm khựng pipeline (đo lại thật)

Pha **tìm vùng biển** ban đầu chạy **đồng bộ** ngay trên luồng phân tích → mỗi khung
hình phải chờ. Đo thật trên `video_test.mp4` (250 khung):

| Chế độ | Trước | Sau (tb/khung) | Sau (khung chậm nhất) |
|---|---|---|---|
| Có ROI | **680,9 ms** | **5,2 ms** | **0,9 ms** |
| Không ROI | **1916,6 ms** | **7,5 ms** | **1,5 ms** |

Cách sửa (chỉ trong `bien_so.py`):
- Tìm vùng chuyển sang **luồng nền daemon** (ghim `BELOW_NORMAL`, giới hạn 2 core).
- **Cache vùng** theo toạ độ tương đối, TTL 10 giây → không tìm lại mỗi khung.
- **Hạn chi phí 50 ms** cho 1 lượt OCR, **tối đa 8 lượt OCR** mỗi lần quét,
  **giới hạn diện tích vùng 250.000 px** (vùng rộng >60.000 px → tìm nền).
- `threading.Lock` quanh **từng** engine OCR (RapidOCR không thread-safe).

**Chi phí đọc 1 biển số** (biển `30A-12345` 440×100 trong khung 640×480, cả 3 chế độ
đều đọc đúng chuỗi):

| Chế độ | median | p95 | max |
|---|---|---|---|
| Không ROI | 14,47 ms | 23,34 ms | **62,14 ms** |
| ROI nhỏ 44.000 px | 10,22 ms | 14,49 ms | **17,69 ms** |
| ROI rộng 0,05–0,95 | 9,01 ms | 18,75 ms | **46,06 ms** |

**Đánh đổi còn lại (đã ghi trong `ISSUE_LOG.md`):** cache vùng bỏ sót biển mới ~2 s;
vùng tìm được là khung **CHỮ** nên biển 2 hàng có thể ghép sai thứ tự; hạn chi phí
50 ms có thể cắt trường hợp biển 2 hàng (đo thật ~54 ms).

### Sửa lỗi ô gợi ý trong ô nhập không hiện

Ô "Vùng cần quét" và ô "Danh sách lớp cần nhận" không hiện dòng gợi ý khi để trống.

**Nguyên nhân:** `customtkinter 5.2.2` chỉ kích hoạt placeholder khi
`textvariable is None or textvariable == ""`; `tkinter.StringVar` **không định nghĩa
`__eq__`** → mọi `CTkEntry` có `textvariable` **không bao giờ** hiện placeholder.
(Cách sửa sai đã thử — chèn chu placeholder bằng `insert()` — làm nhiễu biến thành
`"HUONG DAN GIUONGab"`.)

**Đã sửa:** lớp mới `GoiYTronO` trong `gui.py` — 1 `CTkLabel` phủ lên ô,
`textvariable` luôn sạch, tự ẩn/hiện theo biến, kèm tooltip.

Ba lỗi con đã sửa kèm: nền lệch màu (lấy màu từ bảng màu dự án `MAU["the_phu"]`
thay vì `entry.cget("fg_color")` — theme chốt sau khi dựng form); `place(width=…, height=…)`
raise `ValueError` (đưa `height=24` vào constructor); chữ bị cắt (`anchor="nw"` +
`place(x=12, y=2)`).

Gợi ý dùng dạng **ngắn** vì ô chỉ rộng 102 px: "tự tìm" (31 px) và "mặc định"
(49 px); "để trống = tự tìm trong khung" rộng 159 px → không vừa. Giải thích đầy đủ
nằm ở ghi chú dưới ô + tooltip.

### Ghi chú tốc độ OCR trên GUI dùng số đo thật

Thay con số mơ hồ "20–430 ms" bằng số đo thật (2 chỗ, kèm bản dịch Anh):

> "Tốc độ: đọc biển số chạy ở luồng nền nên không làm khựng video. Mỗi lần quét tốn
> 9–15 ms, khung hình chậm nhất 62 ms (đo thật trên máy này ngày 19/10/2026). Lúc bật
> lần đầu máy phải nạp model nên khựng khoảng 1–2 giây."

Kèm 3 bản dịch Anh còn thiếu của phần tính năng mới. Kiểm chứng tự động bằng
`_kk_kiem_dich_ghi_y.py` (AST đọc mọi lệnh `self._ghi_y(...)`): **30/30** ghi chú đã
có bản dịch Anh, **0 thiếu**.

### Hồi quy bản 3.0 — coordinator tự chạy

| Kiểm tra | Kết quả |
|---|---|
| `py_compile` 5 file lõi | `cam_ai_core.py`, `gui.py`, `app.py`, `bien_so.py`, `tu_chup.py` → **exit 0** |
| 4 lệnh hồi quy CLI | Tất cả **exit 0**; `--help` in đủ cả 8 cờ biển số/tự chụp, không crash |
| `_kiem_tra_gui.py` | **4/4 PASS**; cửa sổ 1610×980; tiêu đề `CamAI v3.0 — Phân tích video giám sát` |
| Chấn lý `chuan_hoa_bien_so` | Chuẩn hoá **28/28**; biển VN **16/16**; biển nước ngoài đọc sai **0/6** |
| Xác nhận đa khung hình | **PASS** — ảnh nghiêng 11° bị cơ chế `mau_thuan` chặn |
| 10 ảnh biển số VN giả | **10/10 PASS**, **0** ảnh bị thêm ký tự |
| Artifact CSV/MP4 | `git status --short -- '*.csv' '*.mp4'` → **rỗng** (không file nào bị đổi) |

### Tự kiểm chứng bằng mắt — tự chụp ảnh + Excel/HTML xem lại

Coordinator **tự chạy lại code hiện tại** và **tự xem bằng mắt** hai tính năng vốn
mới chỉ dựa trên báo cáo của subagent:

**1. Tự chụp ảnh khi có sự kiện (`--tu-chup`) → chạy legit**

```powershell
.venv\Scripts\python.exe -W ignore app.py --input video_test.mp4 --vung vung.txt --tu-chup --tu-chup-dir _kk_out\tu_chup_thuc_te
```

| Kiểm tra | Kết quả |
|---|---|
| File sinh ra | `su_kien_20261019_220301_vao_vung_nguoi1.jpg` — **157.074 B**, 960×540 |
| Số màu đơn sắc | **33.985** (không phải ảnh đen) |
| Trung bình BGR | `[114.5, 114.6, 115.2]` |
| **Coordinator tự xem** | thấy rõ 2 người + overlay tiếng Việt **có dấu**: "An \| Nam 67", "Binh \| Nam 52" |
| Bảng kế CSV | `loai_su_kien=vao_vung`, `ten_hien_thi=Có người vào vùng canh`, `so_nguoi=1` |

**Phát hiện quan trọng:** 6 ảnh cũ ở `_kk_out/ocr_thu/su_kien/`
(`su_kien_2026*_vua_toi/vuot_vung.jpg`, 5.427 B) đo ra là **ẢNH ĐEN HOÀN TOÀN**
(1 màu đơn sắc, max=0, min=0) và tên sự kiện **không tồn tại** trong `LOAI_SU_KIEN`
hiện tại → là artifact của **prototype cũ**, **không phải bằng chứng**. Đã ghi
cảnh báo trong `PROJECT_STATE.md` mục 2.1d + `ISSUE_LOG.md`.

**2. Xuất Excel + HTML xem lại → chạy legit**

| Kiểm tra | Kết quả |
|---|---|
| Excel | `one-by-one-person-detection_tong_ket.xlsx` (12.802 B) đọc bằng openpyxl → **3 sheet có số thật**: `Tong ket` 24×4, `Theo gio` 7×6, `Cu theo giay` 144×8; tiêu đề "BAO CAO TONG KET - CAM" |
| HTML | `one-by-one-person-detection_xem_lai.html` (35.389 B) — **coordinator mở bằng browser thật** |
| **Coordinator tự xem** | render đúng: "1.394 khung hình · 02:19 giây · 0 sự kiện đáng chú ý"; thẻ số liệu KHUNG HÌNH 1.394, GIÂY ĐÔNG NHẤT 00:06, TB 0,74 người, NGƯỜI QUEN 2 (Bình, An); biểu đồ "Số người theo thời gian" |
| Scroll tới đáy | lần 1 `moved=true, actualDeltaY=486, atEnd=true`; lần 2 `moved=false` → đã tới đáy |

**3. Tạo `USE_CASE.md`** (8.235 B) — bản ghi use case chung + tầng nền tảng để lần
sau bí thì lôi ra làm:
- Mục 1: bảng **10 use case chung** đa lĩnh vực (an ninh khu vực, bán lẻ, kho/logistics,
  giao thông, nhà xưởng, trường học/y tế, nuôi trồng, kiểm tra tuân thủ, giao nhận,
  bàn giao khách) — cột "đã có sẵn trong app" + "cần thêm".
- Mục 2: bảng **12 tầng nền tảng N1–N12** + thứ tự ưu tiên
  `N1 → N2 → N8 → N4 → N9 → N3 → N5 → N7 → N6 → N11 → N12 → N10`.
- Mục 3: 8 tính năng AI mở rộng (PPE, Re-ID, segmentation, OCR tổng quát, đếm hàng hoá,
  đếm gia súc, đo khoảng cách, phát hiện hành vi).
- Mục 4: 6 nguyên tắc khi thêm tính năng mới.
- Mục 5: cấu trúc bàn giao nhiều khách (**1 lõi + 1 file cấu hình** .json/.ini).

### Sửa lỗi codec video — trình duyệt không phát được video trong báo cáo xem lại

**Lỗi thật, do coordinator phát hiện bằng cách mở báo cáo bằng browser thật** (không
phải đọc code, không phải tin báo cáo subagent):

| Kiểm tra | Trước khi sửa | Sau khi sửa |
|---|---|---|
| `ffprobe` file video kết quả | `codec_name=mpeg4` (MPEG-4 **Part 2**), 768×432 | **`codec_name=h264`**, 960×540, 10,0 s |
| Thẻ `<video>` trong `*_xem_lai.html` | **"Unable to play media."**, controls `disabled: true`, scrubber **"total time: 0:00"** | **không còn lỗi**, controls bật, scrubber **"total time: 0:10"** |
| Console trình duyệt (`error` + `warn`) | — | **0 entries** |
| `ffmpeg -i <file> -f null -` | — | **exit 0** (decode sạch) |

**Nguyên nhân:** `cam_ai_core.py` ghi video bằng fourcc cố định `mp4v` — đó là
**MPEG-4 Part 2**, Chrome/Edge/Firefox **không có decoder** cho codec này (chỉ
VLC/QuickTime phát được) → người dùng mở báo cáo là **không xem được video**.

**Cách sửa:**
- Hàm mới `_fourcc_ket_qua()` trong `cam_ai_core.py` — **probe 1 lần cho cả tiến
  trình, kết quả cache**: ghi file `.mp4` tạm 2 khung hình 64×64 bằng `avc1`, đọc
  4096 byte đầu (và 64 KB cuối nếu cần) tìm chuỗi `b"avc1"` trong box `stsd` →
  có thì dùng **`avc1` (H.264)**, không có thì lùi về `mp4v`. **Mọi lỗi → lùi về
  `mp4v`** (fail-safe tuyệt đối). File probe luôn được xoá.
- Hằng `FOURCC_KET_QUA = "mp4v"` **giữ nguyên giá trị** (có chỗ khác đang import nó),
  nay chỉ là phương án dự phòng.
- Cả video kết quả lẫn clip tự lưu dùng codec đã chọn; **log rõ codec đang dùng**:
  `[video] codec: H.264 (avc1) - trình duyệt phát được video`.
- Chi tiết đầy đủ (bảng đo, bài học) ở `ISSUE_LOG.md` mục "ĐÃ SỬA".

> **Lưu ý khi đọc log:** OpenCV 5.0.0 in đỏ *"Failed to load OpenH264 library"* khi
> ghi `avc1`, **nhưng file ra vẫn là H.264 hợp lệ** (đã kiểm bằng `ffprobe` + browser).
> Không được coi dòng log đỏ đó là lỗi.

### Chưa đạt / chờ anh

- **Chưa có ảnh biển số VN thật** → mục OCR biển số **chưa nghiệm thu được**.
- **Mục 7 (kéo cửa sổ không giật)** và **mục 8 (độ nhận diện video thật)** vẫn
  **chờ anh tự xác nhận** — không tự đánh dấu đạt.

---

## [2.8] — 2026-10-19 (sau 14:00)

`VERSION` trong `cam_ai_core.py` = **2.8**.

### Đã thêm — tuỳ chọn "Nhận người ở xa (chậm hơn)", MẶC ĐỊNH TẮT

Đoạn video demo có cảnh quay drone/xa làm `yolo11n` nhận gần như **0 người**.
Anh xác nhận camera thật là **camera treo tường/trần, quay ngang hoặc chếch xuống
tầm người** → có người ở xa. Đã triển khai tuỳ chọn chia ô.

- Lõi `cam_ai_core.py`:
  - `TACH_O_MAC_DINH = False`, `TACH_O_TRUNG = 0.35`, `TACH_O_DIEM = 0.0`, `TACH_O_IOU = 0.45`.
  - `AnalysisConfig.tach_o = TACH_O_MAC_DINH`.
  - Hàm mới `detect_tach_o(detector, frame, conf)`: chạy **toàn khung** + **2×2 ô có
    chồng lấn**, gộp trùng bằng `cv2.dnn.NMSBoxes`.
- CLI `app.py`: cờ `--tach-o`, nằm trong group "do nhan nguoi o xa", kèm log cảnh báo
  `[tach-o] CHAM HON ~5.3 lan...` khi bật.
- GUI `gui.py`: nhóm mới **"Nhận người ở xa (chậm hơn)"**, biến `self.v_tach_o`
  mặc định `"0"`, có nhãn song ngữ. Thêm vào `danh_sach_nhom()` để
  `_kiem_tra_gui.py` thực sự kiểm tra nhóm này.

**Mặc định vẫn TẮT** để không phá mục tiêu 1 (live view ≥10 fps) đã đạt.

### Đo thật hiệu quả (không phải lý thuyết)

`_kk_kiem_tach_o.py` chạy đúng hàm sản phẩm `detect_tach_o`, số người trung bình/khung:

| Video | Nền (toàn khung) | Có `--tach-o` |
|---|---:|---:|
| `dam-dong.mp4` | 3.0 | **5.4** |
| `xe-co-giao-thong.mp4` | 1.0 | **4.6** |
| `tre-em-san-choi.mp4` | 9.4 | 8.2 |
| `nguoi-dung-cho.mp4` | 10.1 | 9.9 |

Kết luận trung thực: **cải thiện rõ ở cự ly xa, gần như không đổi ở cự ly gần**.
`nguoi-di-lai` vẫn rất yếu vì người quá nhỏ. Chậm khoảng **5.3 lần**.

### Benchmark 4 phương án — loại 3

| Cách | `nguoi-di-lai` | `dam-dong` | `xe-co` | `tre-em` | ms/khung |
|---|---:|---:|---:|---:|---:|
| `yolo11n` toàn khung (nền) | 0.0 | 3.0 | 1.0 | 9.4 | ~32 |
| `yolo11s` | 0.6 | 2.6 | 1.2 | 10.6 | ~40 |
| Phóng to ×2 | 0.0 | 3.0 | 1.0 | 9.4 | ~46 |
| Chia ô 2×2, chỉ ô | 0.5 | 5.1 | 6.0 | 4.5 | ~146 |
| Chia ô 3×3, chỉ ô | 1.6 | 10.6 | 9.6 | 7.1 | ~320 |
| **Toàn khung + ô 2×2, gộp NMS** | 0.5 | **6.5** | **6.8** | 10.0 | ~170 |

- `yolo11s` **không giúp** (`dam-dong` còn tệ hơn) → không đổi model.
- Phóng to ×2 **vô dụng** vì ultralytics tự resize về `imgsz=640`.
- Chia ô **một mình** làm hỏng video gần (người bị cắt ở rãnh giữa các ô).
- Giữ: toàn khung + 2×2 ô có chồng lấn + NMS.

### Hai lỗi trong code vừa viết — đã phát hiện và sửa

1. **Ô chỉ phủ 70% khung hình.** Sai lầm ban đầu đặt `buoc_x = cw`, `buoc_y = ch`
   khiến 4 ô chỉ phủ 3/4 khung. Sửa thành `buoc_x = w - cw`, `buoc_y = h - ch`.
   Kiểm lại: ô ngang `[0, 624]`, ô dọc `[0, 351]`, ô `336x189` trên khung `960x540`.
2. **NMS loại nhầm nhãn.** Truyền `score_threshold=0.45` khiến mọi nhãn có
   `conf < 0.45` bị xoá dù ngưỡng nhận gốc là `0.25`. Sửa `TACH_O_DIEM = 0.0`
   (chỉ gộp trùng, không loại nhãn), `TACH_O_IOU = 0.45` cho phần gộp.

### Hồi quy bản 2.8 — tự chạy lại, không tin báo cáo

- **Live view đo lại 300 s ở bản 2.8: `14.54 fps`** (giai đoạn ổn định 294.3 s), min
  12 fps/giây, **0/294 giây** dưới 10 fps, 4279 khung vẽ lên UI, nạp model 6.0 s.
  Bản 2.7 là 14.34 fps → **nhánh `--tach-o` không làm giảm fps khi để TẮT**, đúng như
  thiết kế. Bằng chứng: `_kiem_chung/fps_fps_nghiemthu_300s_v28_full.txt`.
  *(Lần chạy đầu của lệnh này chết vì em truyền cờ `--khong-tmp` trong khi script đọc
  tham số theo vị trí — đã ghi vào `ISSUE_LOG.md`.)*
- 4 lệnh `app.py` hồi quy: `EXIT_L1..L4 = 0`, `--help` dài **70 dòng**.
- CSV `output_bao_cao.csv`: **251 dòng × 10 cột**.
- `_kiem_tra_gui.py`: **4/4 PASS** (`EXIT=0`), nhóm mới được kiểm:
  `[OK ] Nhận người ở xa (chậm hơn) mac_dinh_ban_dau=TAT`.
- `_kk_kiem_boc_cuc.py`: `EXIT=0`, nhỏ nhất **75.4%** (1400×900), tràn widget 0,
  tràn nhãn 0. Ảnh `kk_36_boc_cuc.png` — coordinator tự xem: tiêu đề `CamAI v2.8`,
  checkbox mới **đang tắt**, 14 khung người nhãn tách biệt.
- Encoding `gui.py`, `gui_khung.py`, `cam_ai_core.py`, `app.py`: `BOM=False`, `CR=0`.

### Vẫn CHƯA ĐẠT — cần anh xác nhận

Mục 7 (kéo cửa sổ còn giật hay không) và mục 8 (độ nhận diện trên video thật)
**chưa có xác nhận của anh** → không kết luận XONG.

## [2.7] — 2026-10-19 (sau 09:00)

`VERSION` trong `cam_ai_core.py` = **2.7**.

Nghiệm thu 2.5: 6 mục tự đo **đều đạt**. Mục 7 (anh tự kéo cửa sổ) và mục 8 (anh
tự xác nhận độ nhận diện) **vẫn chờ anh xác nhận** — xem `PROJECT_STATE.md` mục 2.

### Đo thật độ nhận diện trên 7 video — phát hiện hạn chế lớn (CHƯA sửa)
Thêm `_kk_kiem_do_nhan_diem.py`: đo 12 khung mẫu/video, đúng model và ngưỡng bản chạy
thật (`yolo11n.pt`, `conf=0.25`). Kết quả coordinator tự xem bằng mắt:

- **Tốt ở cự ly gần, ít người**: `tre-em-san-choi` (9.2 người/khung), `nguoi-dung-cho`
  (9.0), `cua-hang` (6.5), `video_test.mp4` (3.2, conf trung vị 0.82).
- **Thiếu nặng ở cảnh đông**: `dam-dong` chỉ 2–6 người/khung, conf trung vị 0.35.
- **Hỏng hoàn toàn với quay drone**: `nguoi-di-lai` nhận **0 người ở cả 12 khung** dù hình
  có rõ hàng trăm người. `xe-co-giao-thong` chỉ 6/12 khung có người.

**Không tự ý sửa:** đổi sang `yolo11s/m.pt` sẽ chính xác hơn nhưng chậm hơn và có nguy cơ
mất mục tiêu 1 (live view ≥10 fps) đã đạt. Chờ anh quyết định giữ tốc độ hay đổi lấy
chính xác. Chi tiết 3 phương án: `PROJECT_STATE.md` mục 2.3, `ISSUE_LOG.md`.

Bằng chứng: `_kiem_chung/do_nhan_diem.txt` + 7 ảnh `nhan_diem_<tên>.png`.

### Đã sửa — bố cục: video rớt dưới 70% khi cửa sổ hẹp
Đo thật trên widget GUI đang chạy (`winfo_width`), 3 kích thước cửa sổ:

| Kích thước cửa sổ | Trước | Sau |
|---|---|---|
| 1610×980 | 74.9% | **75.5%** |
| 1400×900 | **69.9% — KHÔNG ĐẠT** | **75.4%** |
| 1900×1040 | 79.5% | **83.2%** |

Nguyên nhân: cột sự kiện đặt `minsize=320` **cố định** nên không co lại khi cửa
sổ hẹp. Sửa bằng `_canh_be_rong_cot_su_kien()` trong `gui.py`:
`b = clamp(200, 320, tổng_bề_ngang × 0.24)`, đặt **cả** `minsize` của cột lẫn
`width` của panel (chỉ đổi `minsize` là vô dụng vì Tk lấy bề rộng widget từ
`reqwidth` do nội dung thẻ sự kiện đòi). Hàm được gọi từ `after_idle` khi dựng
GUI và từ `_khi_keo_cua_so` — kéo cửa sổ phải giữ ≥70% ngay từ frame đầu.

### Đã sửa — nhãn người: sửa đúng nghĩa `LE_TRANH`
`_vuot_nhau()` trong `gui_khung.py` trước đây cho phép nhãn chồm thật tới
`le - 1` px (`a[2] <= b[0] + le`). Sửa thành `a[2] + le <= b[0]` cho cả 4 phép.
Đo lại trên khung hình đông nhất tìm được: **15 người, 15/15 nhãn vẽ được,
0 cặp chồm** (trước sửa: 10 người → 1 cặp chồm 3×9 px).

### Đã thêm — script đo có bằng chứng
- `_kk_kiem_boc_cuc.py` — đo bố cục **và** cả "0 nhãn tràn": B1 đo widget ảnh có
  lọt ra ngoài khung video không, B2 vẽ nhãn thật bằng `ve_nguoi` lên đúng ảnh
  đã resize rồi đếm nhãn toả ra ngoài biên ảnh.
- Báo cáo: `_kiem_chung/kk_36_boc_cuc.txt`, ảnh `kk_36_boc_cuc.png`.

### Gotcha mới ghi vào `PROJECT_STATE.md`
- **Chụp ảnh màn hình phải ép cửa sổ lên trước.** Em đã chụp nhầm ảnh khung bình
  luận YouTube vì cửa sổ CamAI bị Chrome che; nhìn ảnh toàn màn hình mới phát
  hiện. `SetForegroundWindow` bị Windows từ chối từ tiến trình nền, nhưng
  `attributes('-topmost')` do chính tiến trình sở hữu cửa sổ thì luôn được.

## [2.6] — 2026-10-19 (sau 08:00)

`VERSION` trong `cam_ai_core.py` = **2.6**.

### Đã sửa — live view: tìm đúng bottleneck thay vì đoán
- **`PUMP_MS` 120 → 30**. Đây mới là nút thắt thật, **không phải YOLO**.
  Bằng chứng đo được (máy này, video 960×540@25):

  | `PUMP_MS` | fps trung bình |
  |---|---|
  | 120 (cũ) | 5.70 |
  | 80 | 7.55 |
  | 50 | 10.32 |
  | 30 | **12.81** (15.38 giai đoạn ổn định) |

  Vòng bơm mỗi lần chỉ lấy khung hình **cuối** trong hàng đợi, nền trần hiển thị
  = `1000 / PUMP_MS`. Ở 120 ms trần chỉ 8.3 fps — đúng bằng cái ta thấy.
- Giả thuyết ban đầu *"YOLO chạy 2 vòng"* **đã bị đo và bác bỏ**: bật thêm pipeline
  `run_analysis` chỉ làm fps giảm 6.02 → 5.38. YOLO một khung hình 38.5 ms,
  vẽ overlay PIL 15.5 ms, nén JPEG 3.2 ms, giải JPEG 4.5 ms → tổng 63 ms.
  Phần còn lại là phía UI: `PhotoImage` + `configure` khoảng 46 ms mỗi lần bơm.
- Bổ sung số đo giải phẳng để sau này không phải đoán lại:
  `_kk_do_fps_live.py` (đo fps luồng UI) và `_kk_do_chi_phi.py` (đo từng phần).
  Cả hai **không sửa mã nguồn sản phẩm**.

### Đã thêm
- **6 video demo mới** đa thể loại trong `video_mau/moi/`, chuẩn hoá 960×540@25 h264
  yuv420p, bỏ audio, 60–130 giây: đi lại, cửa hàng, xe cộ, xếp hàng, đám đông,
  trẻ em sân chơi. Kèm `NGUON_LICENSE.md` ghi rõ giấy phép từng file.
- `VIDEO_MAU` trong `gui.py` nay có **13 thẻ** (7 cũ + 6 mới).
- `LuoiVideoMau` đổi sang **cuộn ngang**, thẻ kích thước cố định
  (`RONG_THUMB + 18` × `CAO_THUMB + 64`) — thêm video không còn ép nhỏ thẻ.
- Bố cục: `KICH_THUOC_CUA_SO` 1720×960 → **1610×980**, `RONG_COT_TRAI` 358→300,
  `RONG_COT_SU_KIEN` 372→320, `TY_LE_COT_VIDEO` 72→76.
- 4 lỗi giao diện đã sửa: nhãn người chồng nhau, dải badge đáy dính chữ,
  nhãn vùng bị đẩy lệch ~343 px, video chưa đủ lớn.

## [2.5] — 2026-10-19 (sau 18h)

> Nhóm thay đổi GUI + cảnh báo + clip an toàn + `--lop`.
> Xem `PROJECT_STATE.md` mục 2 để biết chính xác chỗ nào đạt, chỗ nào chưa.

### Đã thêm
- `CanhBaoNoi` trong `cam_ai_core.py` — cầu nối `canh_bao.py` vào pipeline. Bắn cảnh báo
  `LY_DO_VUOT_DONG` và `LY_DO_DUNG_LAU`. Mặc định **TẮT**.
- 4 cờ mới trong `AnalysisConfig`: `bat_canh_bao`, `canh_bao_mo_phong`, `canh_bao_go`,
  `canh_bao_gioi_han`. 4 cờ CLI tương ứng trong nhóm `canh bao ngoai`.
- Hàm `duong_dan_tam()` / `chuyen_ten_sau_khi_dong()` / `don_file_tam()` — ghi video ra
  `.part.mp4` rồi mới đổi tên.
- `cai_tin_hieu_dung()` — bắt `SIGTERM` + `SIGBREAK` để dừng mềm.
- `_log_an_toan()` — tự lùi bản không dấu khi console cp1252 không in được tiếng Việt.
- `PanelSuKien` trong `gui_khung.py` — widget timeline sự kiện.
- **Bảng thống kê vùng** đè góc trên trái video: `Trong vùng hiện tại / Trung bình / Đỉnh /
  Đáy / A→B`.
- **Danh sách sự kiện** cột phải: mỗi card có ảnh crop mặt thật + `HH:MM:SS · %` + tên +
  `Event:` + `Gender: · Mask:`.
- Checkbox `Cảnh báo (gửi tin ra ngoài)` trên GUI, mặc định **không tick**, kèm ô
  "Chỉ thử (không gửi thật)", ô gộp tin, ô giới hạn.
- Thư viện video demo: dropdown chữ → **7 thẻ ngang có poster thật**, bấm thẻ là chọn.
  Poster chọn bằng Laplacian variance trên nhiều frame, cache ở `_thumb_cache/`.

### Đã sửa
- **`--lop` bị bỏ qua im lặng** → tự bật `--nhan-vat-the` kèm dòng thông báo; lớp sai thì
  báo lỗi + gợi ý lớp gần đúng + liệt kê lớp có sẵn; trả **mã thoát ≠ 0**.
- **Clip hỏng khi kill** → ghi `.part.mp4`, đổi tên sau khi đóng an toàn. File hỏng không
  còn mang tên `.mp4`. Dọn file `.part.mp4` sót lúc khởi động. Có đường dừng mềm `SIGBREAK`.
- **Chữ dính ở góc phải** → tách badge `Đang chạy` khỏi nhãn tiến trình.
- **Giật kéo cửa sổ** → `PIL.LANCZOS` (39,7 ms) → `cv2.INTER_AREA` + debounce 180 ms +
  freeze frame khi kéo.
- Bố cục GUI viết lại: video + bảng thống kê bên trái, danh sách sự kiện bên phải.
- Bỏ cảnh báo trùng ở tầng GUI (lõi đã gửi sẵn, giữ lại sẽ kêu chuông 2 lần/sự kiện).

### Đã kiểm chứng
- 4 lệnh hồi quy CLI: `EXIT=0` cả 4, đúng kỳ vọng. CSV 251 dòng, 10 cột.
- Test GUI 4/4 PASS.
- `--lop motercycle` → gợi ý `motorcycle`, exit 1. `--lop xyz` → exit 1. `--lop car` → exit 0.
- `--bat-canh-bao --canh-bao-mo-phong` → 1 cảnh báo cho sự kiện kéo ~7 giây.
- Encoding: `gui.py`, `gui_khung.py`, `cam_ai_core.py` đều `BOM=False`, `CR=0`.
- Ảnh `kk_30_timeline.png` — coordinator tự xem: bảng thống kê 5 dòng đúng, timeline sự kiện
  có ảnh crop thật, 6 ô số liệu gọn, 7 thẻ poster còn nguyên.

### CHƯA ĐẠT (xem `PROJECT_STATE.md` mục 2)
- Nhãn người **vẫn chồng lên nhau** trên video — coordinator xác nhận bằng mắt ở 2 vòng.
- Dải nhãn đáy dính chữ `Người quan`.
- Nhãn vùng chồn lên khung người.
- Video chiếm ~63% (không phải 72% như agent tuyên bố), chưa đạt ~75% của mẫu tham chiếu.
- Live view **chưa đạt 10 fps** — bottleneck ở `cam_ai_core.py`.
- Cảm giác giật kéo cửa sổ **chưa được anh xác nhận** (chỉ có số đo).
- Trạng thái khẩu trang luôn `Chưa rõ` — dự án chưa có model.

### Đã bỏ (có thể khôi phục)
- Lưới **"Đối tượng phát hiện"** (ảnh crop + bộ lọc Tất cả/Người/Vật thể/Người quen) — vai
  trò chuyển sang danh sách sự kiện. Class `PanelDoiTuong` còn trong `gui_khung.py`.
- 3 checkbox kênh cảnh báo (Phát chuông / Mở hộp thoại / Telegram) — thay bằng 4 ô khớp cờ lõi.

---

## [2.4] — 2026-10-19

### Đã thêm
- File mới `gui_khung.py` — toàn bộ phần vẽ overlay và panel "Đối tượng phát hiện" tách ra khỏi `gui.py`.
  Vẽ bằng PIL (Pillow) vì `cv2.putText` không hiển thị được tiếng Việt có dấu.
- Khung xem video realtime chiếm phần lớn giao diện, hiện ngay khi bấm **BẤT ĐẦU** (không cần bấm xem).
- Panel **"Đối tượng phát hiện"** ở bên phải: ảnh crop thật của từng người/vật thể, có tên,
  tỉ lệ tin cậy, số lần xuất hiện, badge `QUEN`, và bộ lọc "Tất cả / Người / Vật thể / Người quen".
- Dải số liệu 6 ô lớn: Người, Mặt, Người quen, Vào, Ra, Trong vùng.
- Badge trạng thái màu: `Chưa chạy` / `Đang chạy` / `Xong` / `Lỗi`, kèm tiến trình khung hình.
- Overlay vùng canh đổi màu + đổi chữ theo trạng thái: `VÙNG CẢNH - TRỐNG`, `VÙNG CẢNH - ĐANG CÓ NGƯỜI`,
  `ĐỨNG LÂU · N NGƯỜI`, `VƯỢT NGƯỠNG`.

### Đã sửa
- **Lỗi chết khi mở GUI**: `XEM_VIDEO_BE_RONG` được tham chiếu nhưng chưa định nghĩa.
  GUI crash ngay khi khởi động. Đã bổ sung hằng số.
- Khung detect bám đúng người; nhãn đặt **trên** khung, không che mặt.
- Người quen hiện `Tên · Tuổi · Giới` bằng màu riêng (vàng) so với người lạ (xanh lá).
  Tên được giữ lại theo track ID nên không nhấp nháy khi mất mặt ở vài khung.
- Live view chạy đúng nhịp thời gian thực thay vì quét tối đa, nên khung không bị "giật/đuổi".
- Giảm đỉnh lag khi kéo cửa sổ: `334,9 ms` → `254,6 ms`.
- Bỏ cột trống và cắt chữ trong thanh bên trái.

### Đã kiểm chứng (bằng mắt, không chỉ qua test)
- `05_quen_mat.png` — `An · 48 · Nam` và `Bình · 48 · Nam` hiện rõ trên khung, màu vàng khác người lạ.
- `06_quen_panel.png` — thẻ trong panel đổi từ "Người" sang tên thật, badge `QUEN`.
- `07_quen_trong_vung.png` — vùng đổi cam, badge `ĐỨNG LÂU · 1 NGƯỜI`, ô "Trong vùng" = 1.

### Không đụng
- `cam_ai_core.py` chỉ tăng `VERSION`. Không sửa logic.
- `app.py`, `face_engine.py`, `model_info.py`, `web_server.py` không đổi.

## [2.3] — 2026-10-19

### Đã thêm
- Cửa sổ GUI tự canh giữa trong **vùng làm việc thật** của màn hình, không tràn xuống taskbar.
  Dùng `SPI_GETWORKAREA` (vùng làm việc) và `GetWindowRect` (kích thước thật gồm thanh tiêu đề).
- Hằng `KICH_THUOC_CUA_SO` — một nguồn duy nhất cho cả `geometry()` và lệnh canh giữa, tránh lệch nhau.
- Tài liệu bàn giao: `PROJECT_STATE.md`, `CHANGELOG.md`, `ROADMAP.md`, `ISSUE_LOG.md`.

### Đã sửa
- `_canh_giua_trong_vung_lam_viec()` chỉ chạy khi cửa sổ đã có **đúng** kích thước đã định nghĩa.
  Lúc `__init__`, Tk trả kích thước mặc định 200×200 nên phép tính vị trí bị sai và đứng yên.
- Cửa sổ chính nằm trọn trong vùng làm việc (đáy 1029 < 1040 trên màn hình 2560×1080).

### Đã dọn
- Dừng tiến trình tunnel Cloudflare CamAI. **Không đụng** service `Cloudflared` của dự án khác.
- Xóa `C:\Users\TTC\.cloudflared\config.yml` và file credentials của CamAI.
- Xóa 20 file kiểm thử `_kk_*`.

### Đã kiểm chứng
- 4 lệnh hồi quy: đạt kỳ vọng (vùng 192,81→768,513 · max 2 người · 1 lần vào vùng · đứng lâu 10.0s).
- CSV: 251 dòng, đúng 10 cột.
- Test GUI: 4/4 PASS.
- Web: HTTP 200 ở trang chủ, HTTP 401 khi chưa đăng nhập.

### Đã biết (chưa sửa)
- Xem `ISSUE_LOG.md`.

## [2.2] — 2026-10-18

### Đã thêm
- `web_server.py`: web server local FastAPI tại `127.0.0.1:8787`.
  - Đăng nhập bắt buộc, khóa 5 phút sau 5 lần sai.
  - Cookie phiên 12 giờ, `HttpOnly`.
  - Upload tối đa 300 MB, tên UUID, chặn path traversal.
  - Chạy pipeline trong thread nền, có tạm dừng.
  - Tải CSV / MP4 / XLSX / HTML.
  - Giữ 5 lần chạy gần nhất, tự dọn upload cũ.
- GUI: khung xem video realtime, nút Tạm dừng / Tiếp tục, ghi log hàng loạt.

### Đã sửa
- Bảo mật: xóa `MAT_KHAU_MAC_DINH`, chuyển sang fail-closed — chỉ đọc `CAMAI_PASSWORD`,
  tối thiểu 8 ký tự, thiếu thì in hướng dẫn tiếng Việt và thoát mã 2.
- Sửa so sánh mật khẩu tiếng Việt (chuyển sang so sánh byte UTF-8).
- Sửa cookie còn hạn nhưng F5 không mở màn chính.
- Sửa tên báo cáo lấy nhầm stem của CSV.
- Sửa 7 nút video mẫu bị rỗng.

## [2.1] — trước đó

### Đã thêm
- Khoanh vùng cảnh báo: vẽ khu vực cần canh, có người bước vào là báo.
- Đếm ra/vào, nhận diện người quen, ước lượng tuổi/giới.
- Tự lưu clip, nhận diện vật thể.
- Báo cáo Excel + HTML xem lại.