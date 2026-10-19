# SPEC — CamAI: Ứng Dụng Nhận Diện Vật Thể (Object Detection)
## Phạm vi: Video File & Camera Stream Đơn (Local GPU RTX 3090)

> **Mục đích tài liệu:** Đặc tả kỹ thuật và tiêu chí nghiệm thu cho phân hệ **Nhận diện vật thể (Object Detection)** theo yêu cầu của anh Tuấn (2026-10-18).
> **Định hướng phạm vi:** Tối giản và tập trung — giải quyết bài toán chạy mượt từ **File video** hoặc **Stream camera đơn (Webcam / RTSP)**, loại bỏ hoàn toàn sự cồng kềnh của hệ thống camera chuyên nghiệp NVR.

---

## 1. Tuyên bố phạm vi (Scope Boundary)

### 1.1 Những gì NẰM TRONG phạm vi (In-Scope)
1. **Nguồn dữ liệu đầu vào (Single Source Input):**
   - **File video cục bộ:** Hỗ trợ các định dạng phổ biến (`.mp4`, `.avi`, `.mkv`, `.mov`).
   - **Stream camera đơn:** Webcam cắm máy (ID `0`, `1`...) hoặc 1 luồng IP Camera cá nhân qua giao thức RTSP (`rtsp://user:pass@ip:port/h264`).
2. **Nhận diện vật thể (Object Detection & Classification):**
   - Sử dụng mô hình **YOLO11** (yolo11n / yolo11s) tối ưu hóa chạy bằng CUDA trên card **RTX 3090**.
   - Hỗ trợ 80 lớp chuẩn COCO, gom nhóm trực quan:
     - *Người:* Người đi bộ (`person`).
     - *Phương tiện giao thông:* Ô tô (`car`), Xe máy (`motorcycle`), Xe đạp (`bicycle`), Xe buýt (`bus`), Xe tải (`truck`).
     - *Đồ dùng cá nhân:* Ba lô (`backpack`), Túi xách (`handbag`), Vali (`suitcase`), Điện thoại (`cell phone`).
     - *Động vật:* Chó (`dog`), Mèo (`cat`), Chim (`bird`).
   - Tùy chọn lọc đối tượng: Cho phép người dùng tích chọn chỉ detect những nhóm cần thiết (ví dụ: chỉ phát hiện xe, hoặc chỉ phát hiện động vật).
3. **Theo dõi & Đếm đối tượng (Tracking & Counting):**
   - Tích hợp tracker (ByteTrack) để gán ID duy nhất cho mỗi vật thể trong luồng, tránh đếm lặp khi vật thể di chuyển.
   - Thống kê trực tiếp: Số lượng từng loại vật thể đang xuất hiện trong khung hình và tổng lượt đã quét qua.
4. **Hiển thị & Trải nghiệm (UI/UX Live Feed):**
   - Khung hình camera hiển thị trực tiếp (Live View) với tỷ lệ chuẩn.
   - Bounding box mượt, nhãn Tiếng Việt rõ nét, phân biệt màu sắc theo từng phân loại vật thể.
   - Bảng điều khiển chọn nguồn vào và chọn nhóm vật thể gọn gàng, trực quan.
   - Nút chụp ảnh nhanh (Snapshot) và xuất báo cáo sự kiện đơn giản.

### 1.2 Những gì TẠM THỜI LOẠI BỎ (Out of Scope)
- ❌ **Hệ thống NVR chuyên nghiệp:** Không làm lưới 8–16–32 camera cùng lúc; không quản lý luồng ghi đĩa 24/7 theo vòng lặp ổ cứng.
- ❌ **Quản lý hạ tầng đám mây / Internet:** 100% chạy cục bộ trên máy tính, không tạo tài khoản, không đẩy video ra ngoài.
- ❌ **Nhận diện hành vi phức tạp:** Không làm các bài toán cần mô hình chuyên sâu (cháy nổ, bạo lực, trèo tường).

---

## 2. Phân công Agent Team (Agent Team Roles)

Tuân thủ nguyên tắc điều phối dự án CamAI:

| Vai trò | Phụ trách chính | Trách nhiệm cụ thể | File liên quan |
|---|---|---|---|
| **Coordinator (Điều phối)** | Hệ thống | Soát xét spec, kiểm tra 4 lệnh hồi quy, nghiệm thu chỉ số FPS/Độ trễ | `ROADMAP.md`, `AGENT_CHAT.md` |
| **Agent Lõi (Core Engine)** | Agent A | Nâng cấp pipeline xử lý luồng (Drop-frame buffer cho RTSP, tích hợp YOLO11 object classes, tracker ByteTrack cho vật thể) | `cam_ai_core.py`, `app.py` |
| **Agent Giao diện (UI/UX)** | Agent B | Thiết kế khung hiển thị video chất lượng cao, bảng chọn nguồn (File / Cam / RTSP), bộ lọc checkbox nhóm vật thể | `gui.py` |
| **Agent Dữ liệu & Xuất file** | Agent C | Tự lưu snapshot ảnh/clip khi phát hiện vật thể chỉ định, xuất bảng CSV/Excel thống kê | `bao_cao_tong_ket.py` |

---

## 3. Đặc tả kỹ thuật chi tiết (Technical Specifications)

### 3.1 Pipeline Xử lý Nguồn vào (Input Handling)
- **Cơ chế chống trễ luồng Stream (Anti-Lag Buffer):**
  - Khi đọc từ RTSP hoặc Webcam thời gian thực, OpenCV mặc định có buffer ngầm gây trễ (delay tích luỹ 2–5 giây).
  - *Giải pháp:* Dùng một Thread riêng chỉ làm nhiệm vụ lấy khung hình mới nhất (`grab()`/`retrieve()`), luồng xử lý AI chỉ lấy khung hình gần nhất (Latest Frame Only), tự động drop frame thừa khi xử lý chậm.
- **Tự động kết nối lại (Auto-Reconnect):**
  - Nếu mất tín hiệu RTSP/Camera trong 3 giây, tự thử kết nối lại tối đa 5 lần trước khi báo lỗi cho người dùng.

### 3.2 Bộ lọc & Phân loại vật thể (Object Filtering)
Cấu trúc nhóm vật thể được chuẩn hoá thành cấu hình thân thiện:

```python
NHOM_VAT_THE = {
    "nguoi": {"ten": "Người", "classes": [0], "mau": (0, 255, 0)},
    "phuong_tien": {
        "ten": "Phương tiện giao thông",
        "classes": [1, 2, 3, 5, 7],  # bicycle, car, motorcycle, bus, truck
        "mau": (255, 165, 0),
    },
    "do_dung": {
        "ten": "Đồ dùng cá nhân",
        "classes": [24, 26, 28, 67],  # backpack, handbag, suitcase, cell phone
        "mau": (255, 0, 255),
    },
    "thu_cung": {
        "ten": "Động vật / Thú cưng",
        "classes": [14, 15, 16],  # bird, cat, dog
        "mau": (0, 255, 255),
    },
}
```

### 3.3 Hiển thị đồ họa (Rendering)
- **Bounding Box:** Vẽ khung góc bo tròn nhẹ, độ dày tương thích với độ phân giải video.
- **Nhãn (Label):** Nền màu mờ (alpha blend) phía trên hộp, chữ in đậm tiếng Việt không chân dễ đọc: `Tên vật thể + % độ tin cậy + ID`.
- **Thanh đo thời gian thực trên màn hình:**
  - `Nguồn:` [Tên file / Webcam / RTSP]
  - `FPS Xử lý AI:` [25 - 60 FPS]
  - `Đang thấy:` [2 Người, 1 Ô tô, 1 Chó]

---

## 4. Tiêu chí nghiệm thu (Acceptance Criteria)

Mọi tính năng chỉ được đánh dấu là HOÀN THÀNH khi đạt đủ các tiêu chí đo lường sau:

| # | Tiêu chí | Ngưỡng đạt | Cách kiểm tra |
|---|---|---|---|
| **AC1** | **Chạy file Video** | Xử lý mượt video 1080p, không rách hình, vẽ đúng bounding box các vật thể chuyển động | Chạy lệnh test trên video mẫu và xuất ra MP4 xem lại |
| **AC2** | **Chạy Camera/RTSP Stream** | Độ trễ hiển thị (latency) < 250ms so với thực tế; chạy liên tục 15 phút không tràn RAM | Mở webcam hoặc luồng RTSP camera cá nhân |
| **AC3** | **Tốc độ xử lý trên RTX 3090** | Đạt tối thiểu **35 FPS** ở độ phân giải Full HD (1920x1080) với YOLO11n | Kiểm tra bộ đếm FPS trong log |
| **AC4** | **Bộ lọc lớp vật thể** | Khi người dùng bỏ chọn nhóm nào, trên hình và trong thống kê tuyệt đối không hiện nhóm đó | Bỏ chọn "Người", chỉ chọn "Phương tiện" |
| **AC5** | **Không phá vỡ tính năng cũ** | 4 lệnh hồi quy của CamAI (`PROJECT_STATE.md` mục 4) vẫn phải chạy đúng 100% | Chạy đủ 4 lệnh hồi quy tự động |

---

## 5. Kế hoạch triển khai theo từng bước (Implementation Steps)

1. **Bước 1 (Core):** Hoàn thiện wrapper nhận diện vật thể linh hoạt trong `cam_ai_core.py`, hỗ trợ cờ chọn danh mục nhóm vật thể và cơ chế đọc luồng RTSP chống trễ.
2. **Bước 2 (CLI Test):** Cung cấp lệnh CLI để test nhanh:
   - `python app.py --input video.mp4 --nhom-vat-the phuong_tien,do_dung`
   - `python app.py --input 0 --nhom-vat-the all`
3. **Bước 3 (UI Polish):** Nâng cấp giao diện trực tiếp trên GUI: tách riêng tab hoặc khu vực chọn nguồn trực quan (File / Webcam / RTSP) và bảng công tắc nhóm vật thể kèm đếm số lượng thời gian thực.
4. **Bước 4 (Nghiệm thu):** Chạy kiểm thử hồi quy và ghi nhật ký bàn giao vào `AGENT_CHAT.md` & `ROADMAP.md`.
