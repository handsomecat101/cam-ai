# Lộ trình CamAI

Mục tiêu: phần mềm giám sát camera **chạy trên máy anh**, người không rành kỹ thuật cũng dùng được.

Nguyên tắc: **AI và dữ liệu luôn ở trên máy anh.** Cloudflare chỉ là đường vào, không phải nơi xử lý.

---

## ⚠ ĐỊNH HƯỚNG ĐÃ CHỐT — 2026-10-20 (sau 14:20)

Đọc `USE_CASE.md` mục 0 và `PROJECT_STATE.md` mục 0 (đầu file) trước khi làm tiếp.

1. **CamAI = app "detect đa thể loại"** — chạy trên **3 loại nguồn**:
   **file video** ✅ · **ảnh tĩnh** (đang làm) · **quay video / camera** — webcam `0` và camera IP
   `rtsp://` (đang làm). Mục tiêu: **detect càng nhiều thể loại càng tốt**
   (bảng P0→P4 ở `USE_CASE.md` mục 3.1).
2. **Ứng dụng chấm công = 1 APP RIÊNG** (cần CSDL khuôn mặt riêng: nhân sự, ca làm, đối soát),
   dùng **chung** `face_engine.py` + `known_faces/` với CamAI. Nguyên tắc: **CamAI lo detect,
   app kia lo nghiệp vụ + dữ liệu. KHÔNG ôm chấm công vào CamAI.**
3. **Đổi nền tảng (PySide6/Qt) → LÀM SAU** — khi đã chốt phạm vi tính năng thì mới quyết định,
   để **một lần viết lại cho đủ** thay vì viết lại nhiều lần.
4. **Bài học quy trình**: chọn nền tảng phải **nói thẳng giới hạn thẩm mỹ + hỏi anh "đẹp hay
   nhẹ"** trước khi viết nhiều dòng (lần này em đánh đổi im lặng → giao diện "chán"); và
   **luôn có launcher 1-click + hướng dẫn mở app** cho người không rành kỹ thuật.

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
- [x] **Bản 3.3 — đẩy 3 tính năng "dùng tay" vào GUI** (anh chốt hướng (A)):
      tách 2 ô xem video (**"Xem trực tiếp"** + **"Xem khung hình kết quả"**) + nút
      **"Đăng ký người quen…"** (lưu `known_faces/<Tên>/`) + nút **"Vẽ vùng ngay tại đây"**
      (kéo chuột trong chính cửa sổ, module mới `ve_vung_gui.py`) + nút **"Đọc biển số
      thử…"** (đọc 1 ảnh trong vài giây để anh gửi ảnh biển số thật)
- [x] **Sửa lỗi thật bản 3.3**: đọc `StringVar` từ thread nền → `main thread is not in
      main loop` (chặn việc nạp lại danh sách người quen sau khi đăng ký). Sửa bằng cách
      đẩy qua hàng đợi, UI thread xử lý. Kiểm chứng độ nhạy: vô hiệu hóa fix → lỗi tái
      hiện đúng → bật lại → PASS
- [x] **Kiểm chứng bản 3.3 (coordinator tự chạy, không tin báo cáo agent)**: canvas vẽ
      vùng **sai số 0.0000** + tự xem ảnh; GUI **4/4 PASS**; hồi quy batch **PASS**
      (79 lần hiện khung, 107.129 màu); hồi quy e2e **7/7 PASS** (28,3 s); tiếng Anh
      dịch đủ **5/5** chuỗi mới (test vòng VI→EN→VI)

- [x] **Bản 3.4 — thiết kế lại toàn bộ giao diện** (anh yêu cầu vì "app nhìn cứ phèn phèn"):
      dùng skill **`ui-ux-pro-max`** → sinh `design-system/camai/MASTER.md` làm nguồn sự thật;
      file mới `giao_dien.py` chứa toàn bộ hằng số thiết kế; **thanh đầu mới** + icon app;
      **bỏ hết emoji làm icon** (dùng Segoe MDL2 Assets của Windows); typography Segoe UI +
      Cascadia Mono; bổ sung màu cảnh báo hổ phách; component + lưới khoảng cách thống nhất
- [x] **Icon app do AI vẽ** (Nano Banana Pro / Gemini 3 Pro Image): 4 biến thể → chọn bản
      "đầu người + ống kính + khung nhận dạng" (3 hình đơn giản → vẫn rõ ở 16×16px) →
      `assets/camai.png` 512px + `assets/camai.ico` 7 kích thước, hiện ở thanh đầu **và** trên
      thanh tiêu đề cửa sổ Windows
- [x] **Sửa 2 lỗi thị giác** do coordinator phát hiện khi tự mở ảnh: dấu ✓ trong ô checkbox
      biến mất (`fg_color` = `checkmark_color` cùng màu) → tick đổi sang màu nền tối; icon
      nút DỪNG trông như tofu (dùng Stop = hình vuông đặc) → đổi sang Pause

## Đang làm

- [x] **Bản 3.5 — sửa giật kéo cửa sổ + launcher 1-click** (anh báo thật):
      chẩn đoán bằng số đo → thủ phạm `CTkScrollbar._draw()` gọi `update_idletasks()` (xả hết
      hàng đợi idle của cả app) → đã sửa + khởi động ấm → **lần kéo đầu: 984 ms → 19,4 ms,
      0 lần tre**; mở app không chậm hơn. Thêm `Mo CamAI.vbs` + `Mo CamAI.bat` +
      `HUONG-DAN-MO-APP.md`
- [x] **Bản 3.6 — 4 nhóm cấu hình + nguồn ẢNH & CAMERA** (làm theo định hướng mới):
      12 nhóm rời rạc → **4 mục lớn** (NGUỒN / PHÂN TÍCH / BIỂN SỐ & ẢNH / CẢNH BÁO &
      MÔ HÌNH), mỗi mục 1 dòng mô tả, chỉ 1 mục mở tại một lúc; dải video mẫu 212px →
      125px. Thêm **chế độ ảnh** (xuất ảnh đã vẽ khung) + **camera** (webcam `0`, camera
      IP `rtsp://`, dừng bằng `q`) + lệnh `--list-camera`. Kiểm chứng: e2e 7/7, 3.3 4/4,
      thiết kế 7/7, ngôn ngữ 5/5, canvas PASS; CSV video **SHA256 giống hệt** bản gốc
- [x] **Sửa lỗi repo**: `gui_ngon_ngu.json` (lựa chọn ngôn ngữ của người dùng) bị git
      theo dõi → đã `git rm --cached` + `.gitignore`, reset "vi"; bộ e2e không còn phụ thuộc
      ngôn ngữ
- [x] **Bản 3.7 — GUI nối 2 nguồn mới + lớp tiếng Việt + đếm phương tiện**
  - **GUI nối 2 nguồn mới**: nhóm "NGUỒN" thành chọn nguồn tổng quát — nhãn trạng thái
    ("Loại nguồn: Video / Ảnh tĩnh / Camera máy / Camera IP"), 4 nút **Chọn video… /
    Chọn ảnh… / Chọn camera… / Danh sách camera**, hộp thoại chọn camera (quét nền, không
    treo) + ô nhập **địa chỉ camera IP**. Thanh tiến trình **không xác định** khi quay,
    nút **DỪNG** dừng được vòng lặp live.
  - **P1 — chọn lớp vật thể bằng TIẾNG VIỆT**: file mới **`lop_viet.py`** — bảng **80 lớp
    COCO ↔ tiếng Việt** (khớp 100% model, đọc thật từ `yolo11n.pt`) + **~200 từ đồng
    nghĩa** ("ô tô" = "xe hơi", "xe máy" = "mô tô", "xe khách" = "xe buýt"…). `--lop` giờ
    nhận **có dấu / không dấu / tiếng Anh** → cùng kết quả; gõ sai thì báo lỗi **kèm gợi
    ý**. Lệnh **`--list-lop`** in đủ 80 lớp. **Không cần model mới.**
  - **P1 — đếm phương tiện**: `--dem-phuong-tien` — đếm theo từng lớp + tổng lượt + số xe
    nhiều nhất cùng lúc; **4 cột CSV mới ở CUỐI**, 10 cột cũ **không đổi**.
  - **Sửa 3 lỗi thật**: mũi tên mục lớn sai trạng thái (có từ 3.6, coordinator phát
    hiện bằng cách phóng to 3× ảnh) · GUI "xem trực tiếp" chỉ hiểu lớp tiếng Anh (lệch với
    CLI) · OpenCV Hershey âm thầm bỏ dấu tiếng Việt khi vẽ nhãn lên khung.
  - Kiểm chứng: **10 bộ PASS** (e2e 7/7, lớp tiếng Việt 53/53, chức năng 73/73, nguồn GUI
    35/35, 3.3 4/4, thiết kế 7/7, ngôn ngữ 5/5, canvas PASS, không mất tính năng PASS,
    coordinator 35/35); hồi quy video **SHA256 giống hệt** bản gốc.
- [x] **Đẩy lên GitHub + bộ cài máy mới** (anh chuyển sang máy khác)
  - Repo **public**: `https://github.com/handsomecat101/cam-ai` — nhánh `master`, toàn bộ lịch sử, **~3 MB**
  - `cai_dat_may_moi.bat` → tạo `.venv` + cài thư viện + tải 2 model, **1 lệnh**
  - `TAI-MAY-MOI.md` = hướng dẫn máy mới (clone → cài → mở app → git pull/push)
  - **Không commit** (quá nặng / là dữ liệu cá nhân): `models/` 784 MB · `video_mau/` 507 MB · `known_faces/` · `.venv/`
  - `known_faces_mau.zip` (41 KB) — 10 ảnh "An"/"Binh" để anh chuyển máy bằng USB
- [ ] **Chờ anh xác nhận lại mục 7** — mở app (double-click `Mo CamAI.vbs`) rồi kéo cửa sổ xem
      còn giật không. Số đo đã sạch nhưng **cần cảm nhận của người dùng**
- [ ] **Chờ anh xác nhận mục 8** — độ nhận diện; cần video thật của anh
- [ ] **Chờ ảnh biển số Việt Nam thật** của anh — mới nghiệm thu được OCR biển số
      (hiện mới kiểm chứng bằng ảnh giả 10/10). Bản 3.3 đã có nút **"Đọc biển số
      thử…"** → anh gửi ảnh → bấm 1 nút → có kết quả trong vài giây
- [ ] **Camera thật chưa kiểm chứng được** — máy này **không có camera**. Đã kiểm chứng
      đường đi live qua **camera IP giả** (HTTP MJPEG) + đường lỗi (rõ ràng, không treo)
- [ ] **Ô tick chọn 80 lớp trong GUI** — hiện vẫn gõ tay vào ô lớp (đã nhận tiếng Việt).
      Cần danh sách 80 checkbox trong GUI (đọc từ `lop_viet.DANH_SACH_LOP_VIET()`)
- [ ] **App mở mất ~12,5 s** (đo được: `import gui` 6,8 s + dựng giao diện 2,7 s) — chưa tối ưu.
      Nếu anh thấy chờ lâu, em rút ngắn phần nạp thư viện (nạp model OCR/YOLO **trễ** khi bấm
      BẮT ĐẦU thay vì lúc mở app)

## Kế tiếp

> Chi tiết use case + tầng nền tảng + thứ tự ưu tiên: **`USE_CASE.md`**
> Trạng thái từng tính năng (đã chạy legit / có code / chưa chạy): `PROJECT_STATE.md` mục 2.1d

- [ ] **N1b — Nhiều vùng** trong 1 file (bản 3.3 mới làm 1 vùng, đúng như CLI cũ)
- [ ] **N2b — Đăng ký NHIỀU người cùng lúc** trong GUI (bản 3.3 làm 1 người / 1 lần)
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