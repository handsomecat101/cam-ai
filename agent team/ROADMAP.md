# ROADMAP & TIÊU CHÍ NGHIỆM THU — CamAI

> File này là **chuẩn nghiệm thu** của coordinator. Mọi tính năng phải có bằng chứng chạy thật mới được tính là xong.
> Cập nhật: 2026-10-18 · Phiên bản hiện tại: **mã nguồn v2.3** (⚠️ số version trong code **chưa** được nâng — xem E4)

---

## A. ĐÃ CÓ, ĐÃ KIỂM CHỨNG ✅

| # | Tính năng | Bằng chứng |
|---|---|---|
| A1 | Phát hiện người + đếm người (ByteTrack) | `video_test.mp4` chạy đúng, `Nguoi nhieu nhat trong 1 khung hinh: 4` |
| A2 | Đếm người theo lưới ô | đã có từ bản đầu |
| A3 | Đếm ra/vào (LineZone) | đã có từ bản đầu |
| A4 | Nhận diện người quen (ArcFace, ngưỡng 0.40) | `kiem_tra_nhan_dien.py` → 500/500, nhận đúng An + Bình |
| A5 | Ước lượng tuổi / giới tính | video nữ → **1520 nữ / 95 nam**, tuổi TB 36 ✅ khớp nội dung |
| A6 | Làm mờ nền `--pixelate` | đã có |
| A7 | Tự chạy GPU | `[model] models/face_core \| GPU \| detection:CUDA...` |
| A8 | Đăng ký ảnh từ video (`dang_ky_anh.py`) | đã có |
| A9 | Báo cáo CSV 10 cột | MD5 `base1=new1`, `base2=new2`, `base3=new3` (18/10) |
| A10 | Video kết quả đã vẽ khung | đã có |
| A11 | **Khoanh vùng** (`ve_vung.py`) | tọa độ tương đối 0.0–1.0, kéo chuột + nhập tay |
| A12 | **Cảnh báo có người vào vùng** (chặt / nhạy) | `[vung] 192,81 -> 768,513 \| che do chac` / `che do nhay` |
| A13 | **Cảnh báo đông** `--vung-max 2` | `Nguong 2 nguoi: vuot 0 lan` trên `video_test.mp4` |
| A14 | **Cảnh báo đứng lâu** `--canh-lau 3` | `Dung lau hon 3.0s: 1 lan, lan dai nhat 10.0s` — **đo thật**, bug đã sửa (xem B1). ⚠️ Số liệu cũ trong bản ROADMAP trước ("4 lần, dài nhất 2.1s") đo bằng code **còn lỗi** → cần chạy lại trên `people-detection.mp4` |
| A15 | Bộ 9 video mẫu + `kiem_tra_video_mau.py` | quét đủ 9 video, đo số người |
| A16 | **Báo cáo Excel tổng kết** | `bao_cao_tong_ket.py` → 3 sheet `Tong ket`/`Theo gio`/`Cu theo giay`, đều có `freeze='A5'` + autofilter ✅ |
| A17 | **Trang xem lại HTML offline** | đếm trong file: **0** tham chiếu `https://`, **0** `http://`, **0** `fetch`, 1 thẻ `<canvas>` ✅ *(xem B6 — chưa xem bằng mắt)* |
| A18 | **Cảnh báo Telegram + chuông Windows** | `canh_bao.py` có trên đĩa. ⚠️ chưa nối vào GUI, chưa cấu hình token thật |
| A19 | **Sổ đăng ký model tiếng Việt** | `model_info.py` chạy được, in đủ 4 model + cảnh báo dữ liệu giả lập. ⚠️ xem B7 |

---

## B. ĐANG LÀM 🔄

| # | Việc | Agent | Trạng thái | File đang giữ |
|---|---|---|---|---|
| B1 | Sửa bug "đứng lâu" in đúng bằng ngưỡng | Agent A | **Code đã sửa** (`cam_ai_core.py:635-636`), hồi quy pass. **Chưa báo xong** | `cam_ai_core.py` |
| B2 | Tự lưu clip khi có sự kiện | Agent A | **Code đã có** (`ClipRecorder`, `--tu-luu-clip`). Đã sinh 4 clip thử 18/10 17:09. **Chưa xác nhận nội dung clip** | `cam_ai_core.py`, `app.py` |
| B3 | Nhận diện vật thể khác ngoài người | Agent A | **Code đã có** (`--nhan-vat-the`). Chưa có ảnh chụp xác nhận khung/label | `cam_ai_core.py`, `app.py` |
| B4 | Nối báo cáo + cảnh báo + thông tin model vào GUI | Agent A | ❌ **Chưa làm.** `gui.py` chưa import `bao_cao_tong_ket`, `canh_bao`, `model_info` | `gui.py` |
| B5 | Cảnh báo Telegram + chuông Windows | Agent C | File có trên đĩa + `HUONG_DAN_CANH_BAO.md`. Chưa cấu hình token thật | `canh_bao.py` |
| B6 | Xem bằng mắt trang HTML xem lại | — | ❌ **Chưa làm.** Mới kiểm tự động | không sửa file |
| B7 | Sửa version onnxruntime hiển thị sai trong `model_info.py` | Agent D | ❌ **Chưa làm.** In ra `1.20.1`, thực tế `1.23.2` (`ISSUE_LOG.md` #8) | `model_info.py` |

> ⚠️ **Chưa ai báo xong chính thức.** Trước khi coi B1–B3 là nghiệm thu:
> hỏi Agent A, rồi chạy lại 4 lệnh hồi quy (mục E).

---

## C. ROADMAP CÒN PHẢI LÀM — mục tiêu v3.0

Xếp theo giá trị thực tế với anh Tuấn (giám sát an ninh nhà / cửa hàng).

### Ưu tiên 1 — dùng được hằng ngày

| # | Tính năng | Mô tả | Nghiệm thu | Trạng thái |
|---|---|---|---|---|
| C1 ⭐ | **Tự lưu clip khi có chuyện** | Vùng đỏ / đông người / người quen → tự cắt clip 10s, đặt tên theo giờ + lý do | Sinh ra file clip, mở được, đúng 10s, đúng quanh sự kiện | 🟡 code xong, **thiếu xác nhận nội dung** (B2) |
| C2 ⭐ | **Giao diện xem lại** | Video + biểu đồ số người + nhảy tới giây đông nhất | Mở được, biểu đồ vẽ đúng, bấm được | 🟡 code xong, **thiếu xem bằng mắt** (B6) |
| C3 ⭐ | **Nhận diện vật thể (Object Detection)** | Xử lý từ File video & Camera/RTSP stream đơn (xe cộ, đồ vật, thú cưng, người). Xem chi tiết tại `SPEC_OBJECT_DETECTION.md` | Khung + nhãn tiếng Việt rõ nét, phân nhóm chọn lọc, đạt >35 FPS trên RTX 3090, không trễ stream | 🟡 core đã có, **đang triển khai theo spec mới** |
| **C9 ⭐** | **Giao diện rút gọn cho người thường** | Bỏ các tuỳ chọn kỹ thuật khỏi màn hình chính, chỉ giữ: chọn video → bấm chạy → xem kết quả. Mỗi tuỳ chọn nâng cao gói vào nút "Tuỳ chọn khác" | Người không rành công nghệ tự chạy được, không cần đọc hướng dẫn | ❌ **Chưa làm** — `gui.py` ⚠️ Agent A |
| **C10 ⭐** | **Panel "Thông tin model"** | Cho chủ sở hữu thấy: đang dùng model nào, làm gì, file ở đâu, nặng bao nhiêu, thiếu file thì có chạy được không. Lấy từ `model_info.py` | Mở panel ra thấy đủ 4 model + trạng thái + cảnh báo dữ liệu giả lập | ❌ **Chưa làm** — `gui.py` ⚠️ Agent A + `model_info.py` ⚠️ Agent D |
| C11 | **Nút "Xem báo cáo" trong GUI** | Chạy `bao_cao_tong_ket.py` bằng 1 cú bấm rồi mở trang HTML | Bấm là ra file xlsx + html, mở được | ❌ **Chưa làm** — `gui.py` ⚠️ Agent A |
| C12 | **Nút cấu hình cảnh báo trong GUI** | Ô nhập token + chat id, nút kiểm tra | Không phải sửa file `.ini` bằng tay | ❌ **Chưa làm** — `gui.py` ⚠️ Agent A |

### Ưu tiên 2 — nâng cấp đo lường

| # | Tính năng | Mô tả | Nghiệm thu |
|---|---|---|---|
| C4 | **Nhiều vùng cùng lúc** | `--vung` nhận nhiều vùng, đánh số vùng trên video, cảnh báo ghi rõ vùng nào | 3 vùng trên 1 video, mỗi vùng đếm riêng |
| C5 | **Đếm từng cửa riêng** | Đặt được vạch đếm theo toạ độ thay vì cứng giữa khung hình | Vạch vẽ đúng chỗ cửa, đếm vào/ra tách biệt |
| C6 | **Giờ vàng / giờ đen** | Tách báo cáo theo khung giờ anh quan tâm | ⚠️ **Cần thêm cột vào CSV** → **phá quyết định Q1** (`AGENT_CHAT.md`). Phải hỏi anh Tuấn trước |
| C7 | **Theo dõi 1 người cụ thể** | "Bình vào lúc 14:20, ở lại 3 phút rồi đi" | Chọn được người, ra log mốc thời gian |

### Ưu tiên 3 — dọn dẹp & độ tin cậy

| # | Việc | Ghi chú |
|---|---|---|
| C13 | **Nâng `VERSION` lên `"2.3"`** | `cam_ai_core.py:41` vẫn là `"2.2"`. Làm trước tiên khi mở phiên mới |
| C14 | **Cập nhật `README.md`** | Đang ghi **v2.1**, thực tế đã v2.3 |
| C15 | Xoá `known_faces/An` + `known_faces/Binh` | Bắt buộc trước khi dùng thật, nếu không sẽ nhận nhầm người |
| C16 | Viết lại `smoke_test.py` | Đang import `facenet_pytorch` (đã gỡ) + tải ảnh từ Internet → chắc chắn lỗi (`ISSUE_LOG.md` #10) |
| C17 | Đổi `chay_gui.bat` sang `pythonw.exe` | Bỏ cửa sổ console đen (`ISSUE_LOG.md` #6) |
| C18 | Dọn file tạm `_t/`, `_t_canh_bao.*` | ⚠️ `_t_canh_bao.*` thuộc Agent C. Giữ lại `_t/base1-3` làm chuẩn hồi quy |
| C19 | **Test trên video thật của anh** | Đang chỉ test video mẫu (`ISSUE_LOG.md` #9) — đây là **rủi ro lớn nhất** còn lại |

---

## D. CHƯA LÀM ĐƯỢC — nói thẳng với anh

| Tính năng | Vì sao chưa |
|---|---|
| Nhận diện hút thuốc / rút súng / đeo mặt nạ | YOLO11 chỉ biết "người". Cần model chuyên dụng hoặc tự huấn luyện — **đã tìm rất nhiều, không có model offline** |
| Nhận dạng hành vi theo từng người | Cần model hành vi + ReID. Chưa có bản offline |
| Làm nét ảnh ban đêm | Cần model khử nhiễu, chưa có sẵn và không được cài thêm |
| Xem lại trên điện thoại | Camera điện thoại qua browser cần HTTPS → anh đã chọn không làm |
| App điện thoại | Anh đã chốt không làm |
| Kéo-thả file vào GUI | Cần `tkinterdnd2`, không được cài thêm → tạm dùng nút "Chọn video" |

> ⚠️ **Không hứa với anh là sẽ làm được mấy cái trên.**
> Cần model chuyên dụng hoặc tự huấn luyện — đó là công việc riêng, không phải "lắp thêm 1 dòng code".

---

## E. QUY TẮC NGHIỆM THU (bắt buộc)

Một tính năng chỉ được đánh dấu ✅ khi có **cả 3**:

1. **Chạy thật** trên ít nhất 1 video mẫu, không chỉ đọc code.
2. **Dán nguyên văn output thật** vào báo cáo.
3. **Không phá vỡ tính năng cũ** — 4 lệnh hồi quy CLI phải cho output y hệt trước.

**Ngoài ra:** phải phân biệt 3 mức — *chạy được* → *kiểm tự động pass* → ***đã xem bằng mắt***.
Trang HTML xem lại hiện ở **mức 2**. Không được ghi là xong khi chưa có mức 3.

Lệnh hồi quy (luôn chạy sau mỗi thay đổi):
```
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-max 2 --canh-lau 3 --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-nhay --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --no-face
.venv\Scripts\python.exe app.py --help
```
Kỳ vọng dòng đầu quan trọng:
`[vung] 192,81 -> 768,513 | che do chac | toi da 2 nguoi | canh dung lau 3.0s`

Kiểm tra CSV đúng 10 cột (so MD5 với ảnh chụp nền trong `_t/`):
```powershell
cd 'H:\AI Project\cam-ai\_t'
Get-FileHash base1_bao_cao.csv,new1_bao_cao.csv,base2_bao_cao.csv,new2_bao_cao.csv,base3_bao_cao.csv,new3_bao_cao.csv -Algorithm MD5
```
MD5 phải trùng cặp: `base1=new1`, `base2=new2`, `base3=new3`.

### E4 · Sau mỗi nhóm việc xong

Bump version + cập nhật `CHANGELOG.md` + cập nhật `PROJECT_STATE.md` + cập nhật file này +
ghi lỗi mới vào `ISSUE_LOG.md` + ghi quyết định vào `AGENT_CHAT.md`.

⚠️ Quy tắc bảo vệ tài liệu:
- File `.md` và `.py` đều là **UTF-8 không BOM, xuống dòng LF**
- **Không bao giờ** dùng `Get-Content | Set-Content` để sửa file nguồn (`ISSUE_LOG.md` #3)
- Dùng tool `write` / `edit`.