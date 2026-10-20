# Đọc file này đầu tiên khi quay lại làm tiếp

**Ngày cập nhật:** 2026-10-20 (sau 09:50 — bản **3.5** sửa giật kéo cửa sổ (lần kéo đầu: 984 ms → **19,4 ms**) + thêm **launcher 1-click** để anh tự mở app, `VERSION` nay là **3.5**)
**Phiên bàn giao:** `mvs_cb81c4611fb14dd8ba4717ff00672d2b`
**Trạng thái ngắn:** **6 mục nghiệm thu tự đo — CẢ 6 ĐÃ ĐẠT** ở bản 2.8 (đo lại toàn bộ
sau khi thêm `--tach-o`), mỗi mục có output thật kèm tên file. Mục 7 và 8 **chờ anh tự
xác nhận** nên chưa được coi là đạt. Live view **14.54 fps** liên tục 300 giây.
Bố cục **75.4% → 83.2%**. Nhãn người **0 cặp chồm** trên khung 15 người.
Công tắc **"Nhận người ở xa (chậm hơn)"** đã có trong CLI và GUI, **mặc định TẮT**.

**Bản 3.5 (mới nhất):** anh dùng thật và báo **"kéo cửa sổ bị giật lắm"** + **"chả bao giờ chỉ
tôi cách mở app"**. → (1) **Sửa giật**: tìm ra `CTkScrollbar._draw()` gọi `update_idletasks()` →
xả hết hàng đợi idle của **toàn bộ app** → vẽ lại 851 widget → tre 600–900 ms ở **lần kéo
đầu tiên**. Đã sửa + **khởi động ấm** → lần kéo đầu còn **19,4 ms, 0 lần tre**. (2) **Launcher
1-click** `Mo CamAI.vbs` + hướng dẫn `HUONG-DAN-MO-APP.md`. Xem **mục 2.1i**.

**Bản 3.4:** anh yêu cầu thiết kế lại toàn bộ giao diện (vì *"app nhìn cứ phèn phèn"*) bằng skill
**`ui-ux-pro-max`** + làm lại **icon app bằng ảnh AI** (Nano Banana Pro).
Sinh `design-system/camai/MASTER.md` làm nguồn sự thật, tách hằng số sang file mới
`giao_dien.py`, dựng **thanh đầu mới** có icon app, **bỏ hết emoji làm icon** (dùng font
biểu tượng Windows `Segoe MDL2 Assets`), lên lại typography + component + lưới khoảng cách.
Coordinator tự mở ảnh và **phát hiện 2 lỗi thị giác thật** (dấu ✓ trong ô checkbox biến
mất; icon nút DỪNG trông như tofu) → đã sửa. Xem **mục 2.1h**.

**Bản 3.3:** anh chốt hướng **"bộ công cụ AI dùng tay"** — đẩy những thứ
đã có sẵn ở CLI vào **GUI**. Thêm: (1) tách **2 ô xem video** → **"Xem trực tiếp"** +
**"Xem khung hình kết quả"** (trước 1 ô mang 2 nghĩa); (2) nút **"Đăng ký người quen…"**
(lưu vào `known_faces/<Tên>/` ngay trong GUI); (3) nút **"Vẽ vùng ngay tại đây"** (kéo
chuột trong chính cửa sổ, module mới `ve_vung_gui.py`); (4) nút **"Đọc biển số thử…"**
(đọc 1 ảnh để anh gửi ảnh biển số thật mà không cần chạy video). Sửa **1 lỗi thật** do
coordinator phát hiện khi tự chạy: đọc `StringVar` từ thread nền → `main thread is not
in main loop`. Kiểm chứng **4/4 PASS** (bộ script riêng của coordinator) + hồi quy
**7/7 PASS**. Xem **mục 2.1g**.

**Bản 3.2:** sửa **1 lỗi hiển thị** còn lại từ lần rà bản PC — panel
**"Xem video"** (panel lớn nhất của GUI) **đen suốt** khi chạy phân tích theo lô.
Thêm `frame_cb` + `frame_cb_interval` vào `run_analysis()` (khung **đã có overlay**;
`None` → chi phí 0; callback lỗi không làm chết pipeline) + GUI nhận khung qua **hộp
thư 1 ô** (tránh phình bộ nhớ) + giới hạn **10 fps** + ẩn nút "Tạm dừng" ở chế độ lô.
Kiểm chứng **7/7 PASS**, vùng panel đo được **118.735 màu / sáng TB 73,95** (trước là
đen), coordinator **tự xem ảnh** thấy khung người + nhãn **An**/**Binh**. Xem **mục 2.1f**.

**Bản 3.1:** sửa **3 lỗi chết app** tìm được khi rà toàn bộ bản PC —
(1) đường dẫn tương đối bị phân giải theo thư mục đang chạy nên chạy `app.py` từ
thư mục khác là **chết ngay** với `[loi] khong thay bo model ArcFace`; (2) app không
tự tạo thư mục output → lỗi khó hiểu; (3) `--tu-luu-clip` cùng thư mục với video
kết quả thì **xoá mất video kết quả nhưng vẫn exit 0**. Thêm file `duong_dan.py`
làm nguồn sự thật duy nhất cho đường dẫn. Xem **mục 2.1e**.

**Bản 3.0:** thêm **đọc biển số xe Việt Nam**
(module mới `bien_so.py`) + **tự chụp ảnh khi có sự kiện** (module mới `tu_chup.py`),
mặc định **TẮT**. Sửa 3 lỗi nghiêm trọng pipeline OCR, sửa lỗi **ô gợi ý trong ô nhập
không hiện**, và chuyển pha tìm vùng biển sang **luồng nền** để không làm khựng video.
Xem **mục 2.1c**.

> **Hướng hiện tại (anh chốt 2026-10-20):** phần **web/browser TẠM DỪNG**.
> Chỉ hoàn thiện **bản PC**. "Chuẩn xem bản PC có tính năng nào chạy được là được rồi."

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

### 2.1c ĐÃ ĐẠT — bản 3.0 (đo 2026-10-19 sau 18:00, `VERSION` 2.8 → **3.0**)

Bản 3.0 thêm 2 nhóm tính năng lớn + sửa 4 lỗi. **Coordinator tự chạy lệnh và tự xem
ảnh bằng mắt**, không tin báo cáo của agent.

#### ĐÃ ĐẠT

| Hạng mục | Kết quả đo thật | Bằng chứng | Người xác nhận |
|---|---|---|---|
| Module `bien_so.py` (đọc biển số VN, mặc định TẮT) | Chuẩn hoá **28/28** ảnh, biển VN **16/16**, biển nước ngoài đọc sai **0/6** | `_kk_doi_chieu_bien_so_v3.py` (output console) | **Coordinator tự chạy** |
| Module `tu_chup.py` (tự chụp ảnh sự kiện, mặc định TẮT) | Tạo file đúng định dạng `bien_so_YYYYmmdd_HHMMSS_30A-12345.jpg` | `_kk_out/cli_bien_so_VN/` | **Coordinator tự xem** |
| 2 nhóm GUI mới ("Đọc biển số xe", "Tự chụp ảnh khi có sự kiện") | Render đúng, ô "Vùng cần quét" có gợi ý "tự tìm", ghi chú tốc độ có dấu | `_kk_out/v3_40_gui_nhom_bien_so.png`, `zoom_v3_40_bien_so.png`, `_kk_out/v3_41_gui_nhom_tu_chup.png` | **Coordinator tự xem ảnh bằng mắt** |
| **Sửa lỗi ô gợi ý trong ô nhập không hiện** | Chữ "tự tìm" / "mặc định" hiện đầy đủ, nền khớp tuyệt đối `#272F42`, viền trắng liền mạch, **không che viền** | `_kk_out/v3_20_goi_y_hien.png`, `v3_30_goi_y_mac_dinh.png`, `v3_31_goi_y_tu_tim.png`, `zoom_v3_20_goi_y.png`, `zoom_v3_30_mac_dinh.png` | **Coordinator tự xem ảnh bằng mắt** |
| **Đọc biển số KHÔNG làm khựng pipeline** | Trước: **680,9 ms** (có ROI) / **1916,6 ms** (không ROI) mỗi khung → sau: **5,2 ms** / **7,5 ms**; khung chậm nhất **0,9 ms** / **1,5 ms** | `_kk_do_chi_phi_doc_bien_so.py` (250 khung) | **Coordinator tự chạy lại** |
| Chi phí đọc 1 biển số | Không ROI: median **14,47 ms**, p95 **23,34 ms**, **max 62,14 ms**. ROI nhỏ 44.000 px: median **10,22 ms**, p95 **14,49 ms**, **max 17,69 ms**. ROI rộng: median **9,01 ms**, p95 **18,75 ms**, **max 46,06 ms**. Cả 3 chế độ đọc đúng `30A-12345` | `_kk_agent_d_kiem_nen.py` | **Coordinator tự chạy** |
| Xác nhận đa khung hình + cơ chế `mau_thuan` | **PASS** — chuỗi chỉ ghi khi xuất hiện ≥2 khung liên tiếp; ảnh nghiêng 11° bị chặn | `_kiem_chung/kiem_xac_nhan_da_khung.txt` | **Coordinator tự chạy** |
| 10 ảnh biển số VN **giả** → đọc đúng chuỗi | **10/10 PASS**, **0** ảnh bị thêm ký tự | `_kiem_chung/kiem_bien_so_gia.txt` | **Coordinator tự chạy** |
| Ghi chú tốc độ OCR trên GUI dùng **số đo thật** | Thay "20–430 ms" bằng "mỗi lần quét tốn 9–15 ms, khung hình chậm nhất 62 ms (đo thật 19/10/2026)" — 2 chỗ + bản dịch Anh | đọc lại `gui.py` | **Coordinator** |
| Bản dịch Anh cho **mọi** ghi chú | **30/30** ghi chú đã có bản dịch Anh, **0 thiếu** | `_kk_kiem_dich_ghi_y.py` | **Coordinator tự chạy** |
| 4 lệnh hồi quy CLI | Tất cả **exit 0**; `--help` in đủ cả 8 cờ biển số/tự chụp, không crash | output dòng lệnh | **Coordinator tự chạy** |
| `_kiem_tra_gui.py` | **4/4 PASS**, `EXIT=0`; cửa sổ 1610×980; tiêu đề `CamAI v3.0 — Phân tích video giám sát` | output dòng lệnh | **Coordinator tự chạy** |
| `py_compile` 5 file lõi | `cam_ai_core.py`, `gui.py`, `app.py`, `bien_so.py`, `tu_chup.py` → **exit 0** | output dòng lệnh | **Coordinator tự chạy** |
| Artifact CSV/MP4 **không bị đổi** khi bật/tắt tính năng | `git status --short -- '*.csv' '*.mp4'` → **rỗng** | đo trực tiếp | **Coordinator tự chạy** |

#### CHƯA ĐẠT — bản 3.0

| Hạng mục | Vì sao chưa đạt | Việc cần làm |
|---|---|---|
| **OCR biển số chưa nghiệm thu** | Chưa có **ảnh biển số VN thật** của anh. 10 ảnh kiểm chứng là **ảnh giả do PIL dựng** (ánh sáng, nhiễu, góc nghiêng, độ nét thật chưa từng có) | **Anh gửi ảnh biển 2 hàng kiểu `30A`/`12345`** (và biển 1 hàng nếu có) |
| **Cache vùng có thể bỏ sót biển mới** | Vùng tìm được cache 10 s theo toạ độ tương đối; biển mới xuất hiện trong vùng đó có thể chờ tới lượt quét kế tiếp (~2 s) | Chấp nhận hoặc yêu cầu bỏ cache |
| **Biển 2 hàng có thể ghép sai** | Vùng tìm được là khung **CHỮ**, nên `30A` (hàng trên) và `12345` (hàng dưới) ghép vào cùng chuỗi | Chỉ chốt khi có ảnh thật |
| **Hạn chi phí 50 ms có thể cắt trường hợp biển 2 hàng** | Đo thật biển 2 hàng mất ~54 ms → có thể bị cắt khi hết hạn chi phí | Nới hạn nếu ảnh thật cho thấy cần |
| Mục 7 (kéo cửa sổ) + mục 8 (độ nhận diện) | Không đổi so với bản 2.8 | **Anh tự xác nhận** — xem mục 2.2 |

---

### 2.1d TRẠNG THÁI TỪNG TÍNH NĂNG — cái nào đã chạy "legit"

Phân 3 mức để không nhầm "có code" với "đã chạy thật":

- **MỨC 1 (legit)** — đã chạy thật **và** coordinator tự đo / tự xem bằng mắt.
- **MỨC 2** — đã có code **và** đã chạy thật, nhưng coordinator **chưa tự xem bằng mắt**.
- **MỨC 3** — mới có code hoặc chưa chạy thật.

#### MỨC 1 — đã chạy legit

| Tính năng | Bằng chứng |
|---|---|
| Phát hiện người (YOLO11) | đo thật qua `run_analysis()`, 5 tầng model đo CPU — `_kiem_chung/fps_model_yolo11*.txt`, `do_chinh_xac_model.txt` |
| Nhận diện khuôn mặt + tên người quen (ArcFace) | `_kiem_chung/ket_hop_dem_nguoi_va_nhan_dien_mat.txt` (100% khung có mặt ở video đông người) |
| Ước lượng tuổi / giới | CSV có cột `nam`, `nu`, `tuoi_tb` |
| Đếm ra – vào | hồi quy L1 (vào vùng 1), L2 (nhạy max 2/4 người) |
| Canh vùng + vượt ngưỡng + đứng lâu | L1: đứng lâu 1 lần, dài nhất **10.0 s** |
| Lưu clip khi có sự kiện | L3 sinh ra `.mp4` + `.csv` |
| Nhận diện vật thể (80 lớp) | `--lop car` → `xe o to: 15 khung hinh` |
| Chọn CPU/GPU + chọn model | `kk_37_chay_bang_gi.png` — **coordinator tự xem ảnh** |
| `--tach-o` (nhận người ở xa) | `_kiem_chung/kiem_tach_o.txt` (dam-dong 3.0→5.4, xe-co 1.0→4.6) |
| `face_every` tối ưu | bảng 5 cấu hình đo thật (mục 2.5) |
| Live view ≥10 fps | **14.54 fps** liên tục 300 s, 0/294 s dưới 10 fps |
| Bố cục ≥70% + 0 nhãn chồm | 75.4%–83.2%, 0 cặp chồm ở khung 15 người — **tự xem ảnh** |
| 4 lệnh hồi quy + CSV 251×10 | tất cả exit 0, đo trực tiếp |
| `_kiem_tra_gui.py` | 4/4 PASS, `EXIT=0` |
| Encoding UTF-8 không BOM | đo byte thật (`BOM=False CR=0`) |
| Web local | `GET /` → 200; API → 401 chưa đăng nhập (đúng thiết kế) |
| **Sinh** cảnh báo (log) | `--bat-canh-bao` → `[canh bao] ... dung_lau` |
| OCR biển số — **phần logic** | 10/10 ảnh giả, chuẩn hoá 28/28, biển VN 16/16, ngoại sai 0/6, xác nhận đa khung PASS |
| GUI: 2 nhóm mới + tooltip + ô gợi ý | ảnh `v3_40`, `v3_41`, `v3_10`–`v3_13`, `v3_20/30/31`, `zoom_*` — **coordinator tự xem** |
| Ghi chú tốc độ bằng số đo thật | 30/30 ghi chú có bản dịch Anh, 0 thiếu |
| **Tự chụp ảnh khi có sự kiện** (`--tu-chup`) | Chạy lại code **hiện tại** → `su_kien_20261019_220301_vao_vung_nguoi1.jpg` (157 KB, 960×540, 33.985 màu) — **coordinator tự xem**: thấy 2 người + overlay tiếng Việt **"An \| Nam 67"**, **"Binh \| Nam 52"**; `_bang_ke_chup.csv` ghi đúng `vao_vung` / "Có người vào vùng canh" / `so_nguoi=1` |
| **Xuất Excel + HTML xem lại** | Excel `one-by-one-person-detection_tong_ket.xlsx` (12,8 KB) đọc bằng openpyxl → 3 sheet có số thật: `Tong ket` 24×4, `Theo gio` 7×6, `Cu theo giay` 144×8; HTML `_xem_lai.html` (35 KB) **coordinator tự mở bằng browser thật** → render đúng: 1.394 khung hình, 00:06 giây đông nhất, TB 0,74 người, 2 người quen (Bình, An), biểu đồ "Số người theo thời gian" |
| **Video player trong HTML xem lại** (sau khi sửa codec) | Video kết quả giờ dùng **H.264 (`avc1`)** thay cho `mp4v` (MPEG-4 **Part 2** — Chrome/Edge/Firefox **không phát được**). Đo thật: `ffprobe` → **`codec_name=h264`**, 960×540, 10,0 s; `ffmpeg -f null -` → **exit 0**; **coordinator mở HTML bằng browser thật** → `<video>` **không còn "Unable to play media."**, controls **không còn disabled**, scrubber **"total time: 0:10"**, console **0 lỗi** |
| **Rà bản PC: 32 cờ CLI** | **26/26 lệnh EXIT=0**, video đều **H.264 960×540**, CSV đều **251 dòng** — xem mục 2.1e |
| **`--pixelate` (làm mờ mặt)** | B12: **coordinator tự xem ảnh so sánh B8 vs B12** → mặt người trong vùng bị **vỡ hạt (mosaic)**, khung đỏ `VÙNG CẢNH: 1 người` |
| **`--min-face`** | B8 (`--min-face 40`) **không** bắt mặt ở khung hình mà B12 (mặc định) **bắt** → ngưỡng có tác dụng thật |
| **`--vung-bien-so` (vùng ROI cho OCR)** | B9: log `vung ROI: 0.1,0.3,0.9,0.8`; video demo không có biển VN nên `Khong doc duoc bien so nao` — **đúng hành vi** |
| **GUI end-to-end (bấm nút Chạy thật)** | Ảnh `_kk_out/gui_e2e/*.png` — **coordinator tự xem**: `▶ Đang chạy` → `✔ Xong`, `247/250 · 99%`, `2 Người / 2 Mặt / 2 Người quen`, file `.mp4` 16.247.979 B + `.csv` sinh ra |
| **Chạy app từ thư mục bất kỳ** (BUG #1 đã sửa) | CWD = `C:\Windows` + có nhận diện mặt → **EXIT=0**, `[model] ...models\face_core \| GPU \| detection:CUDA`, CSV cột `nguoi_quen` = **"An \| Binh"** |
| **App tự tạo thư mục output** (BUG #2 đã sửa) | `--output` vào thư mục **chưa tồn tại** → thư mục được tạo, có cả `.mp4` + `.csv` |
| **Video kết quả không bị mất khi bật `--tu-luu-clip`** (BUG #3 đã sửa) | Chạy lại B3: file rác `.part.mp4` **bị xoá** (`da don 1 file`) **và** `ket_qua_ket_qua.mp4` **16.253.729 B vẫn còn**, `ffprobe` → `h264,960,540` |
| **Xem video ngay trong lúc chạy phân tích theo lô (GUI)** (bản 3.2) | `_kk_kiem_gui_batch_preview.py` → **PASS**: khung hình hiện lên panel **82 lần**; vùng panel đo được **118.735 màu đơn sắc / sáng TB 73,95 / max 255 min 0** (trước là đen) — **coordinator tự xem ảnh** `v5_dang_chay.png` thấy khung tím `Người 1..4`, khung xanh mặt nhãn **An**/**Binh**, badge `Người: 4 \| Mặt: 2` |
| **Tách 2 ô xem video** (bản 3.3) | `_kk_kiem_gui_b3.py` mục [1] → **PASS**: `chk_xem_video` = **"Xem trực tiếp"**, `chk_xem_ket_qua` = **"Xem khung hình kết quả"**, mặc định cả 2 = "1" — **coordinator tự xem ảnh** `b3_full.png`: cả 3 checkbox hiện đủ chữ, không chồm nhau |
| **Đăng ký người quen trong GUI** (bản 3.3) | `_kk_kiem_gui_b3.py` mục [2] → **PASS**: nút "Đăng ký người quen…" chạy thật trên `known_faces/An/01.jpg` → tạo `known_faces_test/KiemThuV33/01.jpg`, log `> Tìm thấy 1 khuôn mặt`, `> Số ảnh đã lưu: 1`, `> Đã học được: KiemThuV33` |
| **Vẽ vùng trong GUI** (bản 3.3) | `_kk_kiem_gui_b3.py` mục [4] + `_kk_kiem_canvas_vung.py` → **PASS**: canvas kéo chuột trả tọa độ **sai số 0.0000**; file vùng ghi đúng `0.2000 0.1500 0.8000 0.9500`; **coordinator tự xem ảnh** thấy hình chữ nhật xanh đúng chỗ kéo |
| **Đọc biển số thử trong GUI** (bản 3.3) | `_kk_kiem_gui_b3.py` mục [3] → **PASS**: nút "Đọc biển số thử…" đọc ảnh biển số giả 2 hàng → log `Biển số: 30A-12345 \| tin cậy 0.67 \| số hàng: 2`, ảnh crop đã lưu. **Lưu ý: ảnh này là ảnh GIẢ, chưa phải nghiệm thu ảnh thật** |
| **Kéo cửa sổ không giật** (bản 3.5) | `_kk_do_keo_dau_tien.py` (coordinator tự đo) → lần kéo **ĐẦU TIÊN**: `max` **19,4 ms**, `tb` 14,9 ms, `p90` 17,5 ms, **0 lần tre > 30 ms** (trước: **859–984 ms**, 3–9 lần tre). Thời gian mở app **không chậm hơn** (13,3 s → 12,5 s) |
| **Launcher 1-click** (bản 3.5) | `Mo CamAI.vbs` — **đã chạy thật**: tiến trình `pythonw.exe ... gui.py` xuất hiện, đóng sạch. Kèm `Mo CamAI.bat` (in lỗi) + `HUONG-DAN-MO-APP.md` |

#### MỨC 2 — đã chạy thật, chưa tự xem bằng mắt (nên mở xem 1 lần rồi đánh dấu)

| Tính năng | Bằng chứng | Việc còn lại |
|---|---|---|
| Cảnh báo gửi **tin** ra ngoài | `canh_bao.py` sinh log cảnh báo | **Chưa chứng minh tin tới nơi** (Telegram/email) — cần token thật |

#### MỨC 3 — chưa chạy thật / chưa có bằng chứng

| Tính năng | Ghi chú |
|---|---|
| OCR biển số trên **ảnh thật** | Chưa có ảnh thật của anh → chưa chạy được |
| Webcam live `--input 0` | Chưa thử camera thật |
| Web trên điện thoại thật | Chưa |
| Nhiều người dùng đồng thời trên web | Chưa |
| Chạy 24/7 + xoay vòng dữ liệu | Chưa |
| Multi-camera | Chưa — `--input` chỉ nhận **1** nguồn |
| Chống đếm trùng 1 người | Chưa |
| Báo cáo theo ca / ngày | Chưa (CSV là **theo giây**) |
| Đăng ký **nhiều người cùng lúc** trong GUI | Bản 3.3 làm **1 người / 1 lần** (`cluster(max_people=1)`). Muốn nhiều người trong 1 video thì phải tách nhóm nhiều người + giao tên cho từng nhóm |
| **Nhiều vùng** cảnh trong 1 file | Bản 3.3 làm **1 vùng** (đúng như CLI cũ `ve_vung.py`) |
| Dashboard tổng quan | Chưa |
| Rule cảnh báo theo điều kiện (theo giờ, kèm ảnh) | Chưa |
| Giám sát sức khoẻ hệ thống (camera lỗi, ổ đầy) | Chưa |
| Khẩu trang | Chưa — cột `Mask:` luôn "Chưa rõ" |

> Hướng triển khai tiếp (use case chung + tầng nền tảng theo thứ tự ưu tiên) nằm ở
> **`USE_CASE.md`**. Lần sau bí không biết làm gì → lôi file đó ra.

> ⚠️ **Cảnh báo bằng chứng giả — 6 ảnh trong `_kk_out/ocr_thu/su_kien/` KHÔNG dùng được.**
> 6 file `su_kien_2026*_vua_toi/vuot_vung.jpg` (5,4 KB) đo ra là **ẢNH ĐEN HOÀN TOÀN**
> (`mau_don_giac=1`, max=0, min=0). Tên sự kiện `vua_toi` / `vuot_vung` **không có trong**
> hằng số `LOAI_SU_KIEN` hiện tại của `tu_chup.py`
> (`vuot_nguong_dong`, `nguoi_quen`, `vao_vung`, `dung_lau`, `co_nguoi`, `bien_so`).
> → Đây là **artifact của prototype cũ**, KHÔNG phải bằng chứng của code hiện tại.
> Bằng chứng hợp lệ của `--tu-chup` là ảnh **960×540, 157 KB, 33.985 màu** tạo
> ngày 2026-10-19 ở `_kk_out/tu_chup_thuc_te/` (xem dòng MỨC 1 ở trên).

---

### 2.1e RÀ TOÀN BỘ BẢN PC — 2026-10-20, `VERSION` 3.0 → **3.1**

**Phạm vi:** anh chốt "chuẩn xem bản PC có tính năng nào chạy được là được rồi" →
coordinator **tự chạy thật** toàn bộ **32 cờ CLI** của `app.py` + **6 script kiểm chứng
OCR** + **GUI end-to-end**. **Không tính báo cáo của agent** — mọi dòng dưới đây là
output coordinator tự chạy và **tự xem ảnh bằng mắt**.

**Kết quả tổng:** **26/26 lệnh EXIT=0**, video kết quả đều **H.264 960×540**,
CSV đều **251 dòng**. Rà này phát hiện **3 lỗi chết app** (đã sửa, xem bảng dưới) và
**1 lỗi hiển thị** (chưa sửa).

#### A) Lõi & vùng (batch A)

| Cờ | Lệnh đã chạy thật | EXIT | Bằng chứng đo thật |
|---|---|---|---|
| `--no-face` | A1 | 0 | chạy nhanh, không nạp ArcFace, video vẫn ra |
| `--vung` | A2 | 0 | vẽ vùng + đếm "Trong vùng" |
| `--vung-nhay` | A3 | 0 | vùng nhạy hơn, số người trong vùng tăng |
| `--lop car` | A4 | 0 | `xe o to: 15 khung hinh` |
| `--lop car,motorcycle` | B2 | 0 | `xe o to : 15 khung hinh, toi da 1` |
| `--tach-o` | A5 | 0 | nhận người ở xa (dam-dong 3.0→5.4) |
| `--nhan-vat-the` | B1 | 0 | log `nhan them 9 lop: xe dap, xe o to, xe may, ...` |
| `--bat-canh-bao` | A10 + B5 | 0 | `[canh bao] 00:21:45 canh bao: dung_lau` + `chuong: co, hop thoai: co` + `hop thoai tu dong dong sau 60s` — **không có token nên KHÔNG gửi ra ngoài** |
| `--canh-bao-mo-phong` `--canh-bao-gioi-han 2` `--canh-bao-go 5` | B6 | 0 | nhận diện người quen 2 lần, mở phòng khi quá số người |
| `--pixelate` | A11 + B12 | 0 | **coordinator tự xem ảnh**: mặt người trong vùng bị **vỡ hạt** (mosaic), khung đỏ `VÙNG CẢNH: 1 người` |
| `--canh-lau` | hồi quy L1 | 0 | đứng lâu 1 lần, dài nhất **10.0 s** |
| `--face-every 5` | B7 | 0 | ArcFace chạy, video OK |
| `--min-face 40` | B8 | 0 | **so sánh trực tiếp với B12**: cùng 1 khung hình, B8 **không** bắt mặt, B12 (mặc định) **bắt** → cờ này **có tác dụng thật** |
| `--thiet-bi cpu` | A12 | 0 | chạy CPU, chậm hơn nhưng ra kết quả |
| `--model yolo11s.pt` | A13 | 0 | model tải về, chạy được |
| `--tu-luu-clip DIR` `--clip-giay 6` | B3 | 0 | clip 6.0 s = 3.0 s trước + 3.0 s sau; **sau khi sửa BUG #3 thì video kết quả vẫn còn** |
| `--tu-luu-clip DIR` `--clip-ghi-tat-ca` | B4 | 0 | clip 10.0 s; video kết quả vẫn còn |
| `--tu-chup` `--tu-chup-dir DIR` `--tu-chup-nhoan-lai-giay 5` | B10 | 0 | sinh `su_kien_..._nguoi_quen_nguoi4.jpg` + `_bang_ke_chup.csv`; **coordinator tự xem ảnh**: 2 khuôn mặt, khung xanh, nhãn **"An \| Nam 52"** và **"Binh \| Nam 52"** |
| `--doc-bien-so` | A6 | 0 | bật được, không làm khựng pipeline |
| `--doc-bien-so` `--vung-bien-so "0.1,0.3,0.9,0.8"` | B9 | 0 | log `vung ROI: 0.1,0.3,0.9,0.8`; video demo **không có biển số VN** nên `Khong doc duoc bien so nao` — **đúng hành vi**, không phải lỗi |
| `--doc-bien-so` `--bien-so-tin-cay 0.7` `--bien-so-nhoan-lai-giay 10` | B11 | 0 | log cảnh báo rõ: `Model nay KHONG co class 'plate' ... -> doc OCR ca khung hinh` |

#### B) Script kiểm chứng OCR (batch B) — **6/6 PASS**

| Script | Kết quả đo thật |
|---|---|
| `_kk_kiem_bien_so_gia.py` | **10/10** đúng chuỗi |
| `_kk_doi_chieu_bien_so_v3.py` | **16/16** đúng, ngoại sai **0/6**, TB **19,8 ms/crop** |
| `_kk_agent_a_xac_nhan.py` | **PASS** (không báo biển sai) |
| `_kk_do_chi_phi_doc_bien_so.py` | ROI **2,5 ms/khung** vs không ROI **7,5 ms/khung** (250 khung) |
| `_kk_kiem_bien_so.py` | EXIT=0 khi có `PYTHONIOENCODING=utf-8` — lỗi **của script test**, không phải của app (`app.py` đã có `_chuan_hoa_console()`) |
| `_kk_agent_d_kiem_nen.py` | **PASS**, cả 3 chế độ đọc được `30A-12345` |

#### C) GUI end-to-end — coordinator tự xem ảnh

Ảnh: `_kk_out/gui_e2e/gui_dang_chay.png` + `gui_chay_thuc.png`.
Kết quả từ 2 ảnh coordinator **tự mở xem bằng mắt**:

| Hạng mục | Nhìn thấy trong ảnh | Kết luận |
|---|---|---|
| GUI khởi động | `CamAI v3.1 — Phân tích video giám sát`, 12 nhóm tùy chọn, 10 thẻ video mẫu | **ĐẠT** |
| Nút chạy thật | `▶ Đang chạy` → `✔ Xong`, thanh tiến trình xanh, `Khung hình 247/250 · 99%` | **ĐẠT** |
| Số liệu chạy thật | `2 Người · 2 Mặt · 2 Người quen`, nhật ký `frame 200/250 \| Người: 3` | **ĐẠT** |
| Nhận diện tên | `Nguoi da hoc trong video: ['An', 'Binh']` | **ĐẠT** |
| File sinh ra | `video_test_ket_qua.mp4` 16.247.979 B + `video_test_bao_cao.csv` | **ĐẠT** |
| **Khung "Xem video" trong lúc chạy** | **ĐEN, không có hình** | **CHƯA ĐẠT ở bản 3.1** → **đã sửa ở bản 3.2**, xem mục 2.1f |

#### D) 3 BUG THẬT tìm được khi rà — đã sửa ở bản 3.1

| # | Triệu chứng (coordinator tự tái hiện) | Nguyên nhân | Cách sửa | Bằng chứng sau sửa |
|---|---|---|---|---|
| **BUG #1** | Chạy `app.py` với CWD = `C:\Windows` → **exit 1**, `[loi] khong thay bo model ArcFace` (dù model có đủ trên đĩa) | `face_engine.py` dùng `models/face_core` **tương đối theo CWD** | File mới `duong_dan.py` = nguồn sự thật duy nhất; `MODEL_DIRS` tuyệt đối theo `APP_DIR`; `app.py` chuẩn hoá `--input/--faces/--model/--vung/--output` | CWD = `C:\Windows` + **có nhận diện mặt** → **EXIT=0**, log `[model] H:\AI Project\cam-ai\models\face_core \| GPU \| detection:CUDA \| genderage:CUDA \| recognition:CUDA`, CSV 250 dòng, cột `nguoi_quen` = **"An \| Binh"** |
| **BUG #2** | `--output` trỏ vào **thư mục chưa tồn tại** → `[loi] khong gia duoc file video ket qua` | `cv2.VideoWriter` **không tự tạo thư mục** | `cam_ai_core.py`: thêm `tao_thu_muc_cha()`, gọi trước khi mở writer và trước khi ghi CSV; lỗi giờ **nêu rõ thư mục cha** | CWD = `C:\Windows` + thư mục output chưa có → **EXIT=0**, thư mục được tạo, có cả `.mp4` + `.csv` |
| **BUG #3** | `--tu-luu-clip` **cùng thư mục** với video kết quả → log `[clip] da don 1 file .part.mp4 con sot lai` + `[video] ⚠ không ghi được video kết quả`, **exit 0 nhưng MẤT video kết quả** | `don_file_tam_trong_thu_muc()` xoá **mọi** `*.part.mp4` trong thư mục, kể cả file tạm của video kết quả đang được writer giữ | Thêm tham số `giu=(out_path_tam,)` + **lớp bảo vệ thứ hai** registry `_FILE_DANG_GHI` (mọi `VideoWriter` đang ghi đều được bảo vệ) | Chạy lại B3: `[clip] da don 1 file .part.mp4 con sot lai` (file rác **bị xoá**) **và** `ket_qua_ket_qua.mp4` **16.253.729 B vẫn còn**, `ffprobe` → `h264,960,540` |

#### E) 1 lỗi hiển thị — ĐÃ sửa ở bản 3.2

| Vấn đề | Chi tiết | Trạng thái |
|---|---|---|
| **Khung "Xem video" (panel lớn nhất) đen khi chạy phân tích theo lô** | `run_analysis()` chỉ có `progress_cb` + `log`, **không có callback khung hình**; GUI chỉ đẩy `("frame", ...)` ở chế độ **xem trực tiếp** (`gui.py:3631`). Nên bấm "Chạy" trên 1 file → panel lớn nhất **đen suốt**, dù mọi thứ khác chạy đúng. Ngoài ra nút **"Tạm dừng"** (thuộc chế độ trực tiếp) vẫn hiện ở chế độ lô → bấm không có tác dụng | **ĐÃ SỬA** ở bản 3.2 → xem mục 2.1f |

---

### 2.1f BẢN 3.2 — SỬA PANEL "XEM VIDEO" ĐEN KHI CHẠY LÔ (2026-10-20)

**Phát hiện:** 2026-10-20 khi rà bản PC (mục 2.1e mục E). **Sửa xong trong ngày** —
`VERSION` 3.1 → **3.2**.

**Cách sửa (1 lỗi, 4 điểm):**

| # | File | Thay đổi |
|---|---|---|
| 1 | `cam_ai_core.py` | `run_analysis()` nhận thêm `frame_cb: Callable[[bytes], None] \| None = None` + `frame_cb_interval: float = 0.0`. Ngay sau `writer.write(frame)` → encode JPEG (`JPEG_CHAT_LUONG = 80`) rồi gọi `frame_cb`. Khung gửi ra là **khung ĐÃ vẽ overlay** → hiển thị y hình pipeline. `frame_cb is None` → **không encode, chi phí = 0**. Callback ném lỗi → `try/except`, **không làm chết pipeline**, báo lỗi 1 lần |
| 2 | `gui.py` | Hộp thư **1 ô** (`_khung_hinh_moi` + `threading.Lock` + `_khung_hinh_seq`) thay cho `self.queue` — queue không giới hạn sẽ **phình bộ nhớ** (~100 KB/khung × hàng chục nghìn khung) |
| 3 | `gui.py` | Giới hạn **10 fps** (`KHOUNG_HINH_FPS = 10`) |
| 4 | `gui.py` | Nút **"Tạm dừng"** **ẩn** ở chế độ lô (`_cap_nhat_nut_tam_dung_xem()`) — nút này thuộc chế độ xem trực tiếp |

**Bằng chứng — coordinator tự chạy + TỰ XEM ẢNH BẰNG MẮT:**

| Bước | Kết quả |
|---|---|
| `_kk_kiem_gui_batch_preview.py` (GUI chế độ lô, `v_xem_video="0"`) | **PASS** — khung hình hiện lên panel **82 lần**; vùng panel đo được **118.735 màu đơn sắc**, sáng TB **73,95**, max 255 / min 0 → **KHÔNG đen** (trước: ~1 màu, sáng ~0) |
| Ảnh `_kk_out/pc_audit/V5_batch_preview/v5_dang_chay.png` — **coordinator tự mở xem** | Khung hình thật + khung tím `Người 1..4`, khung xanh mặt với nhãn **An** / **Binh**, badge `Người: 4 \| Mặt: 2 \| Vào: 0 \| Ra: 0`, nút "Tạm dừng" **không còn** trong panel |
| Vùng panel cắt riêng `v5_vung_khung_hinh.png` — **tự xem** | Ảnh thật, **không có vùng đen nào** |
| `_kk_kiem_gui_chay_thuc.py` (bộ e2e đầy đủ, thêm mục [7]) | **7/7 PASS** — video `h264,960,540`, CSV **251 dòng**, 250 frame đọc được, thời gian 23,6 s |
| Callback ném lỗi | Pipeline **vẫn chạy hết 250 khung**, không chết |
| Hồi quy CLI | `app.py` không bị ảnh hưởng (`frame_cb=None` → không encode) |

**Chi phí (đo thật, có warm-up + 2 vòng, lấy vòng 2):**

| Cấu hình | Thời gian | Khung/s | Callback gọi |
|---|---|---|---|
| Không `frame_cb` (CLI) | 27,01 s | 9,26 | 0 |
| `frame_cb` mỗi khung | 28,63 s | 8,73 | 250/250 |
| `frame_cb` giới hạn 10 fps (mức GUI dùng) | 29,27 s | 8,54 | 147/250 (~59%) |

> **Nhiễu đo ~3–4%** giữa hai lần chạy cùng cấu hình → hao tổn thực tế của việc xem
> trong lúc chạy nằm trong khoảng **3–8%**. Con số chắc chắn là chi phí encode đo
> riêng: **2,80 ms/khung** (JPEG q=80) → 250 khung = **0,7 s**.

**Bài học:** lần đo đầu của coordinator báo *"callback 0 lần"* là do **lỗi của script
đo** (truyền `lambda j: None` thay vì hàm đếm) — **không phải lỗi app**. Đã sửa
script và đo lại. Bài học chung: **đo bằng công cụ thôi chưa đủ, phải tự mở ảnh xem
bằng mắt** mới tin được "panel không còn đen".

**Còn lại ở bản 3.2 (không tự sửa, cần anh):**

| Vấn đề | Vì sao chưa tự quyết |
|---|---|
| Nhãn ô **"Xem video khi chạy"** giờ mô tả **2** chế độ: TẮT = xem khung hình kết quả (có overlay), BẬT = xem trực tiếp (có nút Tạm dừng) | Đổi nhãn là **copy user-facing** → theo quy tắc đã chốt, **phải hỏi anh** mới đổi. **ĐÃ HỎI 2026-10-20 → anh chọn tách 2 ô, xem mục 2.1g** |
| **Mục 7** (kéo cửa sổ) & **mục 8** (độ nhận diện) | Phải do **anh** xác nhận, em không tự đánh dấu đạt |

---

### 2.1g BẢN 3.3 — ĐẨY 3 TÍNH NĂNG "DÙNG TAY" VÀO GUI + SỬA 1 LỖI THẬT (2026-10-20)

**Anh chốt (2026-10-20):**
1. Nhãn: đổi **"Xem video khi chạy"** → **"Xem trực tiếp"** + thêm ô mới
   **"Xem khung hình kết quả"** (tách 2 nghĩa cũ).
2. Hướng sản phẩm: **(A) Bộ công cụ AI dùng tay** — đẩy những thứ đã có sẵn ở CLI
   vào GUI: OCR biển số, đăng ký người quen, vẽ vùng.

**Cách làm (2 agent, file không chồng lấn):**

| Agent | File sở hữu | Nội dung |
|---|---|---|
| A | `gui.py` | 2 ô xem video + nút "Đăng ký người quen…" + nút "Đọc biển số thử…" + nối nút "Vẽ vùng ngay tại đây" |
| B | `ve_vung_gui.py` (file MỚI) | Module canvas: kéo chuột trong chính cửa sổ → tọa độ tương đối 0..1 |

**4 thay đổi trong `gui.py`:**

| # | Thay đổi | Ghi chú |
|---|---|---|
| 1 | `chk_xem_video` → nhãn **"Xem trực tiếp"**; thêm `v_xem_ket_qua` (mặc định "1") + `chk_xem_ket_qua` → **"Xem khung hình kết quả"** | Bật CẢ 2 → log giải thích "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' tạm không dùng (tránh 2 nguồn hình đè nhau)"; `frame_cb` chỉ bật khi TẮT "Xem trực tiếp" |
| 2 | Nút **"Đăng ký người quen…"** (nhóm Mặt) | Chọn ảnh/video → nhập tên → `collect_faces` + `cluster` + `save_group` (dùng lại `dang_ky_anh.py`) → lưu `known_faces/<Tên>/`. Hỏi xác nhận trước khi ghi đè thư mục đã có (`save_group` xoá thư mục cũ). Chạy ở thread nền, chỉ khoá nút (không khoá cả app) |
| 3 | Nút **"Đọc biển số thử…"** (nhóm biển số) | Đọc **1 ảnh**: `tim_vung()` + `doc_vung()` — **KHÔNG dùng `doc()`** vì `doc()` cần ≥2 khung hình xác nhận nên 1 ảnh sẽ không ra kết quả. Ghi rõ trong UI là chế độ thử 1 ảnh, chưa qua xác nhận đa khung hình |
| 4 | Nút **"Vẽ vùng ngay tại đây"** (nhóm vùng) | Lấy 1 frame giữa video ở thread nền → gọi `ve_vung_gui.ve_vung_trong_gui()` (modal, UI thread) → `ve_vung.save_zone()` ghi file vùng → điền vào ô "File vùng". Import lazy + try/except: thiếu module thì chỉ ghi nhật ký, **không làm chết app**. Nút cũ "Vẽ vùng trên video này" (mở cửa sổ CLI) **giữ nguyên** |

**Module mới `ve_vung_gui.py`:** hộp thoại `CTkToplevel` — ảnh nền co vừa khung, **kéo chuột
trái** để khoanh (hình chữ nhật xanh realtime), nút **Lưu vùng / Chọn lại / Bỏ**, dòng tọa
độ tương đối 4 số hiện realtime, `Esc` = hủy, `grab_set()` + `wait_window()` (modal).
Chuyển pixel→tương đối theo kích thước **ảnh gốc** (không phải ảnh đã co).

**BUG THẬT phát hiện khi coordinator tự chạy (đã sửa):**

| Mục | Nội dung |
|---|---|
| Triệu chứng | Sau khi đăng ký người quen xong, nhật ký hiện `[LỖI] Lỗi khi đăng ký người quen: main thread is not in main loop` và **không** có dòng `> Đã học được: ...` |
| Nguyên nhân | `_chay_dang_ky_nguoi_quen` chạy ở **thread nền** nhưng gọi `_nap_lai_danh_sach_nguoi_quen()` → hàm đó đọc `self.v_faces_dir` (một `tkinter.StringVar`) → **gọi Tk từ thread không phải thread chính** → Tcl ném `RuntimeError` |
| Cách sửa | Thread nền **không** gọi hàm đó nữa mà đẩy `("nap_lai_danh_sach", (faces_dir, threshold))` vào hàng đợi; `_hut_hang_doi()` (UI thread) nhận rồi mới gọi. Giá trị `faces_dir`/`threshold` đọc sẵn ở UI thread nên không đọc biến Tk ở thread nền |
| Kiểm chứng độ nhạy | Cố tình vô hiệu hóa fix → lỗi **tái hiện đúng** → bật lại fix → PASS. Rà toàn bộ code v3.3: không còn chỗ nào khác gọi Tk từ thread nền |

**BẰNG CHỨNG — coordinator tự chạy (không tin báo cáo agent):**

| Bước | Kết quả |
|---|---|
| `_kk_kiem_canvas_vung.py` (script **của coordinator**, không dùng script agent) | **PASS** — kéo chuột giả lập (120,90)→(330,210) trên canvas 640×480 → hàm trả `(0.1875, 0.1875, 0.515625, 0.4375)`, **sai số 0.0000** so với tọa độ mong đợi |
| Ảnh `_kk_out/kiem_canvas/canvas_vung.png` — **coordinator tự mở xem** | Thấy hộp thoại "Vẽ vùng canh — kéo chuột rồi bấm Lưu", **hình chữ nhật xanh** đúng chỗ kéo, dòng `0.1875 0.1875 0.5156 0.4375`, 3 nút Lưu vùng / Chọn lại / Bỏ, chữ tiếng Việt **có dấu** không bị cắt |
| `_kk_kiem_gui_b3.py` (script **của coordinator**, 4 mục) | **4/4 PASS** — (1) 2 ô xem video đúng nhãn + đúng mặc định; (2) đăng ký người quen: tạo thật `known_faces_test/KiemThuV33/01.jpg`, log `> Số ảnh đã lưu: 1`; (3) đọc biển số thử: log `Biển số: 30A-12345 \| tin cậy 0.67 \| số hàng: 2`, ảnh crop đã lưu; (4) vẽ vùng: file `vung_test.txt` có đúng `0.2000 0.1500 0.8000 0.9500` |
| Chạy lại sau khi sửa lỗi Tk | **4/4 PASS** và **KHÔNG còn** dòng `main thread is not in main loop`; có lại dòng `> Đã học được: KiemThuV33` |
| Ảnh `_kk_out/kiem_gui_b3/b3_full.png` — **coordinator tự mở xem** | Thấy 3 checkbox dưới khung video: **"Xem trực tiếp"**, **"Xem khung hình kết quả"**, **"Nhận diện tên trên ảnh"** — đều hiện đủ chữ, không chồm nhau; dòng ghi chú nằm hàng riêng bên dưới |
| Hồi quy `_kk_kiem_gui_batch_preview.py` (tính năng bản 3.2) | **PASS** — khung hình hiện panel **79 lần**, vùng panel **107.129 màu / sáng TB 68,57 / max 255 min 0** → không đen |
| Hồi quy `_kk_kiem_gui_chay_thuc.py` (e2e 7 mục) | **7/7 PASS** — thời gian chạy 28,3 s |

**Còn lại ở bản 3.3 (chưa làm, cần anh quyết):**

| Vấn đề | Vì sao chưa tự quyết |
|---|---|
| **Nhiều vùng** (nhiều vùng cảnh trong 1 file) | Anh chốt hướng A nhưng **"nhiều vùng"** chưa nằm trong yêu cầu cụ thể; bản 3.3 làm **1 vùng** như bản CLI cũ |
| **Đăng ký người quen hàng loạt** (nhiều người cùng lúc) | `cluster(max_people=1)` → hiện **1 người / 1 lần**. Muốn nhiều người trong 1 video thì cần tách nhóm nhiều người + giao tên cho từng nhóm |
| **Mục 7** (kéo cửa sổ) & **mục 8** (độ nhận diện) | Phải do **anh** xác nhận, em không tự đánh dấu đạt. **Mục 7: bản 3.5 đã sửa theo số đo (lần kéo đầu 984 ms → 19,4 ms) — xin anh mở app (double-click `Mo CamAI.vbs`) và thử kéo xem còn giật không** |
| **OCR biển số trên ảnh THẬT** | Vẫn **chưa có ảnh thật** của anh. Bản 3.3 chỉ làm **đường đi ngắn** để anh gửi ảnh → bấm 1 nút → có kết quả ngay |

---

### 2.1h BẢN 3.4 — THIẾT KẾ LẠI TOÀN BỘ GIAO DIỆN + ICON APP DO AI VẼ (2026-10-20)

**Anh yêu cầu:** *"cái lõi app của chúng ta là đẹp hay sao ấy nhỉ mà cái app này nhìn cứ
phèn phèn sao ấy nhỉ, bạn cho 1 bạn nào dùng skill ui-ux-pro-max thiết kế lại cái app cho
tôi đi, cả cái icon của app nữa dùng trình tạo ảnh ai"*.

| Việc | Kết quả |
|---|---|
| Nguồn thiết kế | Skill **`ui-ux-pro-max`** đã cài sẵn ở `H:\AI Project\.agents\skills\ui-ux-pro-max\`. Chạy `--design-system` + domain `color`/`typography`/`ux` → sinh **`design-system/camai/MASTER.md`** làm **nguồn sự thật** cho giao diện |
| Icon app | **`Nano Banana Pro`** (Gemini 3 Pro Image) qua connector `matrix/generate_image` — **4 biến thể**, chọn bản "đầu người + ống kính + khung nhận dạng" → `assets/camai.png` 512px + `assets/camai.ico` (16/24/32/48/64/128/256) |

**3 quyết định em tự chỉnh so với output gốc của skill** (ghi rõ lý do trong MASTER.md mục 0):
1. Skill trả pattern **"Enterprise Gateway"** (landing page + CTA "Contact Sales") → **bỏ**,
   giữ style Data-Dense Dashboard. CamAI là công cụ desktop local, không bán hàng.
2. Query "desktop … dark mode" trả **Cyberpunk UI** (đen + xanh neon + glitch) → **bỏ**.
   Neon trông như tool hacker, tương phản kém, không hợp người dùng không rành kỹ thuật.
3. Skill gợi ý **Fira Sans / Fira Code / Inter** (Google Fonts) → dùng **font có sẵn trên
   Windows** (`Segoe UI`, `Segoe UI Semibold`, `Segoe UI Black`, `Cascadia Mono`) vì app chạy
   **100% offline**.

**Đã thay đổi trong giao diện:**

| Hạng mục | Chi tiết |
|---|---|
| Thanh đầu mới | Icon app + "CamAI v3.3" + nút ngôn ngữ + nút DỪNG / BẮT ĐẦU |
| Icon app | AI vẽ, hiện ở thanh đầu **và** trên thanh tiêu đề cửa sổ Windows |
| Bỏ emoji làm icon | `▶ ● ✔ ✖ ■` → **Segoe MDL2 Assets** (font biểu tượng có sẵn của Windows) |
| Typography | Segoe UI family + Cascadia Mono cho số/mã; **không còn chữ < 12px** |
| Màu | Tách hết sang file mới **`giao_dien.py`**; bổ sung **màu cảnh báo `#F59E0B`** |
| Component | Bo góc thống nhất, nút 36px, ô nhập 32px, viền 1px, 6 ô số liệu có màu theo trạng thái, mỗi checkbox có ghi chú riêng |
| Khoảng cách | Lưới 4/8/12/16/24/32; bỏ viền/đường kẻ thừa |

**BUG THẬT — coordinator phát hiện khi tự mở ảnh (không phải agent báo):**

| # | Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | Ô checkbox đã tick = **ô xanh đặc, mất dấu ✓** | CustomTkinter 5.2.2: ô tô bằng `fg_color`, **dấu ✓ vẽ bằng `checkmark_color`** — đặt cả hai cùng xanh | `checkmark_color = MAU["nen"]` (tương phản ≈ 7,7:1) |
| 2 | Nút **DỪNG** trông như **ô vuông rỗng (tofu)** | Dùng icon Stop (U+E71A) = hình vuông đặc, đọc nhầm là thiếu glyph | Đổi sang **Pause (U+E769)** = hai thanh dọc |

**BẰNG CHỨNG — coordinator tự chạy 6 bộ kiểm chứng trên code cuối (sau khi sửa 2 lỗi):**

| Bộ kiểm chứng | Kết quả |
|---|---|
| `_kk_kiem_gui_chay_thuc.py` (e2e 7 mục) | **7/7 PASS** — `tieu de='CamAI v3.4 — Phân tích video giám sát'`, `VERSION=3.4`, cửa sổ 1610×980; video `h264,960,540,25/1,250 frame`; CSV **251 dòng × 10 cột**; vùng panel **89.095 màu / sáng TB 62,21** → không đen; 36,3 s |
| `_kk_kiem_gui_b3.py` (4 tính năng bản 3.3) | **4/4 PASS** — 2 ô xem video / đăng ký người quen / đọc biển số thử / vẽ vùng |
| `_kk_kiem_gui_batch_preview.py` | **PASS** — khung hình hiện panel **84 lần**, vùng **90.477 màu** → không đen |
| `_kk_kiem_ngon_ngu_v3_3.py` | **5/5 PASS** — 5 chuỗi mới có bản dịch Anh + tiêu đề `CamAI v3.4 — Video surveillance analysis`; quay lại tiếng Việt vẫn đủ dấu |
| `_kk_kiem_giao_dien.py` (**mới**, kiểm tra thẩm mỹ) | **7/7 PASS** — không còn emoji làm icon; font dùng: `Segoe UI` 182, `Segoe UI Semibold` 34, `Segoe MDL2 Assets` 13, `Cascadia Mono` 1, `TkDefaultFont` 2 → **tất cả có thật trên máy**; **chữ nhỏ nhất 12px**; icon app có + app giữ icon; tương phản chữ **≥ 4,5:1** cho mọi cặp nền/chữ; khung video **75,5%** bề ngang (video 947px / cột sự kiện 307px) → **không xấu hơn bản 3.3**; **0 chữ bị cắt** (đã mở hết 12 nhóm rồi đo) |
| `_kk_kiem_canvas_vung.py` | **PASS** — sai số **0.0000** |
| Encoding mọi file đã sửa | **BOM=False, CR=0** |

**Ảnh — coordinator tự mở xem:**
- `_kk_out/kiem_giao_dien/gd_full.png` → thấy **thanh đầu** (icon app AI + "CamAI v3.4" + English + ‖ DỪNG + ▷ BẮT ĐẦU), icon cũng có ở **thanh tiêu đề cửa sổ Windows**, 3 ô xem video có **dấu ✓ nhìn rõ**, mỗi ô có ghi chú riêng, 6 ô số liệu, 13 thẻ video mẫu, cột sự kiện bên phải.
- `_kk_out/agent_g1/v3_cot_trai.png` → đường dẫn video hiện **trọn vẹn**, không cắt.

**BÀI HỌC (đã ghi vào mục 6):**
- `fg_color` của CustomTkinter **không phải "màu chung"** mà là **màu riêng cho từng lớp vẽ**
  → đặt 2 tham số cùng giá trị là mất 1 lớp.
- Kiểm tra icon/checkbox phải **chụp ảnh phóng to 3×**, không tin nhìn bằng mắt ở kích thước nhỏ.
- Chọn glyph **khác hình dạng rõ rệt** giữa các trạng thái (play / dừng / xong).

---

### 2.1i BẢN 3.5 — SỬA GIẬT KÉO CỬA SỔ + LAUNCHER 1-CLICK (2026-10-20)

**Anh báo (2026-10-20, ~07:20):** *"với cả cái app tôi dùng kéo cửa số nó vẫn bị giật lắm, bạn
kiểm tra lại cho tôi nhá, bạn làm mà chả bao giờ chỉ tôi cách mở app gì cả, tôi chỉ dùng được
lúc các bạn test thôi"*.

→ Đây là **lần đầu mục 7 có xác nhận của người dùng** (trước đó chỉ có số đo của coordinator —
và đó là thiếu sót: em đã ghi "CHƯA ĐẠT — chờ anh xác nhận" nhưng cũng **chưa chỉ anh cách
mở app**, nên anh không thể tự dùng để kiểm tra).

### 1. Launcher 1-click (đóng lỗ "chả bao giờ chỉ tôi cách mở app")

| File | Dùng khi nào |
|---|---|
| `Mo CamAI.vbs` | **Cách chính** — double-click, app mở, **không** hiện cửa sổ đen |
| `Mo CamAI.bat` | Khi app không mở — có cửa sổ đen **in lỗi** để chụp màn hình gửi mình |
| `HUONG-DAN-MO-APP.md` | Hướng dẫn đầy đủ cho người không rành kỹ thuật (kèm cách xử lý khi Windows cảnh báo / file bị chặn, cách đưa shortcut lên desktop) |

**Đã kiểm chứng thật:** chạy `Mo CamAI.vbs` → tiến trình `pythonw.exe ... gui.py` **xuất hiện** →
đóng lại sạch, không để lại tiến trình rác.

### 2. Sửa giật kéo cửa sổ — đo, không đoán

**Quy trình:** coordinator đo 4 phép độc lập, **loại trừ 3 giả thuyết sai** trước khi kết luận:

| Giả thuyết | Bằng chứng loại trừ |
|---|---|
| "Do tooltip tạo/huỷ cửa sổ native" | Trong lúc kéo, con trỏ **không nằm trên app** → `Enter=0`, `Leave=0`, tooltip tạo **0** cửa sổ |
| "Do vẽ lại nhiều" | Đo riêng thời gian vẽ lại toàn bộ cửa sổ = **0,5 ms** |
| "Do app chạy nền" | **CPU idle = 0 ms** trong 3 s |

**Cái thật sự (đo được):**

| Bằng chứng | Số đo |
|---|---|
| Chỉ lần kéo **ĐẦU TIÊN** bị | lần 1: **859 ms** → lần 2: 20,2 ms → lần 3: 20,9 ms |
| Cửa sổ **rỗng** không bị | Tk rỗng 21,3 ms · CTk rỗng 18,4 ms · **CamAI đầy đủ 984 ms** |
| **Bỏ hết scrollbar** | còn **144 ms** → scrollbar chiếm ~85% |
| Stack lúc đang tre | `CTkScrollbar._draw` (ctk_scrollbar.py:161 → `self._canvas.update_idletasks()`) → `<Configure>` → `set()` → `_draw()` → … |

**Nguyên nhân gốc:** `CTkScrollbar._draw()` kết thúc bằng `self._canvas.update_idletasks()`.
**`update_idletasks()` là lệnh Tk gốc → nó xả HẾT hàng đợi idle của TOÀN BỘ app** (chứ không
chỉ thanh cuộn) → kéo cửa sổ lần đầu ⇒ vẽ lại **851 widget** ⇒ tre 600–900 ms.

**Cách sửa:**
1. `_patch_scrollbar_khong_ep_ve_lai_ca_app()` (`gui.py:272`, gọi ở `gui.py:1681`): bỏ lệnh
   `update_idletasks()` khỏi `_draw()` của thanh cuộn. Thanh cuộn vẫn được vẽ lại ở vòng idle
   kế tiếp của Tk, nhưng **không còn ép vẽ lại cả app**.
2. **Khởi động ấm**: vẽ sẵn cây widget trước khi người dùng kéo lần đầu.
3. **Tooltip**: tái sử dụng **1 cửa sổ duy nhất** (không tạo/huỷ liên tục), **trì hoãn 450 ms**
   (chuẩn Windows), đóng cửa sổ tooltip khi app đóng.

**KẾT QUẢ (coordinator tự đo lại trên code cuối):**

| Số đo | Trước | Sau |
|---|---|---|
| **Lần kéo đầu tiên — `max`** | **859 – 984 ms** | **19,4 ms** |
| Lần kéo đầu — số lần tre > 30 ms | 3 – 9 | **0** |
| Lần kéo đầu — `tb` / `p90` | — | 14,9 / 17,5 ms |
| Thời gian mở app (tới khi cửa sổ sẵn sàng) | 13,3 s | **12,5 s** (không chậm hơn) |

**BẰNG CHỨNG — 5 bộ kiểm chứng của coordinator chạy trên code cuối:**

| Bộ | Kết quả |
|---|---|
| `_kk_kiem_gui_chay_thuc.py` (e2e 7 mục) | **7/7 PASS** — 29,9 s |
| `_kk_kiem_gui_b3.py` (4 tính năng bản 3.3) | **4/4 PASS** |
| `_kk_kiem_gui_batch_preview.py` | **PASS** — khung hiện panel **103 lần**, 74.061 màu → không đen |
| `_kk_kiem_ngon_ngu_v3_3.py` | **5/5 PASS** (tiêu đề `CamAI v3.4` — bump 3.5 sau) |
| `_kk_kiem_giao_dien.py` | **7/7 PASS** — 0 emoji, font ≥ 12px, icon app, tương phản ≥ 4,5:1, video 75,5%, 0 chữ bị cắt |
| Encoding mọi file đã sửa | **BOM=False, CR=0** |

**Bài học (đã ghi vào mục 6):**
- **Phép đo A/B phải đo lần kéo ĐẦU và các lần sau, không được so sánh 2 lần đo liên tiếp** —
  lần đo đầu luôn dính "phí khởi tạo hiển thị" → em đã ra kết luận sai một lần.
- Trong Tkinter, `update_idletasks()` **không** chỉ vẽ widget vừa thay đổi — nó **xả hết hàng
  đợi idle của cả ứng dụng**. Gọi nó trong handler sự kiện của 1 widget nhỏ (thanh cuộn)
  có thể kéo theo việc vẽ lại **toàn bộ** cây widget.
- Với người dùng không rành kỹ thuật, **phải có launcher 1-click + hướng dẫn**; app mà không
  có đường vào rõ ràng thì mọi số đo của kỹ sư đều vô nghĩa với họ.

---

### 2.2 CHƯA ĐẠT — chờ anh

| Hạng mục | Vì sao chưa đạt | Việc cần làm |
|---|---|---|
| **7. Cảm giác kéo cửa sổ** | Chỉ có số đo, **anh chưa xác nhận**. Em đã sai một lần vì coi số đo là bằng chứng xong | **Anh mở GUI, kéo cửa sổ, xác nhận còn giật hay không.** Nếu còn giật: em sẽ báo cáo tiếp kèm số đo mới |
| **8. Độ nhận diện trên video** | Video demo là video tải về, không phải video thật của anh; `known_faces/An`, `known_faces/Binh` là **dữ liệu giả**. **Đã đo thật (mục 2.3) và phát hiện hạn chế lớn:** quay drone `nguoi-di-lai` nhận 0/12 khung dù có hàng trăm người; `dam-dong` nhận 2–6 người dù cảnh rất đông | **Anh gửi video thật** (và ảnh người quen nếu muốn nhận diện tên), hoặc tự xem và nhận xét. Nếu anh cần nhận tốt ở cự ly xa/đám đông, xem 3 phương án sửa trong mục 2.3 |
| **Đọc biển số xe Việt Nam** (bản 3.0) | **Chưa có ảnh biển số VN thật.** 10 ảnh kiểm chứng là **ảnh giả do PIL dựng**, không đại diện ánh sáng / nhiễu / góc nghiêng / độ nét thật. Logic thì 10/10 PASS nhưng **chưa nghiệm thu được**. **Bản 3.3 đã làm đường đi ngắn**: nút "Đọc biển số thử…" trong GUI → anh gửi ảnh → bấm 1 nút → có kết quả trong vài giây, không cần chạy video | **Anh gửi ảnh biển 2 hàng kiểu `30A`/`12345`** (và biển 1 hàng nếu có) → bấm nút "Đọc biển số thử…" rồi chụp màn hình gửi lại. Chi tiết ở mục 2.1c và 2.1g |
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
| **KHÔNG dùng** `placeholder_text` của customtkinter khi ô có `textvariable` | `customtkinter 5.2.2` chỉ kích hoạt placeholder khi `textvariable` là `None` hoặc `""`; `tkinter.StringVar` **không định nghĩa `__eq__`** → mọi `CTkEntry` có `textvariable` **không bao giờ** hiện placeholder. Cũng **không** chèn chu placeholder bằng `insert` (làm nhiễu biến thành `"HUONG DAN GIUONGab"`) |
| Ô gợi ý = **nhãn `CTkLabel` phủ lên ô** (lớp `GoiYTronO`) | Gợi ý phải **ngắn** ("tự tìm" 31px, "mặc định" 49px) vì ô chỉ rộng 102px; giải thích đầy đủ nằm ở ghi chú dưới + tooltip |
| Nhãn gợi ý lấy màu từ **bảng màu dự án** `MAU["the_phu"]` | `entry.cget("fg_color")` lúc tạo nhãn trả bảng màu theme **cũ** `['#F9F9FA','#343638']` vì `_ap_dung_theme()` chạy **sau** khi dựng form → nền lệch `#343638` vs `#272F42` |
| `customtkinter 5.2.2` **không nhận** `width`/`height` trong `place()` | Raise `ValueError` → phải đưa vào constructor. Nhãn dùng `height=24` (ô cao 28) + `place(x=12, y=2, anchor="nw")` để **không đè viền 1px** của ô |
| Nhãn gợi ý là **con của chính ô nhập** | `anchor="w"` canh giữa trục y tại y=0 → lệch -14px, cắt chữ. `anchor="nw"` mới đúng |
| Tìm vùng biển phải chạy ở **luồng nền daemon** | Pha tìm vùng làm khựng pipeline **680–1916 ms/khung**; đưa sang luồng nền + cache vùng tương đối + hạn chi phí 50 ms → **5,2–7,5 ms/khung** |
| Mỗi engine OCR phải có `threading.Lock` riêng | RapidOCR không thread-safe; engine chỉ-đọc và engine có-tìm-chữ chạy song song |
| Mọi tính năng mới của 3.0 **mặc định TẮT** | CSV giữ nguyên **251 dòng × 10 cột** khi tắt; bật thì thêm **2 cột ở CUỐI** |
| `chuan_hoa_bien_so` **tuyệt đối không bịa ký tự** | Chỉ sửa `O/I/L` tại vị trí bắt buộc, tối đa 1 ký tự, không khớp mẫu → `""`. Thiếu biển còn hơn báo sai |
| Xác nhận đa khung hình **+** cơ chế `mau_thuan` | Chỉ chuỗi xuất hiện ở **≥2 khung liên tiếp** mới coi là chắc; ảnh nghiêng ≥8° mà 2 khung lệch nhau → chặn, ghi `"<mau_thuan>"` |

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
9b. **Tkinter: mọi lời gọi widget / `StringVar` phải ở UI thread.** Đọc `self.v_*` (một
   `tkinter.StringVar`) từ thread nền → `RuntimeError: main thread is not in main loop`
   (bản 3.3 đã dính: xem `ISSUE_LOG.md`). Việc nặng → thread nền → **chỉ** giao tiếp qua
   hàng đợi; giá trị cần đọc từ Tk thì **đọc ở UI thread rồi truyền vào**.
   `self.dich()` thì an toàn vì `self.ngon_ngu` là thuộc tính Python thuần.
9c. **CustomTkinter: `fg_color` KHÔNG phải "màu chung"** — nó là màu **riêng cho từng lớp
   vẽ**. Với `CTkCheckBox`: ô được tô bằng `fg_color`, **dấu ✓ vẽ bằng `checkmark_color`**.
   Đặt hai tham số cùng giá trị → dấu ✓ **biến mất hoàn toàn** (bản 3.4 đã dính).
9d. **Tkinter `widget.grid()` luôn đưa widget vào `widget.master`** (đối số lúc *tạo*), KHÔNG
   phải khung cha hiển thị. Tạo widget ở khung A rồi `grid()` vào khung B → nó **chồng lên
   khung A**, không nằm ở khung B. Phải tạo widget trực tiếp trong khung cha muốn đặt.
9e. **Font mặc định của CustomTkinter là "Roboto" — KHÔNG có trên Windows.** Mọi widget không
   khai báo font sẽ rơi về font mặc định của hệ điều hành. Phải ép lại về font có sẵn.
9f. **Kiểm tra icon/checkbox phải chụp ảnh phóng to 3×.** Ở kích thước thật, dấu ✓ màu
   tối trên ô xanh và icon hình vuông đặc đều trông như lỗi/tofu. Không tin nhìn bằng mắt
   ở kích thước nhỏ.
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
19. **`placeholder_text` của customtkinter KHÔNG hoạt động khi ô có `textvariable`.**
    Ở `customtkinter 5.2.2`, `CTkEntry._activate_placeholder()` chỉ chạy khi
    `textvariable is None or textvariable == ""`; `tkinter.StringVar` **không định
    nghĩa `__eq__`** → so sánh luôn False → placeholder **không bao giờ hiện**.
    Cách sửa đã chọn: lớp `GoiYTronO` (nhãn `CTkLabel` phủ lên ô) trong `gui.py`.
    Cũng **không** chèn chu placeholder bằng `insert` — nó làm nhiễu biến thành
    `"HUONG DAN GIUONGab"`.
20. **`entry.cget("fg_color")` lúc khởi tạo trả bảng màu theme CŨ.** Bước
    `_ap_dung_theme()` (gui.py ~dòng 1944) gán `fg_color=MAU["the_phu"]` cho mọi
    `CTkEntry` **sau khi** form đã dựng → đọc màu lúc tạo nhãn ra
    `['#F9F9FA','#343638']` trong khi ô thật là `#272F42` → nền lệch, thấy rõ bằng
    mắt. Phải lấy màu từ **bảng màu dự án** `MAU["the_phu"]`.
21. **`customtkinter 5.2.2` KHÔNG cho truyền `width`/`height` vào `place()`.** Raise
    `ValueError` → phải đưa vào constructor. Nhãn gợi ý dùng `height=24` (ô cao 28)
    + `place(x=12, y=2, anchor="nw")` để **không đè viền 1px** của ô.
22. **RapidOCR không thread-safe.** Khi chạy engine chỉ-đọc và engine có-tìm-chữ
    song song (tìm vùng ở luồng nền), phải có `threading.Lock` riêng cho từng
    engine — nếu không sẽ ra kết quả OCR sai lung tung, khó tái hiện.
23. **`mp4v` ≠ H.264. Trình duyệt KHÔNG phát được MPEG-4 Part 2.** fourcc `mp4v`
    (MPEG-4 Part 2 / MPEG-4 Visual) **không có decoder** trong Chrome/Edge/Firefox —
    báo cáo HTML mở ra thấy **"Unable to play media."**, controls `disabled: true`,
    scrubber **"total time: 0:00"**. Chỉ VLC/QuickTime phát được. File vẫn có dung
    lượng và `ffprobe` vẫn đọc được nên **rất dễ tưởng là xong**. Phải kiểm
    `codec_name` bằng `ffprobe` (H.264 = `h264`) và **mở thẻ `<video>` bằng trình
    duyệt thật**. OpenCV 5.0.0 in đỏ *"Failed to load OpenH264 library"* khi ghi
    `avc1` **nhưng file vẫn hợp lệ** → đừng kết luận theo stderr. Cách sửa đã dùng:
    `_fourcc_ket_qua()` probe 1 lần có cache (đọc `b"avc1"` trong box `stsd`), lùi về
    `mp4v` nếu máy không có encoder H.264.

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
- **Đọc biển số VN (bản 3.0) mới chỉ kiểm chứng bằng ảnh GIẢ** (PIL dựng). Chưa có
  ảnh thật của anh → chưa đánh giá được độ đúng ngoài đời.
- **Cache vùng biển bỏ sót biển mới ~2 s.** Vùng tìm được cache 10 s theo toạ độ
  tương đối; biển mới xuất hiện trong vùng cũ phải chờ lượt quét kế tiếp.
- **Hạn chi phí 50 ms có thể cắt trường hợp biển 2 hàng** (đo thật ~54 ms).
- **Vùng biển tìm được là khung CHỮ** → biển 2 hàng (`30A` trên, `12345` dưới) có
  thể ghép sai thứ tự. Chỉ chốt được khi có ảnh thật.
- **Chưa có video camera an ninh thực tế của anh** → chưa đo được thời gian quét cho
  use case máy chấm công (mục tiêu 2/8 tiếng).

---

## 8. Việc tiếp theo — thứ tự gợi ý

0. **Sửa lỗi panel "Xem video" đen khi chạy theo lô** (tìm ra 2026-10-20, xem mục
   2.1e mục E). Cần thêm callback khung hình cho `run_analysis()` + đẩy vào GUI,
   và ẩn nút "Tạm dừng" (nút của chế độ trực tiếp) khi đang chạy theo lô.
1. **Anh xác nhận mục 7:** mở GUI, kéo cửa sổ, xác nhận còn giật hay không.
   Nếu còn giật → em đo tiếp và báo kèm số liệu, không tự kết luận.
2. **Anh xác nhận mục 8:** gửi video thật + ảnh người quen (nếu muốn nhận diện
   tên), hoặc tự xem video demo và nhận xét độ đúng.
3. **Anh gửi ảnh biển số xe Việt Nam thật** (biển 2 hàng kiểu `30A`/`12345`; biển
   1 hàng nếu có) để nghiệm thu mục OCR biển số của bản 3.0.
4. **Anh trả lời câu hỏi use case máy chấm công:** camera đặt ở cửa hay trên xe?
   khoảng cách người đứng bao xa? cùng lúc mấy người? cần **nhận diện theo tên**
   hay chỉ **đếm lượt**? — quyết định mặc định `face_every` và có cần bật nhận diện
   mặt mặc định hay không.
5. Cân nhắc khôi phục lại lưới "Đối tượng phát hiện" bị bỏ, và cho chọn kênh cảnh báo
   (cần thêm cờ vào `cam_ai_core.py`).
6. Kiểm lại web local (HTTP 200 + 401).
7. Chờ anh: có làm webcam live không · có cần model khẩu trang không · xóa `known_faces` giả không.

---

## 9. Lịch sử thay đổi

| Ngày | Việc |
|---|---|
| 2026-10-20 (sau 09:50) | **Bản 3.5 — sửa giật kéo cửa sổ + launcher 1-click.** Anh báo thật: *"kéo cửa sổ bị giật lắm"* + *"chả bao giờ chỉ tôi cách mở app"*. **Chẩn đoán bằng số đo** (loại 3 giả thuyết sai: tooltip, vẽ lại, app chạy nền): giật **chỉ ở lần kéo ĐẦU TIÊN** (859–984 ms; lần 2 = 20 ms; cửa sổ rỗng không bị; bỏ scrollbar → còn 144 ms) → thủ phạm là `CTkScrollbar._draw()` gọi **`update_idletasks()`** = xả hết hàng đợi idle **của toàn bộ app** → vẽ lại 851 widget. **Đã sửa + khởi động ấm + tooltip dùng 1 cửa sổ duy nhất, trì hoãn 450 ms** → lần kéo đầu còn **19,4 ms, 0 lần tre**, mở app **không chậm hơn** (13,3 s → 12,5 s). Thêm **`Mo CamAI.vbs`** (launcher 1-click, đã test thật) + **`Mo CamAI.bat`** + **`HUONG-DAN-MO-APP.md`**. 5 bộ kiểm chứng của coordinator PASS hết (e2e 7/7, 3.3 4/4, preview, ngôn ngữ 5/5, thiết kế 7/7). Bump 3.4 → **3.5**. Xem mục **2.1i**. |
| 2026-10-20 (sau 06:45) | **Bản 3.4 — thiết kế lại toàn bộ giao diện + icon app do AI vẽ.** Anh: *"cái app này nhìn cứ phèn phèn"* → dùng skill **`ui-ux-pro-max`** sinh `design-system/camai/MASTER.md` làm nguồn sự thật; file mới **`giao_dien.py`** chứa hằng số thiết kế (màu + bổ sung **màu cảnh báo `#F59E0B`**, font, khoảng cách, bo góc, biểu tượng); **thanh đầu mới 64px** có icon app; **bỏ hết emoji làm icon** → font biểu tượng Windows `Segoe MDL2 Assets`; typography **Segoe UI + Cascadia Mono** (chỉ font có sẵn — app offline); component + lưới khoảng cách 4/8/12/16/24/32 thống nhất. **Icon app vẽ bằng Nano Banana Pro (Gemini 3 Pro Image)**: 4 biến thể → chọn "đầu người + ống kính + khung nhận dạng" → `assets/camai.png` 512 + `assets/camai.ico` 7 kích thước. Coordinator **tự mở ảnh** và phát hiện **2 lỗi thị giác thật**: (1) dấu ✓ trong ô checkbox **biến mất** vì CustomTkinter vẽ ô bằng `fg_color` còn tick bằng `checkmark_color` — đặt cùng màu; (2) icon nút DỪNG trông như **tofu** vì dùng Stop (hình vuông đặc) → đổi sang Pause (2 thanh). Bump 3.3 → **3.4**. Xem mục **2.1h**. |
| 2026-10-20 (sau 04:50) | **Bản 3.3 — đẩy 3 tính năng "dùng tay" vào GUI + sửa 1 lỗi thật.** Anh chốt: tách 2 ô xem video (**"Xem trực tiếp"** + **"Xem khung hình kết quả"**) và đi theo hướng **(A) bộ công cụ AI dùng tay**. Thêm trong `gui.py`: nút **"Đăng ký người quen…"** (lưu `known_faces/<Tên>/`, dùng lại `dang_ky_anh.py`), nút **"Đọc biển số thử…"** (đọc 1 ảnh bằng `tim_vung`+`doc_vung`, **không** dùng `doc()` vì cần ≥2 khung hình), nút **"Vẽ vùng ngay tại đây"**; thêm module mới **`ve_vung_gui.py`** (canvas kéo chuột trong chính cửa sổ → tọa độ tương đối 0..1). Coordinator tự chạy và **phát hiện lỗi thật**: đọc `StringVar` từ thread nền → `main thread is not in main loop` → **đã sửa** (đẩy qua hàng đợi, UI thread xử lý) + kiểm chứng độ nhạy (vô hiệu hóa fix → lỗi tái hiện → bật lại → PASS). Kiểm chứng của coordinator: canvas **sai số 0.0000**, GUI **4/4 PASS**, hồi quy batch **PASS** (79 lần hiện khung, 107.129 màu), e2e **7/7 PASS** (28,3 s). Bump 3.2 → **3.3**. Xem mục **2.1g**. |
| 2026-10-20 (sau 01:30) | **Bản 3.2 — sửa panel "Xem video" đen khi chạy phân tích theo lô.** `run_analysis()` nhận thêm `frame_cb` + `frame_cb_interval` (khung **đã có overlay**; `None` → chi phí 0; callback lỗi không làm chết pipeline). GUI nhận khung qua **hộp thư 1 ô** (tránh phình bộ nhớ), giới hạn **10 fps**, ẩn nút "Tạm dừng" ở chế độ lô. Kiểm chứng: **7/7 PASS**, vùng panel **118.735 màu / sáng TB 73,95** (trước là đen), coordinator **tự xem ảnh** thấy khung người + nhãn **An**/**Binh**. Chi phí đo thật: **3–8%** (nhiễu ~3–4%), encode **2,80 ms/khung**. Bump 3.1 → **3.2**. Xem mục **2.1f**. |
| 2026-10-20 (sau 00:40) | **Bản 3.1 — rà toàn bộ bản PC.** Coordinator tự chạy **32 cờ CLI** (26/26 EXIT=0) + **6 script OCR** (6/6 PASS) + **GUI end-to-end** (tự xem ảnh) → phát hiện và sửa **3 lỗi chết app**: (1) đường dẫn tương đối phân giải theo CWD → app chết khi chạy ngoài thư mục dự án (thêm file mới `duong_dan.py` làm nguồn sự thật); (2) app không tự tạo thư mục output; (3) `--tu-luu-clip` cùng thư mục với video kết quả → **xoá mất video kết quả nhưng exit 0** (thêm `giu=` + registry `_FILE_DANG_GHI`). Phát hiện thêm **1 lỗi hiển thị** (panel "Xem video" đen khi chạy lô) → **đã sửa ở bản 3.2**. Bump 3.0 → **3.1**. Xem mục **2.1e**. |
| 2026-10-19 (sau 22h) | **Sửa lỗi codec video.** Video kết quả/clip tự lưu dùng `mp4v` (MPEG-4 **Part 2**) → trình duyệt **không phát được** ("Unable to play media."). Chuyển sang **H.264 (`avc1`)** bằng probe 1 lần có cache, lùi về `mp4v` nếu máy không có encoder. Đo thật: `ffprobe` → **`codec_name=h264`**, `ffmpeg` decode sạch, mở HTML bằng **browser thật** → player load (`total time: 0:10`), **0 lỗi console**. Nâng "Video player trong HTML xem lại" từ MỨC 2 → **MỨC 1**. |
| 2026-10-19 (sau 20h) | **Bản 3.0.** Thêm **đọc biển số xe Việt Nam** (`bien_so.py`) + **tự chụp ảnh sự kiện** (`tu_chup.py`), mặc định TẮT; 8 cờ CLI; 2 nhóm GUI mới. Sửa 3 lỗi nghiêm trọng pipeline OCR (dùng nhầm engine, bịa biển số, crash `--help`). Chuyển pha tìm vùng biển sang **luồng nền** → pipeline **680–1916 ms/khung → 5,2–7,5 ms/khung**. Sửa lỗi **ô gợi ý trong ô nhập không hiện** (lớp `GoiYTronO`). Ghi chú tốc độ OCR trên GUI thay bằng **số đo thật** (9–15 ms/lần quét, max 62 ms). Bump 2.8 → **3.0**. Mục 7/8 và mục OCR biển số **chờ anh**. |
| 2026-10-19 (sau 09:00) | **Nghiệm thu 2.5 — 6/6 mục tự đo ĐẠT.** Sửa `PUMP_MS` 120→30 (live view **14.34 fps** 300s); sửa `_vuot_nhau` (0 cặp nhãn chồm ở khung 15 người); cột sự kiện co theo (bố cục **75.4%–83.2%**, 0 nhãn tràn). 6 video demo mới → 13 thẻ. Bump 2.5 → 2.6 → **2.7**. Mục 7/8 chờ anh. |
| 2026-10-19 (sau 18h) | Sửa lõi: nối `canh_bao.py`, clip `.part.mp4` an toàn, `--lop` báo lỗi rõ. Đổi bố cục GUI sang 3 vùng theo mẫu (video + timeline sự kiện + bảng thống kê vùng). Nối checkbox cảnh báo. Còn 4 lỗi hiển thị + live view. **Chưa bump VERSION (vẫn 2.4).** |
| 2026-10-19 (trước) | Dừng tunnel CamAI, xóa `config.yml` + credentials. Sửa cửa sổ GUI tràn taskbar. Bump 2.2 → 2.3. Tạo 4 file tài liệu bàn giao. Bump 2.3 → 2.4 + GUI chuyển sang visual. |
| 2026-10-18 | Hoàn thiện GUI (khung realtime, tạm dừng, ghi log hàng loạt) và web server (đăng nhập, khóa 5 phút, tải CSV/XLSX/HTML). Sửa hardcode mật khẩu → fail-closed. |
| trước đó | Lõi AI, CLI, nhận diện mặt, báo cáo Excel/HTML. |