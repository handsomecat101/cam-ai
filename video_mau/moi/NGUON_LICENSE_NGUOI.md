# Nguồn và giấy phép — 5 video người thực tế (Wikimedia Commons)

Ghi lại để không ai tải lại. Tất cả video gốc tải từ **Wikimedia Commons**, sau đó
được cắt lại 8 giây đầu, đổi về `1280x720 / yuv420p / 25 fps / 200 khung`
để nhất quán với quy ước của dự án.

> Lưu ý về tên: tên file trong thư mục do người đặt **đặt theo cảnh nhìn thấy được**,
> KHÔNG phải theo tên file gốc. Bảng dưới là mapping chính xác theo script encode.

## Mapping đầy đủ

| File trong `video_mau/moi/` | File gốc trên Commons | Giấy phép | Tác giả |
|---|---|---|---|
| `di-bo-he-pho.mp4` | [File:Pedestrian area Ljubljana.webm](https://commons.wikimedia.org/wiki/File:Pedestrian_area_Ljubljana.webm) | **CC BY 3.0** | Sounds of Changes |
| `di-bo-duong-pedestrian.mp4` | [File:Video Codec Test pedestrian area 1080p25.y4m.webm](https://commons.wikimedia.org/wiki/File:Video_Codec_Test_pedestrian_area_1080p25.y4m.webm) | **CC0** (public domain) | Taurus Media Technik |
| `nguoi-qua-duong-vach-bo.mp4` | [File:Piedirejo en strato Herzen (Tjumeno).webm](https://commons.wikimedia.org/wiki/File:Piedirejo_en_strato_Herzen_(Tjumeno).webm) | **CC BY-SA 4.0** | RG72 |
| `san-choi-tre-em.mp4` | [File:Children Playing in Cameroon.webm](https://commons.wikimedia.org/wiki/File:Children_Playing_in_Cameroon.webm) | **CC BY-SA 4.0** | Eyongblaise |
| `nguoi-qua-duong-camera-that.mp4` | [File:Roncesvalles Ave crossing at Galley Ave, PXO Type A lights flashing, July 2026.webm](https://commons.wikimedia.org/wiki/File:Roncesvalles_Ave_crossing_at_Galley_Ave,_PXO_Type_A_lights_flashing,_July_2026.webm) | **CC BY-SA 4.0** | Qviri |

Tất cả file gốc đều là **1920x1080**. Credit gốc:

- `Pedestrian area Ljubljana.webm` — credit ghi rõ lấy từ YouTube / archive.org
  (tác giả âm thanh: Sounds of Changes).
- `Video Codec Test pedestrian area 1080p25.y4m.webm` — credit ghi rõ lấy từ
  `http://media.xiph.org/video/derf/y4m/` (bộ mẫu video test của Xiph.Org).
- Ba video còn lại ghi "Own work" (tác giả tự quay).

## Nghĩa vụ ghi nhận

Vì có video **CC BY** và **CC BY-SA**, khi phát hành CamAI ra ngoài (bán, chia sẻ,
đăng mạng) thì **bắt buộc** phải:

1. Ghi tên tác giả gốc + giấy phép tương ứng ở nơi người dùng xem được
   (README, màn hình "Giới thiệu", hoặc file `CREDITS.txt` đi kèm bản phát hành).
2. Với phần **CC BY-SA**: nếu có sửa đổi (đã cắt 8 giây, đổi kích thước, đổi codec)
   thì bản phái sinh vẫn phải giữ giấy phép CC BY-SA 4.0.
3. Không được bán phần mã nguồn/video mới như là của mình.

Riêng video **CC0** (`di-bo-duong-pedestrian.mp4`) thì không phát sinh nghĩa vụ gì.

## Đánh giá thực tế (coordinator tự xem bằng mắt, không tin báo cáo agent)

| File | Tình huống | Đánh giá dùng để test |
|---|---|---|
| `di-bo-he-pho.mp4` | Phố đi bộ kiểu châu Âu, người đi **sát camera**, cao tối đa ~485 px | **Tốt nhất** — gần với người đi tới camera chấm công |
| `di-bo-duong-pedestrian.mp4` | Khu phố đi bộ, nhiều người, cự ly đa dạng | **Tốt** — nhiều người/khung |
| `nguoi-qua-duong-vach-bo.mp4` | Ngã tư có vạch bó, camera cao ~3 m, người ở xa | Khá — người nhỏ, nhận diện mặt gần như không trúng |
| `san-choi-tre-em.mp4` | Sân chơi, người lẫn nhiều vật | Dùng để test **nhận diện sai** (false positive) |
| `nguoi-qua-duong-camera-that.mp4` | Đường lớn, người ở rất xa (~65 px) | **Kém** cho đếm người; chỉ nên dùng để so sánh |

### Lỗi cần lưu ý khi test

- `di-bo-he-pho.mp4` và một số video khác **có fade-in ở đầu** → vài khung hình đầu
  gần như đen. Khi đo phải **bỏ qua 50 khung đầu** (tức 2 giây).
- Video chỉ dài **8 giây / 200 khung**, không đủ để test thời gian dài.
- Không video nào ở đây giống camera an ninh lắp trên tường nhìn chếch xuống
  sàn nhà công ty — cảnh đó vẫn **thiếu**, cần video của người dùng cung cấp.

## Ứng viên đã loại (không đưa vào dự án)

| File | Lý do loại |
|---|---|
| `Roncesvalles...` (bản dùng làm `nguoi-qua-duong-camera-that`) | Người ở rất xa, chỉ 65–68 px |
| `Third_to_second_floor_escalator_Wikimania_20.webm` | Cầu thang cuộn, **không có mặt phẳng sàn rõ** để đếm |
| `Video_en_el_Centro_de_Mazatlán__10_de_agosto.webm` | **Lệch nét nặng**, chụp sát mặt đất |
| `Kids_in_the_Playground.webm`, `Playing_at_playground.webm`, `Margaret_Mahy_Playground_002.webm`, `Two_children_in_the_playground_at_school.webm` | Trùng chủ đề với `san-choi-tre-em`, không thêm giá trị |
| `Common_people_line_for_food_in_Barquisimeto_.webm` | Tải về 0 byte, hỏng |