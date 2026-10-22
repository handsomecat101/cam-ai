# Sổ lỗi CamAI

Ghi lại lỗi đã biết để không phát minh lại. Xem `PROJECT_STATE.md` mục 2 (bảng ĐẠT/CHƯA ĐẠT)
và mục 6 (gotcha) cho việc đang làm.

**Ngày cập nhật:** 2026-10-20

---

# ĐÃ SỬA

## Script kiểm chứng báo FAIL giả — kiểm tra TRƯỚC khi sự kiện xảy ra

**Triệu chứng:** `_kk_kiem_app_qt.py` báo **21/27 PASS**, 6 mục FAIL:
`TU-DANG-NHAP: OK` không thấy · `TOKEN-LOCALSTORAGE` không thấy · không lấy được port/token ·
3 marker hộp thoại (`HOP-THOAI-URL` / `-MK` / `-NUT`) không thấy.

**Nguyên nhân — 2 lỗi của SCRIPT, không phải của sản phẩm:**
1. **Thứ tự thời gian**: script chờ marker *"TAI-TRANG:"* (trang đã nạp) rồi **kiểm tra
   ngay** marker *"TU-DANG-NHAP: OK"* — nhưng tự đăng nhập chạy **sau** khi trang nạp ⇒
   kiểm tra quá sớm. Kịch bản thứ 2 (có `CAMAI_PASSWORD`) **PASS** vì nó làm thêm vài
   bước nên vô tình chờ lâu hơn.
2. **Marker có điều kiện**: `CAMAI_QT_IN_DIALOG` **chưa được bật** ở kịch bản 1 ⇒ các
   marker hộp thoại không bao giờ được in.

**Cách sửa:** thêm `_cho_den_khi(dong, "TU-DANG-NHAP: OK", 40)` **sau** khi chờ trang nạp,
và bật `CAMAI_QT_IN_DIALOG=1` cho cả hai kịch bản ⇒ **28/28 PASS**.

**Cách chứng minh đây là lỗi script chứ không phải lỗi sản phẩm:** coordinator chạy
**app thật** bằng `Start-Process` và đọc log ⇒ thấy đúng chuỗi:
```
[CAMAI-QT] MAT-KHAU-TU-SINH: %?kBrGgoQx
[CAMAI-QT] TU-DANG-NHAP: OK qua fetch (token 43 ky tu da luu vao localStorage)
[CAMAI-QT] TU-DANG-NHAP: GET /api/trang-thai -> HTTP 200 (ok)
[CAMAI-QT] TOKEN-LOCALSTORAGE: ZqWv0sz-IMwa58jjkDjdl_6TKoaoy4XeVEGAxKQW9G4
```

**Bài học:**
- **Khi bộ kiểm chứng FAIL mà tính năng vẫn chạy được thì ĐỪNG SỬA SẢN PHẨM** — hãy
  **chạy thật** và đọc log để phân biệt "lỗi sản phẩm" với "lỗi kỳ vọng của script".
- Mọi **marker kiểm chứng có điều kiện** (biến môi trường) thì script phải bật ở
  **mọi** kịch bản, không chỉ kịch bản đầu.
- Script kiểm chứng phải **chờ theo mốc thời gian của sự kiện**, không kiểm tra ngay
  sau một mốc khác.
- Trên Windows, `Start-Process -ArgumentList` với đường dẫn **có khoảng trắng** phải
  **bọc nháy kép** (`'"H:\AI Project\...\app.py"'`), nếu không sẽ bị tách thành nhiều
  đối số và báo `SyntaxError`.

---

## Thiếu `openh264-2.5.0-win64.dll` → VideoWriter hỏng → **app CRASH lúc thoát** (0xC0000005)

**Triệu chứng:** mỗi lần chạy app/CLI đều in log đỏ:
```
Failed to load OpenH264 library: openh264-2.5.0-win64.dll
  Please check environment and/or download library: https://github.com/cisco/openh264/releases
[libopenh264 @ ...] Unable to create encoder
[ERROR:0@...] global cap_ffmpeg_impl.hpp:3568 open Could not open codec libopenh264, error: Unspecified error (-1313558101)
[ERROR:0@...] global cap_ffmpeg_impl.hpp:3585 open VIDEOIO/FFMPEG: Failed to initialize VideoWriter
```

Hệ quả — **KHÔNG chỉ là log đỏ**:
1. `cv2.VideoWriter` với fourcc `avc1` (H.264) **không khởi tạo được** → file video kết quả có thể hỏng.
2. **Tiến trình CRASH lúc thoát** với `0xC0000005` (access violation) — đo được **4/5 lần trên bản gốc `git HEAD`**, tức là **lỗi có sẵn từ lâu, không phải do ai sửa**.

**Nguyên nhân:** FFmpeg của OpenCV gọi `LoadLibrary("openh264-2.5.0-win64.dll")`. Tên file **phải khớp đúng phiên bản FFmpeg dùng** — đổi tên là FFmpeg không tìm thấy. Máy phát triển **không có** file DLL này (OpenCV chỉ kèm `msopenh264` cho build khác).

**Cách sửa (bản 3.8):**
1. Tải **bản phát hành chính thức của Cisco v2.5.0** → `openh264-2.5.0-win64.dll` đặt cạnh `app.py`/`gui.py` (kèm **giấy phép BSD-2-Clause của Cisco** trong repo).
2. Thêm `_nap_dll_openh264()` — nạp DLL bằng `ctypes.WinDLL` **trước khi** tạo `VideoWriter`, và **giữ handle ở biến global** (Windows `unload` DLL khi handle bị GC). Nạp trước bằng `LoadLibrary` ⇒ FFmpeg dùng được DLL đã nạp dù nó nằm ở thư mục nào.
3. `_fourcc_ket_qua()` **kiểm tra** bằng cách thử mở thật một file mp4 tạm với `avc1` → nếu hỏng thì **fallback `mp4v`** và **báo rõ** codec đang dùng, **không crash**.

**Kết quả đo (coordinator tự chạy lại):**
| | Trước | Sau |
|---|---|---|
| `VideoWriter` với `avc1` | `opened = False` + log đỏ | **`opened = True`** + dòng *"OpenH264 Video Codec provided by Cisco Systems, Inc."* |
| `app.py --input ...` 3 lần liên tiếp | **crash 4/5 lần** (exit `0xC0000005`) | **3/3 lần exit = 0** |
| Codec file kết quả | hỏng / không mở được | **h264**, đọc lại đúng số khung |

**Bài học:**
- **"Log đỏ mà vẫn chạy" là hiểu lầm nguy hiểm** — ở đây log đỏ che một lỗi **crash lúc thoát**. Tài liệu cũ ghi *"file vẫn H.264 hợp lệ"* là **SAI**, đã sửa lại.
- **Lỗi crash lúc thoát thường do tài nguyên chưa giải phóng / encoder hỏng**, không phải do logic chính. Phải tái hiện **nhiều lần** (4/5, 3/5) mới thấy — chạy 1 lần thì tưởng "lúc nào cũng được".
- **DLL của bên thứ ba phải đi kèm giấy phép** trong repo (Cisco OpenH264 là BSD-2-Clause, được phân phối kèm) — không có giấy phép thì không commit.
- Tên file DLL **phải khớp đúng** phiên bản FFmpeg dùng. Đổi tên = không được nạp.

---

## Log "Đang nhận N lớp" KHÔNG dịch được + lỗi chính tả "Bỏ qua l không có"

**Triệu chứng (agent phát hiện khi sửa vòng 3):** 2 dòng log trong khung "xem trực tiếp"
về lớp vật thể:
```
> [vật thể] Đang nhận 2 lớp: xe o to, xe may
> [vật thể] Bỏ qua l không có: xyz
```
- **"Bỏ qua l không có"** — thiếu chữ **"ớp"** ⇒ đọc như lỗi chính tả rõ ràng.
- **"Đang nhận N lớp: …"** khi bật tiếng Anh vẫn **giữ nguyên tiếng Việt**.

**Nguyên nhân:**
1. Lỗi chính tả nằm ngay trong chuỗi f-string của `gui.py`.
2. Bản dịch không dịch được vì khoá trong `DICH_VI_EN` là **mẫu có tham số**:
   `"> [vật thể] Đang nhận {n} lớp: {ds}"`, còn chuỗi thật đã được f-string nội suy
   thành `"> [vật thể] Đang nhận 2 lớp: xe o to, xe may"` ⇒ **không khớp khoá nào** ⇒
   khoá dịch là **khoá chết**.

**Cách sửa (bản 3.7):**
- Sửa chính tả: `"Bỏ qua l không có:"` → `"Bỏ qua lớp không có:"`.
- Tách log thành **2 dòng** để mỗi dòng có tiền tố dịch được, và dùng
  `self.dich(...).format(...)` thay vì f-string thẳng cho dòng có tham số.
- Thêm khoá dịch cho cả 2 tiền tố.

**Bài học:**
- **Khoá dịch có tham số phải dùng `dich(...).format(...)`, không dùng f-string.**
  Nếu không, khoá dịch **chết lặng lẽ** → app "song ngữ" mà 1 chỗ vẫn tiếng Việt.
- Khi thêm chuỗi hiển thị mới, **luôn kiểm tra nó CÓ dịch được** bằng cách bật thử chế độ
  tiếng Anh, không chỉ "đã thêm vào dict" ⇒ dict có khoá ≠ khoá được dùng.
- Lỗi chính tả trong chuỗi hiển thị rất dễ lọt vì không ai đọc log hằng ngày — nên có
  kiểm chứng riêng cho phần dịch (bộ `_kk_kiem_ngon_ngu_v3_3.py`).

---

## Mũi tên mục lớn không phản ánh trạng thái mở/đóng (mọi mục trông giống nhau)

**Triệu chứng:** coordinator chụp ảnh GUI bản 3.6 rồi **phóng to 3×** vùng cột trái
(`_kk_out/agent_a_nguon/zoom_chevron.png`) → thấy mục **NGUỒN đang MỞ** (nội dung hiện
ra bên dưới) nhưng mũi tên vẫn là **ChevronRight (chỉ sang phải)** thay vì
**ChevronDown (chỉ xuống)**. Cả 4 mục lớn đều dùng cùng một mũi tên ⇒ người dùng
**không biết mục nào đang mở**.

**Nguyên nhân (đã xác minh trong code, `gui.py` lớp `NhomLon`):**
- `__init__` tạo nút `self.btn_mo` với `text=bieu_tượng("mui_phai")` — **luôn**.
- Chỉ khi `dat_mo(True)` được gọi thì mới đổi sang `bieu_tượng("mui_xuong")`.
- Với `mo_san=True` (mục NGUỒN), `__init__` chỉ gọi `self.khung.grid()` rồi
  `grid_remove()` nếu đóng — **không gọi `dat_mo()`** ⇒ mũi tên mãi là ChevronRight.

Lỗi này **có từ bản 3.6** (lúc gom 12 nhóm thành 4 mục lớn) — đã kiểm tra lại bằng
`git show 35250e5:gui.py`, code y hệt.

**Cách sửa (bản 3.7):** đặt mũi tên theo trạng thái khởi tạo — `mo_san=True` ⇒
ChevronDown, ngược lại ChevronRight. **KHÔNG** gọi `dat_mo()` trong `__init__` vì hàm đó
có tác dụng phụ đóng các mục lớn khác (vi phạm nguyên tắc "chỉ 1 mục mở tại một lúc").

**Bài học:**
- **Mọi widget có trạng thái phải khởi tạo đúng trạng thái**, không được "để mặc định
  rồi sửa khi hành động xảy ra". Ở đây nhánh `mo_san` không đi qua hàm cập nhật nên
  trạng thái hiển thị bị bỏ sót.
- **Kiểm tra lỗi thị giác bằng ảnh phóng to 3×**, không tin nhìn bằng mắt ở kích thước
  nhỏ — Ở 1610×980 mũi tên trông "đúng", phóng 3× mới thấy sai.
- Khi giao diện dùng **ký hiệu trạng thái** (mũi tên, màu, tick), phải kiểm tra **mọi
  tổ hợp trạng thái**, không chỉ trạng thái "mặc định".

---

## OpenCV Hershey **âm thầm bỏ dấu** tiếng Việt khi vẽ chữ lên khung hình

**Triệu chứng:** nhãn lớp vật thể vẽ lên khung hình bằng `supervision` →
`sv.LabelAnnotator` → `cv2.putText(..., cv2.FONT_HERSHEY_SIMPLEX, ...)`.
Agent đo thực nghiệm (ảnh `_kk_out/_kk_nhan_khung_hinh_2.png`): chuỗi **"ô tô"** hiện
ra thành **"o to"**, **"xe máy"** thành **"xe may"** — dấu **biến mất im lặng**, KHÔNG
bị thay bằng ký tự rác.

**Nguyên nhân:** font Hershey của OpenCV chỉ có **ASCII** — không có glyph dấu tiếng Việt.

**Quyết định (bản 3.7):** chia 2 nơi dùng tên lớp:
| Nơi dùng | Tên hiển thị | Vì sao |
|---|---|---|
| **Nhãn trên khung hình** | **KHÔNG dấu** (`xe o to`) | font Hershey không vẽ được dấu |
| **Log / báo cáo / CSV** | **CÓ dấu** (`ô tô`) | chữ thuần, hiển thị được |

Không chuyển nhãn khung hình sang PIL vì **đường pipeline vẽ khung đã được kiểm chứng
kỹ** — đổi là rủi ro lớn hơn lợi ích (đẹp hơn 1 dấu).

**Bài học:**
- **OpenCV `putText` không hỗ trợ tiếng Việt** — font của hệ điều hành (`segoeui.ttf`)
  hoặc PIL mới vẽ được dấu. Dự án đã có `bien_so.py` dùng PIL vì lý do này.
- Muốn biết font có hỗ trợ dấu hay không thì **phải render ra ảnh rồi xem**, không
  suy đoán từ tên font.

---

## GUI "xem trực tiếp" chỉ hiểu tên lớp tiếng Anh — lệch với CLI

**Triệu chứng:** sau khi `cam_ai_core.py` hỗ trợ chọn lớp bằng **tiếng Việt**, phần
**phân tích** (gọi `run_analysis`) hiểu tiếng Việt, nhưng phần **xem trực tiếp** trong
GUI thì **không**. Nguyên nhân: `gui.py` hàm `_vong_xem()` **tự viết lại** logic chọn lớp:
```python
id_lop = {ten: cid for cid, ten in detector.names.items()}
chon = [x.strip() for x in str(cfg.lop).split(",") if x.strip()]   # CHI tieng Anh
```
→ gõ "ô tô,xe máy" thì `id_lop[t]` không tồn tại ⇒ **khung xem trực tiếp không vẽ khung
vật thể nào**, trong khi báo cáo thì có. Người dùng tưởng app bị hỏng.

**Cách sửa (bản 3.7):** cho `_vong_xem` dùng **cùng hàm chọn lớp** của `cam_ai_core`
(`_chon_lop`) thay vì viết lần thứ hai; có `getattr` fallback để GUI vẫn chạy nếu core
thiếu hàm mới.

**Bài học:**
- **Không được copy logic chọn lớp vào nhiều nơi.** Mỗi quy tắc chỉ nên có **một nơi
  quyết định** — ở đây là `cam_ai_core`. Lặp lại là cách chắc chắn GUI và CLI lệch nhau.
- Khi một agent báo "tôi không sửa được file X vì agent khác đang giữ" thì **đó là tín
  hiệu phải giao vòng sửa tiếp** (vòng 3), không được bỏ qua.

---

## File lựa chọn ngôn ngữ bị commit vào git → app của người dùng tự mở tiếng Anh

**Triệu chứng (bản 3.6, coordinator phát hiện khi kiểm chứng):** file `gui_ngon_ngu.json`
— lưu **lựa chọn ngôn ngữ của người dùng** — đang **bị git theo dõi**. Một script kiểm
chứng đã đổi nó sang `"en"` và để nguyên ⇒ file bị "dính" ở trạng thái English trong repo.

Hậu quả:
1. **App của anh tự mở bằng tiếng Anh** — dù code đã sửa hết sang tiếng Việt có dấu.
2. **Bộ kiểm chứng e2e FAIL** vì nó chỉ tìm chuỗi tiếng Việt (`Kết quả:`, `Báo cáo:`).

Đây là lỗi **loại "trạng thái cá nhân lọt vào repo"** — không phải lỗi code, nhưng làm hỏng
cả trải nghiệm người dùng lẫn độ tin cậy của bộ test.

**Cách sửa (bản 3.6):**
1. `git rm --cached gui_ngon_ngu.json` + thêm vào `.gitignore` → lựa chọn cá nhân **không**
   được commit (giống `known_faces/`, kết quả chạy, cache model).
2. Reset file về `"vi"`.
3. Sửa `_kk_kiem_gui_chay_thuc.py` **không còn phụ thuộc ngôn ngữ**: chấp nhận cả
   `Kết quả:`/`Result:` và `Báo cáo:`/`Report:`.

**Bài học:**
- **Mọi file lưu lựa chọn/trạng thái của người dùng phải nằm trong `.gitignore`**:
  `gui_ngon_ngu.json`, `known_faces/`, thư mục output, cache model.
- **Bộ kiểm chứng không được phụ thuộc ngôn ngữ** — nếu không, chính bộ test sẽ làm hỏng
  app của người dùng (đây chính là thứ đã xảy ra).
- Khi commit, phải **kiểm tra `git status` xem có file trạng thái cá nhân nào lọt lên không**.

---

## Kéo cửa sổ bị giật mạnh — tooltip tạo/huỷ cửa sổ native liên tục

**Triệu chứng:** anh dùng thật thì thấy **kéo cửa sổ bị giật lắm** (mục 7 của bảng nghiệm
thu, trước đây chỉ có số đo của coordinator, **chưa** có xác nhận của anh).

**Đo được (coordinator tự đo, script `_kk_do_giat.py` + `_kk_do_giat_thu_nghiem.py`):**

| Số đo | Kết quả |
|---|---|
| Lần kéo dài nhất bị tre (nền) | **520–647 ms** |
| Số lần tre > 30 ms trong 2–3 s kéo | 3–4 lần |
| **Chi phí vẽ lại toàn bộ cửa sổ** | chỉ **0,5 ms** → **KHÔNG phải do vẽ lại** |
| **CPU khi app đứng yên 3 s** | **0 ms** → **KHÔNG phải app chạy nền** |
| Số widget Tk | **851** (trong đó 586 widget CustomTkinter) |

**Thí nghiệm A/B quyết định** (bỏ binding `<Enter>/<Leave>/<Motion>` trên mọi widget):

| Trạng thái | max gap | số lần tre > 30 ms |
|---|---|---|
| Nền | **520 ms** | 3 |
| Bỏ binding hover (246 binding) | **20,8 ms** | **0** |

→ Thủ phạm là **sự kiện Enter/Leave**, không phải vẽ lại.

**Nguyên nhân (sau khi đo thật, đã loại trừ 2 giả thuyết sai):**

1. ~~Tooltip tạo/huỷ cửa sổ native~~ → **loại trừ**: trong lúc kéo, con trỏ chuột **không nằm
   trên app** (widget dưới con trỏ = `None`), nên **không có** sự kiện `<Enter>/<Leave>`
   nào (`Enter=0`, `Leave=0`) và **không cửa sổ tooltip nào được tạo** (`tao=0`).
2. ~~Chi phí vẽ lại~~ → **loại trừ**: đo riêng thời gian vẽ lại toàn bộ cửa sổ = **0,5 ms**.
3. ~~App chạy nền~~ → **loại trừ**: **CPU idle = 0 ms** trong 3 s.

**Cái thật sự gây tre (đo được):**

| Bằng chứng | Số đo |
|---|---|
| Chỉ xảy ra ở **lần kéo ĐẦU TIÊN** | lần 1: **859 ms** → lần 2: 20,2 ms → lần 3: 20,9 ms (không đổi gì giữa các lần) |
| Cửa sổ **rỗng** không bị | Tk rỗng 21,3 ms · CTk rỗng 18,4 ms · **CamAI đầy đủ 984 ms** |
| **Bỏ hết scrollbar** | còn **144 ms** → scrollbar chiếm **~85%** chi phí |
| Stack lúc đang tre | vòng `CTkScrollbar._draw` (ctk_scrollbar.py:161 → `self._canvas.update_idletasks()`) → `<Configure>` → `_update_dimensions_event` → `_draw` → … |
| Số widget | **851** Tk (586 CustomTk); app có **5 CTkScrollbar** (4 từ `CTkScrollableFrame` + 1 từ `CTkTextbox` nhật ký) |

→ Lần kéo đầu tiên kích hoạt **một lần vẽ lại toàn bộ cây widget** (851 widget) cộng với
**5 scrollbar** kéo theo → 0,6–1,0 s. Các lần kéo sau rẻ vì kích thước đã ổn định.
Lưu ý: "chặn đệ quy `_draw`" bằng re-entrancy guard → **918 ms, không giúp** ⇒ vấn đề không
nằm ở đệ quy mà ở **chi phí vẽ lại lần đầu**.

**Cách sửa (`VERSION` 3.5):**
1. **Tooltip** (đúng về thiết kế, giữ lại): tái sử dụng **1 cửa sổ tooltip duy nhất** (không
   tạo/huỷ liên tục), **trì hoãn 450 ms** (chuẩn Windows), đóng cửa sổ tooltip khi app đóng.
2. **Thủ phạm thật — `CTkScrollbar._draw()`**: hàm này kết thúc bằng
   `self._canvas.update_idletasks()`. **`update_idletasks()` là lệnh Tk gốc → nó xả HẾT
   hàng đợi idle của TOÀN BỘ app**, chứ không chỉ thanh cuộn. Khi kéo/đổi kích thước cửa sổ,
   `<Configure>` bắn lên → canvas đổi "view" → gọi `yscrollcommand` → `CTkScrollbar.set()`
   → `_draw()` → `update_idletasks()` → **vẽ lại toàn bộ 851 widget** → UI tre **600–900 ms**
   ở **lần kéo đầu tiên** (các lần sau rẻ vì kích thước đã ổn định).
   → **Sửa: bỏ lệnh `update_idletasks()` khỏi `_draw()` của thanh cuộn** (hàm
   `_patch_scrollbar_khong_ep_ve_lai_ca_app()` trong `gui.py`). Thanh cuộn vẫn được vẽ lại bình
   thường ở vòng idle kế tiếp của Tk, nhưng **không còn ép vẽ lại cả app**.
   Kèm **khởi động ấm**: vẽ sẵn cây widget trước khi người dùng kéo lần đầu.

**KẾT QUẢ ĐO ĐƯỢC SAU KHI SỬA (coordinator tự chạy lại):**

| Số đo | Trước | Sau |
|---|---|---|
| **Lần kéo ĐẦU TIÊN — `max`** | **859 – 984 ms** | **19,4 ms** |
| Lần kéo đầu — số lần tre > 30 ms | 3 – 9 | **0** |
| Lần kéo đầu — `tb` / `p90` | — | 14,9 / 17,5 ms |
| Thời gian mở app (tới khi cửa sổ sẵn sàng) | 13,3 s | **12,5 s** (không chậm hơn) |
| CPU khi app đứng yên | 0 ms | 0 ms |

**Bài học:**
- Khi app "giật khi kéo cửa sổ", **đừng đoán** — hãy đo 4 thứ: (1) chi phí vẽ lại,
  (2) CPU idle, (3) **lần kéo thứ mấy** bị, (4) so với cửa sổ rỗng. Ở đây, nếu chỉ đo
  "lần kéo đầu" thì ra số 520–980 ms, nhưng nếu đo lần thứ 2 ra 20 ms → biết ngay đây là
  **chi phí khởi tạo hiển thị**, không phải lỗi kéo liên tục.
- **Thí nghiệm A/B phải đảo thứ tự hoặc lặp lại**: lần đo đầu tiên luôn bị "phí" này, nên
  so sánh "có sửa / không sửa" bằng 2 lần đo liên tiếp sẽ ra kết luận **sai**.
- Tooltip mà hiện **ngay lập tức** khi rê chuột vừa gây giật vừa phiền (Windows dùng
  delay ~500 ms). **Luôn có delay.**
- Đừng tạo/huỷ đối tượng native (cửa sổ) trong handler sự kiện tần suất cao — **tái sử dụng**.

---

## Dấu ✓ trong ô checkbox biến mất (ô xanh đặc) — CustomTkinter vẽ 2 lớp cùng 1 màu

**Triệu chứng:** sau khi thiết kế lại giao diện, **mọi ô checkbox đã tick hiện thành một ô
xanh đặc, không thấy dấu ✓** (xem ảnh `_kk_out/agent_g1/v3_cot_trai.png`).

**Nguyên nhân:** CustomTkinter 5.2.2 vẽ checkbox theo **2 lớp màu khác nhau**
(`windows/widgets/ctk_checkbox.py`, dòng 196–207):

```python
if self._check_state is True:
    self._canvas.itemconfig("inner_parts", outline=self._fg_color, fill=self._fg_color)
    self._canvas.itemconfig("border_parts", outline=self._fg_color, fill=self._fg_color)
    self._canvas.itemconfig("checkmark", fill=self._checkmark_color)
```

→ **ô** được tô bằng `fg_color`, **dấu ✓** được vẽ bằng `checkmark_color`.
Code đặt **cả hai** cùng là `MAU["nut"]` (xanh `#22C55E`) → dấu ✓ nằm trên nền cùng màu
→ **biến mất hoàn toàn**.

Ngoài ra đây là lỗi **accessibility**: ô tick chỉ khác nhau bằng màu, không có hình dạng để
nhận biết → người mù màu / màn hình xám không phân biệt được.

**Cách sửa (`VERSION` 3.4):**
- `fg_color = MAU["nut"]` (giữ — màu ô khi tick)
- `checkmark_color = MAU["nen"]` (#0F172A, tương phản **≈ 7,7:1** trên nền xanh → dấu ✓ rõ)
- `border_color = MAU["nut_phu"]`, `hover_color = MAU["nut_hover"]` (giữ)

Sửa ở **cả 2 chỗ** trong `gui.py`: lúc tạo checkbox (khoảng dòng 1360) và lúc gọi lại
style cho toàn bộ widget (khoảng dòng 2260).

**Bài học:** với CustomTkinter, `fg_color` **không** phải "màu chung" — nó là **màu riêng cho
từng lớp vẽ**. Đặt 2 tham số cùng giá trị là mất 1 lớp. Kiểm chứng bằng cách **chụp ảnh
phóng to 3×** chứ không tin nhìn bằng mắt ở kích thước nhỏ.

---

## Icon nút "DỪNG" trông như ô vuông rỗng (tưởng là thiếu glyph)

**Triệu chứng:** nút **DỪNG** hiện `▯ DỪNG` — hình vuông trông **giống hệt ô tofu** của
font bị thiếu ký tự (xem ảnh phóng 3× `_kk_out/agent_g1/_zoom_nut.png`).

**Nguyên nhân:** dùng icon **Stop = U+E71A** của Segoe MDL2 Assets — glyph này là **một hình
vuông đặc**. Cùng font đó, **Play = U+E768** là tam giác rỗng nên nhìn ra là "icon", còn hình
vuông đặc bị đọc nhầm là tofu.

**Cách sửa (`VERSION` 3.4):** đổi sang **Pause = U+E769** (hai thanh dọc) — vừa đúng nghĩa
"tạm dừng", vừa không giống ô vuông.

**Bài học:** chọn glyph có **hình dạng khác nhau rõ rệt** giữa các trạng thái (play/dừng/xong),
đừng dùng các hình "đặc" trông giống ô tofu. Và **luôn phóng to ảnh 3×** khi kiểm tra icon.

---

## Gọi Tk (đọc `StringVar`) từ thread nền → `main thread is not in main loop`

**Triệu chứng:** trong GUI, bấm nút **"Đăng ký người quen…"** → ảnh **được lưu thành
công** (nhật ký có `> Số ảnh đã lưu: 1`), nhưng ngay sau đó nhật ký hiện:

```
[LỖI] Lỗi khi đăng ký người quen: main thread is not in main loop
```

và **không** có dòng `> Đã học được: ...` → danh sách người quen **không được nạp lại**
trong GUI sau khi đăng ký.

**Nguyên nhân:** `_chay_dang_ky_nguoi_quen()` chạy ở **thread nền** (đúng thiết kế: nạp
model ArcFace mất vài giây, không được chặn UI) nhưng lại gọi
`self._nap_lai_danh_sach_nguoi_quen()`. Hàm đó đọc `self.v_faces_dir` — một
`tkinter.StringVar` → **gọi Tk từ thread KHÔNG phải thread chính** → Tcl ném
`RuntimeError: main thread is not in main loop`.

> Lưu ý: lỗi này **chỉ lộ ra khi bơm event loop bằng `app.update()`** (như trong script
> kiểm chứng). Khi app chạy thật với `mainloop()`, thông báo lỗi có thể không hiện —
> nhưng việc đọc biến Tk từ thread nền vẫn là **vi phạm luật của Tkinter** và có thể
> treo/crash ngẫu nhiên. **Không được coi là "chỉ lỗi script".**

**Cách sửa (`VERSION` 3.3):**

1. `_chay_dang_ky_nguoi_quen()` (thread nền) — **không** gọi hàm đọc Tk nữa, chỉ đẩy yêu
   cầu vào hàng đợi: `self.queue.put(("nap_lai_danh_sach", (faces_dir, threshold)))`.
   `faces_dir` và `threshold` **đã được đọc ở UI thread** và truyền vào từ đầu → thread
   nền **không chạm** vào biến Tk.
2. `_nap_lai_danh_sach_nguoi_quen(faces_dir=None, threshold=None)` — nhận 2 giá trị đó;
   khi có thì dùng thẳng, khi không thì mới đọc `self.v_faces_dir` (chỉ an toàn vì lúc
   này hàm chạy ở UI thread).
3. `_hut_hang_doi()` (UI thread) — thêm nhánh xử lý `"nap_lai_danh_sach"`.

**Kiểm chứng:**

| Bước | Kết quả |
|---|---|
| Chạy lại `_kk_kiem_gui_b3.py` (script của coordinator) | **4/4 PASS**, **không còn** dòng `main thread is not in main loop`, có lại dòng `> Đã học được: KiemThuV33` |
| **Kiểm chứng độ nhạy** (vô hiệu hóa fix rồi chạy lại) | Lỗi **tái hiện đúng y như trên** → bật lại fix → PASS. Test này BẮT ĐƯỢC lỗi thật, không phải lỗi script |
| Rà toàn bộ code v3.3 trong `gui.py` | Không còn chỗ nào khác gọi Tk từ thread nền. `self.dich()` an toàn vì `self.ngon_ngu` là thuộc tính Python thuần |

**Bài học (đã ghi vào mục 6 của `PROJECT_STATE.md`):**
- Trong Tkinter, **mọi** lời gọi widget/`StringVar` phải nằm ở **UI thread**.
- Việc nặng → thread nền → **chỉ** giao tiếp qua hàng đợi; giá trị cần đọc từ Tk thì
  **đọc ở UI thread rồi truyền vào**.
- `self.dich()` / thuộc tính Python thuần thì an toàn từ thread nền — nhưng đừng lẫn.

---

## Panel "Xem video" (lớn nhất của GUI) đen khi chạy phân tích theo lô

**Triệu chứng:** mở GUI → bấm **"Chạy"** trên 1 file video → panel lớn nhất bên giữa
("Xem video") **đen suốt**, không hiện khung hình nào, dù mọi thứ khác chạy đúng
(thanh tiến trình chạy, số liệu `2 Người / 2 Mặt / 2 Người quen` có giá trị, file
`.mp4` + `.csv` vẫn sinh ra).

**Nguyên nhân:** `run_analysis()` trong `cam_ai_core.py` chỉ có 2 callback:
`progress_cb` (tiến trình) và `log` (dòng log) — **không có callback khung hình**.
GUI chỉ đẩy `self.queue.put(("frame", buf.tobytes()))` ở chế độ **xem trực tiếp**.
Vì vậy ở chế độ phân tích theo lô không có gì đẩy vào `self.o_hinh` → panel đen.

**Kèm theo:** nút **"Tạm dừng"** (thuộc chế độ xem trực tiếp) vẫn hiện ở chế độ lô →
bấm vào **không có tác dụng** nhưng trông như có.

**Cách sửa (`VERSION` 3.2):**

1. `cam_ai_core.py` — thêm 2 tham số tuỳ chọn vào `run_analysis()`:
   `frame_cb: Callable[[bytes], None] | None = None` và `frame_cb_interval: float = 0.0`.
   Ngay sau `writer.write(frame)` thì encode JPEG (`IMWRITE_JPEG_QUALITY = 80`) rồi
   gọi `frame_cb`.
   - Khung hình gửi ra là **khung ĐÃ vẽ overlay** (khung người, nhãn tên, vùng canh,
     badge) → hiển thị **y hình pipeline**, khác với ảnh thô.
   - `frame_cb is None` → **không encode, chi phí = 0** → CLI không bị ảnh hưởng.
   - `frame_cb_interval > 0` → chỉ gửi **một khung sau mỗi khoảng giây** (giảm chi phí).
   - Callback **ném lỗi** → `try/except` bên trong, **không bao giờ làm chết pipeline**,
     chỉ báo lỗi **1 lần** (`bao_loi_gui_hinh`).
2. `gui.py` — hộp thư **1 ô** (`_khung_hinh_moi` + `threading.Lock` + `_khung_hinh_seq`)
   thay vì đẩy vào `self.queue`. Lý do: `self.queue` **không giới hạn**, đẩy khung
   hình vào đó sẽ **phình bộ nhớ** khi quét video dài (~100 KB/khung × hàng chục
   nghìn khung). Luồng UI đọc và xoá ô sau mỗi vòng `_hut_hang_doi()`.
3. `gui.py` — giới hạn **10 fps** (`KHOUNG_HINH_FPS = 10`).
4. `gui.py` — nút "Tạm dừng" **ẩn** ở chế độ lô (`_cap_nhat_nut_tam_dung_xem()`).

**Kiểm chứng (coordinator tự chạy + tự xem ảnh bằng mắt):**

| Bước | Kết quả |
|---|---|
| `_kk_kiem_gui_batch_preview.py` (GUI chế độ lô, `v_xem_video="0"`) | **PASS** — khung hình hiện lên panel **82 lần**; vùng panel đo được **118.735 màu đơn sắc**, sáng TB **73,95**, max 255 / min 0 → **KHÔNG đen** |
| Ảnh `v5_dang_chay.png` (coordinator tự mở xem) | Thấy khung hình thật + khung tím `Người 1..4`, khung xanh mặt với nhãn **An** / **Binh**, badge `Người: 4 \| Mặt: 2 \| Vào: 0 \| Ra: 0` |
| Vùng panel cắt riêng `v5_vung_khung_hinh.png` | Ảnh thật, **không có vùng đen nào** |
| Nút "Tạm dừng" trong chế độ lô | `hien_thi = False` (đã ẩn) |
| `_kk_kiem_gui_chay_thuc.py` (bộ e2e đầy đủ) | **7/7 PASS** (thêm mục [7] đo vùng panel) — video `h264,960,540`, CSV 251 dòng, 250 frame đọc được |
| Callback ném lỗi | Pipeline **vẫn chạy hết 250 khung**, không chết |

**Bài học:** đo bằng **công cụ** thôi chưa đủ — lần đo đầu của coordinator báo
"callback 0 lần" là do **lỗi của script đo** (truyền `lambda j: None` thay vì hàm
đếm), không phải lỗi app. Đã sửa script và đo lại. Và phải **tự mở ảnh xem bằng mắt**
thì mới tin được "panel không còn đen".

---

## App chết ngay khi chạy từ thư mục khác thư mục dự án — "không thấy bộ model ArcFace"

**Triệu chứng:** chạy `app.py` với thư mục đang chạy (CWD) khác thư mục gốc dự án →
**exit 1** ngay khi khởi động:

```
[loi] khong thay bo model ArcFace.
```

…dù `models/face_core/` **có đủ** `det_10g.onnx`, `w600k_r50.onnx`, `genderage.onnx` trên đĩa.

**Cách tái hiện (coordinator tự chạy):**

```powershell
$code = "import os,sys,runpy; sys.path.insert(0, r'H:\AI Project\cam-ai'); os.chdir(r'C:\Windows'); sys.argv=['app.py','--input',r'H:\AI Project\cam-ai\video_test.mp4','--output',r'...']; runpy.run_path(r'H:\AI Project\cam-ai\app.py', run_name='__main__')"
& 'H:\AI Project\cam-ai\.venv\Scripts\python.exe' -W ignore -c $code
```

**Nguyên nhân:** `face_engine.py` có

```python
MODEL_DIRS = ("models/face_core", "models/buffalo_l")
```

và `resolve_model_dir()` kiểm tra bằng `os.path.isdir(path)` → **theo CWD**.
Cùng kiểu lỗi với `known_faces`, `yolo11n.pt`, `vung.txt` (trong `dang_ky_anh.py`,
`ve_vung.py`).

**Đây là lỗi nghiêm trọng về mặt sản phẩm:** người dùng Windows **rất dễ** chạy
`app.py` bằng cách double-click từ Explorer, bằng shortcut, hoặc từ service/CI —
lúc đó CWD không phải thư mục dự án và **app chết ngay**, dù cài đặt hoàn toàn đúng.

**Cách sửa (`VERSION` 3.1):** thêm file mới **`duong_dan.py`** làm nguồn sự thật duy nhất
cho đường dẫn:

- `APP_DIR` = thư mục gốc dự án, **không phụ thuộc CWD**.
- `chuan_hoa_duong_dan(path)`: tuyệt đối → giữ nguyên; tương đối → ưu tiên bản trong
  CWD, không có thì bản trong `APP_DIR`, không có ở đâu cả thì **giữ nguyên** (để lỗi
  báo đúng chỗ người dùng trỏ tới, **không tự bịa đường dẫn**).
- `face_engine.py`: `MODEL_DIRS` thành tuyệt đối theo `APP_DIR`; `resolve_model_dir()`
  **in ra các đường dẫn đã thử** khi không tìm thấy.
- `app.py` / `cam_ai_core.py` / `dang_ky_anh.py` / `ve_vung.py` / `model_info.py` /
  `gui.py`: dùng chung `APP_DIR`.

**Kiểm chứng:** CWD = `C:\Windows` **có nhận diện mặt** → **EXIT=0**,
`[model] H:\AI Project\cam-ai\models\face_core | GPU | detection:CUDA | genderage:CUDA |
recognition:CUDA`, CSV 250 dòng, cột `nguoi_quen` = **"An | Binh"**.

**Bài học:** mọi đường dẫn **mặc định** của ứng dụng phải phân giải theo thư mục gốc
dự án, không theo CWD. Đường dẫn người dùng gõ tay thì giữ nguyên ý định.

---

## App không tự tạo thư mục output → lỗi "không gia duoc file video ket qua"

**Triệu chứng:** `--output` trỏ vào thư mục **chưa tồn tại** →

```
[loi] khong gia duoc file video ket qua: ...\A16_encoding\ket_qua_ket_qua.mp4
```

Thông báo **không nói** rằng nguyên nhân là thiếu thư mục → người dùng tưởng lỗi codec
hoặc lỗi quyền ghi.

**Nguyên nhân:** `cv2.VideoWriter` **không tự tạo thư mục cha**.

**Cách sửa (`VERSION` 3.1):** `cam_ai_core.py` thêm `tao_thu_muc_cha()`; gọi **trước** khi
mở `VideoWriter` và **trước** khi ghi CSV; lỗi writer/CSV giờ **nêu rõ thư mục cha**
và bọc trong `CamAIError` có thông điệp rõ ràng.

**Kiểm chứng:** CWD = `C:\Windows` + thư mục output chưa tồn tại → **EXIT=0**, thư mục
được tạo, có cả `.mp4` (16.226.963 B) + `.csv`.

---

## `--tu-luu-clip` cùng thư mục với video kết quả → MẤT video kết quả nhưng exit 0

**Triệu chứng:** chạy `--tu-luu-clip DIR` mà `DIR` **trùng** thư mục ghi video kết quả:

```
[clip] da don 1 file .part.mp4 con sot lai
...
[video] ⚠ không ghi được video kết quả, xem ...\k_ket_qua.part.mp4
```

**Exit code vẫn 0** nhưng **file video kết quả không tồn tại** → người dùng tưởng app
chạy xong nhưng không có kết quả, không có cảnh báo lỗi.

**Nguyên nhân:** `don_file_tam_trong_thu_muc()` xoá **mọi** `*.part.mp4` trong thư mục,
kể cả file tạm của video kết quả đang được `VideoWriter` giữ. Vòng dọn này chạy
**trước** khi pipeline ghi frame đầu tiên.

**Cách sửa (`VERSION` 3.1):**

1. Tham số mới `giu=(...)` trong `don_file_tam_trong_thu_muc()` — danh sách đường dẫn
   tuyệt đối **không được xoá**; so sánh bằng `os.path.abspath` + `os.path.normcase`
   (Windows không phân biệt hoa/thường). Call site truyền `giu=(out_path_tam,)`.
2. **Lớp bảo vệ thứ hai:** registry `_FILE_DANG_GHI` — mọi `VideoWriter` đang ghi trong
   tiến trình đều đăng ký file `.part.mp4` của mình (`dang_ghi_file()` / `ngung_ghi_file()`),
   nên **không cleanup path nào** xoá được file đang được ghi, kể cả khi sau này có
   chỗ gọi mới quên truyền `giu`.
3. Vòng dọn bọc `try/except` từng file (trước đó **1 file xoá lỗi làm hỏng cả vòng dọn**).

**Kiểm chứng:** chạy lại B3 (CWD = `C:\Windows`) → file rác `rac_gi_20250101.part.mp4`
**bị xoá** (`[clip] da don 1 file .part.mp4 con sot lai`) **và** `ket_qua_ket_qua.mp4`
**16.253.729 B vẫn còn**, `ffprobe` → `h264,960,540`.

**Bài học:** mọi thao tác dọn file trong thư mục dùng chung phải **loại trừ** file đang
được ghi. Và một lỗi làm mất dữ liệu mà **vẫn exit 0** là loại lỗi nguy hiểm nhất —
người dùng không bao giờ biết mất gì.

---

## Video kết quả dùng codec MPEG-4 Part 2 → trình duyệt báo "Unable to play media"

**Triệu chứng:** báo cáo HTML xem lại (`*_xem_lai.html`) mở bằng trình duyệt thật thì
thẻ `<video>` hiện **"Unable to play media."**, **mọi nút điều khiển bị `disabled: true`**,
thanh tua hiện **"total time: 0:00"** → trình duyệt **không đọc được** file video.

**Đo thật (coordinator tự chạy `ffprobe` trên file cũ):**

| File | `codec_name` | Profile | Kích thước | Thời lượng | Trình duyệt |
|---|---|---|---|---|---|
| `one-by-one-person-detection_ket_qua.mp4` | **mpeg4** | Simple Profile | 768×432 | 9,998 s | **không phát được** |

`codec_name=mpeg4` + profile `Simple Profile` = **MPEG-4 Part 2** (MPEG-4 Visual),
**KHÔNG phải H.264**. Chrome/Edge/Firefox **không có decoder** cho codec này (chỉ
VLC/QuickTime phát được) → đây là lỗi thật, không phải lỗi đường dẫn hay lỗi trình duyệt.

**Nguyên nhân:** `cam_ai_core.py` ghi video bằng fourcc cố định `mp4v`
(`FOURCC_KET_QUA = "mp4v"`), mà `mp4v` chính là MPEG-4 Part 2.

**Đã sửa (2026-10-19):**
- Hàm mới `_fourcc_ket_qua()` trong `cam_ai_core.py` — **probe 1 lần cho cả tiến trình,
  kết quả được cache**:
  1. Ghi 1 file `.mp4` tạm (2 khung hình 64×64 màu đen) bằng fourcc `avc1`.
  2. Đọc **4096 byte đầu** file, tìm chuỗi `b"avc1"` (fourcc thật nằm trong box `stsd`).
  3. Nếu chưa thấy → đọc **64 KB cuối** file (box `moov` chứa `stsd` có thể nằm cuối).
  4. Có `avc1` → dùng **`avc1` (H.264)**; không có → lùi về `mp4v`.
  5. **Mọi lỗi → lùi về `mp4v`** (fail-safe tuyệt đối, không bao giờ làm hỏng pipeline).
  File probe **luôn được xoá** (thử tối đa 5 lần vì Windows có lúc khoá file tạm).
- Hằng `FOURCC_KET_QUA = "mp4v"` **giữ nguyên giá trị** để không phá chỗ khác đang
  import nó; giá trị này giờ chỉ là **phương án dự phòng**.
- Cả **video kết quả** lẫn **clip tự lưu** đều dùng codec đã chọn, và log ra rõ:
  `[video] codec: H.264 (avc1) - trình duyệt phát được video`
  (khi lùi về `mp4v` thì log: `[video] codec: MPEG-4 Part 2 (mp4v) - máy này không có
  encoder H.264`).

**Đo thật sau khi sửa (coordinator tự chạy, không tin báo cáo subagent):**

| Kiểm tra | Kết quả |
|---|---|
| `app.py --input video_test.mp4 --no-face --output ...` | log ra `[video] codec: H.264 (avc1) ...`, **exit 0** |
| `ffprobe` file mới | **`codec_name=h264`**, 960×540, duration **10,0 s** |
| `ffmpeg -i <file> -f null -` | **exit 0** (decode sạch, không lỗi) |
| Mở HTML xem lại bằng **browser thật** | `<video>` **không còn "Unable to play media."**, controls **không còn disabled**, scrubber **"total time: 0:10"** (metadata load thành công) |
| Console trình duyệt (mức `error` + `warn`) | **0 entries** |

**Bài học (cross-project):**
- **"File video tồn tại" ≠ "trình duyệt phát được".** Phải kiểm tra `codec_name` bằng
  `ffprobe`, không suy ra từ dung lượng file.
- **Mở bằng trình duyệt thật, đừng tin vào phỏng đoán.** Lỗi này chỉ lộ ra khi mở
  thẻ `<video>` thật; đọc code thì thấy "có ghi video" và tưởng đã xong.
- **Encoder có thể in log đỏ mà file vẫn hợp lệ.** OpenCV 5.0.0 (FFmpeg prebuilt,
  avcodec 61.19.100) in đỏ *"Failed to load OpenH264 library"* khi ghi `avc1`, nhưng
  file ra **vẫn là H.264 hợp lệ** → phải kiểm chứng bằng `ffprobe` + trình duyệt,
  **không kết luận theo stderr**.
- **Chọn codec bằng probe runtime có cache, không hardcode.** Máy khác có thể thiếu
  encoder H.264 → phải có đường lùi an toàn, và phải **log ra codec đang dùng** để
  lần sau biết ngay mà không cần mở file.

---

## 6 ảnh "tự chụp sự kiện" cũ là ẢNH ĐEN và thuộc prototype cũ — không phải bằng chứng

**Triệu chứng:** khi rà lại bằng chứng tính năng `--tu-chup`, thấy thư mục
`_kk_out/ocr_thu/su_kien/` có 6 file ảnh tên
`su_kien_2026*_vua_toi.jpg` / `su_kien_2026*_vuot_vung.jpg` (mỗi file 5.427 B).
Có nơi đã ghi chúng là "bằng chứng tự chụp ảnh chạy thật" — **SAI**.

**Đo thật (coordinator tự chạy, đọc pixel thật):**

| File | Số màu đơn sắc | max | min | Nhận định |
|---|---|---|---|---|
| 6 file `su_kien_2026*_vua_toi/vuot_vung.jpg` | **1** | **0** | **0** | **ẢNH ĐEN HOÀN TOÀN** |

**Nguyên nhân (2 tầng, đều làm cho bằng chứng vô giá trị):**
1. Ảnh **đen trắng** → không phải ảnh camera thật, không phải khung đã vẽ overlay.
2. Tên sự kiện `vua_toi` / `vuot_vung` **không tồn tại** trong hằng số `LOAI_SU_KIEN`
   của `tu_chup.py` hiện tại
   (`vuot_nguong_dong`, `nguoi_quen`, `vao_vung`, `dung_lau`, `co_nguoi`, `bien_so`).
   → Đây là artifact từ **prototype cũ** (đã bị thay), không phải output của code đang chạy.

**Đã sửa / xử lý:**
- Chạy lại **code hiện tại** để tạo bằng chứng thật:
  ```powershell
  .venv\Scripts\python.exe -W ignore app.py --input video_test.mp4 --vung vung.txt --tu-chup --tu-chup-dir _kk_out\tu_chup_thuc_te
  ```
  → `su_kien_20261019_220301_vao_vung_nguoi1.jpg` (**157.074 B**, 960×540, **33.985 màu**,
  trung bình BGR `[114.5, 114.6, 115.2]`), kèm `_bang_ke_chup.csv` (209 B) ghi đúng
  `loai_su_kien=vao_vung`, `ten_hien_thi=Có người vào vùng canh`, `so_nguoi=1`.
- **Coordinator tự xem ảnh bằng mắt**: thấy rõ 2 người với overlay tiếng Việt có dấu
  **"An | Nam 67"** và **"Binh | Nam 52"** → tính năng tự chụp ảnh **chạy legit**.
- Đã ghi cảnh báo vào `PROJECT_STATE.md` mục 2.1d (khối ⚠️) để không ai dùng nhầm 6 ảnh đen.

**Bài học (cross-project):**
- **File ảnh nhỏ bất thường là dấu hiệu ảnh rỗng.** 5,4 KB với 1 màu đơn sắc → ảnh đen.
  Mọi lần nhận bằng chứng ảnh phải **đo số màu đơn sắc + max/min pixel**, không chỉ nhìn
  kích thước file.
- **Tên sự kiện trong tên file phải khớp hằng số trong code** — không khớp ⇒ artifact của
  phiên bản cũ ⇒ không được dùng làm bằng chứng.
- Artifact cũ trong `_kk_out/` **không tự động là bằng chứng**; phải truy nguồn lại từ code
  hiện tại trước khi kết luận tính năng "đã đạt".

**Ghi chú thêm:** chạy `--tu-chup` **không có vùng canh** thì exit 0 nhưng **không tạo file nào**
(đúng thiết kế: không có sự kiện thì không chụp). Muốn có ảnh thì phải có `--vung`.

---

## OCR biển số làm khựng toàn bộ pipeline — 1,9 giây mỗi khung hình

**Triệu chứng:** bật đọc biển số thì video quét **tụt fps** từ 26 fps xuống dưới 1 fps.
Đo thật trên `video_test.mp4` (250 khung): pha **tìm vùng biển** trong cả khung hình tốn
**1916,6 ms/khung** (không ROI) và **680,9 ms/khung** (có ROI) — tức là **nghìn lần**
nặng hơn phần đọc crop.

**Nguyên nhân:** `BoDocBienSo.doc()` chạy **đồng bộ** ngay trên luồng phân tích. Bên
trong nó gọi engine RapidOCR **có tìm chữ** (`det+cls+rec`) để quét cả khung hình
640×480 tìm mảnh chữ giống biển số. Mỗi lần gọi là **hàng trăm mili giây đến hơn
1 giây** → mỗi khung hình phải chờ.

**Đã sửa (2026-10-19, agent D sửa `bien_so.py`):**
- Chuyển pha **tìm vùng** sang **luồng nền daemon** (ghim `BELOW_NORMAL`, giới hạn
  2 core) → luồng chính không chờ.
- Thêm **cache vùng** theo toạ độ tương đối, TTL 10 giây → không tìm lại mỗi khung.
- Thêm **hạn chi phí 50 ms** cho 1 lượt OCR, **giới hạn 8 lượt OCR** mỗi lần quét,
  **giới hạn diện tích vùng 250.000 px** (vùng rộng >60.000 px → tìm nền).
- `threading.Lock` quanh **từng** engine OCR (RapidOCR không thread-safe).

**Đo thật lại (coordinator tự chạy, `_kk_do_chi_phi_doc_bien_so.py`, 250 khung):**

| Chế độ | Trước | Sau (tb/khung) | Sau (chậm nhất) |
|---|---|---|---|
| Có ROI | 680,9 ms | **5,2 ms** | **0,9 ms** |
| Không ROI | 1916,6 ms | **7,5 ms** | **1,5 ms** |

**Đánh đổi còn lại (phải biết):**
- Cache vùng có thể **bỏ sót biển mới** cho tới lượt quét kế tiếp (~2 s).
- Vùng tìm được là khung **CHỮ** → biển **2 hàng** có thể ghép sai thứ tự.
- ROI rộng có độ trễ 0,5–1,5 s lúc đầu.
- Hạn chi phí 50 ms có thể cắt trường hợp biển 2 hàng (đo thật ~54 ms).

---

## Ô gợi ý trong ô nhập không hiện — "để trống = tự tìm trong khung"

**Triệu chứng:** ô "Vùng cần quét" và ô "Danh sách lớp cần nhận" **không hiện** dòng
gợi ý khi để trống. Người dùng không biết để trống nghĩa là gì.

**Nguyên nhân (không phải lỗi theme):** `customtkinter 5.2.2` chỉ kích hoạt
placeholder khi `textvariable is None or textvariable == ""`. Mà `tkinter.StringVar`
**không định nghĩa `__eq__`** → so sánh với `""` luôn False → **mọi** `CTkEntry` có
`textvariable` **không bao giờ** hiện placeholder. Đây là hành vi của thư viện, không
phải lỗi code của dự án.

**Cách sửa sai đã thử:** chèn chu placeholder vào ô bằng `insert()` → bị customtkinter
từ chối, biến `textvariable` bị nhiễu thành `"HUONG DAN GIUONGab"`.

**Đã sửa (2026-10-19):** lớp mới `GoiYTronO` trong `gui.py` — 1 `CTkLabel` phủ lên
ô, `textvariable` luôn sạch, tự ẩn/hiện theo biến, kèm tooltip `HuongDan`.

**Ba lỗi con phát sinh khi làm nhãn phủ (đều đã sửa):**
1. **Nền lệch màu.** `entry.cget("fg_color")` lúc tạo nhãn trả bảng màu theme **cũ**
   `['#F9F9FA','#343638']` vì bước `_ap_dung_theme()` gán `MAU["the_phu"]` cho mọi
   `CTkEntry` **sau khi** form đã dựng → nền lệch `#343638` vs `#272F42`, thấy rõ
   bằng mắt. Sửa: lấy màu từ **bảng màu dự án** `MAU["the_phu"]`.
2. **`place(width=..., height=...)` raise `ValueError`** — `customtkinter 5.2.2` không
   cho truyền kích thước vào `place()`. Sửa: đưa `height=24` vào constructor.
3. **Chữ bị cắt ở đáy.** `anchor="w"` canh giữa trục y tại y=0 → lệch −14 px. Sửa:
   `anchor="nw"` + `place(x=12, y=2)`.

**Gợi ý phải NGẮN** vì ô chỉ rộng 102 px: "để trống = tự tìm trong khung" rộng 159 px
→ không vừa. Dùng "tự tìm" (31 px) và "mặc định" (49 px); giải thích đầy đủ nằm ở
ghi chú dưới ô + tooltip.

**Đo thật:** chữ hiện đầy đủ, nền khớp tuyệt đối `#272F42`, viền trắng của ô liền
mạch, không che viền. Ảnh: `_kk_out/v3_20_goi_y_hien.png`, `v3_30_goi_y_mac_dinh.png`,
`v3_31_goi_y_tu_tim.png`, `zoom_v3_20_goi_y.png`, `zoom_v3_30_mac_dinh.png`.

---

## OCR biển số: dùng nhầm engine → chậm ~100 lần

**Triệu chứng:** đọc 1 crop biển số mất **320–1473 ms**. Quét video có biển số
sẽ tự động tụt FPS.

**Nguyên nhân:** `BoDocBienSo.nap()` dùng `RapidOCR()` — bản **có tìm chữ (det+cls+rec)**.
Nhưng khi crop biển số **đã định vị sẵn** thì không cần tìm chữ, chỉ cần đọc.

**Đã sửa (2026-10-19):** tách làm **2 engine riêng** trong `bien_so.py`:
- engine **chỉ đọc**: `RapidOCR(use_text_det=False, use_angle_cls=False)` → dùng cho
  crop đã định vị (nhanh **5–10.5 ms/crop**).
- engine **có tìm chữ**: dùng để **tìm vùng biển** trong cả khung hình.

**Gotcha API (rất dễ sai):** RapidOCR 1.2.3 **bỏ qua tham số `use_det` lúc gọi**,
tham số này chỉ có tác dụng **lúc khởi tạo**. Nên phải tạo 2 đối tượng riêng, không
dùng chung 1 engine rồi đổi cờ.

**Đo thật** (`_kiem_chung/so_2_kieu_ocr.txt`): 1473 ms (có tìm chữ) → **10.5 ms**
(chỉ đọc). Ngoài ra engine bỏ qua ảnh có `h <= 30` hoặc `w/h > 8`.

**Bài học:** con số "9.4 ms/ảnh" từng được báo trước đó là của engine **chỉ đọc**;
pipeline cũ dùng engine **có tìm chữ** nên thực tế là **1–5 giây/crop**. Số đo phải
đo trên **đúng đường code sản phẩm**, không đo trên một biến thể lý tưởng.

---

## `chuan_hoa_bien_so` BỊA biển số nước ngoài thành biển Việt Nam

**Triệu chứng:** biển Đức `"MS WL 345"` bị trả về **`"50W-1345"`** — hợp lệ về
hình thức biển Việt Nam, nhưng là **bịa**. Lưu xuống sẽ ghi sai biển nước ngoài
thành biển VN trong báo cáo.

**Nguyên nhân:** `_sua_theo_vi_tri` quá lỏng lẻo — tự chế thêm ký tự để " ép cho
khớp mẫu" thay vì loại bỏ ký tự lạ.

**Đã sửa (2026-10-19):** quy tắc mới — **tuyệt đối không thêm/bịa ký tự**:
- chỉ **loại bỏ** ký tự lạ (không phải chữ/số/dấu gạch),
- viết hoa,
- thêm dấu gạch giữa 2 hàng,
- sửa `O/I/L` **chỉ tại vị trí bắt buộc** và **chỉ khi phần còn lại khớp mẫu**,
- mẫu VN khớp chặt `^\d{2}[A-Z]\d{4}$` và `^\d{2}[A-Z]\d{5}$`.

**Đo thật** (`_kiem_chung/kiem_bien_so_gia.txt`): 10/10 ảnh biển số VN (ảnh giá)
đọc đúng, **không ảnh nào bị thêm ký tự** (chuỗi chuẩn hoá luôn là tập con của chuỗi
gốc sau khi bỏ ký tự lạ).

---

## OCR biển số: ảnh xoay nhẹ (~6°) bị bỏ qua hoàn toàn

**Triệu chứng:** biển số xoay ~6° (rất phổ biến với camera gắn lệch) → OCR
**không trả về gì dù chữ rõ nét**.

**Nguyên nhân:** OCR không tự deskew; chữ xiên vượt ngưỡng nhận dạng của model.

**Đã sửa (2026-10-19):** khi OCR thất bại trên 1 crop → **thử lại với các góc xoay
±3°, ±6°, ±9°** (`cv2.getRotationMatrix2D` + `warpAffine`, bỏ viền trắng, không cắt
mất chữ). Chỉ thử khi thất bại — **không xoay luôn** (để không làm hỏng 10/10 ảnh
đang đúng).

**Đo thật:** ảnh xoay 6° chuyển từ `KHONG DOC DUOC` → `PASS doc='30A-12345'`.
Kết quả chung: **10/10** ảnh biển số VN giá đọc đúng.

---

## GUI: ô "Thư mục lưu ảnh" cắt mất đường dẫn

**Triệu chứng:** ô nhập thư mục hiển thị `H:\AI Project\cam-ai\anh` — cắt giữa
chừng, không có dấu `…` và không có tooltip.

**Đã sửa (2026-10-19):** thêm tooltip hiện đường dẫn đầy đủ khi rê chuột vào ô.

**Bằng chứng:** `_kk_out/zoom_thu_muc.png` (trước) và `_kk_out/zoom_thu_muc_fix.png` (sau).

---

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
