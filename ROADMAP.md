# Lộ trình CamAI

Mục tiêu: phần mềm giám sát camera **chạy trên máy anh**, người không rành kỹ thuật cũng dùng được.

Nguyên tắc: **AI và dữ liệu luôn ở trên máy anh.** Cloudflare chỉ là đường vào, không phải nơi xử lý.

---

## Đã xong

- [x] Lõi AI: phát hiện/đếm người, nhận diện mặt, người quen, tuổi/giới
- [x] Đếm ra – vào
- [x] Canh vùng + cảnh báo vượt ngưỡng + đứng lâu
- [x] Tự lưu clip, nhận diện vật thể
- [x] Xuất CSV 10 cột, Excel, HTML xem lại
- [x] GUI desktop: accordion tiếng Việt, khung realtime, tạm dừng/tiếp tục
- [x] Web local: đăng nhập, upload, chạy, tạm dừng, tải kết quả
- [x] Bảo mật: không hardcode mật khẩu, fail-closed khi thiếu `CAMAI_PASSWORD`
- [x] Bốn lệnh hồi quy + test GUI 4/4
- [x] GUI visual (v2.4): video realtime chiếm phần lớn, overlay rõ, tên người quen trên khung,
      panel "Đối tượng phát hiện" gom ảnh crop thật, trạng thái bằng màu/badge
- [x] Bỏ hướng tunnel — dừng chạy, dọn file credentials cục bộ
- [x] Nối `canh_bao.py` vào `cam_ai_core.py` — có chuông cảnh báo thật, mặc định TẮT
- [x] `--lop` báo lỗi rõ + gợi ý lớp gần đúng + mã thoát ≠ 0 (trước đây bị bỏ qua im lặng)
- [x] Clip hỏng khi kill: ghi `.part.mp4` rồi mới đổi tên — file hỏng không còn mang tên đúng
- [x] Bố cục GUI theo mẫu tham chiếu: video lớn · danh sách sự kiện dạng timeline ·
      bảng thống kê vùng 5 dòng (hiện tại / trung bình / đỉnh / đáy / A→B)
- [x] Thư viện video demo có poster thật, bấm thẻ là chọn (thay dropdown chữ)
- [x] 6 video demo mới đa thể loại → **13 thẻ** (v2.6), kèm `NGUON_LICENSE.md`
- [x] **Live view ≥10 fps** (v2.6): `PUMP_MS` 120 → 30, đo thật **14.34 fps** liên tục
      300.2 s, 0/293 giây dưới 10 fps. Giả thuyết "YOLO chạy 2 vòng" đã bị đo và bác bỏ
- [x] **0 cặp nhãn chồm** trên khung 15 người (v2.7): sửa `_vuot_nhau` theo đúng nghĩa
      `LE_TRANH`; 15/15 nhãn vẽ được
- [x] **Video ≥70% bề ngang + 0 nhãn tràn** (v2.7): cột sự kiện co theo → 75.4%–83.2%
- [x] 4 lỗi hiển thị 2.5 đã sửa: dải badge đáy tách, nhãn vùng không chồn khung
- [x] **Công tắc "Nhận người ở xa (chậm hơn)"** (v2.8): `--tach-o` trong lõi/CLI/GUI,
      **mặc định TẮT** (anh đã chọn sau khi đo). Đo thật: `dam-dong` 3.0 → 5.4,
      `xe-co-giao-thong` 1.0 → 4.6, video gần không đổi; chậm 5.3×
- [x] Hồi quy bản 2.8 tự chạy: 4 lệnh `app.py` exit 0, `--help` 70 dòng, CSV 251×10,
      `_kiem_tra_gui.py` 4/4, bố cục 75.4% nhỏ nhất, encoding `BOM=False CR=0`

## Đang làm

- [ ] **Chờ anh xác nhận mục 7** — kéo cửa sổ, còn giật hay không (chỉ có số đo)
- [ ] **Chờ anh xác nhận mục 8** — độ nhận diện; cần video thật của anh

## Kế tiếp

- [ ] Khôi phục lưới "Đối tượng phát hiện" bị bỏ (chờ anh chọn) + cho chọn kênh cảnh báo
- [x] Web: cập nhật lại sau khi GUI đổi — kiểm lại HTTP 200 + 401 (2026-10-19: trang chủ 200, API 401)
- [ ] Thử web trên điện thoại thật
- [ ] Thử nhiều người dùng đồng thạt trên web
- [ ] Chuông Windows bằng âm thanh hệ thống
- [ ] Rà lại `known_faces/` — dữ liệu giả, chờ anh đồng ý xóa

## Chờ anh quyết

- [ ] Có thêm ô chọn webcam (camera live) trong GUI không?
- [ ] Có cần model nhận diện khẩu trang không? (hiện cột `Mask:` luôn "Chưa rõ")
- [ ] Giữ lưới "Đối tượng phát hiện" hay chỉ giữ timeline sự kiện?

## Tương lai — chỉ khi app ổn định

- [ ] Telegram bot gửi cảnh báo
- [ ] Cân nhắc public qua Cloudflare tunnel (dữ liệu vẫn ở máy anh).
      Tunnel thử nghiệm `camvision` đã dừng theo yêu cầu của anh; xem `PROJECT_STATE.md` mục 7.