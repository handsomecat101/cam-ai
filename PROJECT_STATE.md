# Đọc file này đầu tiên khi quay lại làm tiếp

**Ngày cập nhật:** 2026-10-19 (sau 14:00 — bản 2.8 đã thêm `--tach-o`, `VERSION` nay là **2.8**)
**Phiên bàn giao:** `mvs_cb81c4611fb14dd8ba4717ff00672d2b`
**Trạng thái ngắn:** **6 mục nghiệm thu tự đo — CẢ 6 ĐÃ ĐẠT** ở bản 2.8 (đo lại toàn bộ
sau khi thêm `--tach-o`), mỗi mục có output thật kèm tên file. Mục 7 và 8 **chờ anh tự
xác nhận** nên chưa được coi là đạt. Live view **14.54 fps** liên tục 300 giây.
Bố cục **75.4% → 83.2%**. Nhãn người **0 cặp chồm** trên khung 15 người.
Công tắc **"Nhận người ở xa (chậm hơn)"** đã có trong CLI và GUI, **mặc định TẮT**.

> **Quy tắc cho phiên sau:** đọc mục 2 (bảng ĐẠT/CHƯA ĐẠT) trước. Không tin báo cáo
> của agent nếu chưa tự mở app và nhìn bằng mắt. Em đã sai một lần vì báo "xong"
> khi agent mới chỉ đo được số liệu.

---

## 1. Dự án này là gì

CamAI — phần mềm giám sát camera/video chạy trên máy Windows của anh Tuấn.
Xem video, đếm người, đếm ra–vào, canh vùng, nhận diện người quen, ước lượng tuổi/giới,
tự lưu clip, nhận diện vật thể, gửi cảnh báo, xuất CSV/Excel/HTML.

Nguyên tắc bất di bất dịch: **mọi tính toán và dữ liệu nằm trên máy anh.**
Không đẩy AI lên cloud. Cloudflare chỉ là "cánh cửa" nếu sau này public.

---

## 2. BẢNG ĐẠT / CHƯA ĐẠT — đọc mục này trước

### 2.1 ĐÃ ĐẠT — nghiệm thu bản 2.5 (đo 2026-10-19, `VERSION` 2.6 → 2.7)

Bảng nghiệm thu chính thức, **6 mục tự đo**:

| # | Mục tiêu | Kết quả đo thật | Bằng chứng | Người xác nhận |
|---|---|---|---|---|
| 1 | Live view ≥10 fps liên tục 300s | **BẢN 2.8 ĐO LẠI: 14.54 fps** (giai đoạn ổn định 294.3s); min 12 fps/giây; **0/294 giây** dưới 10 fps; 4279 khung vẽ lên UI; nạp model 6.0s. Bản 2.7 đo được 14.34 fps → **thêm nhánh `--tach-o` không làm giảm fps khi để TẮT** | `_kiem_chung/fps_fps_nghiemthu_300s_v28_full.txt` (bản 2.7: `fps_nghiemthu_300s_full.txt`) | **Coordinator tự chạy**, chế độ `full` (live view + pipeline cùng chạy) |
| 2 | 0 cặp nhãn chồm với ≥10 người | Khung **15 người**: **15/15 nhãn vẽ được, 0 cặp chồm**, mọi nhãn nằm trong khung | `_kiem_chung/kk_35_don_cuc_10_nguoi.png` | **Coordinator tự xem ảnh bằng mắt** |
| 3 | Video ≥70% bề ngang + 0 nhãn tràn | 1610px → **75.5%**; 1400px → **75.4%**; 1900px → **83.2%**; tràn widget **0 px**; tràn nhãn **0** | `_kiem_chung/kk_36_boc_cuc.txt` + `kk_36_boc_cuc.png` (đo lại ở bản 2.7) | **Coordinator tự chạy + tự xem ảnh** |
| 4 | 4 lệnh hồi quy + CSV | L1 vùng `192,81 -> 768,513`, max vùng 2, vào vùng 1, đứng lâu 1 lần dài nhất 10.0s; L2 nhạy max 2/4 người; L3 ghi ra mp4+csv; L4 `--help` **70 dòng** (bản 2.8); CSV **251 dòng × 10 cột** | `output_bao_cao.csv` + output 4 lệnh | **Coordinator tự chạy** lại ở bản 2.8 |
| 5 | `_kiem_tra_gui.py` | **4/4 PASS**, `EXIT=0`; tiêu đề cửa sổ `CamAI v2.8`; nhóm mới được kiểm: `[OK ] Nhận người ở xa (chậm hơn) mac_dinh_ban_dau=TAT` | output dòng lệnh | **Coordinator tự chạy** lại ở bản 2.8 |
| 6 | Encoding 3 file | `gui.py` `BOM=False CR=0`; `gui_khung.py` `BOM=False CR=0`; `cam_ai_core.py` `BOM=False CR=0`; `ast.parse` OK cả 3 | đo byte thật | **Coordinator tự chạy** |

**Kết luận nghiệm thu:** 6 mục tự đo **đều đạt**. Chưa được coi là xong hoàn toàn vì
mục 7 và 8 phải do anh xác nhận (mục 2.2).

### 2.1b ĐÃ ĐẠT (lịch sử, giữ lại vì dùng để so lại)

| Hạng mục | Bằng chứng | Người xác nhận |
|---|---|---|
| `--lop` sai báo lỗi rõ | `--lop motercycle` → gợi ý `('motercycle' co phai la 'motorcycle'?)` + liệt kê 80 lớp; **exit 1** | **Coordinator tự chạy** |
| `--lop` sai tồn tại | `--lop xyz` → `[loi] khong co lop vat the nay: xyz`; **exit 1** | **Coordinator tự chạy** |
| `--lop` hợp lệ tự bật | `--lop car` → `Đã bật tự động nhận diện vật thể vì có dùng --lop (car)` → `xe o to: 15 khung hinh, toi da 1`; **exit 0** | **Coordinator tự chạy** |
| Cảnh báo nối vào lõi | `--bat-canh-bao --canh-bao-mo-phong` → `[canh bao] 05:23:46 canh bao: dung_lau` + `Su kien da canh bao: 1` | **Coordinator tự chạy** |
| Cảnh báo mặc định TẮT | 4 lệnh hồi quy không có dòng `[canh bao]` nào | **Coordinator tự chạy** |
| Clip hỏng không còn mang tên đúng | Ghi `.part.mp4`, đổi tên sau khi đóng. Sau khi chạy: **không còn file `.part.mp4` sót** | **Coordinator tự chạy** |
| Thư viện 13 video mẫu có poster thật | 13 thẻ ngang, poster lấy từ frame thật ở ~40% thời lượng | **Coordinator tự xem ảnh** `kk_34_the_moi.png` |
| 4 lỗi hiển thị 2.5 đã sửa | Ảnh `kk_32_fix.png`: không còn nhãn chồn, dải badge đáy tách, nhãn vùng không đè khung | **Coordinator tự xem** |

### 2.2 CHƯA ĐẠT — chờ anh

| Hạng mục | Vì sao chưa đạt | Việc cần làm |
|---|---|---|
| **7. Cảm giác kéo cửa sổ** | Chỉ có số đo, **anh chưa xác nhận**. Em đã sai một lần vì coi số đo là bằng chứng xong | **Anh mở GUI, kéo cửa sổ, xác nhận còn giật hay không.** Nếu còn giật: em sẽ báo cáo tiếp kèm số đo mới |
| **8. Độ nhận diện trên video** | Video demo là video tải về, không phải video thật của anh; `known_faces/An`, `known_faces/Binh` là **dữ liệu giả**. **Đã đo thật (mục 2.3) và phát hiện hạn chế lớn:** quay drone `nguoi-di-lai` nhận 0/12 khung dù có hàng trăm người; `dam-dong` nhận 2–6 người dù cảnh rất đông | **Anh gửi video thật** (và ảnh người quen nếu muốn nhận diện tên), hoặc tự xem và nhận xét. Nếu anh cần nhận tốt ở cự ly xa/đám đông, xem 3 phương án sửa trong mục 2.3 |
| **Trạng thái khẩu trang** | Chưa làm | Cột `Mask:` luôn hiện `Chưa rõ`. `FaceResult` không có trường này và **dự án chưa có model khẩu trang**. Chờ anh quyết có cần không |
| **Lưới "Đối tượng phát hiện" đã bị bỏ** | Agent tự quyết khi đổi bố cục; vai trò chuyển sang danh sách sự kiện. Class `PanelDoiTuong` còn nguyên trong `gui_khung.py` | Chờ anh chọn: giữ lại lưới, hay chỉ giữ timeline sự kiện |
| **Chọn kênh cảnh báo** | 3 checkbox cũ (Phát chuông / Mở hộp thoại / Telegram) bị thay bằng 4 ô khớp cờ lõi. `AnalysisConfig` chỉ có 4 cờ nên không truyền được kênh nào bật | Cần thêm cờ vào `cam_ai_core.py` — chờ anh xác nhận muốn có |
| **Web local** | Chạy lại sau khi lõi đổi (2026-10-19): `GET /` → **200**; `/api/trang-thai`, `/api/tai-ket-qua` → **401** chưa đăng nhập; `/api/phan-tich` → 405 vì là POST. **Không còn nằm trong danh sách chưa đạt.** | **Coordinator tự chạy** |
| **Chưa có webcam live** | `--input 0` có trong CLI nhưng chưa thử webcam thật | Chờ anh xác nhận có làm không |

### 2.3 ĐO ĐỘ NHẬN DIỆN THẬT — có hạn chế lớn, anh PHẢI biết trước khi xác nhận mục 8

Đo ngày 2026-10-19 bằng `_kk_kiem_do_nhan_diem.py` — đúng model và ngưỡng của bản chạy thật
(`yolo11n.pt`, `conf=0.25`, class `person`), 12 khung mẫu rải đều trên mỗi video.

| Video | Người/khung (trung bình) | Nhận xét khi nhìn ảnh bằng mắt |
|---|---|---|
| `tre-em-san-choi` | 9.2 (tối đa 16) | **Tốt.** Bám đúng trẻ em, số khung khớp mắt thường |
| `nguoi-dung-cho` | 9.0 (tối đa 18) | Tốt ở cự ly gần |
| `cua-hang` | 6.5 (tối đa 9) | Khá, conf trung vị 0.59 |
| `video_test.mp4` | 3.2 | **Tốt nhất.** conf trung vị 0.82 |
| `dam-dong` | 3.0 | **Thiếu nặng.** Cảnh đám đông rất đông, mỗi khung nhận 2–6 người, conf trung vị chỉ 0.35 |
| `xe-co-giao-thong` | 1.0, chỉ 6/12 khung có người | **Yếu.** Người ở xa và nhỏ, conf 0.26–0.58 |
| `nguoi-di-lai` | **0.0** | **HỎNG.** Video quay drone cao, rõ ràng có hàng trăm người, nhận **0 người ở cả 12 khung** |

**Kết luận kỹ thuật (chưa phải kết luận mục 8 — mục 8 anh xác nhận):**

CamAI nhận diện **tốt ở cự ly gần, ít người** — đúng bài toán giám sát camera thường.
CamAI **yếu dần khi người nhỏ/xa** và **hỏng hoàn toàn với video quay drone từ trên cao**.

Nguyên nhân khả năng cao: `yolo11n.pt` là model nano, ưu tiên tốc độ; khi thân người
chỉ còn ~10–20 px thì không đủ đặc trưng để nhận. Ngưỡng `conf=0.25` đã là mặc định
mềm nhất của ultralytics.

**Việc có thể làm nếu anh cần nhận tốt hơn (chưa làm, chờ anh quyết):**
1. Đổi `yolo11n.pt` → `yolo11s.pt` hoặc `yolo11m.pt`: chính xác hơn, chậm hơn
   (ước giảm fps live view, có thể mất mục tiêu 1).
2. Tăng kích thước khung hình đầu vào (hiện video 960×540).
3. Chia nhỏ khung hình thành các ô (tile) để người nhỏ được phóng to trước khi dò.

**Bằng chứng:** `_kiem_chung/do_nhan_diem.txt` + 7 ảnh `nhan_diem_<tên video>.png`
— coordinator **đã tự mở xem bằng mắt**, không chỉ đọc số.

### 2.4 ĐÃ ĐO 4 PHƯƠNG ÁN NÂNG CAO — 2 phương án loại, 1 phương án tốt nhưng đắt

Đo ngày 2026-10-19 bằng `_kk_bench_nang_cao.py` và `_kk_bench_gop.py`.
Không sửa code sản phẩm. Số người/khung, trung bình trên 8 khung mẫu.

| Cách | `nguoi-di-lai` | `dam-dong` | `xe-co-giao-thong` | `tre-em-san-choi` (đang tốt) | `nguoi-dung-cho` (đang tốt) | ms/khung |
|---|---:|---:|---:|---:|---:|---:|
| A. Nền: `yolo11n`, toàn khung | 0.0 | 3.0 | 1.0 | 9.4 | 10.1 | ~32 |
| B. `yolo11s`, toàn khung | 0.6 | **2.6 ↓** | 1.2 | 10.6 | — | ~40 |
| C. Phóng to ×2 | **0.0** | **3.0 =** | **1.0 =** | **9.4 =** | — | ~46 |
| D. Chia ô 2×2 (chỉ ô) | 0.5 | 5.1 | 6.0 | **4.5 ↓↓** | — | ~146 |
| D'. Chia ô 3×3 (chỉ ô) | 1.6 | 10.6 | 9.6 | **7.1 ↓** | — | ~320 |
| **G. Toàn khung + ô 2×2, gộp NMS** | 0.5 | **6.5** | **6.8** | **10.0** | **12.4** | ~170 |

**Kết luận từng phương án:**

- **Phương án C (phóng to ×2) — LOẠI. Không làm được gì cả.**
  Số nhận ra **y hệt** nền ở mọi video. Lý do: ultralytics tự resize ảnh về
  `imgsz=640` bên trong, nên phóng to thủ công ở ngoài không có tác dụng.
- **Phương án B (`yolo11s`) — LOẠI.** `dam-dong` còn **tệ hơn** (3.0 → 2.6).
  Đổi model không giải quyết được bản chất vấn đề.
- **Phương án D (chỉ chia ô) — LOẠI vì làm hỏng video đang tốt.**
  `tre-em-san-choi` rơi 9.4 → 4.5 (mất hơn một nửa). Nguyên nhân: người ở gần bị
  **cắt đôi ở rãnh giữa các ô** nên không nhận được.
- **Phương án G (toàn khung + ô 2×2, gộp NMS) — TỐT NHẤT VỀ CHÍNH XÁC.**
  Cải thiện mạnh video xa (`dam-dong` 3.0 → 6.5, `xe-co-giao-thong` 1.0 → 6.8)
  mà **không làm hỏng** video gần (9.4 → 10.0; 10.1 → 12.4).

**Vấn đề duy nhất của G là tốc độ:** ~170 ms/khung so với ~32 ms nền, tức **chậm hơn 5.3 lần**.
Dựa trên số đo mục tiêu 1 (YOLO+ByteTrack 38.5 ms, tổng 63.4 ms → 14.34 fps),
bật G sẽ đưa live view xuống **khoảng 5 fps — mất mục tiêu 1**.

**Đề xuất — ANH ĐÃ CHỌN và đã triển khai (xem mục 2.5):** làm G thành **công tắc bật/tắt, mặc định TẮT**.
- Tắt (mặc định): giữ nguyên 14.34 fps, giữ đúng hành vi hiện tại.
- Bật: dùng khi phân tích **video đã quay sẵn** ở cự ly xa — chấp nhận chậm hơn.

**Bằng chứng:** `_kiem_chung/bench_nang_cao.txt`, `_kiem_chung/bench_gop.txt`.

### 2.5 ĐÃ GIAO — công tắc "Nhận người ở xa (chậm hơn)" bản 2.8, MẶC ĐỊNH TẮT

Anh đã chọn phương án G (mục 2.4). Đã triển khai đầy đủ:

| Nơi | Nội dung |
|---|---|
| `cam_ai_core.py` | `TACH_O_MAC_DINH=False`, `TACH_O_TRUNG=0.35`, `TACH_O_DIEM=0.0`, `TACH_O_IOU=0.45`; `AnalysisConfig.tach_o`; hàm mới `detect_tach_o(detector, frame, conf)`; `run_analysis()` rẽ nhánh khi `cfg.tach_o` |
| `app.py` | Cờ `--tach-o`, trong group "do nhan nguoi o xa", có log cảnh báo chậm ~5.3 lần |
| `gui.py` | Nhóm **"Nhận người ở xa (chậm hơn)"**, `self.v_tach_o="0"`, nhãn song ngữ; đã thêm `nhom_tach_o` vào `danh_sach_nhom()` để test GUI thật sự kiểm |

**Đo lại bằng đúng hàm sản phẩm** (`_kk_kiem_tach_o.py`, số người trung bình/khung):

| Video | Nền | Có `--tach-o` | Tốc độ |
|---|---:|---:|---:|
| `dam-dong.mp4` | 3.0 | **5.4** | 0.31× |
| `xe-co-giao-thong.mp4` | 1.0 | **4.6** | 0.20× |
| `tre-em-san-choi.mp4` | 9.4 | 8.2 | 0.19× |
| `nguoi-dung-cho.mp4` | 10.1 | 9.9 | 0.23× |

**Nói thẳng để anh biết:** cải thiện **rõ** ở cự ly xa (`dam-dong` +80%, `xe-co` +360%),
gần như **không đổi** ở cự ly gần (`nguoi-dung-cho` 10.1 → 9.9). `nguoi-di-lai` vẫn rất
yếu vì người quá nhỏ. Đổi lại chậm **khoảng 5.3 lần**, nên **không bật mặc định**.

**Hai lỗi em tự gây ra và đã tự sửa** (ghi vào `ISSUE_LOG.md`):
1. Ô chia chỉ phủ 70% khung hình — sai lầm đặt `buoc = kích thước ô`; sửa thành
   `buoc = kích thước khung - kích thước ô`.
2. NMS xoá nhầm nhãn dưới ngưỡng — truyền `score_threshold=0.45` dù ngưỡng nhận gốc
   là `0.25`; sửa thành `TACH_O_DIEM = 0.0` (chỉ gộp trùng, không loại nhãn).

**Bằng chứng:** `_kiem_chung/kiem_tach_o.txt`, `_kiem_chung/bench_gop.txt`, chạy thật
`app.py --tach-o` trên `dam-dong.mp4` → `EXIT=0`, log `[tach-o]` có mặt, max 6 người/khung.

---

### 2.5 ĐÃ ĐO — CHỌN CPU/GPU + KẾT HỢP ĐẾM NGƯỜI VÀ NHẬN DIỆN MẶT (2026-10-19)

Đo bằng **chính `run_analysis()` của sản phẩm** (có vẽ khung + ghi file), `yolo11n.pt`, CUDA.
Coordinator tự chạy, không tin báo cáo agent.

#### a) Chọn CPU/GPU — ĐÃ ĐẠT

| Việc | Kết quả | Bằng chứng | Người xác nhận |
|---|---|---|---|
| `cam_ai_core.py` có `thiet_bi` + `THIET_BI_MAC_DINH="auto"` | `THIET_BI_CHON = ("auto","cuda","cpu")`; `detector = YOLO(cfg.model).to(chon_thiet_bi(...))` | đọc mã + `py_compile` exit 0 | Coordinator |
| `app.py --thiet-bi {auto,cuda,cpu}` | `--help` hiện đúng 3 lựa chọn | `app.py --help` | Coordinator |
| GUI dropdown "Chạy bằng" | `Tự động`→`auto`, `GPU (CUDA)`→`cuda`, `CPU`→`cpu` — **cả 3 khớp đúng** | `_kiem_chung/kk_37_chay_bang_gi.png` | **Coordinator tự xem ảnh** |
| Nhóm "Máy này chạy bằng gì" truy cập được | Cột trái là `CTkScrollableFrame`, cuộn xuống là thấy dropdown | ảnh trên (đã cuộn `yview 0.246→1.0`) | **Coordinator tự xem ảnh** |
| Đã nằm trong Git | commit `1f05591` đã chứa `THIET_BI_MAC_DINH`, `GIA_TRI_CHE_THIET_BI` | `git show HEAD:cam_ai_core.py` | Coordinator |

#### b) Câu hỏi "có kết hợp được không" — ĐÃ ĐO, KẾT LUẬN RÕ

Video `nguoi-dung-cho.mp4` (~10 người/khung), mỗi cấu hình đo 2 lần:

| Cấu hình | fps | người/khung | mặt/khung | % khung có mặt | Nhanh hơn |
|---|---|---|---|---|---|
| `face_every=1` (mặc định) | 5.15 | 9.88 | 9.01 | 100% | 1.00× |
| `face_every=2` | 7.62 | 9.92 | 4.27 | 47.9% | 1.48× |
| `face_every=5` | 12.45 | 9.93 | 1.80 | 20.0% | 2.42× |
| `face_every=10` | 23.36 | 10.19 | 0.90 | 9.6% | 4.53× |
| `no_face` (tắt hẳn) | 26.91 | 10.39 | 0.00 | 0% | 5.22× |

**Kết luận: ĐƯỢC KẾT HỢP, không phải chọn 1 trong 2.**
- **Đếm người không đổi** ở mọi cấu hình (9.88 → 10.19). YOLO chạy độc lập với engine mặt.
- `face_every` bỏ qua **toàn bộ** engine mặt ở những khung không khớp
  (`cam_ai_core.py:945`), nên vẫn nhận diện đúng người ở các khung có quét.
- `face_every=10` đạt **87% tốc độ khi tắt hẳn** nhưng vẫn còn nhận diện mặt.

**Bằng chứng:** `_kiem_chung/ket_hop_dem_nguoi_va_nhan_dien_mat.txt`,
script `_kk_ket_hop_dem_va_mat.py`. **Coordinator tự chạy và tự đọc số.**

#### c) Chi phí nhận diện mặt TĂNG THEO MẬT ĐỘ NGƯỜI

| Video | người/khung | `no_face=False` | `no_face=True` | Hệ số |
|---|---|---|---|---|
| `nguoi-dung-cho` | ~10 | 4.17 fps (196–271 ms) | 18.31 fps (45–62 ms) | **3.59–4.96×** |
| `xe-co-giao-thong` | 0.0–0.5 | 12.11 fps (74–93 ms) | 28.85 fps (31–40 ms) | **2.14–2.69×** |

**Cảnh báo cho UI:** không được ghi "tắt nhận diện mặt = nhanh gấp N lần" với N cố định.
Camera đông người thì N≈4, camera vắng thì N≈2.4. Số đúng phải theo cảnh.

**Bằng chứng:** `_kiem_chung/xac_nhan_no_face.txt`,
`_kiem_chung/do_on_dinh_no_face_nguoi-dung-cho.mp4.txt`,
`_kiem_chung/do_on_dinh_no_face_xe-co-giao-thong.mp4.txt`.

#### d) Thông lưu quét video dài

Báo cáo agent: `_kiem_chung/thong_luu_video_dai.txt` (278 dòng, có tự nêu giới hạn).
Điểm chính đã **kiểm chứng lại**:
- Giải mã video ~560–674 fps → **không phải nút cài**.
- Nạp lại model 0.097 s/lần → **không phải nguyên nhân** giật/lag.
- Nút cài thật là **nhận diện ArcFace mỗi khung** (đo lại ở (b), (c)).
- Tăng `conf` **không** làm nhanh (30.9→28.4→28.9 fps) và làm mất người → **không dùng**.
- `imgsz` nhỏ **không** giúp (416 chỉ +19%, 320 mất 14% người) → **không dùng**.
- Phương án tracker thay YOLO định kỳ (F) **tệ hơn** cả về tốc độ lẫn độ nhận diện → **loại**.

> **Chưa đo qua `run_analysis`:** tham số "YOLO mỗi N khung". Số của agent đo bằng
> vòng lặp rút gọn, **không** gồm vẽ khung + ghi file. Chưa được đưa vào sản phẩm.

#### e) CHƯA ĐẠT — việc còn mở

| Hạng mục | Vì sao chưa đạt | Việc cần làm |
|---|---|---|
| `VERSION` chưa bump cho nhóm CPU/GPU | Code đã vào commit nhưng `VERSION` vẫn là `2.8` | Bump lên `2.9` + cập nhật 4 file tài liệu |
| Chưa hiện tác động tốc độ trên GUI | Anh yêu cầu mỗi công tắc phải ghi rõ ảnh hưởng tốc độ | Viết số đo thật vào `_ghi_y()`, dùng khoảng 2–5× theo mật độ người |
| Chưa đo "YOLO mỗi N khung" qua `run_analysis` | Số agent chưa đủ tin | Đo lại qua đường chạy thật rồi mới chốt |
| Chưa có video thực tế của anh | Bộ video mẫu không đại diện camera an ninh | **Anh gửi video thật** để đo đúng thời gian quét |
| Chưa biết anh cần đếm người, nhận diện người quen, hay cả hai | Quyết định mặc định GUI | **Anh trả lời** |
| Agent tìm video CC0 thực tế | Chạy từ trước, chưa trả kết quả | Đang chờ |

---

## 3. Quyết định đã chốt — KHÔNG mở lại

| Quyết định | Lý do |
|---|---|
| Không làm tunnel Cloudflare | Anh yêu cầu dừng. Pipeline cần GPU/OpenCV/ONNX, chạy local là bắt buộc. |
| GUI là CustomTkinter, không chuyển sang web | Anh muốn app desktop dễ dùng. Web là bản thứ hai. |
| CSV giữ đúng 10 cột | Đã dùng nhiều nơi, đổi là vỡ tương thích. |
| Ô "Lưu kết quả" là THƯ MỤC | `cam_ai_core.output_paths()` tự ghép đuôi `_ket_qua.mp4` / `_bao_cao.csv`. |
| Web bắt buộc đăng nhập | Anh chọn. |
| Mật khẩu web chỉ từ `CAMAI_PASSWORD`, ≥8 ký tự, thiếu là fail-closed | Không hardcode bí mật. |
| GUI accordion mặc định thu gọn hết | Người không rành kỹ thuật không bị ngợp. |
| Không dùng emoji làm icon | Ràng buộc của anh. |
| Overlay tiếng Việt vẽ bằng PIL/Pillow | `cv2.putText` không có glyph dấu. |
| Giữ tên theo track ID | Tránh nhấp nháy khi mất mặt ở vài frame. |
| Thư viện video demo phải có poster thật, chọn bằng click | Dropdown chữ "tù mù" anh không chấp nhận. |
| Mỗi agent sở hữu file riêng, không sửa chồng | Tránh đụng độ. Quy tắc: agent GUI = `gui.py`, `gui_khung.py`; agent lõi = `cam_ai_core.py`, `app.py`, `canh_bao.py` |
| Không sửa lõi chỉ để phục vụ wrapper | Nếu bottleneck ở lõi thì phải báo rõ, không lách. |

---

## 4. Cách chạy + cách kiểm chứng

### 4.1 GUI desktop

```powershell
cd 'H:\AI Project\cam-ai'
.venv\Scripts\pythonw.exe gui.py
```

### 4.2 Web local

```powershell
cd 'H:\AI Project\cam-ai'
$env:CAMAI_PASSWORD = "<mật khẩu ít nhất 8 ký tự>"
.venv\Scripts\python.exe web_server.py
```

Mở `http://127.0.0.1:8787`. Thiếu `CAMAI_PASSWORD` thì in hướng dẫn và **thoát mã 2**.

### 4.3 Bốn lệnh hồi quy — chạy sau MỖI lần sửa code

```powershell
cd 'H:\AI Project\cam-ai'
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-max 2 --canh-lau 3 --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --vung vung.txt --vung-nhay --no-face
.venv\Scripts\python.exe app.py --input video_test.mp4 --no-face
.venv\Scripts\python.exe app.py --help
```

**Kết quả mong đợi (đo thật 2026-10-19):**
- L1: vùng `192,81 -> 768,513`, nhiều nhất trong vùng **2**, vào vùng **1** lần, đứng lâu >3.0s **1 lần dài nhất 10.0s**
- L2: chế độ nhạy — nhiều nhất **2**, vào vùng **1**
- L3: không vùng — nhiều nhất **4** người/khung
- L4: `--help` exit 0
- CSV `output_bao_cao.csv`: **251 dòng, 10 cột**

### 4.4 Test GUI

```powershell
.venv\Scripts\python.exe _kiem_tra_gui.py
```

Mong đợi **4/4 PASS**: mặc định thu gọn hết · bấm tiêu đề mở/đóng · checkbox tự bung/thu gọn · cửa sổ con thông tin model.

### 4.5 Kiểm tra encoding (bắt buộc sau mỗi lần sửa file tiếng Việt)

```powershell
$base='H:\AI Project\cam-ai\'
foreach ($f in @('gui.py','gui_khung.py','cam_ai_core.py')) {
  $b=[System.IO.File]::ReadAllBytes($base + $f)
  $bom = ($b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
  $cr = ($b | Where-Object { $_ -eq 13 }).Count
  Write-Output "$f BOM=$bom CR=$cr"
}
```

Mong đợi `BOM=False CR=0` cho cả 3 file.
**Lưu ý:** phải dùng **đường dẫn tuyệt đối**. `.NET` dùng process cwd, không dùng
PowerShell location — dùng đường dẫn tương đối sẽ báo "Could not find file" dù file có thật.

---

## 5. Cấu trúc thư mục

| File | Vai trò | Ai được sửa |
|---|---|---|
| `cam_ai_core.py` | Lõi AI. `VERSION="2.7"` | Agent lõi |
| `app.py` | CLI | Agent lõi |
| `canh_bao.py` | Chuông/cảnh báo. **ĐÃ nối vào core** (qua `CanhBaoNoi`) | Agent lõi |
| `gui.py` | GUI desktop (~157 KB). Xây bố cục, phát hiện sự kiện | Agent GUI |
| `gui_khung.py` | Toàn bộ vẽ overlay + `PanelSuKien` (PIL, tiếng Việt có dấu) | Agent GUI |
| `web_server.py` | Web local FastAPI | — |
| `face_engine.py` | Nhận diện mặt. `FaceResult` chỉ có box/name/score/age/sex/face_size | — |
| `bao_cao_tong_ket.py` | Xuất Excel + HTML | — |
| `model_info.py` | Danh bạ model cho cửa sổ con | — |
| `_kiem_tra_gui.py` | Test accordion 4/4. **GIỮ LẠI** | — |
| `_kk_chup.py`, `_kk_chup_toan_man_hinh.py`, `_kk_bam_chay.py` | Script chụp ảnh. **GIỮ LẠI** | — |
| `video_mau/` | 7 video mẫu | — |
| `known_faces/An`, `known_faces/Binh` | **Dữ liệu giả**, chờ anh đồng ý xóa | — |
| `_thumb_cache/` | Cache poster video mẫu (7 thumbnail hợp lệ) | Agent GUI |
| `_kiem_chung/` | Ảnh chụp kiểm chứng | — |
| `_web_tmp/` | Thư mục làm việc web server (~83 MB) | — |

### Ảnh kiểm chứng

| Ảnh | Nội dung | Trạng thái |
|---|---|---|
| `kk_27_layout_moi.png` | Bố cục sau khi thay dropdown bằng thẻ poster | Đạt |
| `kk_28_chon_the.png` | Bấm thẻ "Cô xe" → đổi đường dẫn | Đạt |
| `kk_29_dang_chay.png` | Video chạy, khung + nhãn tên. **Phát hiện nhãn chồn** | Đạt (lỗi được phát hiện ở đây) |
| `kk_30_timeline.png` | Bố cục timeline mới. **Vẫn còn nhãn chồn** | Chưa đạt (đã sửa ở 2.7) |
| `kk_31_canh_bao.png` | Phóng to checkbox cảnh báo | Đạt |
| `kk_32_fix.png` | 4 lỗi giao diện 2.5 sau khi sửa | Đạt — **coordinator tự xem** |
| `kk_34_the_moi.png` | 13 thẻ poster thật | Đạt — **coordinator tự xem** |
| `kk_35_don_cuc_10_nguoi.png` | **15 người, 15 nhãn, 0 cặp chồm** (mục tiêu 2) | Đạt — **coordinator tự xem** |
| `kk_36_boc_cuc.png` | **Ảnh cửa sổ thật ở bản 2.7** 1916×1079: 13 khung bám người, nhãn tách biệt, video chiếm ~75%, tiêu đề cửa sổ `CamAI v2.7` (mục tiêu 3) | Đạt — **coordinator tự xem** |
| `kk_36_boc_cuc.txt` | Số đo bố cục 3 kích thước + đo nhãn tràn | Đạt |
| `kk_36_toan_man_hinh.png` | Ảnh toàn màn hình lúc đo — dùng để phát hiện cửa sổ bị che | Chỉ để đối chiếu |
| `fps_nghiemthu_300s_full.txt` | **Bài đo nghiệm thu live view 300s** (mục tiêu 1) | Đạt |

---

## 6. Gotcha kỹ thuật dỹ sai nhất

1. **PowerShell 5.1 đọc file UTF-8 không BOM thành ANSI.** `Get-Content` hiển thị
   `CamAIâ€”Phân tích`. Fix: `Get-Content -Encoding UTF8`.
2. **Console cp1252 không in được tiếng Việt có dấu.** `UnicodeEncodeError` khi `print()`
   ra terminal — lỗi console, KHÔNG phải lỗi file. Đã có `_log_an_toan()` tự lùi bản
   không dấu trong `cam_ai_core.py`.
3. **Không dùng `Get-Content | Set-Content` để sửa file tiếng Việt.** Nó chèn BOM, đổi
   LF→CRLF và double-encode. Dùng tool `edit`/`write`.
4. **`[System.IO.File]::ReadAllBytes()` dùng đường dẫn tương đối sẽ fail.** Phải truyền
   đường dẫn tuyệt đối.
5. **`winfo_height()` chỉ trả phần client, thiếu thanh tiêu đề (~39px).** `gui.py` dùng
   `GetWindowRect` qua ctypes + `SPI_GETWORKAREA`.
6. **Lúc `__init__`, Tk trả kích thước mặc định 200×200** chứ không phải kích thước đã
   `geometry()`. Phải chờ `winfo_width()` khớp mới tính.
7. **`Select-Object -First N` trong PowerShell cắt pipeline → exit code -1.** Đây là
   broken pipe của PowerShell, KHÔNG phải lỗi app. Muốn đo exit code thật thì
   `$o = & python ... 2>&1` rồi `$LASTEXITCODE`, đọc `$o` sau.
8. **`rm` với nhiều file một lúc hay bị treo.** Xóa 1–2 file mỗi lệnh. `rm` của runtime
   là trash có thể khôi phục, còn `Remove-Item -Force` bị chặn.
9. **`ast.parse()` PASS không bảo chứng GUI mở được.** Lỗi hằng số chưa định nghĩa là
   lỗi runtime. Phải chạy thật rồi chụp ảnh.
10. **`cv2.putText` không hiển thị tiếng Việt có dấu.** Mọi overlay vẽ bằng PIL/Pillow.
11. **Log `nhan_dien` của pipeline chính không tự đẩy tên xuống overlay live-view.**
    Live-view chạy YOLO + ArcFace riêng; phải tự quét tên theo track ID.
12. **`taskkill /F` KHÔNG bắt được, không có cách nào chặn.** Đây là giới hạn Windows.
    Cái sửa được: file hỏng không mang tên `.mp4` nữa (thành `.part.mp4`) + có đường
    dừng mềm thật là `SIGBREAK` (Ctrl+Break). Trên máy này `taskkill` không kèm `/F`
    bị **từ chối** với tiến trình console, nên Ctrl+Break là cách duy nhất.
13. **Chụp ảnh GUI phải ÉP CỬA SỔ LÊN TRƯỚC, không được chỉ chụp theo toạ độ Tk.**
    Em đã chụp nhầm ảnh khung bình luận YouTube vì cửa sổ CamAI bị Chrome che; chỉ
    khi chụp **toàn màn hình** mới phát hiện ra. `SetForegroundWindow` bị Windows từ
    chối khi gọi từ tiến trình nền/PowerShell, nhưng `attributes('-topmost')` do
    **chính tiến trình sở hữu cửa sổ** gọi thì luôn được. Sau đó chụp theo HWND:
    `u32.GetAncestor(app.winfo_id(), 2)` rồi `GetWindowRect` + `ImageGrab.grab(bbox, all_screens=True)`.
14. **Nút thắt live view là `PUMP_MS`, KHÔNG phải YOLO.** Đo đã bác bỏ giả thuyết
    "YOLO chạy 2 vòng": bật thêm pipeline chỉ làm fps 6.02 → 5.38. Vòng bơm mỗi lần
    chỉ lấy khung **cuối** trong hàng đợi nên trần hiển thị ≈ `1000 / PUMP_MS`.
    Ở `PUMP_MS=120` trần chỉ 8.3 fps. Chi phí đo phẳng: YOLO+ByteTrack 38.5 ms,
    vẽ PIL 15.5 ms, JPEG 4.5 ms → tổng 63 ms (15.8 fps lý thuyết); phần còn lại là
    `PhotoImage`/`configure` ~46 ms mỗi lần bơm.
15. **Chỉ đổi `minsize` của cột grid thì KHÔNG co cột.** Tk lấy bề rộng widget từ
    `reqwidth` (nội dung thẻ sự kiện đòi), nên phải set **cả** `minsize` của cột
    **và** `width` của panel.
16. **Chạy script kiểm chứng phải dùng `.venv\Scripts\python.exe`.** `python` trong
    PATH thiếu `supervision` → `ModuleNotFoundError`, dễ tưởng lỗi code.
17. **Trong script kiểm chứng, đừng dùng `"DAT" in "KHONG DAT"`** — chuỗi `"DAT"`
    nằm trong `"KHONG DAT"` nên luôn True. Phải so sánh nguyên vẹn hoặc dùng bool.
18. **Chờ khung hình đầu tiên phải có điều kiện, không đợi cứng.** Nạp model mất
    ~7 s; đợi cứng 4 s thì đo nhầm là "video không chạy".

---

## 7. Việc chưa làm / giới hạn thật

- **Chưa có video/ảnh thật của anh** → chưa đánh giá được độ chính xác production.
  Ảnh quảng cáo HuiFan/HFSECURITY chỉ dùng làm **tham chiếu bố cục**, không suy đoán
  được model hay độ chính xác của sản phẩm đó.
- **Không có model khẩu trang** → cột `Mask:` luôn hiện `Chưa rõ`.
- **`known_faces/An`, `known_faces/Binh` là dữ liệu giả.**
- Web **đã kiểm lại** (2026-10-19): trang chủ 200, API 401 chưa đăng nhập — đúng thiết kế.
- Web **chưa thử trên điện thoại thật**, **chưa thử nhiều người dùng đồng thời**.
- Chỉ chạy thật **một** video mẫu đầy đủ trong kiểm chứng web.
- **Số đo 300s dùng FILE VIDEO, chưa phải webcam thật.** Cần nhiều tiến trình
  GUI/AI dừng trước khi đo hiệu năng — nhiều instance cùng giữ model GPU sẽ làm
  sai số đo fps.
- Còn thư mục `_dns_probe/` rỗng, một tiến trình giữ handle nên chưa xóa được.
- Tunnel `camvision` trên Cloudflare đã dừng nhưng resource local chưa xóa hết.

---

## 8. Việc tiếp theo — thứ tự gợi ý

1. **Anh xác nhận mục 7:** mở GUI, kéo cửa sổ, xác nhận còn giật hay không.
   Nếu còn giật → em đo tiếp và báo kèm số liệu, không tự kết luận.
2. **Anh xác nhận mục 8:** gửi video thật + ảnh người quen (nếu muốn nhận diện
   tên), hoặc tự xem video demo và nhận xét độ đúng.
3. Cân nhắc khôi phục lại lưới "Đối tượng phát hiện" bị bỏ, và cho chọn kênh cảnh báo
   (cần thêm cờ vào `cam_ai_core.py`).
4. Kiểm lại web local (HTTP 200 + 401).
5. Chờ anh: có làm webcam live không · có cần model khẩu trang không · xóa `known_faces` giả không.

---

## 9. Lịch sử thay đổi

| Ngày | Việc |
|---|---|
| 2026-10-19 (sau 09:00) | **Nghiệm thu 2.5 — 6/6 mục tự đo ĐẠT.** Sửa `PUMP_MS` 120→30 (live view **14.34 fps** 300s); sửa `_vuot_nhau` (0 cặp nhãn chồm ở khung 15 người); cột sự kiện co theo (bố cục **75.4%–83.2%**, 0 nhãn tràn). 6 video demo mới → 13 thẻ. Bump 2.5 → 2.6 → **2.7**. Mục 7/8 chờ anh. |
| 2026-10-19 (sau 18h) | Sửa lõi: nối `canh_bao.py`, clip `.part.mp4` an toàn, `--lop` báo lỗi rõ. Đổi bố cục GUI sang 3 vùng theo mẫu (video + timeline sự kiện + bảng thống kê vùng). Nối checkbox cảnh báo. Còn 4 lỗi hiển thị + live view. **Chưa bump VERSION (vẫn 2.4).** |
| 2026-10-19 (trước) | Dừng tunnel CamAI, xóa `config.yml` + credentials. Sửa cửa sổ GUI tràn taskbar. Bump 2.2 → 2.3. Tạo 4 file tài liệu bàn giao. Bump 2.3 → 2.4 + GUI chuyển sang visual. |
| 2026-10-18 | Hoàn thiện GUI (khung realtime, tạm dừng, ghi log hàng loạt) và web server (đăng nhập, khóa 5 phút, tải CSV/XLSX/HTML). Sửa hardcode mật khẩu → fail-closed. |
| trước đó | Lõi AI, CLI, nhận diện mặt, báo cáo Excel/HTML. |