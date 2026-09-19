# 🎧 HƯỚNG DẪN SỬ DỤNG & VẬN HÀNH DISCORD MUSIC BOT
> **Tài liệu hướng dẫn chi tiết dành cho Discord Music Bot**  
> *Hỗ trợ phát nhạc YouTube, phát trọn bộ Playlist Spotify, điều khiển qua tin nhắn riêng (DM), xáo trộn ngẫu nhiên (Shuffle / Random) và chuyển bài tùy ý.*

---

## 📌 MỤC LỤC
1. [Giới thiệu & Tính năng nổi bật](#1-giới-thiệu--tính-năng-nổi-bật)
2. [Cơ chế hoạt động ngầm (Spotify & YouTube)](#2-cơ-chế-hoạt-động-ngầm-spotify--youtube)
3. [Điều kiện tiên quyết & Cài đặt môi trường](#3-điều-kiện-tiên-quyết--cài-đặt-môi-trường)
4. [Bảng tra cứu lệnh bot (Command Reference)](#4-bảng-tra-cứu-lệnh-bot-command-reference)
5. [Chi tiết cách sử dụng các lệnh](#5-chi-tiết-cách-sử-dụng-các-lệnh)
   - [5.1. Nhóm lệnh phát nhạc & tìm kiếm](#51-nhóm-lệnh-phát-nhạc--tìm-kiếm)
   - [5.2. Nhóm lệnh điều hướng & thứ tự phát](#52-nhóm-lệnh-điều-hướng--thứ-tự-phát)
   - [5.3. Nhóm lệnh quản lý hàng đợi & kết nối](#53-nhóm-lệnh-quản-lý-hàng-đợi--kết-nối)
6. [Các kịch bản sử dụng thực tế](#6-các-kịch-bản-sử-dụng-thực-tế)
7. [Khắc phục lỗi thường gặp (Troubleshooting)](#7-khắc-phục-lỗi-thường-gặp-troubleshooting)

---

## 1. Giới thiệu & Tính năng nổi bật

Discord Music Bot được xây dựng trên nền tảng **Python (`discord.py`)**, kết hợp công cụ trích xuất **`yt-dlp`** cùng bộ giải mã **`FFmpeg`**, mang đến trải nghiệm nghe nhạc chất lượng cao và mượt mà trong server Discord.

### ✨ Các tính năng chính:
* **Hỗ trợ đa nền tảng:** Phát nhạc từ liên kết YouTube (video lẻ / playlist), tìm kiếm theo từ khóa tự do, và đọc danh sách bài hát từ **Spotify** (Single / Album / Playlist).
* **Nạp danh sách siêu tốc (Lazy Loading):** Khi đưa vào một Playlist Spotify 50–100 bài, bot chỉ mất 1–2 giây để nạp tên bài hát vào hàng đợi. Luồng âm thanh chỉ được trích xuất khi bài hát chuẩn bị phát, tránh làm treo bot.
* **Hỗ trợ điều khiển qua DM (Direct Message):** Bạn không cần gõ lệnh trong kênh chat công khai của Server; bạn có thể nhắn tin trực tiếp cho bot. Bot sẽ tự nhận diện bạn đang ở phòng Voice nào trong các Server chung để tham gia và phục vụ.
* **Chế độ phát linh hoạt:** 
  - Tuần tự từ trên xuống dưới.
  - Lặp lại 1 bài cố định (`!loop`).
  - Xáo trộn danh sách 1 lần (`!shuffle`).
  - Chế độ tự bốc bài ngẫu nhiên liên tục (`!random`).
* **Nhảy bài tùy chọn (`!skipto`):** Cho phép bạn chọn phát ngay lập tức một bài hát bất kỳ đang chờ trong danh sách.

---

## 2. Cơ chế hoạt động ngầm (Spotify & YouTube)

```
[Link Playlist/Track Spotify]
              │
              ▼
   (Đọc Metadata qua yt-dlp)
     Tên bài + Tên Nghệ sĩ
              │
              ▼
 (Tìm kiếm tự động trên YouTube Music)
              │
              ▼
(Lấy Audio Stream phân giải cao)
              │
              ▼
[FFmpeg giải mã & phát vào Voice Discord]
```

1. **Rào cản bản quyền của Spotify:** Spotify bảo vệ âm thanh bằng chuẩn DRM nghiêm ngặt. API của Spotify không cấp luồng audio đầy đủ cho các ứng dụng bên ngoài (trừ 30 giây nghe thử).
2. **Cơ chế Match âm thanh:** Bot đọc tên bài hát và nghệ sĩ từ link Spotify của bạn, sau đó tự động tìm kiếm kết quả tương ứng có độ chính xác cao nhất trên YouTube.
3. **Hiệu năng cao:** Nhờ áp dụng cơ chế *extract_flat*, bot không tải toàn bộ luồng audio của cả playlist cùng lúc, giúp tiết kiệm băng thông và phản hồi tức thì.

---

## 3. Điều kiện tiên quyết & Cài đặt môi trường

Để bot hoạt động ổn định trên máy chủ hoặc máy cá nhân (Windows/Linux):

### 1. Phần mềm cần thiết
* **Python 3.10+**: Đã tích hợp vào biến môi trường PATH.
* **FFmpeg**: Công cụ giải mã audio (đã có trong PATH).
* **Deno Runtime**: Dùng để hỗ trợ `yt-dlp` giải mã các thử thách chữ ký JavaScript và PO Token của YouTube.
  ```powershell
  # Cài đặt trên PowerShell (Windows)
  irm [https://deno.land/install.ps1](https://deno.land/install.ps1) | iex
  ```

### 2. Cài đặt thư viện Python
Trong thư mục dự án, chạy lệnh:
```bash
pip install -U discord.py yt-dlp python-dotenv
```

### 3. File cấu hình `.env`
Tạo file `.env` đặt cùng cấp thư mục với `bot.py`:
```env
DISCORD_TOKEN=your_discord_bot_token_here
```

### 4. Khởi chạy Bot
* **Trên Windows PowerShell:**
  ```powershell
  python bot.py
  # hoặc
  .\bot.py
  ```
* **Trên Linux/macOS:**
  ```bash
  python3 bot.py
  ```

---

## 4. Bảng tra cứu lệnh bot (Command Reference)

> **Tiền tố mặc định (Prefix):** `!`  
> *(Bạn có thể gõ lệnh trên kênh chat của Server hoặc gửi tin nhắn riêng cho Bot).*

| Lệnh | Viết tắt | Tham số | Mô tả ngắn |
| :--- | :---: | :--- | :--- |
| `!play` | `!p` | `<tên bài / link>` | Thêm bài hát hoặc playlist vào hàng đợi và phát. |
| `!pause` | — | Không có | Tạm dừng bài hát đang phát. |
| `!resume` | — | Không có | Tiếp tục phát nếu đang bị tạm dừng. |
| `!skip` | `!s` | Không có | Chuyển ngay sang bài tiếp theo. |
| `!skipto` | — | `<số thứ tự>` | Nhảy trực tiếp đến bài số N trong hàng đợi. |
| `!shuffle` | — | Không có | Xáo trộn ngẫu nhiên danh sách chờ hiện tại một lần. |
| `!random` | — | Không có | Bật / Tắt chế độ tự bốc ngẫu nhiên bài tiếp theo. |
| `!loop` | — | Không có | Bật / Tắt chế độ lặp lại bài hát hiện tại. |
| `!queue` | `!q` | Không có | Xem danh sách hàng đợi và trạng thái phát hiện tại. |
| `!stop` | — | Không có | Dừng nhạc, xóa toàn bộ hàng đợi. |
| `!leave` | `!dc` | Không có | Ngắt kết nối và cho bot rời khỏi phòng Voice. |
| `!help` | `!h` | Không có | Hiển thị bảng hướng dẫn rút gọn trong Discord. |

---

## 5. Chi tiết cách sử dụng các lệnh

### 5.1. Nhóm lệnh phát nhạc & tìm kiếm

#### `!play <từ khóa / link>` (Viết tắt: `!p`)
* **Mục đích:** Tìm bài hát hoặc giải mã liên kết để đưa vào phòng voice.
* **Đặc điểm:**
  - Nếu đưa vào từ khóa (vd: `!play nấc thang lên thiên đường`), bot sẽ tìm kiếm trên YouTube và lấy kết quả sát nhất.
  - Nếu đưa vào link YouTube đơn lẻ hoặc link YouTube Playlist, bot sẽ nhận diện và đưa vào hàng đợi.
  - Nếu đưa vào link bài hát, album hoặc playlist từ **Spotify**, bot sẽ tự động trích xuất danh sách bài hát và thêm vào queue.
* **Ví dụ:**
  ```
  !play Cắt đôi nỗi sầu
  !p [https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT](https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT)
  !play [https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M](https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M)
  ```

#### `!pause` & `!resume`
* **`!pause`**: Tạm dừng luồng âm thanh đang phát trong phòng thoại.
* **`!resume`**: Tiếp tục phát lại bài hát đang tạm dừng mà không làm mất vị trí thời gian của bài.

---

### 5.2. Nhóm lệnh điều hướng & thứ tự phát

#### `!skip` (Viết tắt: `!s`)
* Bỏ qua bài hát đang phát hiện tại.
* Nếu chế độ `!loop` đang bật, việc dùng `!skip` sẽ tự động hủy lặp để chuyển sang bài tiếp theo.

#### `!skipto <số thứ tự>`
* Cho phép bạn xem số thứ tự qua lệnh `!queue`, sau đó nhảy ngay đến bài mong muốn, xóa các bài nằm trước nó.
* **Ví dụ:** Trong danh sách chờ có 10 bài, bạn muốn nghe bài số 4 ngay:
  ```
  !skipto 4
  ```

#### `!shuffle`
* Đảo lộn ngẫu nhiên vị trí các bài hát đang có sẵn trong hàng đợi một lần duy nhất.
* Thích hợp khi bạn vừa nạp một playlist dài và muốn thay đổi thứ tự nghe bài.

#### `!random`
* Chuyển đổi trạng thái giữa **Tuần tự** và **Ngẫu nhiên**.
* **Khi BẬT:** Mỗi khi bài hát hiện tại kết thúc, bot sẽ bốc thăm ngẫu nhiên một bài trong danh sách chờ để phát.
* **Khi TẮT:** Bot phát lần lượt theo thứ tự từ trên xuống dưới (`!queue`).

#### `!loop`
* Chế độ lặp lại bài hát đang phát. Khi bài hát chạy hết thời lượng, bot sẽ tự động tua lại từ đầu thay vì chuyển sang bài trong hàng đợi.

---

### 5.3. Nhóm lệnh quản lý hàng đợi & kết nối

#### `!queue` (Viết tắt: `!q`)
* Hiển thị bảng Embed thông tin:
  - Tên bài đang phát và liên kết nguồn.
  - Top 10 bài hát tiếp theo đang chờ trong danh sách.
  - Tổng số lượng bài còn lại trong hàng đợi.
  - Trạng thái hiện tại: Đang lặp (`Loop`), Đang ngẫu nhiên (`Random`) hay Tuần tự.

#### `!stop`
* Dừng phát nhạc ngay lập tức.
* Xóa sạch toàn bộ các bài hát đang nằm trong hàng đợi.
* Bot vẫn tiếp tục ở lại phòng Voice để chờ lệnh tiếp theo.

#### `!leave` (Viết tắt: `!dc`)
* Xóa danh sách bài hát và đưa bot rời khỏi kênh đàm thoại (Disconnect).

---

## 6. Các kịch bản sử dụng thực tế

### Kịch bản 1: Mở trọn vẹn Playlist Spotify & Nghe ngẫu nhiên
1. Bạn tham gia vào phòng Voice bất kỳ trong Server (ví dụ: `Phòng Chém Gió`).
2. Mở tin nhắn riêng với Bot (DM) hoặc gõ vào kênh chat:
   ```
   !play [https://open.spotify.com/playlist/37i9dQZF1DX4WYpdgoIcn6](https://open.spotify.com/playlist/37i9dQZF1DX4WYpdgoIcn6)
   ```
3. Bot sẽ thông báo: `📚 Đã thêm Playlist ... (50 bài hát) vào hàng đợi!`.
4. Bật chế độ phát ngẫu nhiên:
   ```
   !random
   ```
5. Thưởng thức âm nhạc. Bot sẽ tự động trích xuất luồng âm thanh YouTube của từng bài ngẫu nhiên khi đến lượt phát.

### Kịch bản 2: Bỏ qua các bài không thích và chọn bài cụ thể
1. Gõ `!queue` để xem danh sách 10 bài kế tiếp.
2. Thấy bài số 5 là bài bạn thích nghe ngay lúc này:
   ```
   !skipto 5
   ```
3. Bot lập tức ngắt bài hiện tại và phát bài số 5.

---

## 7. Khắc phục lỗi thường gặp (Troubleshooting)

### 1. Lỗi: `The term 'bot.py' is not recognized...`
* **Nguyên nhân:** PowerShell không cho phép chạy trực tiếp tên file mà không có chỉ định đường dẫn hoặc trình thực thi.
* **Khắc phục:** Chạy bằng cú pháp:
  ```powershell
  python bot.py
  # hoặc
  .\bot.py
  ```

### 2. Cảnh báo: `WARNING: [youtube] ... ios client https formats require a GVS PO Token`
* **Nguyên nhân:** YouTube áp dụng cơ chế xác thực PO Token để ngăn chặn tải video hàng loạt.
* **Khắc phục:**
  1. Đảm bảo đã cài **Deno** (`deno --version`).
  2. Đã thêm cấu hình `js_runtimes` trong `YTDL_OPTIONS` trỏ đến `C:\Users\Admin\.deno\bin\deno.exe`.
  3. Cập nhật `yt-dlp` mới nhất:
     ```powershell
     pip install --upgrade yt-dlp
     ```

### 3. Lỗi: `HTTP Error 403: Forbidden` khi truyền tải luồng âm thanh
* **Nguyên nhân:** YouTube chặn IP datacenter hoặc yêu cầu xác thực phiên trình duyệt.
* **Khắc phục:** Bật tính năng đọc cookie trình duyệt trong cấu hình `yt-dlp`:
  ```python
  'cookiesfrombrowser': ('chrome',),  # Hoặc 'edge', 'firefox'
  ```
  *(Lưu ý: Hãy tắt trình duyệt trước khi khởi động bot để tránh bị khóa file cookie).*

### 4. Bot không phản hồi khi nhắn lệnh qua DM
* **Nguyên nhân:** Bot chưa bật quyền `intents.members = True` hoặc bạn chưa cùng server chung với bot trong khi đang ở phòng Voice.
* **Khắc phục:** Vào [Discord Developer Portal](https://discord.com/developers/applications), mục **Bot** -> bật công tắc **Server Members Intent** và **Message Content Intent**.

---
*Tài liệu được biên soạn phục vụ cho hệ thống Discord Music Bot.*