# CÀI CAMAI TRÊN MÁY MỚI

Tài liệu này dành cho **máy tính khác** — anh clone repo từ GitHub rồi làm theo.

> Repo: `https://github.com/handsomecat101/cam-ai` (private — cần đăng nhập GitHub của anh)
> Bản hiện tại: **v3.7**

---

## 0. Trước khi bắt đầu — cần có gì

| Cần | Ghi chú |
|---|---|
| **Windows 10/11** | App dùng `winsound`, `winreg`, chuông hệ thống → Windows là bắt buộc |
| **Python 3.10 – 3.13** | Kiểm tra: gõ `py -3 --version` trong cmd. Chưa có thì tải từ python.org (bật ô "Add to PATH") |
| **~2 GB đĩa trống** | Model ArcFace chiếm ~780 MB, video mẫu ~507 MB |
| **Python của hệ thống** | Script cài đặt sẽ tự tạo `.venv` bên trong dự án — **không cài gì vào Python hệ thống** |
| **Mạng internet** (1 lần) | Để tải thư viện + model. Sau đó app chạy **100% offline** |
| **GPU NVIDIA** (không bắt buộc) | Không có GPU thì app chạy CPU, chậm hơn nhưng vẫn chạy |

---

## 1. Tải code về (2 phút)

Mở **cmd** (không phải PowerShell) rồi gõ:

```bat
git clone https://github.com/handsomecat101/cam-ai.git
cd cam-ai
```

GitHub sẽ hỏi username + password. Ở ô **Password** dán **Personal Access Token** (không phải mật khẩu GitHub):
GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → tick **`repo`** → copy token.

> Nếu anh muốn khỏi nhập token mỗi lần: `git config --global credential.helper manager` rồi đăng nhập 1 lần bằng trình duyệt.

---

## 2. Cài đặt (10–20 phút, tùy tốc độ mạng)

Trong thư mục `cam-ai`, **double-click** `cai_dat_may_moi.bat`.

Hoặc gõ trong cmd:

```bat
py -3 cai_dat_may_moi.py
```

Script sẽ làm lần lượt:
1. Kiểm tra Python + thư mục dự án
2. Tạo `.venv` (môi trường ảo riêng cho dự án)
3. Cài thư viện từ `requirements.txt`
4. Tải model YOLO (`yolo11n.pt`)
5. Tải model khuôn mặt ArcFace (`models/buffalo_l` + `models/face_core`)
6. In tổng kết + hướng dẫn mở app

**Nếu bước 3 báo lỗi về `torch`:** `requirements.txt` cố ý để dòng `torch` ở dạng **comment** vì bản CUDA 12.6 không có trên PyPI. Script sẽ in ra lệnh cài đúng cho máy có GPU. Máy **không có GPU** thì dùng:
```bat
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install onnxruntime
```

**Nếu bước 5 tải model lỗi mạng:** tải lại sau, hoặc copy thẳng thư mục `models` từ máy cũ sang (xem mục 4).

---

## 3. Mở app

Double-click **`Mo CamAI.vbs`** trong thư mục `cam-ai`.

- Không mở được → double-click `Mo CamAI.bat` để xem lỗi chi tiết.
- Chi tiết: `HUONG-DAN-MO-APP.md`.

App mở mất **~12 giây** (nạp thư viện nặng) — bình thường, không phải treo.

---

## 4. Những thứ KHÔNG có trong git (và cách lấy lại)

Git chỉ chứa **code + tài liệu** (~3 MB). Các thứ nặng bị `.gitignore` loại có chủ đích:

| Mất gì | Kích thước | Cách lấy lại |
|---|---|---|
| `models/` (ArcFace, buffalo_l) | 784 MB | ✅ **Tự động** — bước 5 của script cài đặt. Hoặc copy thư mục `models` từ máy cũ |
| `yolo11n.pt` | 5,4 MB | ✅ **Tự động** — bước 4. Hoặc copy từ máy cũ |
| `video_mau/` (7 video mẫu) | 507 MB | ⬜ **Copy từ máy cũ** (USB / ổ mạng / cloud). Bản quyền xem `video_mau/moi/NGUON_LICENSE_NGUOI.md` |
| `known_faces/` (ảnh "An", "Binh") | ~1 MB | ⬜ **Copy từ máy cũ** (đây là ảnh khuôn mặt — em cố ý KHÔNG đưa vào git). Hoặc đăng ký lại bằng nút **"Đăng ký người quen…"** trong app |
| `.venv/` | vài GB | ✅ **Tự động** — script cài đặt tạo lại |
| `clip_da_luu/`, `anh_bien_so/`, `anh_su_kien/`, `_kk_out/` | — | Không cần, app tự tạo |

> **Vì sao không đưa model vào git?** GitHub giới hạn 100 MB mỗi file, repo nặng 1,3 GB sẽ clone chậm và tốn băng thông. Model tải lại được trong 5 phút, còn repo 3 MB thì clone trong 10 giây.

---

## 5. Làm việc tiếp (sau khi clone)

```bat
cd cam-ai

git pull              :: lay code moi nhat tu may cu
git status            :: xem anh da sua gi
git add .
git commit -m "mo ta thay doi"
git push              :: day len GitHub
```

Nhánh hiện tại: **`master`**.

### Nếu anh muốn làm việc song song trên 2 máy
```bat
git checkout -b ten-nhanh-moi   :: tao nhanh rieng
```
rồi `git push -u origin ten-nhanh-moi`.

---

## 6. Kiểm tra sau khi cài (2 phút)

```bat
:: app chay duoc khong
.venv\Scripts\python.exe -W ignore smoke_test.py

:: xem 80 lop COCO bang tieng Viet
.venv\Scripts\python.exe -W ignore app.py --list-lop

:: xem may co camera gi
.venv\Scripts\python.exe -W ignore app.py --list-camera

:: phan tich thu 1 video mau
.venv\Scripts\python.exe -W ignore app.py --input video_mau\car-detection.mp4 --lop "ô tô,xe máy"
```

---

## 7. Ghi chú nhanh (gotcha đã biết)

- **Nhãn vật thể trên khung hình không có dấu** ("xe o to") — vì OpenCV `putText` không vẽ được dấu tiếng Việt. **Báo cáo / CSV thì có dấu** ("ô tô"). Không phải lỗi.
- **Log đỏ `libopenh264`** mỗi lần chạy — file video kết quả **vẫn là H.264 hợp lệ**, không sao.
- **Máy không có camera** → `--list-camera` báo "không có camera nào"; chỉ test được đường camera IP `rtsp://...`.
- **File tiếng Việt trong repo là UTF-8 không BOM, xuống dòng LF** — đừng để Notepad/PowerShell `Set-Content` ghi đè lại (sẽ thêm BOM và đổi CRLF).
- **Đừng commit `.venv/`, `models/`, `video_mau/`, `known_faces/`** — `.gitignore` đã loại sẵn.

---

## 8. Nếu có sự cố

1. Đọc `PROJECT_STATE.md` (trạng thái + bằng chứng), `ISSUE_LOG.md` (lỗi đã biết), `CHANGELOG.md` (lịch sử thay đổi).
2. Chạy bộ kiểm chứng trong repo (tên bắt đầu bằng `_kk_`):
   ```bat
   .venv\Scripts\python.exe -W ignore _kk_kiem_gui_chay_thuc.py
   .venv\Scripts\python.exe -W ignore _kk_kiem_nguon_viet.py
   ```
3. Mở app bằng `Mo CamAI.bat` để thấy lỗi thật thay vì thấy hộp thoại.
