# Use case & backlog tính năng — CamAI

**Ngày lập:** 2026-10-19 (sau 21:30) — **cập nhật 2026-10-20 (sau 14:20) theo quyết định của anh**
**Mục đích:** ghi lại các hướng dùng + những tính năng nên làm tiếp, để lần sau bị bí
không biết làm gì thì lôi file này ra triển khai, không phải nghĩ lại từ đầu.

> **Nguyên tắc:** CamAI là **một lõi AI dùng chung** cho nhiều lĩnh vực. Mỗi use case
> khác nhau ở *cấu hình + rule + báo cáo*, không phải ở thuật toán. Nên ưu tiên làm
> **tầng nền tảng** (mục 2) trước khi thêm model AI mới.

---

## 0. ĐỊNH HƯỚNG SẢN PHẨM — anh chốt 2026-10-20 (sau 14:20)

| Quyết định | Nội dung |
|---|---|
| **CamAI là app "detect đa thể loại"** | Một app, chạy được trên **3 loại nguồn**: **file video** (đã có ✅) · **ảnh tĩnh** (đang làm) · **quay video / camera** — webcam `0` và camera IP `rtsp://` (đang làm) |
| **Ứng dụng chấm công → tách ra app riêng** | Việc chấm công cần **cơ sở dữ liệu khuôn mặt riêng** (dữ liệu nhân sự, ca làm, đối soát) → **KHÔNG ôm vào CamAI**. Nó sẽ là **1 app khác**, dùng **chung** module `face_engine.py` + thư mục `known_faces/` với CamAI. Nguyên tắc: **CamAI = detect; app kia = nghiệp vụ + dữ liệu** |
| **Đổi nền tảng → làm SAU** | Tạm dừng việc cân nhắc PySide6/Qt. Khi đã chốt phạm vi tính năng thì mới quyết định đổi lớp giao diện, để **một lần viết lại cho đủ** thay vì viết lại nhiều lần |

**Điểm cốt lõi để nhớ:** CamAI **không** phải app chấm công. CamAI là **máy detect** —
nhận vào một nguồn hình ảnh, trả về **mọi thứ nó nhận ra được** (người, mặt, tên, biển số,
vật thể, sự kiện ra/vào) + ảnh đã vẽ khung + báo cáo. Ứng dụng nào dùng nó thì tự đặt
rule và dữ liệu riêng.

---

## 1. Các hướng dùng (use case)

Mỗi dòng là một hướng. Cột "đã có sẵn" là những gì **đang chạy thật** trong app hiện tại.

| # | Lĩnh vực | Dùng để làm gì | Đã có sẵn trong app | Cần thêm |
|---|---|---|---|---|
| 1 | **An ninh khu vực** (cửa hàng, kho, văn phòng, bãi xe) | Phát hiện người lạ, canh vùng, đứng lâu, giám sát ban đêm | Phát hiện người, canh vùng, ngưỡng đông, đứng lâu, cảnh báo, lưu clip/ảnh | Rule theo giờ, cảnh báo kèm ảnh, dashboard |
| 2 | **Bán lẻ / cửa hàng** | Đếm lưu lượng khách, giờ ca đông, đường đi trong cửa hàng | Đếm người/giây, đếm ra–vào, vùng | Báo cáo theo giờ, heatmap đường đi, chống đếm trùng |
| 3 | **Kho / logistics** | Đếm xe ra–vào, đọc biển số, đối chiếu đơn hàng | Nhận diện vật thể (xe), đếm ra–vào (người), OCR biển số | Tái dùng đếm ra–vào cho lớp **xe**, báo cáo theo biển số, multi-camera |
| 4 | **Giao thông / cổng** | Đếm xe theo chiều, phân loại xe, biển số | Nhận diện vật thể, OCR biển số | Đếm xe theo chiều, phân loại xe tải/xe khách/container |
| 5 | **Nhà xưởng / sản xuất** | An toàn lao động: mũ bảo hiểm, găng tay, khoảng cách | Phát hiện người, vùng | **Train model PPE riêng** (mũ, găng, áo phao) |
| 6 | **Trường học / cơ sở y tế** | Đếm ra–vào, phát hiện vắng mặt | Đếm ra–vào, nhận diện người quen, lịch sử sự kiện | Báo cáo theo lớp/phòng, theo ca, lịch |
| 7 | **Nuôi trồng** | Đếm gia súc, phát hiện lạc đàn | Nhận diện vật thể (bò, cừu, ngựa… có trong COCO) | Model riêng cho gia súc Việt Nam, cảnh báo lạc đàn |
| 8 | **Kiểm tra tuân thủ** | Khẩu trang, mũ bảo hiểm, khoảng cách an toàn | Vùng, đứng lâu | Model riêng + đo khoảng cách giữa 2 người |
| 9 | **Giao nhận / xe giao hàng** | Đếm hàng, giao đúng người, biển số xe | OCR biển số, nhận diện người quen | Đếm hàng hoá, chụp ảnh bằng chứng giao hàng |
| 10 | **Bàn giao cho khách** | Khách tự xem báo cáo mà không cần biết AI là gì | GUI 12 nhóm + CSV/Excel/HTML + web local | Dashboard, cấu hình theo khách, chạy 24/7 |

---

## 2. Tầng nền tảng — xây 1 lần, mọi use case đều dùng

Đây là phần **ưu tiên cao nhất**. Vì sao: 80% khó khăn của hệ thống giám sát là
**vận hành và báo cáo**, không phải thuật toán. Thêm model mới thì tăng độ khó bảo
trì mà không giải quyết vấn đề "người không rành kỹ thuật vẫn dùng được".

| # | Tầng nền tảng | Hiện trạng | Việc cần làm | Có thể dùng cho use case |
|---|---|---|---|---|
| N1 | **Vẽ vùng / đường ngắm trong GUI, nhiều vùng** | **Xong bản 3.3**: nút "Vẽ vùng ngay tại đây" — kéo chuột **trong chính cửa sổ** (module mới `ve_vung_gui.py`), ghi ra file vùng `.txt`, đo **sai số 0.0000** | Còn **nhiều vùng** trong 1 file | 1, 2, 3, 5, 6, 8 |
| N2 | **Đăng ký người quen trong GUI** | **Xong bản 3.3**: nút "Đăng ký người quen…" — chọn ảnh/video → nhập tên → lưu `known_faces/<Tên>/`, tự nạp lại danh sách người quen | Còn: đăng ký **nhiều người cùng lúc** trong 1 video | 1, 2, 6, 9, 10 |
| N12 | **Giao diện dễ nhìn, dễ dùng cho người không rành kỹ thuật** | **Xong bản 3.4**: thiết kế lại toàn bộ giao diện theo skill `ui-ux-pro-max` → `design-system/camai/MASTER.md`; thanh đầu mới có icon app; bỏ hết emoji làm icon (dùng font biểu tượng Windows); typography + component + lưới khoảng cách thống nhất; **icon app do AI vẽ** | Còn: bản điện thoại / web cho người không dùng máy tính | 1, 5, 6, 11 |
| N3 | **Dashboard tổng quan + lịch sử sự kiện lưu lâu dài** | Chỉ có timeline sự kiện trong 1 phiên | 1 màn hình "hôm nay: N người · M sự kiện · camera nào lỗi" + lưu lâu dài | tất cả |
| N4 | **Rule cảnh báo theo điều kiện** | Cảnh báo cố định: vượt ngưỡng / đứng lâu | Cấu hình được trong GUI: *"quá 3 người trong vùng sau 22h"*, *"xe vào lúc 3h"*, kèm **ảnh** | 1, 3, 4, 6, 8 |
| N5 | **Nhiều camera / nhiều nguồn** | `--input` chỉ nhận **1** nguồn | Chạy N nguồn, gộp vào 1 báo cáo | 3, 4, 10 |
| N6 | **Chạy 24/7 + xoay vòng dữ liệu** | Chưa có | Giữ N ngày, tự xoá cũ, tự khởi động lại | 1, 3, 4, 10 |
| N7 | **Giám sát sức khoẻ hệ thống** | Chưa có | Cảnh báo: camera rớt khung / mất hình / ổ đầy / model lỗi | tất cả |
| N8 | **Báo cáo theo ca / ngày / tháng** | CSV là **theo giây**; Excel/HTML có nhưng theo giờ | Bảng theo ca (sáng/chiều/đêm), theo ngày, theo từng người | 2, 3, 6, 10 |
| N9 | **Chống đếm trùng 1 người** | Chưa có | "1 track ID = 1 lượt", chỉ tính lúc đi qua đường | 1, 2, 6 |
| N10 | **Chế độ không lưu ảnh** (chỉ giữ số đếm) | Chưa có | Tắt lưu clip/ảnh, chỉ ghi số | 1, 6, 8, 10 |
| N11 | **Cảnh báo đa kênh + kèm ảnh** | `canh_bao.py` gửi **tin** | Thêm ảnh khung hình, thêm kênh (âm thanh Windows) | 1, 3, 4, 10 |
| N12 | **Cài như dịch vụ Windows + kiosk** | Chưa có | Tự lên khi bật máy, hẹn giờ bật/tắt, chế độ toàn màn hình | 1, 3, 4, 10 |

**Thứ tự nên làm:** N1 → N2 → N8 → N4 → N9 → N3 → N5 → N7 → N6 → N11 → N12 → N10

> N1 và N2 rẻ nhất (đã có sẵn code CLI, chỉ cần nhúng vào GUI) và giảm rào cản cài đặt
> nhiều nhất → làm trước.

---

## 3. Tính năng AI mở rộng (cần model riêng — làm SAU tầng nền tảng)

### 3.1 Bảng "thể loại detect" — mục tiêu: **phủ càng nhiều càng tốt**

Hiện CamAI đã detect được (đều **đã chạy thật**, xem `PROJECT_STATE.md` mục 2.1d):

| # | Thể loại | Cơ chế hiện tại | Trạng thái |
|---|---|---|---|
| 1 | **Người** | YOLO11 `person` | ✅ có |
| 2 | **Khuôn mặt** | ArcFace (scrfd + w600k) | ✅ có |
| 3 | **Tên người quen** | ArcFace embedding + `known_faces/` | ✅ có |
| 4 | **Tuổi / giới** | `genderage.onnx` | ✅ có |
| 5 | **Biển số xe** | RapidOCR (2 engine) + regex VN | ✅ có (chưa có ảnh thật để nghiệm thu) |
| 6 | **Vật thể 80 lớp COCO** | YOLO11 (`--lop`) | ✅ có — **bản 3.7 nhận tiếng Việt** ("ô tô, xe máy, chó, mèo…" hoặc không dấu "o to, xe may", hoặc tiếng Anh). `--list-lop` in đủ 80 lớp. Còn thiếu: **ô tick chọn 80 lớp** trong GUI |
| 7 | **Ra / vào theo vùng** | bbox + vùng canh | ✅ có |
| 8 | **Đứng lâu / quá ngưỡng đông** | quy tắc theo thời gian | ✅ có |

**Cần làm tiếp (xếp theo giá trị / công):**

| Ưu tiên | Thể loại | Cần gì | Ghi chú |
|---|---|---|---|
| **P0** | **Nguồn ảnh tĩnh** | chế độ phân tích 1 ảnh, xuất ảnh đã vẽ khung | ✅ xong (bản 3.6 lõi + bản 3.7 GUI) |
| **P0** | **Nguồn camera** (webcam `0`, camera IP `rtsp://`) | chọn thiết bị, chạy live, dừng bằng phím | ✅ xong (bản 3.6 lõi + bản 3.7 GUI). **Camera thật chưa kiểm chứng** (máy này không có camera) |
| **P1** | **Chọn lớp vật thể bằng TIẾNG VIỆT** | map 80 lớp COCO → nhóm tiếng Việt (Phương tiện / An toàn lao động / Giao thông / Động vật / Đồ vật / …) + ô chọn có tick | ✅ **gõ tiếng Việt xong** (bản 3.7, `lop_viet.py`, 80 lớp khớp 100% model + ~200 từ đồng nghĩa). Còn lại: **ô tick 80 lớp trong GUI** |
| **P1** | **Đếm phương tiện** | dùng lớp `car/motorcycle/bus/truck` + đếm ra–vào | ✅ xong (bản 3.7, `--dem-phuong-tien`): theo lớp + tổng lượt + max cùng lúc, 4 cột CSV mới ở cuối |
| **P2** | **Mũ bảo hiểm / PPE** | YOLO11 có class `helmet` → dùng được ngay, sau đó mới train model PPE đầy đủ | Không cần model mới ở bước đầu |
| **P2** | **Biển chữ / số móc / số container** | RapidOCR (đã có) chạy trên vùng chữ | Chỉ cần thêm quy tắc vùng |
| **P2** | **Đo khoảng cách giữa 2 người** | bbox + toạ độ mặt đất | Không cần model mới |
| **P3** | **Đếm theo chiều (vào/ra riêng theo làn)** | vùng + hướng chuyển động | Nâng cấp của đếm ra–vào |
| **P3** | **Re-ID xuyên camera** | model re-ID | Cần cho multi-camera |
| **P4** | **Phân vùng (segmentation)** | model segmentation | Ảnh crop đẹp hơn |
| **P4** | **OCR tổng quát / đếm hàng hoá / gia súc / hành vi** | train model riêng | Chỉ khi khách cụ thể cần |

### 3.2 Tính năng cần model riêng (làm SAU tầng nền tảng)

| Tính năng | Cần gì | Ghi chú |
|---|---|---|
| **PPE** (mũ bảo hiểm, găng tay, áo phao) | Train YOLO mới | Data tự thu từ camera của khách |
| **Re-ID xuyên camera** | Model re-ID | 1 người qua 2 camera vẫn giữ 1 ID → cần cho N5 |
| **Phân vùng (segmentation)** | Model segmentation | Tách người khỏi nền chính xác hơn cho ảnh crop lưu lại |
| **OCR tổng quát** | Tái dùng RapidOCR | Ngoài biển số: số móc, biển chữ, số container |
| **Đếm hàng hoá trên kệ** | Train model riêng | Cho bán lẻ / kho |
| **Đếm gia súc** | Train model riêng | Cho nông nghiệp |
| **Đo khoảng cách giữa 2 người** | Dùng bbox + toạ độ | Kiểm tra khoảng cách an toàn, không cần model mới |
| **Phát hiện hành vi** (chạy, ngồi, quay lưng) | Pose / phân loại | Chống trộm cắp, phát hiện lạc đàn |

---

## 4. Nguyên tắc khi thêm tính năng mới

1. **Mặc định TẮT** — không được làm hỏng 6 mục nghiệm thu đã đạt (xem `PROJECT_STATE.md` mục 2.1).
2. **CSV giữ nguyên 10 cột** khi tính năng tắt; cột mới chỉ thêm **ở CUỐI** khi bật.
3. **Ghi tác động tốc độ bằng số đo thật**, không dùng nhãn mơ hồ ("nhanh hơn ~5×" phải
   kèm đo).
4. **Mọi thao tác sửa file tiếng Việt**: dùng tool `edit`/`write`, **không** dùng
   `Get-Content | Set-Content` (sẽ hỏng UTF-8 + thêm BOM + đổi CRLF).
5. **Có bằng chứng ảnh/video thật** cho mỗi tính năng mới — coordinator tự xem bằng mắt.
6. **Bump `VERSION`** + cập nhật đủ 4 file tài liệu (`PROJECT_STATE.md`, `CHANGELOG.md`,
   `ISSUE_LOG.md`, `ROADMAP.md`).

---

## 5. Cấu trúc khi bàn giao cho nhiều khách

```
1 lõi CamAI
  └── 1 file cấu hình .json / .ini theo khách
        ├── danh sách camera / nguồn video
        ├── vùng canh (nhiều vùng)
        ├── rule cảnh báo + lịch ca
        ├── ngưỡng + model + thiết bị
        └── mẫu báo cáo (cột nào, chia ca thế nào)
```

Cài cho khách = **đổi 1 file**, không đụng code. Đây là hướng đi từ N1+N2+N8+N4.
