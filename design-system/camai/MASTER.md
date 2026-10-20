# CamAI — Design System (MASTER)

> Nguồn sự thật cho mọi thay đổi giao diện của CamAI. Sinh từ skill `ui-ux-pro-max`
> (design-system search + `color`/`typography`/`ux` domains), rồi **chỉnh lại cho đúng
> bản chất sản phẩm**: app desktop CustomTkinter, nền tối, dành cho người **không
> rành kỹ thuật**.
>
> Lệnh đã chạy:
> ```
> python "H:\AI Project\.agents\skills\ui-ux-pro-max\scripts\search.py" \
>   "desktop video surveillance analytics AI tool professional dashboard" \
>   --design-system -p "CamAI" --variance 5 --motion 3 --density 7 -f markdown --persist
> ```
> Kèm `--domain color --query "dark mode monitoring dashboard alert"`.

---

## 0. Ba quyết định sửa so với output gốc của skill (và lý do)

| # | Skill gốc ra | Quyết định của CamAI | Lý do |
|---|---|---|---|
| 1 | Pattern **"Enterprise Gateway"**, CTA "Contact Sales + Login" | **Bỏ pattern**, giữ **Style = Data-Dense Dashboard** | Pattern đó là của **landing page bán hàng**. CamAI là công cụ desktop chạy local, không có "Contact Sales". |
| 2 | Query "desktop … dark mode" trả **Cyberpunk UI** (đen + xanh neon `#00FF41` + glitch) | **Bỏ**, dùng palette **dark slate + xanh trạng thái** (mục 2) | Neon/scanline trông như "tool hacker", khó đọc, tỉ lệ tương phản kém. Người dùng mục tiêu không rành kỹ thuật → cần **giao diện sạch, tin cậy**. |
| 3 | Font gợi ý **Fira Sans / Fira Code / Inter** (Google Fonts) | Dùng **font có sẵn trên Windows**: `Segoe UI` (+ `Segoe UI Semibold`) cho chữ, `Cascadia Mono`/`Consolas` cho số & mã | App chạy **100% offline**; không được phụ thuộc tải font ngoài. Ghi rõ ở đây để không ai "sửa" ngược lại. |

---

## 1. Nguyên tắc (bắt buộc)

1. **Không emoji làm icon.** Mọi ký hiệu trạng thái dùng **font biểu tượng của Windows**
   (`Segoe Fluent Icons` nếu có, không thì `Segoe MDL2 Assets`), hoặc **chữ viết tắt**
   (`OK`, `LỖI`), hoặc **hình vẽ bằng PIL**. Cấm các ký tự như `✔ ✖ ■ ▶ ●` trong ô chữ.
2. **Tương phản chữ ≥ 4,5:1** với nền (skill: `contrast-text-4.5`).
3. **Cỡ chữ thân bài ≥ 13px**, nhãn ≥ 12px. **Không** chữ < 12px.
4. **Chiều cao nút ≥ 36px** (app desktop, chuột — không phải 44px cảm ứng).
5. **Mọi màu dùng qua hằng số trong `MAU`**, không rải hex trong widget.
6. **Tiếng Việt CÓ DẤU** trên mọi chuỗi hiển thị; comment trong code **KHÔNG DẤU**.
7. Không thêm dependency. Chỉ `customtkinter` + `PIL` + `tkinter`.
8. Không phá chức năng: **mọi mục cũ phải chạy đúng** (kiểm chứng bằng các script `_kk_kiem_*`).

---

## 2. Bảng màu (đã dùng gần đúng trong `gui.py` — giữ, chỉ tinh chỉnh)

Lấy từ domain `color` của skill: *"Financial Dashboard"* + *"Smart Home/IoT Dashboard"*.

| Vai trò | Hex | Dùng cho |
|---|---|---|
| `nen` | `#0F172A` | nền cửa sổ |
| `the` | `#1B2336` | thẻ/nhóm, thanh tiêu đề nhóm |
| `the_phu` | `#272F42` | ô nhập, hàng phụ |
| `chu` | `#F8FAFC` | chữ chính |
| `chu_phu` | `#94A3B8` | chữ phụ trên nền chính |
| `chu_phu_the` | `#CBD5E1` | chữ phụ trên nền thẻ |
| `nut` | `#22C55E` | nút chính (CTA) + trạng thái **thành công** |
| `nut_hover` | `#16A34A` | hover nút chính |
| `nut_phu` | `#334155` | nút phụ |
| `nut_phu_hover` | `#475569` | hover nút phụ |
| `vien` | `#334155` | viền 1px |
| `loi` | `#EF4444` | **lỗi / nguy hiểm** |
| `canh_bao` | `#F59E0B` | **cảnh báo / chờ** (chưa có — PHẢI thêm) |
| `focus` | `#FFFFFF` | viền focus (nếu dùng nền tối) |

> Skill yêu cầu **status color xanh / hổ phách / đỏ** cho trạng thái — CamAI đang thiếu
> màu **hổ phách** (`#F59E0B`) cho trạng thái "đang chạy / chờ". Phải bổ sung.

---

## 3. Typography

| Vai trò | Font | Cỡ | Đậm | Dùng cho |
|---|---|---|---|---|
| Tiêu đề app | `Segoe UI` | 22–24 | Bold | dòng tên trên thanh đầu |
| Tiêu đề khu vực | `Segoe UI` | 14–15 | Semibold | "Xem video", "Danh sách sự kiện" |
| Nhãn nhóm | `Segoe UI` | 12 | Semibold + viết HOA + giãn chữ 0.6px | "NGUỒN", "PHÂN TÍCH", "KẾT QUẢ" |
| Nhãn ô | `Segoe UI` | 13 | Normal | nhãn bên trái mỗi hàng cấu hình |
| Chữ nhập liệu | `Segoe UI` | 13 | Normal | ô nhập, dropdown |
| Chữ phụ / ghi chú | `Segoe UI` | 12 | Normal, màu `chu_phu` | ghi chú dưới nhóm |
| Số / mã / toạ độ | `Cascadia Mono` (fallback `Consolas`) | 12–13 | Normal | số liệu, tọa độ, thời gian |
| Badge số liệu | `Segoe UI` | 26–30 | Bold | 6 ô số liệu |

Quy tắc: **không dùng quá 3 cỡ chữ trong 1 vùng**; khoảng cách dòng ≥ 1.4.

---

## 4. Lưới khoảng cách (spacing scale)

`4 · 8 · 12 · 16 · 24 · 32` px. Cùng một vai trò **luôn dùng đúng một giá trị**:

| Vai trò | Giá trị |
|---|---|
| padding trong thẻ | 16 |
| padding nhóm con | 12 |
| khoảng cách giữa các hàng cấu hình | 8 |
| khoảng cách giữa các khối lớn | 24 |
| padding quanh mép cửa sổ | 16–20 |
| bo góc: nút / ô nhập / thẻ | 8 (nút), 6 (ô nhập), 10 (thẻ) |
| viền | 1px, màu `vien` |

---

## 5. Bố cục (layout)

```
┌──────────────────────────────────────────────────────────────┐
│  [icon] CamAI            [ngôn ngữ]      [BẮT ĐẦU ▶]        │  ← thanh đầu 64px
├───────────────┬──────────────────────────┬───────────────────┤
│  CỘT TRÁI     │   CỘT GIỮA              │  CỘT PHẢI        │
│  (280–320px)  │   (video lớn nhất)      │  (320–360px)     │
│               │                          │                   │
│  NGUỒN        │   ┌──────────────────┐   │  DANH SÁCH SỰ     │
│  · video      │   │                  │   │  KIỆN            │
│  · kết quả    │   │   KHUNG VIDEO    │   │  (timeline)      │
│               │   │                  │   │                   │
│  PHÂN TÍCH    │   └──────────────────┘   │  THỐNG KÊ VÙNG   │
│  · 12 nhóm    │   [3 ô xem] [ghi chú]    │  (6 số liệu)     │
│               │   ┌──────────────────┐   │                   │
│  MẪU VIDEO    │   │  NHẬT KÝ          │   │                   │
│  (gập lại)    │   └──────────────────┘   │                   │
└───────────────┴──────────────────────────┴───────────────────┘
```

- **Video là vùng lớn nhất**, phải giữ tỉ lệ ≥ 70% bề ngang (đã đo 75,4%–83,2% — **không
  được làm tệ hơn**).
- **Cột trái**: nhóm "Nguồn" + "Phân tích" (12 nhóm) + "Video mẫu" **gập lại được**.
- **13 thẻ video mẫu** hiện chiếm ~180px chiều cao ở đáy → gom thành **1 hàng cuộn ngang**
  hoặc 1 khung gập/ mở, **không** được đẩy video lên trên.
- **Thanh đầu** mới: icon + tên app + đổi ngôn ngữ + nút hành động chính.
- Mọi cột cuộn được; **không** cắt chữ.

---

## 6. Component

| Thành phần | Quy tắc |
|---|---|
| Nút chính | nền `nut`, chữ `#052E16`, bo góc 8, cao 36, hover `nut_hover` |
| Nút phụ | nền `nut_phu`, chữ `chu`, viền 1px `vien` |
| Ô nhập / dropdown | nền `the_phu`, chữ `chu`, viền 1px `vien`, bo góc 6, **chiều cao 32** |
| Checkbox | dùng `CTkCheckBox` với `checkmark_color="nen"` (#0F172A — **tối**), `fg_color="nut"` (xanh) → **dấu ✓ tối nằm trên ô xanh**, tương phản ≈ 7,7:1; `hover_color="nut_hover"`, nhãn 13px `chu`. **KHÔNG** đặt `fg_color` và `checkmark_color` cùng một màu — CustomTkinter vẽ ô bằng `fg_color` và dấu ✓ bằng `checkmark_color`, đặt giống nhau là dấu ✓ **biến mất** (xem `ISSUE_LOG.md`) |
| Thẻ/khung | nền `the`, bo góc 10, viền 1px `vien`, padding 16 |
| Ô số liệu | nền `the`, số 28px bold màu `chu`, nhãn 12px `chu_phu`; **màu theo trạng thái**: `nut` (bình thường), `canh_bao` (đang chạy), `loi` (lỗi) |
| Trạng thái | dùng **màu** + **chữ**, không chỉ màu (accessibility); kèm biểu tượng font Windows |
| Nhật ký | nền `nen`, chữ 12px `chu_phu`, mã màu `Cascadia Mono` |

---

## 7. Trước khi giao (Pre-Delivery Checklist của skill)

- [ ] Không emoji làm icon
- [ ] Tương phản chữ ≥ 4,5:1
- [ ] Chữ thân bài ≥ 13px, không chữ < 12px
- [ ] Mọi nút ≥ 36px, khoảng cách ≥ 8px
- [ ] Focus/hover nhìn thấy được
- [ ] Không chữ bị cắt, không tràn khung
- [ ] Video vẫn ≥ 70% bề ngang
- [ ] Mọi chuỗi hiển thị có bản dịch Anh trong `DICH_VI_EN`
- [ ] Các script `_kk_kiem_gui_chay_thuc.py` (7/7), `_kk_kiem_gui_b3.py` (4/4),
      `_kk_kiem_gui_batch_preview.py` (PASS), `_kk_kiem_ngon_ngu_v3_3.py` (5/5) vẫn PASS
