# Lộ trình CamAI

Mục tiêu: phần mềm giám sát camera **chạy trên máy anh**, người không rành kỹ thuật cũng dùng được.

Nguyên tắc: **AI và dữ liệu luôn ở trên máy anh.** Cloudflare chỉ là đường vào, không phải nơi xử lý.

---

## Đã xong

- [x] Lõi AI: phát hiện/đếm người, nhận diện mặt, người quen, tuổi/giới
- [x] Đếm ra – vào
- [x] Canh vùng + cảnh báo vượt ngưỡng + đứng lâu
- [x] Tự lưu clip, nhận diện vật thể
- [x] Xuất CSV 10 cột, Excel, HTML xem lại
- [x] GUI desktop: accordion tiếng Việt, khung realtime, tạm dừng/tiếp tục
- [x] Web local: đăng nhập, upload, chạy, tạm dừng, tải kết quả
- [x] Bảo mật: không hardcode mật khẩu, fail-closed khi thiếu `CAMAI_PASSWORD`
- [x] Bốn lệnh hồi quy + test GUI 4/4
- [x] GUI visual (v2.4): video realtime chiếm phần lớn, overlay rõ, tên người quen trên khung,
      panel "Đối tượng phát hiện" gom ảnh crop thật, trạng thái bằng màu/badge
- [x] Bỏ hướng tunnel — dừng chạy, dọn file credentials cục bộ
- [x] Nối `canh_bao.py` vào `cam_ai_core.py` — có chuông cảnh báo thật, mặc định TẮT
- [x] `--lop` báo lỗi rõ + gợi ý lớp gần đúng + mã thoát ≠ 0 (trước đây bị bỏ qua im lặng)
- [x] Clip hỏng khi kill: ghi `.part.mp4` rồi mới đổi tên — file hỏng không còn mang tên đúng
- [x] Bố cục GUI theo mẫu tham chiếu: video lớn · danh sách sự kiện dạng timeline ·
      bảng thống kê vùng 5 dòng (hiện tại / trung bình / đỉnh / đáy / A→B)
- [x] Thư viện video demo có poster thật, bấm thẻ là chọn (thay dropdown chữ)
- [x] 6 video demo mới đa thể loại → **13 thẻ** (v2.6), kèm `NGUON_LICENSE.md`
- [x] **Live view ≥10 fps** (v2.6): `PUMP_MS` 120 → 30, đo thật **14.34 fps** liên tục
      300.2 s, 0/293 giây dưới 10 fps. Giả thuyết "YOLO chạy 2 vòng" đã bị đo và bác bỏ
- [x] **0 cặp nhãn chồm** trên khung 15 người (v2.7): sửa `_vuot_nhau` theo đúng nghĩa
      `LE_TRANH`; 15/15 nhãn vẽ được
- [x] **Video ≥70% bề ngang + 0 nhãn tràn** (v2.7): cột sự kiện co theo → 75.4%–83.2%
- [x] 4 lỗi hiển thị 2.5 đã sửa: dải badge đáy tách, nhãn vùng không chồn khung
- [x] **Công tắc "Nhận người ở xa (chậm hơn)"** (v2.8): `--tach-o` trong lõi/CLI/GUI,
      **mặc định TẮT** (anh đã chọn sau khi đo). Đo thật: `dam-dong` 3.0 → 5.4,
      `xe-co-giao-thong` 1.0 → 4.6, video gần không đổi; chậm 5.3×
- [x] Hồi quy bản 2.8 tự chạy: 4 lệnh `app.py` exit 0, `--help` 70 dòng, CSV 251×10,
      `_kiem_tra_gui.py` 4/4, bố cục 75.4% nhỏ nhất, encoding `BOM=False CR=0`
- [x] **Bản 3.0 — đọc biển số xe Việt Nam** (mặc định TẮT): module mới `bien_so.py`,
      2 engine OCR riêng (chỉ-đọc / có-tìm-chữ), regex biển VN, chuẩn hoá **không bịa
      ký tự**, xác nhận đa khung hình + cơ chế `mau_thuan`, lưu ảnh crop
- [x] **Bản 3.0 — tự chụp ảnh khi có sự kiện** (mặc định TẮT): module mới
      `tu_chup.py`, kèm `_bang_ke_chup.csv`
- [x] **Bản 3.0 — 8 cờ CLI** + 2 nhóm GUI mới ("Đọc biển số xe", "Tự chụp ảnh khi có
      sự kiện"), bản dịch Anh đủ **30/30** ghi chú
- [x] **Đọc biển số không làm khựng pipeline**: pha tìm vùng chuyển sang luồng nền
      + cache vùng + hạn chi phí 50 ms → **680,9 ms → 5,2 ms/khung** (có ROI),
      **1916,6 ms → 7,5 ms/khung** (không ROI)
- [x] **Sửa lỗi ô gợi ý trong ô nhập không hiện** (lớp `GoiYTronO`): "tự tìm" /
      "mặc định" hiện đúng, nền khớp tuyệt đối, không che viền
- [x] **Ghi chú tốc độ OCR trên GUI dùng số đo thật**: 9–15 ms/lần quét, max 62 ms
      (thay con số mơ hồ "20–430 ms")
- [x] **Sửa lỗi codec video — trình duyệt không phát được video trong báo cáo xem lại**:
      video kết quả + clip tự lưu chuyển từ `mp4v` (MPEG-4 Part 2, **không có decoder
      trong Chrome/Edge/Firefox**) sang **H.264 (`avc1`)**. Chọn codec bằng **probe 1 lần
      có cache**, lùi về `mp4v` nếu máy không có encoder H.264. Đo thật sau fix:
      `ffprobe` → **`codec_name=h264`**, `ffmpeg` decode sạch (exit 0), mở HTML bằng
      **browser thật** → player load được (`total time: 0:10`), **0 lỗi console**
- [x] **Rà toàn bộ bản PC** (2026-10-20, bản 3.1): coordinator tự chạy **32 cờ CLI**
      (**26/26 EXIT=0**), **6 script OCR** (**6/6 PASS**), **GUI end-to-end** (tự xem
      ảnh) → mọi video kết quả **H.264 960×540**, mọi CSV **251 dòng**
- [x] **Sửa 3 lỗi chết app** tìm được khi rà:
      (1) đường dẫn tương đối phân giải theo CWD → app **chết** khi chạy ngoài thư mục
      dự án (thêm file mới `duong_dan.py` làm nguồn sự thật duy nhất);
      (2) app không tự tạo thư mục output;
      (3) `--tu-luu-clip` cùng thư mục với video kết quả → **xoá mất video kết quả
      nhưng exit 0** (thêm `giu=` + registry `_FILE_DANG_GHI`)
- [x] **Sửa panel "Xem video" đen khi chạy phân tích theo lô** (bản 3.2):
      thêm `frame_cb` + `frame_cb_interval` vào `run_analysis()` (khung **đã có overlay**,
      `frame_cb=None` → chi phí = 0, callback lỗi không làm chết pipeline) + GUI nhận
      khung qua **hộp thư 1 ô** (tránh phình bộ nhớ) + giới hạn **10 fps** + ẩn nút
      "Tạm dừng" ở chế độ lô. Kiểm chứng: **7/7 PASS**, vùng panel đo được
      **118.735 màu / sáng TB 73,95** (trước là đen), coordinator **tự xem ảnh** thấy
      khung người + nhãn **An**/**Binh**

## Đang làm

- [ ] **Chờ anh xác nhận mục 7** — kéo cửa sổ, còn giật hay không (chỉ có số đo)
- [ ] **Chờ anh xác nhận mục 8** — độ nhận diện; cần video thật của anh
- [ ] **Chờ ảnh biển số Việt Nam thật** của anh — mới nghiệm thu được OCR biển số
      (hiện mới kiểm chứng bằng ảnh giả 10/10)

## Kế tiếp

> Chi tiết use case + tầng nền tảng + thứ tự ưu tiên: **`USE_CASE.md`**
> Trạng thái từng tính năng (đã chạy legit / có code / chưa chạy): `PROJECT_STATE.md` mục 2.1d

- [ ] **N1 — Vẽ vùng / đường ngắm trong GUI, nhiều vùng** (đã có `ve_vung.py` CLI → nhúng vào GUI)
- [ ] **N2 — Đăng ký người quen trong GUI** (đã có `dang_ky_anh.py` CLI → nhúng vào GUI)
- [ ] **N8 — Báo cáo theo ca / ngày** (CSV hiện là theo giây)
- [ ] **N4 — Rule cảnh báo theo điều kiện + kèm ảnh**
- [ ] **N9 — Chống đếm trùng 1 người**
- [ ] **N3 — Dashboard tổng quan + lịch sử sự kiện lưu lâu dài**
- [ ] Khôi phục lưới "Đối tượng phát hiện" bị bỏ (chờ anh chọn) + cho chọn kênh cảnh báo
- [x] Web: cập nhật lại sau khi GUI đổi — kiểm lại HTTP 200 + 401 (2026-10-19: trang chủ 200, API 401)
- [ ] Thử web trên điện thoại thật
- [ ] Thử nhiều người dùng đồng thạt trên web
- [ ] Chuông Windows bằng âm thanh hệ thống
- [ ] Rà lại `known_faces/` — dữ liệu giả, chờ anh đồng ý xóa

## Chờ anh quyết

- [ ] **Camera máy chấm công**: đặt ở cửa hay trên xe? khoảng cách người đứng bao xa?
      cùng lúc bao nhiêu người? cần **nhận diện theo tên** hay chỉ **đếm lượt**?
      (quyết định mặc định `face_every` và có bật nhận diện mặt mặc định hay không)
- [ ] Có thêm ô chọn webcam (camera live) trong GUI không?
- [ ] Có cần model nhận diện khẩu trang không? (hiện cột `Mask:` luôn "Chưa rõ")
- [ ] Giữ lưới "Đối tượng phát hiện" hay chỉ giữ timeline sự kiện?
- [ ] Có nới hạn chi phí OCR 50 ms không? (biển 2 hàng đo ~54 ms → có thể bị cắt)

## Tương lai — chỉ khi app ổn định

- [ ] Telegram bot gửi cảnh báo
- [ ] Cân nhắc public qua Cloudflare tunnel (dữ liệu vẫn ở máy anh).
      Tunnel thử nghiệm `camvision` đã dừng theo yêu cầu của anh; xem `PROJECT_STATE.md` mục 7.