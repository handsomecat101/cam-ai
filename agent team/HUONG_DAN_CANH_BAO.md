# Hướng dẫn cài cảnh báo Telegram cho CamAI

Tài liệu này viết cho người **chưa từng dùng Telegram Bot**. Làm đúng từng bước là được.

---

## 0. Cảnh báo này là cái gì? Cần gì?

Khi CamAI thấy có người trong vùng canh, nó báo anh **2 nơi**:

| Kênh | Cách hoạt động | Cần mạng? |
|---|---|---|
| **1. Tin nhắn Telegram** (quan trọng nhất) | Tin nhắn chữ bay vào điện thoại anh, anh ở ngoài nhà vẫn thấy | **Có** (điện thoại + máy tính cần Internet) |
| **2. Chuông + hộp thoại trên máy tính** | Máy tính kêu *bíp* và bật lên một hộp thoại màu vàng ngay trên màn hình | **Không** (vẫn chạy khi mất mạng) |

> 🔒 **CamAI chỉ gửi CHỮ. Không bao giờ gửi hình ảnh hay video lên Telegram.**
> Video vẫn nằm trên máy tính của anh, không bị đẩy lên Internet.

Anh chỉ cần làm phần Telegram (mục 1–4). Phần chuông/hộp thoại đã chạy sẵn, không cần làm gì.

---

## 1. Tạo con bot Telegram (lấy token)

Bot là một con "trợ lý" trong Telegram. Nó **không tự gửi tin** — chỉ khi CamAI nhờ nó gửi thì nó mới gửi.

1. Mở ứng dụng **Telegram** trên điện thoại (hoặc Telegram Desktop trên máy tính).
2. Bấm vào ô tìm kiếm phía trên, gõ: `@BotFather` → bấm vào kết quả có tên **BotFather** (dấu tick xanh, tên chính tả `BotFather`).
   - Nếu anh gõ trong ô tìm kiếm mà không ra, hãy vào Telegram Desktop rồi làm tiếp từ đây.
3. Bấm nút **START** (hoặc gõ lệnh `/start`) ở cuối màn hình.
4. Gõ lệnh: `/newbot` rồi bấm Enter.
5. Bot hỏi: *"Alright, a new bot. How are we going to call it?"*
   → Gõ tên hiển thị, chữ được phép có dấu cách. Ví dụ: `CamAI Nha Toi`
   *(Chỉ là tên hiển thị thôi, anh đổi thoải mái.)*
6. Bot hỏi tiếp: *"Good. Now let's choose a username for your bot"*
   → Gõ một tên đăng nhập **không có dấu cách**, phải **kết thúc bằng chữ `bot`**. Ví dụ: `camai_nha-toi_bot`
   - Username phải là duy nhất toàn mạng Telegram. Nếu báo *"username is already taken"* thì thêm vài số vào cuối, ví dụ `camai_nha-toi_bot2026`.
7. **Bot trả về đoạn mã màu xanh**, dạng:

   ```
   9876543210:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
   ```

   👉 **Đoạn này chính là TOKEN. Copy nó, giữ cẩn thận.** (Cách dùng ở bước 3. Cách bảo mật ở mục 6.)

**Chưa tạo bot được?** Không sao cả — bỏ qua Telegram, phần chuông + hộp thoại trên máy tính vẫn dùng được bình thường.

---

## 2. Lấy `chat_id` (mã của cuộc trò chuyện)

`chat_id` là mã số của "không gian" mà tin nhắn sẽ tới. Với cách đơn giản nhất, nó là **ID của chính tài khoản Telegram của anh**.

1. Mở Telegram, tìm `@userinfobot` → bấm vào → bấm **START**.
2. Bot trả về đoạn chữ, ví dụ:

   ```
   Id: 123456789
   First: An
   Username: an123
   ```

   👉 Số `123456789` chính là `chat_id` của anh. Copy nó.

*(Mẹo: nếu anh muốn bot nhắn vào một **nhóm chat** thay vì nhắn riêng — thêm bot vào nhóm, vào nhóm gõ `@userinfobot`, dùng `getUpdates` để lấy `chat.id` của nhóm, nhập số đó vào `chat_id` kèm dấu trừ, ví dụ `-1001234567890`. Nhóm phải **công khai** (group privacy off) để bot đọc được tin nhắn.)*

---

## 3. Điền vào file cấu hình `canh_bao.ini`

1. Mở thư mục `H:\AI Project\cam-ai`.
2. Tạo một **file text mới**, tên **`canh_bao.ini`**.
   - ⚠️ **Phải là `.ini`, không phải `.txt`.** Windows hay tự thêm `.txt` vào cuối — xem cách làm đúng bên dưới.
   - Cách chắc chắn: mở Notepad → *File* → *Save As* → Ở ô *Save as type* chọn **All files (\*.\*)** → đặt tên `canh_bao.ini` → *Save as type* chọn **All files**. Khi đó Notepad **không** tự thêm `.txt`.
3. Dán nội dung mẫu sau vào (thay `DAN_TOKEN_CUA_ANH` và `SO_CHAT_ID_CUA_ANH` bằng số thật của anh):

```ini
[telegram]
token = DAN_TOKEN_CUA_ANH
chat_id = SO_CHAT_ID_CUA_ANH
```

   Ví dụ đã điền thật:

```ini
[telegram]
token = 9876543210:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
chat_id = 123456789
```

4. Lưu lại (Ctrl + S).

**Hai lỗi hay gặp nhất:**

- **Thừa khoảng trắng**: `token = 123` (có khoảng trắng) là đúng. `token=123` cũng chạy, nhưng giữ cho giống mẫu cho chắc.
- **Dòng `[telegram]` phải còn nguyên**, có cả hai chữ và dấu ngoặc vuông. Xóa mất là phần mềm không tìm thấy token.

> 💡 Muốn **tắt Telegram** mà không cần xóa file: đổi tên file thành `canh_bao.ini.bak`, hoặc xem mục 5.

---

## 4. Kiểm tra đã cấu hình đúng chưa

Mở **Command Prompt** (nhấn `Ctrl + R`, gõ `cmd`, Enter), rồi gõ:

```
cd /d "H:\AI Project\cam-ai"
.venv\Scripts\python.exe canh_bao.py --kiem-tra
```

Đọc kết quả:

| Mục trong kết quả | Nghĩa là |
|---|---|
| `Token : 987654...Dsaw <- canh_bao.ini [telegram] token` | ✅ Đã đọc token từ file |
| `Chat ID : 123456789 <- canh_bao.ini [telegram] chat_id` | ✅ Đã đọc chat_id |
| `[5/6] ... [OK] Da gui thanh cong` | ✅ **Tin đã về điện thoại** — mở Telegram kiểm tra |
| `[5/6] ... [LOI] khong gui duoc: ...` | ❌ Xem mục *Xử lý lỗi* bên dưới |
| `CHUA san sang` | ❌ Chưa tìm thấy token/chat_id — làm lại mục 3 |

**Đang yên lặng và không hiện gì?** Chạy với đầy đủ đường dẫn:

```
H:\AI Project\cam-ai\.venv\Scripts\python.exe H:\AI Project\cam-ai\canh_bao.py --kiem-tra
```

Nếu Telegram nhận được tin, anh sẽ thấy trong bước `[3/6]` tiếng **bíp** và bước `[4/6]` một **hộp thoại vàng** trên màn hình. Hộp thoại tự đóng sau 60 giây nên không cần bấm gì.

---

## 5. Cách tắt khi không dùng

Chọn **một** trong các cách sau, cách nào cũng được:

| Cách | Làm gì | Kết quả |
|---|---|---|
| **A. Đơn giản nhất** | Đổi tên file `canh_bao.ini` → `canh_bao.ini.bak` | Hết cấu hình, phần mềm chỉ còn chuông + hộp thoại |
| **B. Tắt hẳn cả 2 kênh** | Khi chạy thêm tham số `--khong-telegram --khong-chuong --khong-hien-hop-thoai` | Im lặng hoàn toàn |
| **C. Bỏ cảnh báo khỏi CamAI** | Trong `cam_ai_core.py`, xoá hoặc chú thích dòng gọi `CANH_BAO.guii(...)` (xem mục 7) | CamAI không còn gọi cảnh báo |
| **D. Gỡ hẳn 2 file** | Xoá `canh_bao.py` và `HUONG_DAN_CANH_BAO.md` | Xem mục 7 trước khi xoá, vì `cam_ai_core.py` có gọi tới |

> Nếu dùng **cách C hoặc D**, phải bỏ luôn dòng `from canh_bao import CanhBao` trong `cam_ai_core.py`, nếu không phần mềm sẽ báo lỗi khi khởi động.

**Không muốn cài lại nữa?** Chỉ cần giữ nguyên file `canh_bao.ini` ở chỗ cũ, mỗi khi muốn dùng lại chỉ cần đổi tên nó về.

---

## 6. 🔒 Cảnh báo bảo mật (đọc phần này)

### Token là gì? Nghiêm trọng cỡ nào?

`token` **là mật khẩu của con bot**. Ai có token là **gửi được tin nhắn từ bot của anh**, tới bất kỳ ai.

### Những điều TUYỆT ĐỐI không làm

1. **Đừng gửi token cho ai** — kể cả người hỗ trợ kỹ thuật. Chỉ cần gửi *ảnh chụp màn hình* thì được, **đừng gửi ảnh có token**.
2. **Đừng đăng token lên mạng** — không up lên Google Drive công khai, không dán vào group/chat, không paste vào website không tin cậy.
3. **Đừng chụp màn hình file `canh_bao.ini` rồi đăng lên đâu đó.** File đó là "chìa khóa".
4. **Đừng ghi token thẳng vào `canh_bao.py`** hay bất kỳ file `.py` nào — nếu sau này up code lên mạng, token bay theo. CamAI cố ý **không** cho phép viết token vào code mà chỉ đọc từ file `canh_bao.ini` / biến môi trường.

### Lỡ lộ rồi thì làm gì? (thu hồi token)

Đừng hoảng — làm 3 bước sau, **10 giây là xong**:

1. Mở Telegram, vào lại `@BotFather`.
2. Gõ lệnh `/revoke` rồi chọn đúng con bot của anh.
3. Bot sẽ **cấp token mới**. Token cũ **chết ngay lập tức** — kẻ xấu gửi tin tới đâu cũng không được nữa.
4. Mở lại file `canh_bao.ini`, dán token mới vào, lưu lại.

*(Cách khác: `@BotFather` → `/token` → chọn bot → lấy token mới, sau đó `/revoke` để vô hiệu token cũ.)*

### Thêm một lớp an toàn nữa

Nếu anh lo lắng về việc token bị lộ qua máy tính:

- **Chỉ nhắn cho chính mình**: đừng tạo nhóm, cứ để `chat_id` là ID cá nhân của anh. Người lạ không có token thì gửi vào nhóm cũng vô nghĩa — nhưng hạn chế `chat_id` về đúng tài khoản của anh vẫn tốt hơn.
- **Kiểm tra định kỳ**: thỉnh thoảng vào `@BotFather` xem bot có bị ai đổi thông tin gì không.
- **Máy tính dùng chung**: đừng lưu Telegram trên máy tính công cộng.

---

## 7. Người viết code nối cảnh báo vào CamAI như thế nào?

> Phần này **không phải** anh cần làm. Nếu CamAI của anh đã có sẵn cảnh báo thì bỏ qua.

`canh_bao.py` là một **module độc lập**, import được từ file khác. Người viết code chỉ cần **3 dòng**:

```python
from canh_bao import CanhBao                                          # dòng 1
CANH_BAO = CanhBao()                                                  # dòng 2
CANH_BAO.guii(su_kien[0], {"so_nguoi": zone_count, "mo_ta": video_name})  # dòng 3
```

**Chèn ở đâu trong `cam_ai_core.py`:**

- **Dòng 1** (`from canh_bao import CanhBao`) — vào khối `import` ở đầu file, cạnh `import cv2`.
- **Dòng 2** (`CANH_BAO = CanhBao()`) — ngay **dưới khối hằng số**, tầm dòng 87 (ngay sau khối `TEN_VAT_THE`).
- **Dòng 3** (`CANH_BAO.guii(...)`) — trong `run_analysis()`, **ngay sau dòng 665** (`prev_over_crowd = over_crowd`), tức là **sau khi** biến `su_kien` đã gom xong các lý do, **trước** khối `# --- khung nguoi + duong dem`. Ở đó `su_kien` chứa `LY_DO_VAO_VUNG`, `LY_DO_VUOT_DONG`, `LY_DO_DUNG_LAU`, `LY_DO_NGUOI_QUEN`, `LY_DO_CO_NGUOI`, và có sẵn biến `zone_count` để đếm người.

> ⚠️ **Lưu ý quan trọng:** Ở `cam_ai_core.py`, danh sách `su_kien` chỉ được điền khi `recorder is not None` (tức là đang bật chế độ tự lưu clip). Nếu muốn cảnh báo chạy **cả khi không lưu clip**, hãy đặt dòng 3 **ra ngoài** khối `if recorder is not None:` đó.

**Các tham số của `CanhBao(...)` (đều có giá trị mặc định, không bắt buộc):**

```python
CANH_BAO = CanhBao(
    gioi_han=5,       # tối đa 5 tin / 1 phút, hơn là bị chặn
    go=60,            # cùng 1 loại sự kiện trong 60s thì chỉ gửi 1 tin, kèm số đếm
    bat_telegram=True, # đặt False = tắt Telegram, chỉ dùng chuông + hộp thoại
    bat_chuong=True,   # đặt False = không kêu bíp
    hien_hop_thoai=True, # đặt False = không bật hộp thoại
)
```

**Các hàm quan trọng:**

| Hàm | Việc |
|---|---|
| `CANH_BAO.guii(loai_su_kien, chi_tiet)` | Gửi 1 cảnh báo. Trả `True` nếu có ít nhất 1 kênh thành công. **Đây là hàm chính.** |
| `CANH_BAO.tong_ket()` | Trả về `dict` thống kê (đã gửi mấy tin, hỏng mấy tin, bị gộp mấy tin...). Dùng để in ra cuối buổi. |
| `CANH_BAO.tat()` | Tắt và in bảng thống kê cuối cùng. Gọi 1 lần khi thoát chương trình. |

`chi_tiet` là một `dict`, nhận các khoa: `video`, `so_nguoi`, `mo_ta`, `duong_dan_xem`, `gio`.

Các mã sự kiện có sẵn câu tiếng Việt: `vao_vung`, `vuot_nguong_dong`, `dung_lau`, `nguoi_quen`, `co_nguoi` (đúng bằng các hằng `LY_DO_*` của `cam_ai_core.py`), thêm `co_nguoi_vao_vung`, `nhiem_viet`, `ra_khoi_vung`, `chuyen_dong`, `canh_bao_he_thong`. Có thể tự thêm trong bảng `NHAN_SU_KIEN` ở đầu `canh_bao.py`, hoặc truyền thẳng câu tiếng Việt vào `guii()`.

**Muốn thêm cờ bật/tắt từ dòng lệnh**, người viết code nên thêm vào `app.py`/`gui.py`:

```python
parser.add_argument("--khong-can-bao", action="store_true", help="tat canh bao")
parser.add_argument("--khong-telegram", action="store_true", help="chi dung chuong + hop thoai")
```

rồi truyền xuống:

```python
CANH_BAO = CanhBao(bat_telegram=not args.khong_telegram,
                   hien_hop_thoai=not args.khong_can_bao)
```

---

## 8. Chống spam (đã có sẵn, không cần làm gì)

Anh không sợ bị nhắn 500 tin lúc có người đứng trước camera. CamAI tự lo:

| Tính năng | Mặc định | Nghĩa là |
|---|---|---|
| Gộp tin trùng | `--go 60` giây | Người đứng trong vùng 1 phút → **1 tin duy nhất**, kèm "đã gộp thêm N lần" |
| Giới hạn tốc độ | `--gioi-han 5` tin/phút | Dù 500 sự kiện/tư giây thì cũng chỉ gửi tối đa 5 tin/phút |
| Mất mạng | `--timeout 10` giây | Mạng chết, tin nhắn treo, CamAI vẫn chạy tiếp, không bị đứng hình |
| Hộp thoại | `--het-hop-thoai 60` giây | Hộp thoại tự đóng, không bao giờ bắt anh phải bấm OK |
| Chống chồng hộp thoại | — | Còn hộp thoại nào đang mở thì không bật thêm cái thứ hai |

Muốn siết chặt hơn: `--gioi-han 2 --go 180`. Muốn bớt: `--gioi-han 10 --go 30`.

---

## 9. Xử lý lỗi thường gặp

| Bạn thấy | Nguyên nhân | Cách sửa |
|---|---|---|
| `Chua co token / chat_id` | Chưa tạo file `canh_bao.ini`, hoặc file sai tên (thành `.ini.txt`) | Làm lại mục 3. Kiểm tra file có đúng tên `canh_bao.ini` không |
| `HTTP 404 ... Not Found` | Token sai hoặc còn dấu cách thừa ở cuối | Mở lại `@BotFather` → `/token` → copy lại cho đúng |
| `HTTP 401 Unauthorized` | Token thuộc bot khác | Lấy lại token đúng con bot |
| `bot can't initiate conversation` | Chưa mở chat với bot và bấm Start | Mở Telegram → tìm bot của anh → bấm **START** một lần |
| `chat not found` | `chat_id` sai | Làm lại mục 2 với `@userinfobot` |
| Không thấy tin trên điện thoại | Máy tính mất mạng, hoặc tin bị gộp trong 60 giây vừa rồi | Bật chuông thử bằng `--kiem-tra`; xem mục 4 |
| Nghe không thấy tiếng bíp | Máy tính đang im (chế độ im lặng) | Windows: **Settings → System → Sound** → kiểm tra volume, tắt Focus Assist |
| Hộp thoại không hiện | Đã có một hộp thoại khác đang mở, hoặc đang chạy nền không có màn hình | Đóng hộp thoại cũ; tắt `--khong-hien-hop-thoai` khi chạy nền |

---

## 10. Tóm tắt trong 5 dòng

1. Telegram → `@BotFather` → `/newbot` → copy **token**.
2. Telegram → `@userinfobot` → `/start` → copy **chat_id**.
3. Tạo file `canh_bao.ini` cùng thư mục với `canh_bao.py`, điền token + chat_id.
4. Chạy `.venv\Scripts\python.exe canh_bao.py --kiem-tra` → thấy `[OK] Da gui thanh cong` là xong.
5. Lỡ lộ token → `@BotFather` → `/revoke` → lấy token mới, dán lại vào file.

**Chỉ gửi chữ. Không gửi hình ảnh, không gửi video. Chuông + hộp thoại vẫn hoạt động kể cả khi mất mạng.**