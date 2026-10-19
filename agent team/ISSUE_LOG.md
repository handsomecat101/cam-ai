# ISSUE_LOG — CamAI · Lỗi đã gặp và cách tránh lặp lại

> Mỗi mục ghi: **Triệu chứng → Nguyên nhân thật → Đã sửa → Cách tránh lặp**.
> Ngày kiểm tra lại toàn bộ: **18/10/2026**.

---

## #1 · Bug "đứng lâu" in đúng bằng ngưỡng

**Triệu chứng**
Chạy `--canh-lau 3` thì dòng `Nguoi dung lao nhat` **luôn ra `3.0s`**.
Đổi `--canh-lau 10` thì ra `10.0s`. Con số luôn **bằng ngưỡng**, không bao giờ khác.

**Nguyên nhân thật**
Code chụp thời điểm **lần đầu vượt ngưỡng** rồi ghi luôn giá trị ngưỡng đó vào biến
`longest_loiter`. Nó **không đo** thời gian thật khi người đó rời vùng.

Hệ quả: biến tên nghe có vẻ là "thời gian đứng lâu nhất" nhưng thật ra là
"ngưỡng bạn gõ vào". Báo cáo cho anh là sai hoàn toàn.

**Đã sửa**
`cam_ai_core.py:635-636` — gán `longest_loiter = held` ngay trong vòng lặp.
`held = now - entered_at[tid]` là thời gian đo liên tục từ lúc người đó vào vùng.
Comment ngay tại dòng 634 ghi rõ: *"do tu luc vao vung - khong phai ban bang nguong"*.

**Kiểm chứng**
```
Dung lau hon 3.0s: 1 lan, lan dai nhat 10.0s
Nguoi dung lao nhat: 10.0s
```
`10.0s` là thời gian thật (video dài đúng 10s, người đó ở trong vùng suốt video),
**không còn bằng ngưỡng 3.0**.

**Cách tránh lặp**
- Muốn đo thời gian thì phải lấy `now - thời_điểm_bắt_đầu`, **không bao giờ lấy lại ngưỡng cấu hình**.
- `CHANGELOG.md` mục v2.1 vẫn còn dòng "đứng lâu 1 lần (3.0s)" — đó chính là bằng chứng bug.
  Đừng xoá, đó là tài liệu tham chiếu.
- Dạng bug này rất dễ quay lại: **test bằng 2 ngưỡng khác nhau**, nếu kết quả đổi y hệt
  theo ngưỡng thì đã lặp lại bug.

---

## #2 · Dự án KHÔNG có git — câu lệnh cứu file là `git checkout`

**Triệu chứng**
Sau khi PowerShell làm hỏng file nguồn, có thông tin khuyên "cứu bằng `git checkout -- <file>`".
Chạy thì báo lỗi vì **thư mục này không phải git repo**.

**Nguyên nhân thật**
Đã kiểm tra ngày 18/10/2026: `H:\AI Project\cam-ai` **KHÔNG có thư mục `.git`**.
Project chưa bao giờ được `git init`, hoặc đã bị mất `.git` lúc sao chép ổ đĩa.

**Đã sửa**
Không có cách nào "checkout" lại. Cách khôi phục thật:
dùng tool `edit` / `write` viết lại đúng nội dung UTF-8, dựa từ `PROJECT_STATE.md` mục 3 và mục 6.

**Cách tránh lặp**
- **Luôn soát bản sao trước khi sửa file lớn**: copy ra `.bak` bằng `Copy-Item`, sửa xong thì xoá.
- Đừng tin bất kỳ lời khuyên nào nói "dùng git cứu" khi làm việc trong dự án này.
- Nếu muốn có git: `cd 'H:\AI Project\cam-ai'; git init` — nhưng **cần chủ sở hữu đồng ý**,
  và phải `.gitignore` loại `.venv/` (rất lớn) và các file video kết quả.

---

## #3 · PowerShell 5.1 phá file nguồn — hỏng 3 thứ cùng lúc

**Triệu chứng**
Sau khi dùng `Get-Content ... | Set-Content` để "sửa nhanh" một file `.py`:
1. Đầu file xuất hiện ký tự lạ (`ï»¿`) — do **BOM** bị chèn
2. Tiếng Việt hỏng: `Anh Tuấn` → `Anh Tuáº¥n` — do **sai encoding**
3. File đổi từ xuống dòng CRLF sang LF (hoặc ngược lại)

**Nguyên nhân thật**
PowerShell 5.1 mặc định:
- Đọc file UTF-8 bằng **cp1252** → hiểu sai dấu tiếng Việt, rồi ghi lại byte đã hiểu sai
- `-Encoding UTF8` của 5.1 **có ghi BOM**
- Ghi ra bằng ký tự xuống dòng của hệ thống, không giữ kiểu cũ

Ba lỗi này **luôn đi kèm nhau** trong 1 thao tác. Không thể chọn chỉ 1.

**Đã sửa**
Dựng lại file bằng tool `write` / `edit`, kiểm tra byte sau khi ghi.

**Cách tránh lặp**
- **TUYỆT ĐỐI KHÔNG** dùng `Get-Content | Set-Content` để sửa file nguồn.
  Chỉ dùng nó để **đọc** (và phải kèm `-Encoding UTF8`).
- Muốn kiểm tra file có bị hỏng không, dùng đo byte thay vì đọc mắt:

```powershell
$b=[System.IO.File]::ReadAllBytes('ten_file.py')
$bom=($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
$t=[System.Text.Encoding]::UTF8.GetString($b)
"bytes=$($b.Length) BOM=$bom CRLF=$(([regex]::Matches($t,"`r`n")).Count) LF=$(([regex]::Matches($t,"`n")).Count)"
```

- Quy tắc đúng của dự án này: **UTF-8, KHÔNG BOM, xuống dòng LF**.
  (Đã đo byte thật ngày 18/10/2026 trên cả file `.py` và `.md` — toàn bộ đều LF, không BOM.)
- Ngoại lệ duy nhất: file CSV do `cam_ai_core.py` ghi bằng `utf-8-sig` (**có BOM**) — cố ý để Excel đọc tiếng Việt.

---

## #4 · insightface im lặng rơi về CPU (3 bẫy)

**Triệu chứng**
Code đã truyền đúng `CUDAExecutionProvider` nhưng phần mềm vẫn chạy chậm.
In ra thấy `[model] ... | CPU |` thay vì `GPU`. **Không có lỗi, không có cảnh báo** —
chỉ chậm hơn 5,8 lần nên nhiều khi không ai nhận ra.

**Nguyên nhân thật — 3 bẫy riêng biệt**

| # | Bẫy | Sửa | Chỗ |
|---|---|---|---|
| 1 | `prepare(ctx_id=-1)` — insightface 2.1 **ép CPU** | Phải `prepare(ctx_id=0)` | `face_engine.py:131` |
| 2 | Nạp DLL CUDA của torch **sau** khi onnxruntime đã import | Nạp **trước** → `_enable_cuda()` chạy lúc import module | `face_engine.py:36-67` |
| 3 | Truyền `provider_options={}` | Phải `None` (hoặc không truyền) | Xem ghi chú bên dưới |

**Đo thật trên RTX 3090:**

| Cách | Tốc độ |
|---|---|
| `ctx_id=-1` (CPU) | 226 ms/khung hình |
| `ctx_id=0` (CUDA) | **39 ms/khung hình** |

Nhanh gấp **5,8 lần**.

**Ghi chú về bẫy số 3:** `CHANGELOG.md` mục v2.0 có ghi
*"`provider_options={}` rỗng cũng làm GPU rơi về CPU — phải truyền `None`"*.
Nhưng **code hiện tại không truyền `provider_options` cho `FaceAnalysis` nữa**
(`face_engine.py:126-130` chỉ truyền `providers`) — tức là đang tương đương `None`.
Bẫy này đã được xử lý bằng cách **bỏ hẳn tham số**, chứ không phải truyền `None` tường minh.

**Đã sửa**
`face_engine.py:36-67` — hàm `_enable_cuda()` nạp `torch/lib` vào `PATH` và
gọi `torch.zeros(1, device="cuda")` để nạp CUDA runtime vào tiến trình **trước khi**
insightface/onnxruntime được import.

**Cách tránh lặp**
- Kiểm tra dòng `[model]` in ra. Chữ `GPU` + `CUDA` là đúng. Thấy `CPU` là rơi CPU.
- ⚠️ `cam_ai_core.py:441` **cố ý** import `face_engine` **bên trong hàm**, không ở đầu file.
  Comment ở `cam_ai_core.py:443-445` giải thích: chuyển import lên đầu sẽ làm GPU chạy sai.
  **Đừng "tối ưu" chỗ này.**
- Hai cảnh báo sau là **vô hại**, bỏ qua được:
  ```
  FutureWarning: estimate is deprecated
  Skip loading CUDA and cuDNN DLLs since torch is imported.
  ```

---

## #5 · `onnxruntime-gpu==1.20.1` không tồn tại trên PyPI

**Triệu chứng**
Cài theo hướng dẫn cũ, `pip` báo không tìm thấy phiên bản `1.20.1` cho `onnxruntime-gpu`.

**Nguyên nhân thật**
Bản `onnxruntime-gpu` **không có** bản 1.20.1 trên PyPI (đường phát hành GPU tách riêng và
đánh số khác). Bản phải dùng cho môi trường này là **1.23.2**.

**Đã sửa**
`requirements.txt` ghim `onnxruntime-gpu==1.23.2`. Đã cài và chạy được.

**Cách tránh lặp**
- Trước khi cài bất cứ thứ gì, kiểm tra `requirements.txt` đã có chưa.
- **Không được `pip install` thêm bất cứ thứ gì.** Cấm cài `basicsr`, `realesrgan`, `torchreid`
  — chúng kéo NumPy/ABI cũ về và phá Python 3.13 + NumPy 2.5.4.
- Ưu tiên thứ máy đã có sẵn (6 tracker của ultralytics, `PolygonZone`, `CLAHE`).

---

## #6 · `chay_gui.bat` để lại cửa sổ console đen

**Triệu chứng**
Anh double-click `chay_gui.bat`, giao diện mở được, nhưng **phía sau còn một cửa sổ
console đen** phải đóng tay.

**Nguyên nhân thật**
`chay_gui.bat:17` gọi `.venv\Scripts\python.exe gui.py`.
Bản `python.exe` **luôn in ra cửa sổ console**. Bản không in là `pythonw.exe`.

**Đã sửa**
⚠️ **CHƯA SỬA.** Chưa đổi vì `chay_gui.bat` không thuộc phạm vi công việc đang chạy.

**Cách sửa khi làm**
Đổi dòng gọi trong `chay_gui.bat` từ
`.venv\Scripts\python.exe gui.py` → `.venv\Scripts\pythonw.exe gui.py`

⚠️ Đánh đổi: `pythonw.exe` **không in lỗi ra console**. Nếu app lỗi sẽ im lặng —
phải xử lý bằng cách ghi log ra file thay vì in ra màn hình.
`gui.py` có sẵn cơ chế ghi log, có thể dùng lại.

---

## #7 · Không kéo-thả được file vào GUI

**Triệu chứng**
Anh quen dùng kéo-thả file video vào cửa sổ. GUI hiện tại **không kéo-thả được**,
phải bấm nút "Chọn video" rồi đi tìm file trong hộp thoại.

**Nguyên nhân thật**
Tkinter mặc định **không hỗ trợ kéo-thả**. Cần gói `tkinterdnd2`.
Gói này **không được cài** theo luật "không `pip install` thêm" (xem ISSUE_LOG #5).

**Đã sửa**
⚠️ **CHƯA SỬA — đây là quyết định có chủ đích, không phải lỗi.**
Dùng nút "Chọn video" làm phương án thay thế.

**Cách tránh lặp / hướng xử lý**
- Trước khi đề xuất cài thêm thư viện, hỏi: **nó có phá NumPy 2.5.4 / Python 3.13 không?**
- Nếu sau này anh vẫn muốn kéo-thả, đề xuất lại `tkinterdnd2` cho anh Tuấn quyết định,
  kèm cảnh báo rủi ro.

---

## #8 · Máy cài SONG SONG 2 gói onnxruntime (CPU 1.20.1 + GPU 1.23.2)

**Triệu chứng**
Chạy `model_info.py` in ra:
```
  onnxruntime          : 1.20.1
  onnxruntime-gpu      : 1.23.2
```
Nhưng dùng `onnxruntime.__version__` lại ra **1.23.2**.

**Chẩn đoán SAI đã từng ghi ở đây — và sự thật**
Bản cũ của mục này kết luận:
*"bản `onnxruntime-gpu` cài đè lên metadata của gói `onnxruntime`, còn sót metadata cũ (1.20.1)"*.

**Kết luận đó SAI.** `model_info.py` in **đúng cả hai dòng** vì máy **thật sự có 2 gói cài song song**,
không phải vì metadata bị đọc sai. Ai đọc lại mục cũ đừng tin.

**Số đo đã kiểm chứng (18/10/2026), chạy thật trên máy này:**

Lệnh:
```powershell
cd 'H:\AI Project\cam-ai'
.venv\Scripts\python.exe -c "import importlib.metadata as m, onnxruntime, os; print('module:', os.path.dirname(onnxruntime.__file__)); [print(p, m.distribution(p)._path) for p in ['onnxruntime','onnxruntime-gpu']]"
```

Kết quả nguyên văn:
```
module: H:\AI Project\cam-ai\.venv\Lib\site-packages\onnxruntime
onnxruntime C:\Users\TTC\AppData\Roaming\Python\Python313\site-packages\onnxruntime-1.20.1.dist-info
onnxruntime-gpu H:\AI Project\cam-ai\.venv\Lib\site-packages\onnxruntime_gpu-1.23.2.dist-info
```

Đo bổ sung:
```
onnxruntime.__version__            = 1.23.2
get_available_providers()          = ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
.venv\pyvenv.cfg                   = include-system-site-packages = true
sys.path thứ tự                   = .venv\Lib\site-packages (trước)  ->  C:\Users\TTC\AppData\Roaming\Python\Python313\site-packages (sau)
```

**Nguyên nhân thật — tại sao vẫn chạy đúng GPU**
`.venv` được tạo bằng `--system-site-packages`, nên venv **nhìn thấy** thư viện user cài ngoài.
Gói CPU `onnxruntime 1.20.1` nằm ở user site-packages, gói GPU `onnxruntime-gpu 1.23.2` nằm trong venv.
Vì thư mục venv đứng **trước** user site trong `sys.path`, Python nạp bản GPU.

**Mức độ nguy hiểm — ĐÁNH GIÁ LẠI TỪ SỐ ĐO**
Hai gói **KHÔNG cài chung một thư mục**:

| Gói | Thư mục module |
|---|---|
| `onnxruntime` 1.20.1 (CPU) | `C:\Users\TTC\AppData\Roaming\Python\Python313\site-packages\onnxruntime` (586 file) |
| `onnxruntime-gpu` 1.23.2 (GPU) | `H:\AI Project\cam-ai\.venv\Lib\site-packages\onnxruntime` (622 file) |

→ **Hiện tại KHÔNG ghi đè lẫn nhau.** Rủi ro ghi đè là rủi ro **có điều kiện**, chỉ xảy ra nếu ai đó
chạy `pip install onnxruntime` (bản CPU) **trong khi .venv đang hoạt động** — lúc đó nó sẽ được
cài vào đúng thư mục của bản GPU và đè lên file của bản GPU.

**Cách xử lý nếu sau này phần mềm chạy chậm bất thường / rơi về CPU im lặng**
1. Chạy lại **đúng lệnh đo ở trên** — xem `module:` trỏ về thư mục nào.
2. Nếu `module:` trỏ về thư mục user (bản CPU 1.20.1) thì đã bị ghi đè → phải cài lại
   `onnxruntime-gpu==1.23.2` trong `.venv` (xem ISSUE_LOG #5).
3. Sau đó kiểm tra 3 bẫy ArcFace ở ISSUE_LOG #4 — vì chậm có thể do nguyên nhân khác.

**Đã sửa**
`model_info.py` — phần in console:
- Bỏ 2 dòng rời rạc, thay bằng **1 dòng** lấy từ `onnxruntime.__version__` (module đang chạy thật):
  `onnxruntime-gpu : 1.23.2   <- ĐANG CHẠY THẬT trên máy này`
- Bản CPU chỉ in thành **ghi chú**, không in thành dòng phiên bản song song.
- Dòng `Chạy trên GPU (CUDA)` viết lại rõ: `có – phần mềm chạy được bằng card màn hình NVIDIA`.
- **Không** đổi key trong dict `lay_phien_ban()` (vẫn giữ `onnxruntime` và `onnxruntime-gpu`).

**Cách tránh lặp**
- Khi hiển thị "phiên bản đang chạy" cho người dùng: đọc **module đang chạy**, không đọc metadata gói.
  Metadata chỉ nói "gói này có cài không", không nói "máy đang dùng gói này".
- Trước khi `pip install` bất cứ thứ gì vào dự án này, nhớ luật ở ISSUE_LOG #5 và PROJECT_STATE 9.8.
- Cài xong phải chạy lại lệnh đo ở trên, **không tin** vào việc pip báo "thành công".

---

## #9 · Chưa test trên video thật của chủ sở hữu

**Triệu chứng**
Mọi kết quả "đã kiểm chứng" hiện tại đều đến từ:
- `video_test.mp4` — **sinh ra bằng script từ 1 ảnh mẫu `sample_bus.jpg`**
- 9 video mẫu Intel trong `video_mau/`

**Nguyên nhân**
Chủ sở hữu chưa cung cấp video thật từ camera của mình.

**Hệ quả — đây là GIỚI HẠN THẬT, không phải lỗi:**
- Chưa biết phần mềm chạy tốt với camera thật (góc thấp, ánh sáng yếu, mưa, người mặc đồ kín)
- Chưa biết tốc độ thật với video 1080p dài
- Chưa biết tỉ lệ nhận nhầm người trong điều kiện thật
- `video_test.mp4` quá đơn giản: 250 khung hình, 10 giây, 1 góc quay

**Đã sửa**
⚠️ **CHƯA SỬA — chờ video thật từ chủ sở hữu.**

**Cách tránh lặp**
- **Đừng hứa anh là "đã kiểm chứng" khi mới chỉ test trên video mẫu.**
  Phải nói rõ: "test trên video mẫu, chưa test video nhà anh".
- Khi có video thật, chạy lại 4 lệnh hồi quy và ghi kết quả thật.

---

## #10 · `smoke_test.py` gần như chắc chắn sẽ lỗi

**Triệu chứng**
Chạy `smoke_test.py` sẽ hỏng, vì nó còn dùng công nghệ **đã bị thay thế từ v2.0**.

**Nguyên nhân thật**
`smoke_test.py` vẫn còn:

| Dòng | Vấn đề |
|---|---|
| `import urllib.request` + `URL = "https://ultralytics.com/images/bus.jpg"` | **Cần Internet** — trái nguyên tắc chạy local, và sẽ hỏng nếu máy không mạng |
| `from facenet_pytorch import MTCNN, InceptionResnetV1` | Thư viện **đã bị gỡ** từ v2.0 (chuyển sang ArcFace) |

**Đã sửa**
⚠️ **CHƯA SỬA.** File này nằm ngoài phạm vi việc đang chạy.

**Cách tránh lặp**
- **Đừng chạy `smoke_test.py`.** File này là di sản v1.x.
- Cần thì viết lại bằng `face_engine.FaceEngine` + `yolo11n.pt` và ảnh **cục bộ** (`sample_bus.jpg`).
- Khi xoá thư viện cũ, **quét tìm chỗ nào còn import nó** — đây là hậu quả của việc
  gỡ thư viện mà không rà lại toàn bộ chỗ dùng.

---

## #11 · Máy có tiến trình Python cũ từ 15/10 — **CHƯA GIẢI QUYẾT**

**Triệu chứng**
Máy chạy chậm bất thường. Quét thấy **7 tiến trình Python** cũ từ **15/10/2026**,
mỗi tiến trình đã ăn CPU trong **522–744 giây**.

**Nguyên nhân**
Chưa xác định. Có thể là:
- Phiên chạy `app.py` bị bỏ ngỏ không tắt
- Script kiểm tra chạy song song
- Tiến trình treo

**Đã sửa**
❌ **CHƯA GIẢI QUYẾT — và cố ý KHÔNG tự tắt.**

**Vì sao không tự tắt:** không biết chủ sở hữu có đang dùng những tiến trình đó không.
Tắt nhầm có thể mất việc đang làm. Đây là việc **phải hỏi chính chủ sở hữu**.

**Việc cần làm — dành cho chủ sở hữu:**
1. Mở **Task Manager** (Ctrl + Shift + Esc)
2. Vào tab **Details**
3. Tìm các dòng `python.exe` có **Start time** từ 15/10/2026
4. Xác nhận với người nhận việc rồi mới End task

**Cách tránh lặp**
- Chạy xong `app.py` thì **đóng cửa sổ console** (hoặc bấm Ctrl+C) — đừng bỏ mở.
- Dùng GUI thì bấm nút **Dừng** thay vì đóng tab.
- Nếu thấy máy chậm bất thường, kiểm tra Task Manager **trước khi** nghi ngờ phần mềm.

---

## #12 · CSV không lưu ngưỡng đông người

**Triệu chứng**
Muốn làm báo cáo "số lần vượt quá 5 người" nhưng đọc lại CSV thì **không biết lúc chạy
anh đã đặt ngưỡng mấy**.

**Nguyên nhân thật — đây là GIỚI HẠN THẬT CỦA DỮ LIỆU, KHÔNG PHẢI LỖI**
`cam_ai_core.py` ghi CSV 10 cột (`cam_ai_core.py:784-787`), trong đó có `trong_vung`
(số người trong vùng) nhưng **không** có cột ngưỡng.
Mà 10 cột là **hợp đồng đã chốt, không được thêm cột** (xem `PROJECT_STATE.md` mục 9.4).

**Cách xử lý hiện tại**
Khi làm báo cáo, truyền ngưỡng bằng tay:

```
.venv\Scripts\python.exe bao_cao_tong_ket.py --csv ten.csv --nguong-dong 3
```

Bỏ trống thì `bao_cao_tong_ket.py` tự lấy = **số người nhiều nhất quan sát được trong vùng**
(`max_trong_vung`), và trang HTML có ghi rõ là ngưỡng tự động.

**Cách tránh lặp**
- **Đừng "sửa" bằng cách thêm cột 11 vào CSV.** Sẽ phá hợp đồng dữ liệu và mọi báo cáo cũ.
- **Đừng coi đây là bug** rồi đi tìm lỗi. Nó là giới hạn đã biết.
- Muốn bỏ giới hạn thì phải đổi thiết kế CSV — cần anh Tuấn đồng ý trước.

---

## #13 · Lần chạy đầu của `bao_cao_tong_ket.py` gặp 3 lỗi thật

Ghi lại vì người sau rất dễ lặp lại 3 lỗi này khi viết file sinh báo cáo.

### 13.1 · `NameError` vì import đặt sai chỗ

**Triệu chứng:** `NameError: name 'openpyxl' is not defined`

**Nguyên nhân thật:** `import openpyxl` được đặt **bên trong một hàm**, nhưng các hàm khác
(`_viet_tieu_de`, `_canh_le`) lại dùng `openpyxl` như **biến toàn cục** → tên không tồn tại ở phạm vi đó.

**Đã sửa:** chuyển import lên **cấp module**, kèm `try/except ImportError` để thiếu thư viện
vẫn chạy được phần HTML (`bao_cao_tong_ket.py:40-48`).

**Cách tránh lặp:** import ở **cấp module** trừ khi có lý do rõ ràng (lazy import nặng).
Import trong hàm chỉ hợp lý khi cố ý tránh tốn thời gian khởi động — và khi đó phải truyền
qua tham số chứ không đọc như biến toàn cục.

### 13.2 · Cảnh báo "cột lạ" báo nhầm

**Triệu chứng:** in ra cảnh báo "CSV có cột không nhận diện được" với CSV **hoàn toàn đúng 10 cột**.

**Nguyên nhân thật:** **đảo ngược điều kiện** — kiểm tra nhầm `cột không nằm trong danh sách`
thành `cột không nằm trong danh sách` ở nhánh ngược lại.

**Đã sửa:** đảo lại điều kiện cho đúng chiều.

**Cách tránh lặp:** khi viết điều kiện kiểu "A nằm trong B", **viết thành khẳng định dương**
(`if ten not in ten_hop_le:`) thay vì phủ định kép (`if not ten in ...`).
Phủ định kép rất dễ đảo nhầm. Có `10 lỗi cổ điển` về chỗ này.

### 13.3 · Gõ nhầm "rongng" thay vì "ròng"

**Triệu chứng:** cột Excel hiển thị `rongng` thay vì `ròng` — nhìn rất vô lý.

**Nguyên nhân:** gõ tay nhầm, không ai đọc lại trước khi chạy.

**Đã sửa:** sửa lại chữ.

**Cách tránh lặp:** sau khi sinh file báo cáo, **mở ra nhìn bằng mắt** ít nhất 1 lần.
Báo cáo là thứ anh đọc — lỗi chính tả trong đó làm mất niềm tin vào cả phần mềm.
Xem thêm mục #14.

---

## #14 · Trang HTML xem lại CHƯA được xem bằng mắt

**Triệu chứng**
Trang HTML được kiểm bằng công cụ (`node --check` + `html.parser` + mở trình duyệt),
nhưng **chưa ai xác nhận bằng mắt** rằng các nút bấm được, biểu đồ vẽ đúng.

**Nguyên nhân**
Kiểm tự động bắt được lỗi cú pháp, **không bắt được** lỗi trải nghiệm người dùng.

**Đã kiểm chứng được (18/10/2026):**

| Kiểm tra | Kết quả |
|---|---|
| Tham chiếu `https://` trong file HTML | **0** |
| Tham chiếu `http://` | **0** |
| `fetch(` / `XMLHttpRequest` | **0** |
| Thẻ `<canvas>` | 1 |

→ Trang **tự chứa hoàn toàn**, chạy offline được. Phần này đã tin được.

**CHƯA kiểm chứng được:**

| Cần xem bằng mắt | Vì sao quan trọng |
|---|---|
| Bấm vào điểm trên biểu đồ có nhảy video đúng giây không | Đây là tính năng chính |
| Nút lớn "nhảy tới giây đông nhất" có chạy không | Tính năng chính |
| Danh sách sự kiện bấm được không | Tính năng chính |
| Video có mở được không | Phụ thuộc đường dẫn tương đối |
| Đọc có dễ không với người không rành công nghệ | Yêu cầu cốt lõi của anh Tuấn |

**Lưu ý kỹ thuật:** video được nhúng bằng **đường dẫn tương đối** tính từ thư mục chứa file
HTML (`bao_cao_tong_ket.py:963-980`). Nếu chuyển file HTML đi nơi khác mà không chuyển cả
video → **video không mở được**. Khi chép sang máy khác, chép **cả 2 file** vào cùng thư mục.

**Cách tránh lặp**
- Quy tắc chung của dự án: **có bằng chứng mới được ghi là "đã xong"**.
- Phân biệt 3 mức: *chạy được* → *kiểm tự động pass* → *đã xem bằng mắt*.
  Trang HTML hiện ở **mức 2**.