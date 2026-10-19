# UI_DAC_TA.md — Bố cục giao diện `gui.py` (bản v2)

> **Đọc file này đầu tiên khi quay lại làm tiếp.**
> Cập nhật: 2026-10-18 · Trạng thái: chạy được, đã kiểm chứng tự động.

## 1. Vì sao viết lại

Chủ sở hữu (không rành công nghệ) nói thẳng:

> *"cái menu đừng có làm chan lan kiểu đấy, mà chọn cái tính năng gì để detect thì nó mở setting của nó ra thôi,
> đừng có kể 1 đóng dài ngoằng như thế"*

Bản cũ là **1 khung cuộn dài** chứa 7 nhóm, mở lên thấy hết ~30 ô. Bản v2: **mỗi tính năng là 1 dòng,
mặc định thu gọn, bấm vào mới bung ô cài đặt của riêng tính năng đó**.

## 2. Nguyên tắc bắt buộc khi sửa tiếp

1. **Mặc định thu gọn hết.** Lúc mở phần mềm không được thấy đống ô.
2. **Chỉ dùng `grid()` + `grid_remove()`** để ẩn/hiện. **KHÔNG `pack_forget`** (trộn grid với pack làm
   vỡ bố cục).
3. **Cửa sổ chính không có thanh cuộn.** Thêm nhóm/ô mới thì phải chừa chỗ, phải gọn.
4. **Tắt checkbox → tự thu gọn + khôi phục mặc định** (danh sách `mac_dinh` truyền vào `NhomTinhNang`).
5. **Chuỗi hiển thị lên màn hình thì CÓ DẤU** (chủ sở hữu đọc). **Comment/docstring không dấu** (quy ước repo).
6. **Không gọi `os.chdir()`** — giữ đường dẫn tương đối như mặc định của `app.py`.
7. Chỉ sửa `gui.py`. `cam_ai_core.py`, `app.py`, `model_info.py`, `canh_bao.py`, `ve_vung.py`,
   `bao_cao_tong_ket.py` là **file của người khác** — đọc được, sửa thì phải hỏi.

## 3. Bố cục cửa sổ chính (1180x780, tối thiểu 1000x700, theme tối)

| Hàng | Nội dung |
|------|----------|
| 0 | Tiêu đề `CamAI — Phân tích video giám sát` |
| 1 | `Video` [chọn video…] [Mở thư mục clip] · `Lưu kết quả` [chọn…] |
| 2 | **8 dòng tính năng** (mặc định thu gọn hết) |
| 3 | `[▶ BẮT ĐẦU] [⏹ DỪNG]` |
| 4 | Thanh tiến trình + trạng thái khung hình |
| 5 | 4 ô số: Người · Mặt · Vào · Ra |
| 6 | Nhật ký (cuối **200** dòng) + nút `Mở video kết quả` + `Xem báo cáo` |
| 7 | Dòng lỗi (đỏ) |

### 8 dòng tính năng (đúng thứ tự này)

| # | Tên | Mặc định | Ô cài đặt bên trong |
|---|-----|----------|---------------------|
| 1 | Phát hiện người | **BẬT** | Ngưỡng tin cậy, Mô hình nhận diện, Vẽ khung / Vẽ nhãn tên / Làm mờ nền |
| 2 | Nhận diện khuôn mặt | **BẬT** | Ước lượng tuổi & giới tính (khoá), Ngưỡng giống mặt, Bỏ qua mặt nhỏ, Quét mặt mỗi, Thư mục ảnh đã học, Đọc lại danh sách |
| 3 | Đếm ra vào | TẮT | (chỉ có dòng giải thích) |
| 4 | Canh vùng | TẮT | File vùng, Vẽ vùng, Chỉ cần một phần chân, Vượt quá N người, Đứng lâu N giây |
| 5 | Lưu clip khi có sự kiện | TẮT | Tổng thời lượng 1 clip, Ghi clip cả khi không canh vùng |
| 6 | Nhận diện thêm vật thể khác | TẮT | Danh sách lớp cần nhận |
| 7 | Cảnh báo | TẮT | Phát chuong / Hộp thoại / Telegram, Thử gửi 1 cảnh báo |
| 8 | Thông tin mô hình AI | — | Nút mở **cửa sổ con** |

**Lưu ý số 1 — "Đếm ra vào" mặc định TẮT.** Bản GUI cũ mặc định BẬT. Đổi theo đúng bản vẽ bố cục mà
anh Tuấn duyệt. Nếu muốn quay lại BẬT: đổi `self.v_dem_ra_vao` trong `_khoi_tao_bien()` sang `"1"`.

## 4. Kiểm chứng

```powershell
cd 'H:\AI Project\cam-ai'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe _kiem_tra_gui.py
```

Dựng cửa sổ thật trong chính tiến trình test (không dùng `mainloop`), rồi kiểm:

1. Mặc định thu gọn hết — `winfo_manager() == ""` và `winfo_viewable() == 0` ở cả 8 nhóm.
2. Bấm giả lập từng tiêu đề (`nhom.btn_mo.invoke()`) → widget cài đặt **thực sự xuất hiện**, bấm lần hai → biến mất.
3. Bật/tắt checkbox → tự bung / tự thu gọn / khôi phục mặc định.
4. Mở cửa sổ con, dò đủ 4 model, đóng lại không treo.

Exit code: `0` = tất cả PASS, `1` = có FAIL, `2` = lỗi ngoại lệ.

## 5. Hai chỗ CỐ Ý làm vậy — đừng "sửa cho đẹp"

1. **Checkbox "Ước lượng tuổi và giới tính" bị khoá (`state="disabled"`, luôn BẬT).**
   `cam_ai_core.AnalysisConfig` **không có** tham số tắt tính năng này — `face_engine` luôn chạy
   `genderage` khi bật nhận diện khuôn mặt. Hiện khoá để không hứa hão. Muốn cho tắt được thì phải
   **thêm tham số vào `cam_ai_core.py` + `app.py`** (việc của người sở hữu file đó, không tự làm).

2. **`show_line` (Đếm ra vào) mặc định `False`.** Xem mục 3 ở trên.

## 6. Ánh xạ giao diện → tham số (`cam_ai_core.AnalysisConfig`)

| Ô giao diện | Trường |
|-------------|--------|
| ô Video | `input`, `output` |
| Phát hiện người | `no_face` (ngược), `conf`, `model`, `pixelate`, `show_box`, `show_label` |
| Nhận diện khuôn mặt | `no_face`, `faces_dir`, `face_threshold`, `min_face`, `face_every` |
| Đếm ra vào | `show_line` |
| Canh vùng | `vung`, `vung_nhay`, `vung_max`, `canh_lau` |
| Lưu clip | `tu_luu_clip` (rỗng = tắt), `clip_giay`, `clip_ghi_tat_ca` |
| Vật thể khác | `nhan_vat_the`, `lop` |

## 7. Nguyên tắc kỹ thuật phải giữ

- Pipeline chạy **thread nền daemon**, chỉ đẩy vào `queue.Queue`; `root.after()` mỗi 120 ms rồi mới
  đụng widget. **Không bao giờ gọi widget Tkinter từ thread nền.**
- `_gui_canh_bao()` gọi `CanhBao().guii()` **trên thread nền + `try/except`** → lỗi mạng không treo GUI.
- `open_in_explorer()` luôn truyền `os.path.abspath(...)` — `os.startfile` **không** nhận đường dẫn tương đối.
- Nút `Xem báo cáo` chạy `bao_cao_tong_ket.py` bằng `subprocess.Popen([sys.executable, ...])` (không chặn),
  và báo rõ khi chưa có file CSV.

## 8. Việc chưa làm / giới hạn thật

- **Chưa kiểm bằng mắt.** Mọi kiểm chứng trên là kiểm tra widget bằng `winfo_*`. Chủ sở hữu vẫn phải
  tự mở và soi bằng mắt: độ rộng nhãn, chữ `▶ ▼ ⏹ ⏸` có hiện đúng không, độ cao khung nhật ký.
- **Mở nhiều nhóm cùng lúc sẽ bóp nhỏ khung nhật ký** (khung nhật ký có `height=140` nên không biến mất hẳn,
  nhưng vẫn chật). Chưa xử lý — chấp nhận được vì mặc định là thu gọn hết.
- **Cảnh báo chỉ nối 3 sự kiện**: `vao_vung`, `dung_lau`, `vuot_nguong_dong`. Chưa gửi cảnh báo cho
  `nguoi_quen` hay `co_nguoi`.
- **`conf` không có trong CLI `app.py`** nhưng có trong `AnalysisConfig`; GUI vẫn dùng (giữ nguyên hành vi bản cũ).
- Chưa thử nút `Vẽ vùng`, `Xem báo cáo`, `Mở thư mục clip` với người thật trong phiên này (cần bấm tay).

## 9. Lịch sử

- **2026-10-18** — v2: viết lại toàn bộ `gui.py`. Thêm `NhomTinhNang` (1 dòng = 1 tính năng, mũi tên mở/đóng),
  cửa sổ con "Thông tin mô hình AI", nút `Xem báo cáo`, nút `Mở thư mục clip`, nhóm `Cảnh báo`,
  nhật ký rút còn 200 dòng. Thêm `_kiem_tra_gui.py`.