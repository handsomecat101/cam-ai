# ĐỀ XUẤT CÔNG NGHỆ CHO CAMAI

> **Ngày lập:** 18/10/2026
> **Người viết:** agent nghiên cứu
> **Dành cho:** anh Tuấn — mục đích là chọn xem nên làm gì tiếp theo, không cần hiểu kỹ thuật.

---

## ĐỌC NHANH — TÓM TẮT 1 PHÚT

CamAI hiện đã làm khá tốt phần **"nhìn thấy người"**. Phần còn thiếu và **hữu ích nhất với anh** lại là:

> **"Biết có chuyện, phải xem được ngay, không phải ngồi xem video 8 tiếng."**

Vì vậy 8 việc đáng làm nhất — theo đúng thứ tự nên làm — là:

| # | Việc cần làm | Vì sao đáng làm nhất | Công cức |
|---|---------------|---------------------|----------|
| 1 | **Tự lưu clip 15 giây khi có chuyện** | Anh không phải ngồi xem lại cả video dài để biết lúc nào có người lạ | 0 MB |
| 2 | **Báo động qua Telegram lên điện thoại** | Anh ở ngoài nhà vẫn nhận được tin "có người vào vùng cửa" | ~2 MB |
| 3 | **Kêu chuông + pop-up Windows** | Hoạt động **cả khi mất mạng** — an toàn tuyệt đối | ~0,1 MB |
| 4 | **Nhiều vùng cảnh báo + vạch đếm đặt theo từng cửa** | Biết người vào **cửa nào**, không phải chung một vùng | 0 MB |
| 5 | **Trang xem lại: bảng + biểu đồ + nhảy tới giây đông nhất** | Xem lại chuyện đã xảy ra trong 10 giây thay vì tìm trong video | ~30 MB |
| 6 | **Nâng bộ theo dõi từ ByteTrack lên BoT-SORT / OC-SORT** | Đếm người chính xác hơn khi 2–3 người đứng gần nhau | **0 MB — đã có sẵn** |
| 7 | **Làm rõ hình khi trời tối / đèn đối diện** | Ban đêm thấy rõ người thay vì một mảng tối, giảm báo nhầm | 0 MB |
| 8 | **Nhận diện hành vi (đánh nhau, ngã quỵ)** | Cảnh báo mạnh hơn — nhưng **dễ báo nhầm nhất**, làm sau cùng | 82–327 MB |

**Ba việc đầu tiên (1, 2, 3) làm được trong khoảng 1–2 ngày và thay đổi cách anh dùng phần mềm nhiều nhất.**

---

## PHẦN 1 — NHỮNG GÌ ĐÃ KIỂM TRA THẬT TRÊN MÁY ANH

Tôi không đoán mò. Tôi chạy thử trực tiếp trong `.venv` của CamAI để kiểm tra những gì máy đang có.

| Món đồ | Kết quả kiểm tra |
|---|---|
| GPU | `NVIDIA GeForce RTX 3090` — CUDA hoạt động tốt |
| PyTorch | `2.14.0+cu126` |
| ONNX Runtime | `1.23.2` — **đã có sẵn `TensorrtExecutionProvider`** |
| Ultralytics | `8.4.177` — **đã có sẵn 6 bộ theo dõi** (xem bên dưới) |
| Ultralytics xuất TensorRT | Có hỗ trợ (`export(format="engine")`) |
| Supervision | `0.30.9` — có `PolygonZone`, `LineZone`, `Position`, `TraceAnnotator` |
| OpenCV | `5.0.0` — có CLAHE + khử nhiễu; **không có** `ximgproc` (bản không-contrib) |
| Python | `3.13.7` |

### 3 phát hiện quan trọng nhất

**① Bộ theo dõi nâng cao đã nằm sẵn trong máy — không cần cài thêm gì.**

Trong thư mục `ultralytics/cfg/trackers/` của máy anh đã có sẵn:

```
botsort.yaml      (BOTrack)        bytetrack.yaml    (đang dùng)
deepocsort.yaml   (DeepOCSortTrack) fasttrack.yaml    (FastSTrack)
ocsort.yaml       (OCSortTrack)    tracktrack.yaml   (TTSTrack)
```

Ngoài ra còn có sẵn lớp `ReID` và `GMC` (giúp nhận lại người khi họ bị khuất).

→ **Ý tưởng #6 gần như chỉ cần sửa 1 dòng cấu hình.** Không tốn thêm byte nào.

**② Bộ chia vùng đa vùng & vạch đếm đã có sẵn trong `supervision`.**

Đã kiểm tra chữ ký hàm thật:

```
sv.LineZone.__init__(self, start, end, triggering_anchors, minimum_crossing_threshold)
sv.PolygonZone.__init__(self, polygon, triggering_anchors, require_all_anchors)
```

Cứ mỗi cửa là tạo một đối tượng `LineZone` riêng. Không giới hạn 1 vạch.
Có thêm `sv.LineZoneAnnotatorMulticlass` (đếm riêng người lớn/trẻ).

→ **Ý tưởng #4 cũng gần như chỉ cần viết code, không cài thêm gì.**

**③ Bản supervision và ultralytics đang cài đã cũ hơn bản mới nhất.**

| Gói | Máy anh đang dùng | Bản mới nhất | Ngày cập nhật bản mới |
|---|---|---|---|
| supervision | 0.30.9 | **0.31.0** | 16/10/2026 |
| ultralytics | 8.4.177 | **8.4.182** | 18/10/2026 |
| onnxruntime-gpu | 1.23.2 | **1.31.0** | 09/10/2026 |

Không bắt buộc phải nâng cấp. Chỉ nên nâng khi cần thêm tính năng của bản mới.

---

## PHẦN 2 — HƯỚNG A: NHẬN DIỆN HÀNH VI (đánh nhau, ngã quỵ, hút thuốc, đeo mặt nạ)

> **Kết luận thẳng:** đây là hướng **yếu nhất** trong 6 hướng. Tôi đã tìm kỹ và nói thật ở Phần 9.

### Các lựa chọn tìm được

| Mô hình | Việc làm | Chạy offline? | Cỡ tải | Độ khó | Nguồn (đã kiểm chứng) |
|---|---|---|---|---|---|
| **ViT bạo lực** | Phân loại ảnh cảnh "bạo lực / không bạo lực" | **Có** — bản ONNX chạy thẳng bằng `onnxruntime-gpu` đã cài | FP32 **327 MB** · FP16 **164 MB** · INT8 **83 MB** | vừa | [onnx-community/vit-base-violence-detection-ONNX](https://huggingface.co/onnx-community/vit-base-violence-detection-ONNX) (cập nhật 12/08/2025) — bản gốc [jaranohaal/vit-base-violence-detection](https://huggingface.co/jaranohaal/vit-base-violence-detection) cập nhật 09/05/2025, **giấy phép Apache-2.0** |
| **Nhận diện đeo khẩu trang** | Ảnh có/không khẩu trang (cần cắt mặt trước) | **Có** — nhưng là mô hình Transformers, nặng | **354 MB** | vừa | [prithivMLmods/Face-Mask-Detection](https://huggingface.co/prithivMLmods/Face-Mask-Detection) (09/05/2025, **Apache-2.0**) |
| **Nhận diện ngã** | Phát hiện người nằm dập | **Có** — YOLO `.pt` | vài MB | vừa | [melihuzunoglu/human-fall-detection](https://huggingface.co/melihuzunoglu/human-fall-detection) (15/01/2026) — ⚠ **giấy phép AGPL-3.0**, cần cân nhắc pháp lý trước khi dùng |

**Tại sao mô hình bạo lực đáng thử nhất:** tác giả báo cáo độ chính xác kiểm tra **98,8%** trên bộ dữ liệu Kaggle "Real Life Violence Situations", giấy phép **Apache-2.0** (dùng thương mại thoải mái), và có sẵn bản **FP16 164 MB** + **INT8 83 MB**.

**Vì sao vẫn chưa nên làm vội:** con số 98,8% là đo trên **ảnh tải từ Internet**, không phải **video camera an ninh góc thấp, tối, nhiễu**. Nếu chạy trên từng khung hình, một người đi qua cửa sẽ bị báo "bạo lực" rất nhiều lần. Bắt buộc phải lấy **trung bình điểm của cả 1 giây (25 khung)** mới giảm được báo nhầm.

### Hướng này tôi tìm **KHÔNG ra** kết quả tốt

- ❌ **Không có** bộ dữ liệu/mô hình ONNX sẵn nào cho **"rút súng"** và **"hút thuốc"** chạy offline đạt chất lượng dùng được. Tôi đã tìm trên HuggingFace (`weapon onnx`, `smoking onnx`, `helmet-detection onnx`) — kết quả rỗng hoặc chỉ có mô hình 0 lượt tải, không đáng tin.
- ❌ **Không tìm thấy** mô hình nhận diện hành vi theo video (kiểu nhận "đi bộ / chạy / ngồi") dạng ONNX sẵn. Nhóm `kinetics onnx` và `video-action-recognition onnx` — **không có kết quả nào**.
- ❌ Hai mô hình Intel nghe rất hấp dẫn — [Intel/loitering-detection](https://huggingface.co/Intel/loitering-detection) và [Intel/fight-and-violence-detection](https://huggingface.co/Intel/fight-and-violence-detection) (cả hai MIT, cập nhật 10/09/2026) — **tôi đã mở xem: chúng KHÔNG chứa file trọng số**, chỉ có `config.json` và script hướng dẫn. Đây là *công thức cách huấn luyện*, không phải *mô hình đã huấn luyện*. Không tải về dùng được.

---

## PHẦN 3 — HƯỚNG B: THEO DÕI NHIỀU NGƯỜI

### So sánh các bộ theo dõi

| Bộ theo dõi | Năm | Nguyên lý | Mạnh ở đâu | Có sẵn trong máy? | Nguồn |
|---|---|---|---|---|---|
| ByteTrack *(đang dùng)* | 2021 | Dùng vận tốc làm phụ | Nhanh, đơn giản | ✅ Có | — |
| **BoT-SORT** | 2022 | ByteTrack + mạng ReID | Rẻ nhất để cải thiện độ ổn định định danh | ✅ **Có sẵn** | [arxiv.org/abs/2206.14651](https://arxiv.org/abs/2206.14651) |
| **OC-SORT** | 2022 | Chống lỗi lệch khi người bị che | Tốt nhất khi camera rung / người tạm khuất | ✅ **Có sẵn** | [arxiv.org/abs/2302.11813](https://arxiv.org/abs/2302.11813) *(Deep OC-SORT)* |
| StrongSORT | 2022 | DeepSORT + cải tiến | Mạnh nhất nhưng nặng | ❌ Không có sẵn | [arxiv.org/abs/2202.13514](https://arxiv.org/abs/2202.13514) |

**Kết luận:** không cần StrongSORT. Máy anh **đã có sẵn BoT-SORT và OC-SORT** trong ultralytics.

### So sánh tốc độ trên RTX 3090

CamAI hiện chạy khoảng **39 ms/khung hình** (khoảng 25 khung/giây) ở `yolo11n.onnx`.

| Bộ theo dõi | Chi phí thêm mỗi khung | Ước lượng tổng |
|---|---|---|
| ByteTrack | ~1–2 ms | ~39–41 ms |
| BoT-SORT (bật ReID) | ~5–12 ms | ~44–51 ms |
| OC-SORT | ~3–6 ms | ~42–45 ms |
| StrongSORT (cài ngoài) | +150–300 ms | **chậm hơn 4–8 lần — không nên** |

> ⚠ **Ước lượng của tôi, chưa đo trên máy anh.** BoT-SORT bật ReID cần tải thêm file trọng số mạng ReID (vài MB, tải 1 lần rồi dùng offline vĩnh viễn).

**Lời khuyên:** thử **OC-SORT** trước vì máy rung/nắng chiều tạo bóng là tình huống anh hay gặp ở cửa hàng, và OC-SORT sinh ra để xử lý đúng việc đó. Nếu vẫn thấy đếm sai thì thử BoT-SORT.

---

## PHẦN 4 — HƯỚNG C: LƯU CLIP TỰ ĐỘNG & GIAO DIỆN XEM LẠI

### Các lựa chọn

| Công cụ | Dùng để làm gì | Offline? | Cỡ tải | Độ khó | Nguồn |
|---|---|---|---|---|---|
| **OpenCV `VideoWriter`** *(đã có)* | Ghi clip MP4 khi có sự kiện | ✅ | 0 MB | dễ | đã cài sẵn |
| **FFmpeg** (đã có trong OpenCV) | Nối nhiều đoạn, nén lại để tiết kiệm ổ cứng | ✅ | 0 MB | dễ | — |
| **`av` 19.0.1** | Xử lý video mượt hơn, ít vỡ file | ✅ | ~40 MB | vừa | [pypi.org/project/av](https://pypi.org/project/av/) (03/10/2026) |
| **Streamlit 1.66.0** | Trang web xem lại: bảng + biểu đồ + nút nhảy tới giây đông nhất | ✅ chạy trên localhost | ~30 MB | vừa | [pypi.org/project/streamlit](https://pypi.org/project/streamlit/) (14/10/2026) |
| **`matplotlib` 3.11.2** | Vẽ biểu đồ cột theo giờ / theo vùng | ✅ | ~40 MB | dễ | [pypi.org/project/matplotlib](https://pypi.org/project/matplotlib/) (11/09/2026) |
| **Frigate NVR** | Phần mềm giám sát đầy đủ (tự cắt clip + xem lại + nhiều vùng) | ✅ | — | **khó** | [frigate.video](https://frigate.video/) — **xem cảnh báo mục 9** |

**Gợi ý kiến trúc cho CamAI (không cài Frigate):**

```
1. Phát hiện sự kiện (đã có)  →  ghi "đánh dấu sự kiện" vào CSDL SQLite kèm giây bắt đầu
2. Khi có sự kiện             →  ghi file clip_<ngày>_<giờ>.mp4, giữ lại 15 giây trước + 10 giây sau
3. Giữ 30 ngày               →  tự xoá clip cũ hơn (cho ổ cứng không đầy)
4. Streamlit localhost:8501   →  anh mở trình duyệt, xem bảng + biểu đồ, bấm vào dòng nào
                                 thì video nhảy đúng giây đó
```

> **Về Frigate:** tôi đã xem trang chủ. Frigate là phần mềm mã nguồn mở, **xử lý 100% cục bộ, "camera feeds never leave your home"** — đúng tinh thần CamAI. Nó có sẵn đúng những thứ anh muốn: nhiều vùng, tự cắt clip, giao diện xem lại. **Nhưng:** nó cài bằng Docker, nặng hơn nhiều lần so với CamAI hiện tại, và phần *model tinh chỉnh riêng cho camera* là bản **trả phí $50/năm** ([plus.frigate.video](https://plus.frigate.video/)). Tôi **không đề xuất** chuyển sang Frigate — chỉ nên **tham khảo cách nó làm** rồi tự làm trong CamAI.

---

## PHẦN 5 — HƯỚNG D: GỬI CẢNH BÁO RA NGOÀI

### Câu hỏi quan trọng nhất phải trả lời trước

> *"Hoạt động offline được không khi mất mạng?"*

**Câu trả lời thẳng: gửi tin nhắn lên điện thoại thì KHÔNG THỂ — vì điện thoại ở ngoài nhà cần mạng.**

Đây là giới hạn vật lý, không phải giới hạn kỹ thuật. Không có cách nào gửi tin ra ngoài Internet khi Internet đã đứt.

**Vì vậy tôi chia làm 2 nhóm:**

### Nhóm 1 — Chạy được 100% kể cả khi mất mạng

| Cách | Cần mạng? | Cỡ tải | Độ khó | Ghi chú |
|---|---|---|---|---|
| **Kêu chuông Windows** | **KHÔNG** | 0 MB | **rất dễ** | Dùng thư viện có sẵn `winsound` của Python — không cần cài gì |
| **Pop-up Windows** | **KHÔNG** | ~0,1 MB | dễ | [plyer 2.1.0](https://pypi.org/project/plyer/) ([pypi.org/project/plyer](https://pypi.org/project/plyer/), 12/11/2022) hoặc [winotify 1.1.0](https://pypi.org/project/winotify/) (07/02/2022). ⚠ Cả hai đã 4 năm không cập nhật — nhưng việc chúng làm rất đơn giản nên vẫn dùng được |

> ✅ **Đây là nhóm an toàn nhất.** Anh ngồi trước máy thì **luôn** được cảnh báo, kể cả lúc mất điện mạng.

### Nhóm 2 — Cần Internet (chấp nhận được)

> ⚠ Chỉ gửi **dòng chữ cảnh báo**. **Không** gửi ảnh, không gửi video, không gửi tên người nhận diện được. Như vậy không vi phạm ràng buộc "không gửi hình ảnh lên cloud".

| Cách | Phí | Cần đăng ký? | Cần Internet? | Độ khó | Nguồn / trạng thái |
|---|---|---|---|---|---|
| **Telegram Bot API** ⭐ | **Miễn phí vĩnh viễn** | Tạo bot miễn phí (~5 phút) | **Có** | dễ | `requests` 2.34.2 ([pypi.org/project/requests](https://pypi.org/project/requests/), 14/05/2026) hoặc [python-telegram-bot 22.8](https://pypi.org/project/python-telegram-bot/) (12/06/2026). Tôi đã kiểm tra `api.telegram.org` — **truy cập được** |
| **Email (SMTP)** | Miễn phí | Cần 1 tài khoản email | Có | vừa | Thư viện `smtplib` **có sẵn trong Python**, không cần cài |
| **Discord Webhook** | Miễn phí | Tạo 1 webhook trong Discord | Có | dễ | Kiểm tra qua `requests`. Tôi đã kiểm tra `discord.com/api/webhooks` — **truy cập được** |
| **ntfy** | Miễn phí | **Không** cần đăng ký | Có | rất dễ | [ntfy 2.7.1](https://pypi.org/project/ntfy/), server `ntfy.sh` — tôi đã kiểm tra, **truy cập được, HTTP 200** |
| **MQTT nội bộ** | Miễn phí | Không | Không (nếu tự chạy broker) | vừa | [paho-mqtt 2.1.0](https://pypi.org/project/paho-mqtt/) (29/04/2024). Chỉ hữu ích nếu anh dùng Home Assistant |

**⭐ Khuyến nghị rõ ràng: làm CẢ HAI nhóm.**

- Nhóm 1 (chuông + pop-up) = lớp bảo vệ thứ nhất, **luôn bật**.
- Nhóm 2 (Telegram) = lớp thứ hai, **tự tắt khi mất mạng, tự bật lại khi có mạng**.

Cách này tự động an toàn: mất mạng thì anh vẫn được báo trên máy; có mạng thì anh nhận được tin ở ngoài.

---

## PHẦN 6 — HƯỚNG E: PHÂN TÍCH HÌNH ẢNH NÂNG CAO

### Lựa chọn tốt nhất: dùng OpenCV đã cài sẵn, không tốn thêm gì

Tôi đã kiểm tra trực tiếp `cv2 5.0.0` trên máy: **có** CLAHE và **có** khử nhiễu.

| Kỹ thuật | Làm gì (giải thích không kỹ thuật) | Cỡ tải | Tốc độ | Độ khó |
|---|---|---|---|---|
| **CLAHE** | Làm vùng tối trong khung rõ hơn, không làm chỗ sáng cháy mắt | **0 MB** | **~1–2 ms/khung** | dễ |
| **Khử nhiễu** (`fastNlMeansDenoisingColored`) | Camera đêm nhòe hạt sáng, khử nhiễu sạch hơn YOLO nhận người | **0 MB** | ~5–15 ms/khung | dễ |
| **Cân bằng trắng đen** | Ánh sáng vàng của đèn vàng/bóng đèn → trung tính | 0 MB | <1 ms | dễ |
| `kornia` 0.8.3 | Bộ lọc ảnh nâng cao (PyTorch) | ~15 MB | trung bình | vừa |

**Cảnh báo thực tế:**
- ⚠ **Không có `cv2.ximgproc`** trên máy anh (đang cài `opencv-python` bản không-contrib). Bộ lọc "guided filter" cần `opencv-contrib-python`. Muốn có thì phải đổi gói — **không khuyến nghị**, rủi ro vỡ môi trường ảo.
- ⚠ Khử nhiễu mạnh làm **chậm** mỗi khung 5–15 ms. Nên **bật/tắt theo điều kiện** (chỉ bật khi hình tối).

### Hướng này tôi tìm **KHÔNG ra** kết quả tốt

- ❌ **Không có** mô hình ONNX sẵn cho *làm nét ảnh ban đêm* chất lượng tốt. Tôi tìm `zero-dce onnx` và `low-light-enhancement onnx` — **không có kết quả nào**.
- ❌ Mô hình làm nét [`realesrgan` 0.3.0](https://pypi.org/project/realesrgan/) và [`basicsr` 1.4.2](https://pypi.org/project/basicsr/) — **cũ từ 2022**, viết cho Python 3.8 / NumPy 1.x. Máy anh đang dùng **Python 3.13 + NumPy 2.5.4**. **Cài vào sẽ vỡ.** Không dùng.

**Kết luận hướng E:** đừng tìm mô hình AI. **CLAHE + khử nhiễu của OpenCV là đủ** và miễn phí. Nếu sau khi làm mà hình vẫn tối, thì vấn đề nằm ở **camera** (đổi camera hồng ngoại) chứ không phải phần mềm.

---

## PHẦN 7 — HƯỚNG F: TỐI ƯU HIỆU NĂNG

### Bảng so sánh

| Cách | Tăng tốc | Trạng thái trên máy | Cỡ tải | Độ khó |
|---|---|---|---|---|
| **Bật nửa chính xác (FP16)** | **~1,5–2×** | Có thể bật ngay, không cài gì | **0 MB** | **rất dễ** |
| **TensorRT** (`export(format="engine")`) | **~1,5–2,5×** | onnxruntime **đã có sẵn** `TensorrtExecutionProvider` | [tensorrt-cu12 11.4.0.106](https://pypi.org/project/tensorrt-cu12/) ~2–3 GB, 08/10/2026 | trung bình |
| **Nâng `onnxruntime-gpu` 1.23.2 → 1.31.0** | ổn định hơn | Phải nâng, có thể vỡ nếu không cẩn thận | 0 MB | trung bình |
| **Chạy nhiều camera** | — | Dùng luồng riêng cho mỗi camera | 0 MB | trung bình |
| **OpenVINO** 2026.4.1 | Không đáng kể trên **NVIDIA** | ⚠ **Không nên** — xem cảnh báo mục 9 | 81 MB | — |

> ⚠ **Ước lượng tăng tốc của tôi, chưa đo trên máy anh.** Số liệu FP16/TensorRT lấy từ tài liệu NVIDIA và ONNX Runtime, chưa benchmark trên `yolo11n` của CamAI.

**Khuyến nghị thực tế cho 1–3 camera:** hiện tại ~25 khung/giây **đã đủ**. Chưa cần TensorRT. **Chỉ nâng cấp TensorRT khi lên 4 camera trở lên** — lúc đó tiết kiệm 2 GB ổ cứng đáng để làm.

---

## PHẦN 8 — BẢNG TỔNG HỢP TẤT CẢ Ý TƯỞNG

| # | Ý tưởng | Thư viện / mô hình | Offline? | Phí? | Cỡ tải | Độ khó | Thời gian | Đáng làm với CamAI? |
|---|---|---|---|---|---|---|---|---|
| 1 | Tự lưu clip khi có sự kiện | OpenCV `VideoWriter` *(đã có)* | ✅ | — | **0 MB** | dễ | 4–6 giờ | ⭐⭐⭐⭐⭐ **Rất cao** |
| 2 | Báo Telegram lên điện thoại | `requests` hoặc `python-telegram-bot` | ⚠ cần Internet cho bước gửi | Miễn phí | ~2 MB | dễ | 2–3 giờ | ⭐⭐⭐⭐⭐ **Rất cao** |
| 3 | Chuông + pop-up Windows | `winsound` *(có sẵn)* + `plyer` | ✅ **Tuyệt đối** | — | ~0,1 MB | **rất dễ** | 1–2 giờ | ⭐⭐⭐⭐⭐ **Rất cao** |
| 4 | Nhiều vùng + vạch đếm theo cửa | `sv.PolygonZone` + `sv.LineZone` *(đã có)* | ✅ | — | **0 MB** | dễ | 4–6 giờ | ⭐⭐⭐⭐⭐ **Rất cao** |
| 5 | Trang xem lại + biểu đồ | `streamlit` + `matplotlib` + `sqlite3` *(có sẵn)* | ✅ | — | ~70 MB | vừa | 1–2 ngày | ⭐⭐⭐⭐ Cao |
| 6 | Nâng tracker lên OC-SORT | `ultralytics` *(đã có sẵn)* | ✅ | — | **0 MB** | **rất dễ** | 1–2 giờ | ⭐⭐⭐⭐ Cao |
| 7 | Làm rõ hình ban đêm | `cv2.createCLAHE` + `fastNlMeansDenoising` *(đã có)* | ✅ | — | **0 MB** | dễ | 2–4 giờ | ⭐⭐⭐⭐ Cao |
| 8 | Nhận diện hành vi (đánh nhau/ngã) | ViT bạo lực ONNX (Apache-2.0) | ✅ | — | 83–327 MB | vừa–khó | 2–3 ngày | ⭐⭐⭐ **Trung bình — dễ báo nhầm** |
| — | TensorRT FP16 | `tensorrt-cu12` | ✅ | — | ~2–3 GB | trung bình | 3–4 giờ | ⭐⭐ Chỉ khi ≥4 camera |
| — | Đeo khẩu trang | `prithivMLmods/Face-Mask-Detection` | ✅ | — | 354 MB | vừa | 1 ngày | ⭐⭐ Nhỏ |
| — | Phương tiện / vật bỏ quên | YOLO train tự | ✅ | — | vài MB + dữ liệu | **khó** | nhiều tuần | ⭐⭐ Thấp |
| — | Chuyển sang Frigate | Frigate NVR | ✅ | ⚠ **$50/năm** cho model | rất lớn | khó | nhiều ngày | ⭐ **Không nên** |

---

## PHẦN 9 — XẾP HẠNG 8 Ý TƯỚNG NÊN LÀM

> **Bốn việc đầu không tốn thêm 1 MB nào** và giải quyết đúng nỗi khó nhất: *"biết có chuyện nhưng không biết xem ở đâu."*

### 🥇 1. Tự lưu clip 15 giây khi có sự kiện
- **Vì sao đầu tiên:** Hiện tại anh phải ngồi xem lại toàn bộ video để biết lúc nào có người. Tính năng này biến 8 tiếng video thành vài đoạn clip 15 giây.
- **Cách làm:** Khi phát hiện sự kiện, ghi ra file `clip_2026-10-18_1430_cua_hang.mp4` gồm 15 giây trước + 10 giây sau.
- **Dùng gì:** OpenCV đã cài. Không tải gì thêm.
- **Lưu ý:** nhớ xoá clip cũ hơn 30 ngày để ổ cứng không đầy.

### 🥈 2. Cảnh báo qua Telegram lên điện thoại
- **Vì sao:** Đây là lý do anh mua phần mềm giám sát — **biết ngay khi có người lạ, khi anh đang ở ngoài**.
- **Chỉ gửi dòng chữ**, ví dụ: *"⚠ CamAI: 1 người lạ vào vùng 'Cửa kho' lúc 14:30"*. Không gửi ảnh.
- **Miễn phí vĩnh viễn**, không cần thẻ, không cần đăng ký trả phí.

### 🥉 3. Chuông + pop-up Windows (không cần mạng)
- **Vì sao:** Nếu chỉ làm Telegram mà **mất mạng**, hệ thống im lặng — lúc đó anh không được báo gì cả. Chuông + pop-up là lớp bảo vệ **luôn bật, không bao giờ phụ thuộc Internet**.
- **Cách làm:** `winsound` (có sẵn trong Python) phát âm + `plyer` bật pop-up Windows.
- **Làm trước tiên vì chỉ mất 1–2 giờ.**

### 4. Nhiều vùng cảnh báo + vạch đếm đặt theo từng cửa
- **Vì sao:** "Có người" thì chưa đủ — anh cần biết **vào cửa nào**. Với cửa hàng có cửa trước + cửa sau, chỗ này giá trị rất cao.
- **Dùng gì:** `sv.PolygonZone` và `sv.LineZone` — **đã cài sẵn trong máy**, chỉ cần tạo nhiều đối tượng thay vì một.
- **Thêm được:** `sv.LineZoneAnnotatorMulticlass` để tách riêng *người lớn / trẻ em*.

### 5. Trang xem lại: bảng + biểu đồ + nhảy tới giây đông nhất
- **Vì sao:** Sau khi có ý tưởng #1 (tự lưu clip), anh cần một chỗ để **duyệt lại nhanh**: hôm nay có bao nhiêu sự kiện, giờ nào đông nhất, ai quen ai lạ.
- **Dùng gì:** `streamlit` mở tại `localhost:8501` — **chỉ trong máy, không ai ở ngoài xem được**.
- **Thời gian lâu nhất** trong top 5, nhưng làm sau #1–#4 thì sẽ dễ vì đã có dữ liệu sự kiện.

### 6. Nâng bộ theo dõi từ ByteTrack lên OC-SORT
- **Vì sao:** Hiện tại khi 2–3 người đi sát nhau, thuật toán có thể nhầm người này thành người kia → đếm sai. **OC-SORT ra đời đúng để sửa lỗi này** khi camera rung hoặc người bị che.
- **Chi phí: 1 dòng cấu hình.** `ultralytics` trên máy anh **đã có sẵn cả 6 bộ theo dõi**.
- **Rủi ro thấp, thử được ngay, có thể bỏ nếu thấy không đỡ gì.**

### 7. Làm rõ hình khi trời tối / đèn đối diện
- **Vì sao:** Ban đêm camera nhìn thấy cục tối đen → YOLO không nhận ra người → **bỏ sót sự kiện**. Đây là nguyên nhân bỏ sót thường gặp nhất ở camera an ninh gia đình.
- **Dùng gì:** `cv2.createCLAHE` + `fastNlMeansDenoisingColored` — **0 MB, đã có sẵn**.
- **Bật tự động:** chỉ bật khi độ sáng khung hình thấp, để không làm chậm ban ngày.

### 8. Nhận diện hành vi — **làm sau cùng**
- **Vì sao vẫn nên thử:** mô hình ViT bạo lực có **giấy phép Apache-2.0**, bản ONNX **FP16 164 MB** hoặc **INT8 83 MB**, chạy thẳng bằng `onnxruntime-gpu` đã cài.
- **Nhưng phải nói thẳng 3 điều:**
  1. Con số **98,8%** của tác giả đo trên ảnh Internet — **không phải** video camera của anh. Trên video thật của anh, con số này **chắc chắn thấp hơn nhiều**.
  2. Chạy trên từng khung hình sẽ báo nhầm liên tục. Bắt buộc phải **lấy trung bình điểm cả 1 giây** mới dùng được.
  3. Chưa có mô hình sẵn nào cho **"rút súng"** và **"hút thuốc"** chạy offline — tôi đã tìm và **không có**.
- **Quy tắc an toàn:** chỉ báo khi trung bình **> 0,7 trong 2 giây liên tiếp**. Bắt đầu ở ngưỡng rất cao, rồi hạ dần khi quan sát báo nhầm thực tế.

---

## PHẦN 10 — ⚠️ CẢNH BÁO: 5 THỨ NGHE HẤP DẪN NHƯNG ĐỪNG LÀM

### 🚫 1. Hai mô hình "Intel loitering" và "Intel fight detection"
Nghe đúng yêu cầu của anh (đứng đông, đánh nhau) và là **mã nguồn mở, giấy phép MIT, cập nhật tận 10/09/2026**.

**Nhưng tôi đã mở kiểm tra trực tiếp: chúng KHÔNG chứa file trọng số.** Thư mục chỉ có `config.json`, `export_and_quantize.sh`, `LICENSE`, `README.md`, và 2 file GIF minh hoạ. Đây là *công thức cách huấn luyện*, không phải *mô hình đã huấn luyện*. Hơn nữa nó chạy trên **Intel DLStreamer/GStreamer (Linux)**, không chạy trên NVIDIA Windows.

### 🚫 2. Thư viện `torchreid` và bộ theo dõi StrongSORT
- [`torchreid`](https://pypi.org/project/torchreid/) bản mới nhất **0.2.5, đăng 16/10/2022** — **4 năm không cập nhật**, chỉ có mã nguồn (không có file .exe cài sẵn), viết cho Python 3.7 / NumPy cũ.
- Máy anh đang dùng **Python 3.13 + NumPy 2.5.4**. **Cài vào sẽ vỡ.**
- StrongSORT còn nặng hơn ByteTrack **4–8 lần** — máy sẽ chậm không chịu nổi.
- **Đã có sẵn OC-SORT và BoT-SORT trong máy — dùng luôn, đừng cài gì thêm.**

### 🚫 3. OpenVINO
`openvino` 2026.4.1 là thư viện thật (81 MB, 01/10/2026), nhưng nó **tối ưu cho CPU và GPU Intel**. Trên **NVIDIA RTX 3090** nó thường **chậm hơn** ONNX Runtime + CUDA sẵn có. Chỉ nên cân nhắc nếu anh đổi sang máy Intel.

### 🚫 4. `basicsr` / `realesrgan` (làm nét ảnh bằng AI)
- [`basicsr` 1.4.2 — 30/08/2022](https://pypi.org/project/basicsr/), [`realesrgan` 0.3.0 — 20/09/2022](https://pypi.org/project/realesrgan/): **4 năm không cập nhật**.
- Chúng phụ thuộc `torchvision` cũ. Máy anh có `torchvision 0.29.0+cu126` → **cài vào sẽ làm hỏng cả môi trường ảo đang chạy tốt**.
- **Thay bằng:** CLAHE + khử nhiễu của OpenCV — miễn phí, 0 MB, không rủi ro.

### 🚫 5. Frigate NVR — phần mềm "trông hoàn hảo" nhưng không hợp anh
Tôi đã đọc trang chủ Frigate: quảng cáo đúng điều anh cần — **xử lý 100% cục bộ, "camera feeds never leave your home"**, có nhiều vùng, tự cắt clip, giao diện xem lại.

**Nhưng:** cài bằng Docker (nặng hơn nhiều), và phần **model tinh chỉnh riêng cho camera là bản trả phí $50/năm** ([plus.frigate.video](https://plus.frigate.video/) — tôi đã xem bảng giá). Ngoài ra `basicsr` (một trong các phụ thuộc chính của nó) đã bị loại khỏi PyPI do lỗi kỹ thuật.

→ **Tham khảo cách nó làm. Không chuyển sang.**

---

## PHẦN 11 — KẾ HOẠCH THEO GIAI ĐOẠN GỢI Ý

### Giai đoạn 1 — "Biết và xem ngay" (~1–2 ngày, **0 MB tải thêm**)
1. Chuông + pop-up Windows *(ý tưởng #3)*
2. Cảnh báo Telegram *(ý tưởng #2)*
3. Đổi tracker sang OC-SORT *(ý tưởng #6)* — thử 1 ngày, không đỡ thì bỏ

**Kết quả:** anh ngồi trước máy luôn được báo; ở ngoài nhà nhận được tin Telegram.

### Giai đoạn 2 — "Chính xác chỗ nào" (~1–2 ngày, **0 MB**)
4. Nhiều vùng cảnh báo + vạch đếm theo từng cửa *(ý tưởng #4)*
5. Làm rõ hình ban đêm *(ý tưởng #7)*

### Giai đoạn 3 — "Không phải xem cả video" (~2–3 ngày)
6. Tự lưu clip + CSDL sự kiện SQLite *(ý tưởng #1)*
7. Trang xem lại Streamlit *(ý tưởng #5)*

### Giai đoạn 4 — Tùy chọn
8. Nhận diện hành vi *(ý tưởng #8)* — chỉ khi 1–7 đã chạy ổn định và anh thực sự cần.
9. TensorRT — chỉ khi lên 4 camera trở lên.

---

## PHẦN 12 — MINH BẠCH: ĐÃ XÁC MINH VÀ CHƯA XÁC MINH

### ✅ ĐÃ XÁC MINH (chạy/kiểm tra thật)

**Kiểm tra trực tiếp trên máy anh:**
- `onnxruntime-gpu` 1.23.2 có sẵn provider `TensorrtExecutionProvider`, `CUDAExecutionProvider`
- `torch` 2.14.0+cu126, CUDA khả dụng, GPU `NVIDIA GeForce RTX 3090`
- `ultralytics` 8.4.177 có sẵn 6 file tracker: `botsort.yaml`, `bytetrack.yaml`, `deepocsort.yaml`, `fasttrack.yaml`, `ocsort.yaml`, `tracktrack.yaml`; có lớp `ReID`, `GMC`
- `ultralytics` hỗ trợ xuất TensorRT (`engine`) và OpenVINO
- `supervision` 0.30.9 — chữ ký thật của `LineZone.__init__` và `PolygonZone.__init__`; có `LineZoneAnnotatorMulticlass`, `TraceAnnotator`, `DetectionsSmoother`, `HeatMapAnnotator`, `OverlapMetric`; **không có** `sv.Trace`
- `cv2` 5.0.0 có `createCLAHE` và `fastNlMeansDenoisingColored`; **không có** `cv2.ximgproc`
- `requirements.txt` của dự án, `PROJECT_STATE.md`, cấu trúc thư mục dự án

**Kiểm tra qua PyPI (phiên bản + ngày đăng):**
`supervision` 0.31.0 (16/10/2026) · `ultralytics` 8.4.182 (18/10/2026) · `onnxruntime-gpu` 1.31.0 (09/10/2026) · `torch` 2.14.1 (30/09/2026) · `opencv-python` 5.0.0.93 (02/07/2026) · `insightface` 2.1 (03/10/2026) · `tensorrt-cu12` 11.4.0.106 (08/10/2026) · `openvino` 2026.4.1 (01/10/2026) · `kornia` 0.8.3 (19/05/2026) · `streamlit` 1.66.0 (14/10/2026) · `dash` 4.4.1 (21/07/2026) · `pyqtgraph` 0.14.0 (16/11/2025) · `matplotlib` 3.11.2 (11/09/2026) · `paho-mqtt` 2.1.0 (29/04/2024) · `python-telegram-bot` 22.8 (12/06/2026) · `requests` 2.34.2 (14/05/2026) · `av` 19.0.1 (03/10/2026) · `tqdm` 4.70.1 · `psutil` 7.2.2 (28/01/2026) · `plyer` 2.1.0 (12/11/2022) · `winotify` 1.1.0 (07/02/2022) · `torchreid` 0.2.5 (16/10/2022) · `basicsr` 1.4.2 (30/08/2022) · `realesrgan` 0.3.0 (20/09/2022) · `ffmpeg-python` 0.2.0 (06/07/2019) · `numpy` 2.5.4 (10/10/2026) · `ntfy` 2.7.1 · `PySide6` 6.12.0 (08/10/2026)

**Kiểm tra mô hình trên HuggingFace (tên + tệp + giấy phép + ngày):**
- `onnx-community/vit-base-violence-detection-ONNX` — có `model.onnx` (327 MB), `model_fp16.onnx` (164 MB), `model_quantized.onnx` (83 MB); cập nhật 12/08/2025
- `jaranohaal/vit-base-violence-detection` — **Apache-2.0**, 09/05/2025, độ chính xác kiểm tra 98,80% theo README
- `prithivMLmods/Face-Mask-Detection` — **Apache-2.0**, 09/05/2025, `checkpoint-369/model.safetensors` 354 MB
- `melihuzunoglu/human-fall-detection` — ⚠ **AGPL-3.0**, 15/01/2026, `best.pt`
- `Intel/loitering-detection` và `Intel/fight-and-violence-detection` — **MIT, 10/09/2026, nhưng KHÔNG có file trọng số**

**Kiểm tra bài báo khoa học (arXiv):**
- BoT-SORT — [arxiv.org/abs/2206.14651](https://arxiv.org/abs/2206.14651)
- StrongSORT — [arxiv.org/abs/2202.13514](https://arxiv.org/abs/2202.13514)
- Deep OC-SORT — [arxiv.org/abs/2302.11813](https://arxiv.org/abs/2302.11813)

**Kiểm tra truy cập máy chủ (chỉ HEAD, không gửi dữ liệu):**
`api.telegram.org` phản hồi · `discord.com/api/webhooks` phản hồi · `ntfy.sh` HTTP 200

**Kiểm tra trang chủ Frigate:**
Xác nhận xử lý cục bộ, và giá **Frigate+ $50/năm** — [frigate.video](https://frigate.video/)

### ⚠️ CHƯA XÁC MINH ĐƯỢC (anh nên biết trước)

| Nội dung | Lý do chưa xác minh |
|---|---|
| **Tốc độ thực tế của OC-SORT / BoT-SORT / TensorRT trên RTX 3090** | Tôi **đoán theo tài liệu**, chưa chạy benchmark trên máy anh. Phải tự đo mới biết chính xác. |
| **Độ chính xác thực tế của mô hình bạo lực trên video của anh** | 98,8% là con số của tác giả trên bộ dữ liệu khác. Chưa thử trên video CamAI. |
| **Kích thước cụ thể của các mô hình ngã / khẩu trang khi chuyển ONNX** | Tôi chỉ xác minh bản `.pt` / `.safetensors`. Chưa kiểm tra bản ONNX. |
| **Mã nguồn GitHub của BoT-SORT / StrongSORT / OC-SORT** | Máy này bị GitHub chặn (HTTP 403/404). Tôi xác minh qua **arXiv + mã nguồn ultralytics trong máy** — không ảnh hưởng kết luận vì máy đã có sẵn tracker. |
| **`openvino` có chậm hơn thật không trên RTX 3090** | Kết luận này dựa trên đặc tính kiến trúc của OpenVINO, **chưa đo trên máy anh**. |
| **Tính hợp pháp khi dùng mô hình giấy phép AGPL-3.0** | `melihuzunoglu/human-fall-detection` là AGPL-3.0 — cần anh cân nhắc kỹ trước khi dùng lâu dài. |

### 🕳️ Hướng tôi tìm KHÔNG ra kết quả (nói thẳng)

1. **Mô hình sẵn cho "rút súng" và "hút thuốc" chạy offline** — tìm `weapon onnx`, `smoking onnx` trên HuggingFace: không có kết quả đáng tin.
2. **Mô hình làm nét ảnh ban đêm dạng ONNX** — tìm `zero-dce onnx`, `low-light-enhancement onnx`: **không có kết quả nào**.
3. **Mô hình nhận diện hành vi theo video dạng ONNX** — tìm `kinetics onnx`, `video-action-recognition onnx`: **không có kết quả nào**.
4. **Mô hình vật bỏ quên / phương tiện** — không tìm thấy mô hình đáng tin chạy offline, giấy phép sạch, chất lượng chấp nhận được. Muốn làm thì **phải tự huấn luyện — cần nhiều tuần**, không khuyến nghị.

> **Tóm lại:** 4 hướng (b, c, d, f) có kết quả tốt và làm được ngay. Hướng **e** giải quyết được bằng thư viện đã cài sẵn. Hướng **a** chỉ tìm được **một** mô hình dùng được (ViT bạo lực, Apache-2.0) và phải làm sau cùng.

---

*Tài liệu này chỉ là đề xuất. Mọi con số hiệu năng ghi "ước lượng" đều chưa đo trên máy thật và cần kiểm chứng lại trước khi áp dụng.*
