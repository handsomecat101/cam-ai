# Nhật ký thay đổi CamAI

Định dạng: Keep a Changelog. Phiên bản theo Semantic Versioning.

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