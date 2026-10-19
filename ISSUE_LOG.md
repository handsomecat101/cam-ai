# Sổ lỗi CamAI

Ghi lại lỗi đã biết để không phát minh lại. Xem `PROJECT_STATE.md` mục 2 (bảng ĐẠT/CHƯA ĐẠT)
và mục 6 (gotcha) cho việc đang làm.

**Ngày cập nhật:** 2026-10-19

---

# ĐÃ SỬA

## `canh_bao.py` chưa được dùng

**Triệu chứng:** có nhóm "Cảnh báo" trên GUI nhưng không kêu chuông, không gửi tin.

**Nguyên nhân:** file tồn tại nhưng không ai gọi. `cam_ai_core.py` chưa import.

**Đã sửa (2026-10-19):** thêm class `CanhBaoNoi` trong `cam_ai_core.py` làm cầu nối, bắn
`LY_DO_VUOT_DONG` và `LY_DO_DUNG_LAU` trong vòng lặp khi `cfg.bat_canh_bao` bật.
Mặc định **TẮT** nên hành vi cũ không đổi.

Fail-safe: import lazy trong `try/except`; lỗi import hoặc lỗi gửi → in 1 dòng lỗi rồi tự
tắt cảnh báo, phân tích vẫn chạy tiếp. Không có mốc thời gian cứng nào chốt spam trong
code — chỉ dùng biến trạng thái `self.chot`.

**Bằng chứng chạy thật:**
```
$ app.py --input video_test.mp4 --vung vung.txt --vung-max 2 --canh-lau 3 --no-face --bat-canh-bao --canh-bao-mo-phong
[canh bao] 05:23:46 canh bao: dung_lau
--- CANH BAO ---
Su kien da canh bao: 1
```
Sự kiện kéo dài ~7 giây nhưng chỉ **1 dòng** → chốt 1-lần/sự kiện đúng.

**LƯU Ý AN TOÀN:** `CanhBao` mặc định **kêu chuông + mở hộp thoại** trên máy thật
(`canh_bao.py` ~dòng 174-190). Trên GUI, checkbox là `Cảnh báo (gửi tin ra ngoài)` và
mặc định **không tick**. Đừng tự bật cho người dùng.

---

## `--lop xyz` bị bỏ qua im lặng

**Triệu chứng:** truyền `--lop xyz` mà không bật `--nhan-vat-the` → không có hiệu ứng, không báo lỗi.

**Nguyên nhân:** `cam_ai_core.py` chỉ đọc `lop` khi `nhan_vat_the` bật.

**Đã sửa (2026-10-19):** `--lop` tự bật `--nhan-vat-the` kèm dòng thông báo; lớp sai thì
báo lỗi + gợi ý lớp gần đúng (khoảng cách ký tự) + liệt kê lớp có sẵn; trả **mã thoát ≠ 0**.

**Bằng chứng chạy thật:**
| Lệnh | Kết quả | Exit |
|---|---|---|
| `--lop motercycle` | `('motercycle' co phai la 'motorcycle'?)` + 80 lớp có sẵn | 1 |
| `--lop xyz` | `[loi] khong co lop vat the nay: xyz` | 1 |
| `--lop car` | `Đã bật tự động nhận diện vật thể vì có dùng --lop (car)` → `xe o to: 15 khung hinh, toi da 1` | 0 |

**Thay đổi hành vi:** trên GUI, nếu anh gõ lớp trong ô mà quên tick "nhận vật thể", trước đây
bị bỏ qua im lặng, **bây giờ sẽ tự bật và in dòng log**. Đây là chủ ý, và có log minh bạch.
Lỗi vẫn là `CamAIError` (không `sys.exit`), GUI bắt ở `gui.py` và hiện cho người dùng.

---

## Clip MP4 hỏng khi hard kill

**Triệu chứng:** `moov atom not found` khi mở file kết quả.

**Nguyên nhân:** đang ghi MP4 thì bị giết cứng. Moov atom nằm cuối file, chưa kịp ghi
thì file vô dụng.

**Đã sửa một phần (2026-10-19):**
1. Ghi ra **`.part.mp4`**, chỉ đổi tên thành `.mp4` sau khi đóng video an toàn. File hỏng
   không còn mang tên đúng.
2. Dọn file `.part.mp4` sót lại lúc khởi động.
3. Bắt `SIGTERM` + `SIGBREAK` để dừng mềm.

**Bằng chứng chạy thật:** sau khi chạy, `Get-ChildItem -Filter '*.part.mp4'` → không có.

**GIỚI HẠN THẬT — không có cách nào chặn `taskkill /F`.** Đây là giới hạn Windows, không
phải thiếu sót code. Ngoài ra:
- `taskkill /PID` **không** kèm `/F` bị **từ chối** với tiến trình console trên máy này
  (`This process can only be terminated forcefully`).
- `os.kill(pid, SIGTERM)` / `Stop-Process` trên Windows là `TerminateProcess` → handler
  `SIGTERM` không chạy được dù đã cài.
- **Đường dừng mềm thật sự hoạt động là `SIGBREAK`** (Ctrl+Break trong console, hoặc
  `CTRL_BREAK_EVENT` tới process group tạo bằng `CREATE_NEW_PROCESS_GROUP`).

**Còn lại:** file `.part.mp4` hỏng sau kill cứng vẫn nằm trên đĩa cho tới lần chạy kế tiếp.

---

## Lỗi chữ tiếng Việt khi in ra console

**Triệu chứng:** `UnicodeEncodeError: 'charmap' codec can't encode character`.

**Đã sửa:** thêm `_log_an_toan()` trong `cam_ai_core.py` — thử in bản có dấu, nếu console
lỗi thì tự in bản không dấu, chương trình vẫn chạy.

---

# ĐÃ SỬA ở `VERSION` 2.7 (2026-10-19)

## Nhãn người chồng lên nhau trên khung — đã sửa

**Triệu chứng:** trong ảnh `kk_29_dang_chay.png` và `kk_30_timeline.png`, nhãn `Người 4` và
`Bình · 34` nằm cùng trục Y, chồng đè lên nhau giữa video, đọc không được.

**Lịch sử:** agent lần 1 tuyên bố đã sửa và viết "không cái nào chồng nhau". Coordinator
mở ảnh và **xác nhận vẫn còn lỗi**. Không được tin báo cáo, phảy xem ảnh.

**Nguyên nhân thật (đo được):** `_vuot_nhau()` trong `gui_khung.py` dùng
`a[2] <= b[0] + le` — nghĩa là cho phép nhãn chồm thật tới `le - 1` px, trái với ý
nghĩa `LE_TRANH` là khoảng cách tối thiểu phải chừa.

**Đã sửa:** đổi thành `a[2] + le <= b[0]` (và tương ứng 3 phép còn lại).

**Bằng chứng đo lại** (`_kk_test_va_cham_nhan.py`, `kk_35_don_cuc_10_nguoi.png`):

| | Khung hình | Nhãn vẽ được | Cặp chồm |
|---|---|---|---|
| Trước sửa | 10 người | — | **1** (3×9 px) |
| Sau sửa | **15 người** | **15/15** | **0** |

**Cách tránh (giữ lại):** nộp hàm đo va chạm in ra **số cặp chồm = 0** trên khung hình
đông nhất tìm được, và siết bài sao cho **mọi** người đều có nhãn.

---

## Live view chậm — đã sửa, đạt 14.34 fps

**Triệu chứng:** live view chỉ **1,4 fps** (lượt đầu), agent đo **6,17 fps** (lượt sau,
chưa tự kiểm lại). Mục tiêu anh đặt: **10 fps**.

**Giả thuyết SAI đã bị đo và bác bỏ:** *"bottleneck nằm ở `cam_ai_core.py` / YOLO chạy
2 vòng"*. Bật thêm pipeline `run_analysis` chỉ làm fps **6.02 → 5.38**.

**Chi phí đo phẳng** (`_kk_do_chi_phi.py`): `grab` 0.1 ms · `read` 1.5 ms ·
**YOLO + ByteTrack 38.5 ms** · vẽ overlay PIL 15.5 ms · nén JPEG 3.2 ms ·
giải JPEG 4.5 ms → tổng **63.4 ms** (15.8 fps lý thuyết).

**Nguyên nhân thật:** nút thắt ở **phía UI** — `PUMP_MS` và `PhotoImage`/`configure`
~46 ms mỗi lần bơm. Vòng bơm mỗi lần chỉ giữ khung **cuối** trong hàng đợi nên trần
hiển thị ≈ `1000 / PUMP_MS`. Ở `PUMP_MS=120` trần chỉ **8.3 fps**.

**Đã sửa:** `PUMP_MS` 120 → **30** trong `gui.py`.

| `PUMP_MS` | 120 | 80 | 50 | **30** | 20 |
|---|---|---|---|---|---|
| fps trung bình | 5.70 | 7.55 | 10.32 | **12.81** | 14.71 |

**Bằng chứng nghiệm thu** (`_kiem_chung/fps_nghiemthu_300s_full.txt`, chế độ `full`:
live view + pipeline cùng chạy, **không** override `PUMP_MS`): thời gian đo
**300.2 s** · 4206 khung vẽ lên UI · nạp model 7.0 s · đo giai đoạn 293.3 s ·
**FPS giai đoạn 14.34** · min 11 fps/giây · max 17 · **0/293 giây** dưới 10 fps.

**Cách tránh:** đo fps bằng cách bọc hàm vẽ khung hình bằng hàm đếm, chạy GUI thật qua
`mainloop()`, đếm số lần gọi **trên luôn UI**. Phải dừng hết tiến trình GUI/AI khác
trước khi đo. Tách rõ "khởi động nạp model" và "giai đoạn ổn định" nhưng vẫn công khai
cả hai, không giấu warm-up.

---

## Video không đủ 70% bề ngang khi cửa sổ hẹp — đã sửa

**Triệu chứng:** cửa sổ 1610px → 74.9% (đạt), **1400px → 69.9% (KHÔNG đạt)**, 1900px → 79.5%.

**Nguyên nhân:** cột sự kiện đặt `minsize=320` **cố định** nên không co lại khi cửa sổ
hẹp. Đồng thời `PanelSuKien` không set minsize nên nó cũng không ép được nhỏ.

**Đã sửa:** thêm `_canh_be_rong_cot_su_kien()` trong `gui.py` —
`b = clamp(200, 320, tổng_bề_ngang × 0.24)`, set **cả** `minsize` của cột **và**
`width` của panel. Gọi từ `after_idle` khi dựng GUI và từ `_khi_keo_cua_so`.

**Bằng chứng đo lại** (`kk_36_boc_cuc.txt`): 1610px **75.5%** · 1400px **75.4%** ·
1900px **83.2%**. Tràn widget **0 px**, tràn nhãn **0**.

**Gotcha liên quan:** chỉ đổi `minsize` của cột grid là **vô dụng** — Tk lấy bề rộng
widget từ `reqwidth` (nội dung thẻ sự kiện đòi), phải set `width` của panel.

---

## Chụp ảnh GUI ra nhầm nội dung của cửa sổ khác

**Triệu chứng:** chụp "vùng khung video" được ảnh toàn đen + khung bình luận YouTube.

**Nguyên nhân:** cửa sổ CamAI **bị cửa sổ khác che**, và `ImageGrab` chụp bề mặt màn
hình chứ không phải nội dung cửa sổ. Chỉ khi chụp **toàn màn hình** mới phát hiện ra.

**Cách tránh:** trước khi chụp phải ép cửa sổ lên trước bằng
`app.attributes("-topmost", True)` + `lift()` (do **chính tiến trình sở hữu cửa sổ**
gọi nên luôn được; `SetForegroundWindow` thì Windows từ chối khi gọi từ tiến trình
nền). Sau đó chụp theo HWND thật:
`u32.GetAncestor(app.winfo_id(), 2)` → `GetWindowRect` → `ImageGrab.grab(bbox, all_screens=True)`.

**Bài học chung:** ảnh chụp mà không nhìn **toàn màn hình** để đối chiếu thì không đáng
tin. Phải tự mở xem từng ảnh.

---

## `"DAT" in "KHONG DAT"` luôn đúng

**Triệu chứng:** script kiểm chứng báo đạt khi thực ra thất bại.

**Nguyên nhân:** chuỗi `"DAT"` nằm trong `"KHONG DAT"`, nên phép `in` luôn trả về True.

**Cách tránh:** so sánh nguyên vẹn (`dong[-2].endswith(": DAT")`) hoặc dùng biến bool
riêng, đừng dựa vào `in` với chuỗi phủ định.

---

## Chạy script kiểm chứng bằng `python` trong PATH → thiếu module

**Triệu chứng:** `ModuleNotFoundError: No module named 'supervision'`.

**Nguyên nhân:** `python` trong PATH không phải Python của `.venv`.

**Cách tránh:** luôn dùng `.venv\Scripts\python.exe` cho mọi script kiểm chứng.

---

## Đợi cứng 4 giây rồi kết luận "video không chạy"

**Triệu chứng:** bài đo bố cục báo "không có khung hình".

**Nguyên nhân:** nạp model mất **~7 giây**, nên 4 giây chưa có khung hình nào.

**Cách tránh:** trong script kiểm chứng phải **chờ có điều kiện** (lặp `after` tới khi
`app._anh_gu is not None`, có mốc chặn trên, ví dụ 90 giây) chứ không đợi cứng.

---

# CHƯA SỬA

## Nhãn người chồng lên nhau trên khung — lỗi tái diễn 2 lần

**Triệu chứng:** trong ảnh `kk_29_dang_chay.png` và `kk_30_timeline.png`, nhãn `Người 4` và
`Bình · 34` nằm cùng trục Y, chồng đè lên nhau giữa video, đọc không được.

**Lịch sử:** agent lần 1 tuyên bố đã sửa và viết "không cái nào chồng nhau". Coordinator
mở ảnh và **xác nhận vẫn còn lỗi**. Không được tin báo cáo, phải xem ảnh.

**Nguyên nhân đoán:** đo nhãn bằng font ước lượng khác font vẽ thật; hoặc thuật toán chạy
trước khi khung hình có kích thước cuối; hoặc chỉ so với rect vừa đặt chứ không so với
tất cả rect đã đặt.

**Cách tránh (bắt buộc):** nộp hàm đo va chạm in ra **số cặp chồm phải bằng 0** trên khung
hình tổng hợp có 8–12 khung người dồn cục. Không được chỉ bằng mắt trên ảnh thu nhỏ.
Nếu thuật toán dồn nhãn không giải quyết được: bỏ nhãn khi đông, chỉ hiện nhãn người quen,
hoặc đưa nhãn sang bảng bên cạnh.

---

## Live view chậm — chưa đạt mục tiêu

**Triệu chứng:** live view chỉ **1,4 fps** (lượt đầu), agent đo **6,17 fps** (lượt sau,
chưa tự kiểm lại). Mục tiêu anh đặt: **10 fps**.

**Nguyên nhân:** bottleneck nằm ở **`cam_ai_core.py`**, không phải lớp GUI. Main pipeline
không có nhận diện mặt cũngng 6,47 fps. Đổi nhịp nhận diện (`face_every` từ 1 xuống 3) chỉ
cải thiện ít.

**Rào cản khi sửa:** agent GUI không được phép sửa `cam_ai_core.py`. Phải giao riêng agent lõi.

**Đo fps đúng cách:** bọc hàm vẽ khung hình bằng hàm đếm, chạy GUI thật qua `mainloop()`,
đếm số lần được gọi **trên luôn UI** trong N giây. Đây là fps thực sự lên màn hình, không
phải fps đọc video. **Phải dừng hết tiến trình GUI/AI khác trước khi đo** — nhiều instance
cùng giữ model GPU sẽ làm sai số đo.

---

## Giật khi kéo cửa sổ — chưa được anh xác nhận

**Triệu chứng:** anh báo giật khi kéo cửa sổ.

**Đã làm (đo được, chưa xác nhận cảm giác):** không có `<Configure>`; resize chạy trong
pump 120 ms. `PIL.LANCZOS` tốn **39,7 ms**; toàn bộ resize event trung bình **58,2 ms**.
Thay bằng `cv2.INTER_AREA` + debounce 180 ms + freeze frame khi kéo. Sau đó: khoảng
**0,010 ms** mỗi drag event; redraw sau thả chuột khoảng **19,7 ms**.

**Trạng thái:** **CHƯA XÁC NHẬN.** Coordinator đã báo "xong" dựa trên số đo — **sai**.
Cảm giác giật hay không chỉ anh mới quyết được. **Cần anh tự kéo thử.**

*(Ghi chú 2.7: `PUMP_MS` 120 → 30 giúp live view mượt hơn nhiều, nên nhiều khả năng
cảm giác giật cũng giảm. Nhưng đây vẫn là **suy đoán** — anh kéo thử rồi xác nhận.)*

---

## Dải nhãn tổng kết ở đáy video bị dính chữ — ĐÃ SỬA ở 2.6

**Triệu chứng (cũ):** đọc được `Người 3 · Người quan 2 · Trong vùng: 0` — chữ "Người quan"
dính liền, mất khoảng cách.

**Đã sửa:** tách từng mục thành badge riêng có nền riêng.
**Bằng chứng:** ảnh `kk_36_boc_cuc.png` — dải đáy đọc rõ từng ô:
`14 Người | 0 Mặt | 0 Người quen | 0 Vào | 0 Ra | 0 Trong vùng`, không dính chữ.

---

## Nhãn vùng chồn lên khung người — ĐÃ SỬA ở 2.6

**Triệu chứng (cũ):** nhãn `VÙNG CANH · TRỐNG` nằm chồng lên khung vàng của người.

**Nguyên nhân:** nhãn vùng chỉ né bảng thống kê, không né nhãn người.

**Đã sửa:** nhãn vùng tránh vùng đã bị chiếm. Bằng chứng: `kk_32_fix.png` và
`kk_36_boc_cuc.png` — coordinator tự xem, không còn chồn.

---

## Trạng thái khẩu trang luôn "Chưa rõ"

**Nguyên nhân:** **dự án chưa có model nhận diện khẩu trang.** `face_engine.FaceResult`
chỉ có `box / name / score / age / sex / face_size`.

**Không được đoán bừa.** Cần cài model riêng.

---

## Lưới "Đối tượng phát hiện" bị bỏ khỏi bố cục

**Nguyên nhân:** agent tự quyết bỏ khi dựng bố cục mới, chuyển vai trò sang danh sách sự kiện.
Class `PanelDoiTuong` còn nguyên trong `gui_khung.py` nếu sau này muốn gọi lại.

**Cần hỏi anh:** có muốn giữ lại không.

---

## Không chọn được kênh cảnh báo

**Triệu chứng:** 3 checkbox cũ (Phát chuông / Mở hộp thoại / Gửi tin Telegram) bị thay bằng
4 ô khớp 1:1 với cờ lõi. `AnalysisConfig` chỉ có 4 cờ nên không truyền được kênh nào bật.

**Lưu ý:** các biến `v_cb_chuong` / `v_cb_hop_thoai` / `v_cb_telegram` còn tồn tại (mặc định
1/1/0) nhưng **không còn widget nào điều khiển**. Bấm nút "Thử gửi" sau khi tắt "Chỉ thử"
sẽ dùng kênh mặc định = chuông + hộp thoại, không Telegram.

**Cách sửa:** phải thêm cờ vào `cam_ai_core.py`.

---

## Console Windows không in được tiếng Việt có dấu

**Cách tránh:** đọc file bằng `Get-Content -Encoding UTF8`. Nếu cần in từ Python, đặt
`PYTHONIOENCODING=utf-8`. Đã có `_log_an_toan()` tự lùi bản không dấu.

---

## PowerShell hiển thị sai tiếng Việt

**Triệu chứng:** `Get-Content README.md` ra `CamAIâ€”Phân tích video giám sát`.

**Nguyên nhân:** PowerShell 5.1 đọc file UTF-8 **không BOM** theo kiểu ANSI.

**Cách tránh:** `Get-Content -Encoding UTF8`.

---

## `Select-Object -First N` làm sai exit code

**Triệu chứng:** `EXIT_B=-1` dù `app.py` chạy thành công.

**Nguyên nhân:** `Select-Object -First N` đóng pipeline sớm → broken pipe → PowerShell báo
`-1`. Đây là hành vi của PowerShell, **KHÔNG phải lỗi app**.

**Cách tránh:** gom output rồi đọc sau:
```powershell
$o = & .venv\Scripts\python.exe app.py ... 2>&1
Write-Output "EXIT=$LASTEXITCODE"
$o | Select-String -Pattern '...'
```

---

## `[System.IO.File]::ReadAllBytes()` với đường dẫn tương đối

**Triệu chứng:** `Could not find file 'H:\AI Project\gui.py'` dù file có thật trong `cam-ai`.

**Nguyên nhân:** .NET dùng **process cwd**, không dùng PowerShell location. `cd` trong
PowerShell không đổi cwd của tiến trình.

**Cách tránh:** dùng đường dẫn **tuyệt đối**.

---

## `rm` bị treo khi xóa nhiều file

**Triệu chứng:** `rm -- file1 file2 ... (15 file)` treo >120 giây, exit 1.

**Cách tránh:** xóa 1–2 file mỗi lệnh. Dùng `rm` của runtime (trash có thể khôi phục).
`Remove-Item -Force` bị permission gate chặn — đừng thử.

---

## Thư mục `_dns_probe` không xóa được

**Triệu chứng:** `The process cannot access the file because it is being used by another process`.

**Nguyên nhân:** một tiến trình còn giữ handle trong thư mục (thư mục rỗng).

**Cách tránh:** thử lại sau khi tiến trình liên quan kết thúc. Thư mục rỗng nên không ảnh hưởng.

---

## GUI crash khi mở: hằng số chưa định nghĩa

**Triệu chứng:** chạy `gui.py` báo `NameError` ngay khi khởi tạo (đã xảy ra với `XEM_VIDEO_BE_RONG`).

**Cách tránh:** `ast.parse()` **không đủ** — phải **thật sự mở cửa sổ** rồi chụp ảnh mới biết.
Sau khi sửa luôn chạy:
```
.venv\Scripts\python.exe _kiem_tra_gui.py
```

---

## `cv2.putText` không hiển thị tiếng Việt có dấu

**Triệu chứng:** chữ trên khung hiện kiểu `Nguoi: 2`, `VUNG CANH`, mất dấu.

**Nguyên nhân:** `cv2.putText` chỉ dùng font Hershey ASCII, không có glyph tiếng Việt.

**Cách tránh:** vẽ overlay bằng PIL/Pillow với font hệ thống có dấu. Đã tách riêng thành
`gui_khung.py`.

---

## Nhận diện tên có trong log nhưng khung vẫn ghi "Người N"

**Triệu chứng:** nhật ký hiện `Nhận diện: An | Bình`, nhưng khung vẫn ghi `Người 1`.

**Nguyên nhân:** live-view thread chạy YOLO + ArcFace **riêng**, không dùng kết quả của
pipeline chính. Hai luồng độc lập.

**Cách tránh:** phải tự quét tên theo track ID rồi giữ lại giá trị cuối để nhãn không
nhấp nháy khi mất mặt ở vài khung.

---

## Cửa sổ GUI tràn xuống taskbar

**Đã sửa (v2.3):** dùng `SPI_GETWORKAREA` để lấy vùng làm việc, `GetWindowRect` để đo cửa
sổ thật. Phải chờ `winfo_width()` khớp kích thước đã định nghĩa trước khi tính, vì lúc
`__init__` Tk trả 200×200 mặc định.

**Kinh nghiệm:** `winfo_*` của Tk **không** phản ánh trạng thái thật của cửa sổ Windows.
Khi cần chính xác thì đo bằng Win32 API.
---

## NHẬN DIỆN HỎNG KHI NGƯỜI Ở XA / VIDEO QUAY DRONE

**Hiện trạng (2026-10-19): CHƯA SỬA — vẫn còn nguyên.** Đo thật cho thấy giới hạn thật
của bản hiện tại, không phải lỗi cấu hình.

**Triệu chứng:**
- `video_mau/moi/nguoi-di-lai.mp4` (quay drone cao độ): nhận **0 người ở cả 12 khung mẫu**,
  trong khi hình có rõ hàng trăm người.
- `video_mau/moi/dam-dong.mp4` (ngã tư đông): nhận 2–6 người mỗi khung, conf trung vị 0.35.
- `video_mau/moi/xe-co-giao-thong.mp4`: chỉ 6/12 khung có người, conf 0.26–0.58.

**Nguyên nhân:** `AnalysisConfig.model = "yolo11n.pt"` — model nano ưu tiên tốc độ.
Khi thân người chỉ còn ~10–20 px, đặc trưng không đủ để nhận.
`conf=0.25` đã là mặc định mềm nhất của ultralytics nên hạ thêm cũng ít giúp.

**Không tự ý sửa vì:** đổi model sang `yolo11s/m` sẽ chậm hơn và có nguy cơ **mất mục tiêu 1**
(live view ≥10 fps) đã đạt được. Cần anh quyết định: giữ tốc độ hay đổi lấy chính xác.

**Cách tránh tái phát:** khi chọn video demo hoặc video thật, phải chọn video quay ở
**cự ly gần** (camera treo tường, quay ngang tầm người). Video drone / quay từ trên cao
không thuộc phạm vi mà `yolo11n` xử lý được.

**Cách kiểm chứng lại sau này:** `python -W ignore _kk_kiem_do_nhan_diem.py`
rồi **tự mở ảnh `_kiem_chung/nhan_diem_<ten>.png` xem bằng mắt**, không được chỉ đọc số.

**Phương án nâng cao (đã đo thật 2026-10-19, xem `PROJECT_STATE.md` mục 2.4):**
- Phóng to khung hình ×2: **vô dụng** — ultralytics tự resize về 640px bên trong.
- Đổi `yolo11n` → `yolo11s`: **không giúp**, `dam-dong` còn tệ hơn (3.0 → 2.6).
- Chia ô 2×2 **không kèm toàn khung**: **làm hỏng** video gần (9.4 → 4.5).
- **Toàn khung + ô 2×2 gộp NMS**: chính xác nhất, không hồi quét video gần,
  nhưng chậm hơn 5.3× (~170 ms/khung) nên bật sẽ mất mục tiêu 1.
  → **ĐÃ TRIỂN KHAI bản 2.8** thành công tắc `--tach-o`, **mặc định TẮT** (anh đã chọn).
  Bật lên: `dam-dong` 3.0 → 5.4, `xe-co-giao-thong` 1.0 → 4.6. Chậm 5.3×.

**Bài học chung:** khi thấy "kết quả y hệt nền ở mọi case" thì nghĩ ngay tới
**phép toán bị thư viện hủy bên trong** (ở đây là resize về `imgsz=640`),
đừng tưởng là video không có người.

---

## `detect_tach_o` chỉ quét 3/4 khung hình — ô không phủ toàn bộ

**Hiện trạng (2026-10-19): ĐÃ SỬA.** Lỗi do em tự viết, tự phát hiện, tự sửa.

**Triệu chứng:** ô chia đè lên nhau nên phần giữa khung bị quét 2 lần, còn **vùng
sát mép phải và mép dưới không ô nào phủ**. Người đứng sát mép bị bỏ sót mà trông như
"ô không nhận được".

**Nguyên nhân:** đặt bước nhảy bằng **kích thước ô** thay vì **kích thước khung trừ ô**:
```python
buoc_x = cw          # SAI
buoc_y = ch          # SAI
```
Cần `buoc_x = w - cw`, `buoc_y = h - ch` để ô cuối trượt tới đúng mép khung.

**Kiểm chứng lại:** khung 960×540 → ô 336×189, vị trí ô ngang trong khoảng `[0, 624]`,
ô dọc `[0, 351]` ⇒ 624+336 = 960 và 351+189 = 540, tức **phủ đúng bằng 100%**.

**Cách tránh tái phát:** mọi phép chia ô phải có **assert phủ kín**:
`buoc * (số ô - 1) + kích thước ô == kích thước khung`.

---

## `NMSBoxes` với `score_threshold` cao hơn ngưỡng nhận — XOÁ NHẦM nhãn

**Hiện trạng (2026-10-19): ĐÃ SỬA.** Lỗi nguy hiểm nhất trong đợt này.

**Triệu chứng:** sau khi bật `--tach-o`, số nhãn **giảm** ở video gần
(`tre-em-san-choi` 9.4 → 8.2) — tức công tắc làm mất người chứ không phải chỉ chậm.

**Nguyên nhân:** `cv2.dnn.NMSBoxes` có tham số `score_threshold` mặc định `0.0`,
nhưng em truyền `score_threshold=0.45` với tưởng đó là "ngưỡng tin cậy". Ô nào trả về
nhãn có `conf < 0.45` (rất nhiều, vì ngưỡng nhận gốc chỉ là `0.25`) **bị NMS loá khỏi
kết quả**. Nghĩa là công tắc đã âm thầm nâng ngưỡng nhận gốc lên gần gấp đôi.

**Sửa:** tách rõ hai khái niệm trong `cam_ai_core.py`:
```python
TACH_O_DIEM = 0.0    # score_threshold — KHÔNG loại nhãn nào
TACH_O_IOU  = 0.45   # nms_threshold  — chỉ gộp khung trùng
```
**Cách tránh tái phát:** khi dùng hàm gộp của OpenCV, phải đọc kỹ tên tham số:
`score_threshold` là **ngưỡng loại**, `nms_threshold` mới là **ngưỡng trùng**. Tuyệt đối
không dùng lại giá trị ngưỡng nhận gốc cho tham số có tên `score_threshold`.

**Cách kiểm chứng lại:** `python -W ignore _kk_kiem_tach_o.py` — so cột nền và cột
`detect_tach_o`; **video gần không được GIẢM**.

---

## Nhóm GUI mới không được `_kiem_tra_gui.py` kiểm vì thiếu trong `danh_sach_nhom()`

**Hiện trạng (2026-10-19): ĐÃ SỬA.**

**Triệu chứng:** nhóm "Nhận người ở xa (chậm hơn)" hiện trên GUI nhưng khi chạy
`_kiem_tra_gui.py` thì **không có dòng nào kiểm nhóm này** — test 4/4 PASS trông có vẻ
đủ nhưng thực ra **nhóm mới chưa hề được kiểm**. Đây đúng là loại "báo đạt bằng số mà
không có bằng chứng" mà anh đã cảnh báo.

**Nguyên nhân:** `danh_sach_nhom()` trong `gui.py` là danh sách tường minh các nhóm
được test; nhóm mới không được thêm vào nên test không bao giờ chạm tới.

**Sửa:** thêm `"nhom_tach_o"` vào vòng `for ten in (...)` trong `danh_sach_nhom()`.
Sau đó test in ra: `[OK ] Nhận người ở xa (chậm hơn) mac_dinh_ban_dau=TAT`.

**Cách tránh tái phát:** thêm nhóm GUI mới thì **bắt buộc** khai báo trong
`danh_sach_nhom()` cùng lúc, và khi báo "đạt" phải dán dòng `[OK ]` của chính nhóm mới
vào báo cáo — không dán lại dòng PASS của nhóm cũ.

---

## `_kk_do_fps_live.py` nhận tham số theo VỊ TRÍ, không có cờ `--khong-tmp`

**Hiện trạng (2026-10-19): ĐÃ GHI NHỚ, không sửa script.**

**Triệu chứng:** lệnh đo fps 300 giây của bản 2.8 chết ngay trước khi chạy:
```
ValueError: invalid literal for int() with base 10: '--khong-tmp'
```

**Nguyên nhân:** em gõ lệnh theo kiểu argparse quen thuộc. Nhưng script này đọc
`sys.argv[1..5]` theo thứ tự:
```
_kk_do_fps_live.py <video> <giay> <full|xem> <nhan> [pump_ms]
```
Em đẩy `--khong-tmp` vào vị trí thứ 5 nên `int(sys.argv[5])` ném `ValueError`.

**Cách tránh tái phát:** script kiểm chứng trong dự án này phần lớn dùng **thứ tự vị
trí**, không phải cờ. Trước khi chạy, **đọc dòng `if __name__ == "__main__"`** để xem
đúng cú pháp, hoặc chạy không tham số để đọc dòng hướng dẫn `dung:` mà script in ra.
