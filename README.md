# 🎵 Discord Music Bot (Node.js + Lavalink v4)

Bot phát nhạc Discord hiện đại, mượt mà được xây dựng trên nền tảng **Node.js (Discord.js v14)** kết hợp cùng **Kazagumo & Shoukaku** và hệ thống máy chủ âm thanh **Lavalink v4**. Dự án được tối ưu hóa đặc biệt để chạy ổn định 24/7 trên các nền tảng đám mây như **Render, Railway, VPS**.

---

## ✨ Điểm nổi bật & Tính năng chính

### 🚀 Hiệu năng cao & mượt mà
- **Âm thanh chất lượng cao (Lavalink v4)**: Xử lý giải mã âm thanh trên node Lavalink chuyên dụng, không gây nghẽn CPU/RAM trên bot server.
- **Hỗ trợ đa nguồn**: Phát nhạc mượt mà từ **YouTube**, **Spotify** (bài hát, album, danh sách phát), **SoundCloud** và tìm kiếm từ khóa.
- **Tự động chuyển tiếp thông minh (Fallback)**: Tự động phân giải và khớp nhạc qua nhiều nguồn dự phòng khi có nguồn gặp sự cố.

### 🎛️ Bảng điều khiển tương tác (Now Playing UI)
- **Embed tự động cập nhật**: Hiển thị ảnh bìa sắc nét, thời lượng, người yêu cầu, trạng thái lặp và âm lượng.
- **Thanh tiến trình thời gian thực**: Tự động làm mới mỗi 10 giây thể hiện chính xác vị trí bài hát.
- **9 nút bấm điều khiển tức thì**:
  - `⏮️` Phát lại bài trước đó trong lịch sử
  - `⏯️` Tạm dừng / Tiếp tục
  - `⏭️` Bỏ qua bài hiện tại (Skip)
  - `🔁` Đổi chế độ lặp (Tắt ➡️ Lặp bài 🔂 ➡️ Lặp danh sách 🔁)
  - `🔀` Xáo trộn hàng đợi (Shuffle)
  - `🔉` Giảm âm lượng (-10%)
  - `🔊` Tăng âm lượng (+10%)
  - `📜` Xem nhanh danh sách chờ
  - `🛑` Dừng nhạc và rời phòng thoại

### 🔊 Quản lý âm lượng linh hoạt
- **Âm lượng mặc định tối ưu (130%)**: Mang lại âm lượng to, rõ ràng và ấm áp hơn so với mức chuẩn của Discord.
- **Lệnh `/volume`**: Tùy chỉnh linh hoạt từ **1% đến 200%**.

---

## 📋 Danh sách Slash Commands

| Lệnh | Tham số | Mô tả |
| :--- | :--- | :--- |
| `/play` | `query` *(bắt buộc)* | Phát bài hát từ tên bài, link YouTube, Spotify, SoundCloud |
| `/playskip` | `query` *(bắt buộc)* | Chèn bài hát mới và lập tức bỏ qua bài đang phát |
| `/playtop` | `query` *(bắt buộc)* | Chèn bài hát lên vị trí đầu tiên của hàng đợi (ưu tiên phát kế tiếp) |
| `/nowplaying` (hoặc `/np`) | *Không* | Xem thông tin chi tiết bài đang phát kèm bảng nút điều khiển |
| `/pause` | *Không* | Tạm dừng phát nhạc |
| `/resume` | *Không* | Tiếp tục phát bài hát |
| `/skip` | *Không* | Bỏ qua bài hát đang phát |
| `/skipto` | `index` *(bắt buộc)* | Nhảy thẳng tới bài hát số `index` trong danh sách chờ |
| `/previous` | *Không* | Phát lại bài hát vừa nghe từ lịch sử nghe nhạc |
| `/queue` | `page`, `remove`, `move_from`, `move_to`, `clear` | Xem và quản lý hàng đợi phân trang với các nút Next/Prev |
| `/repeat` | `mode` *(tùy chọn)* | Đổi chế độ lặp (Off / Track / Queue) |
| `/shuffle` | *Không* | Xáo trộn ngẫu nhiên thứ tự các bài hát trong hàng đợi |
| `/volume` | `level` *(tùy chọn: 1-200)* | Xem hoặc điều chỉnh âm lượng (1% đến 200%) |
| `/history` | *Không* | Xem lịch sử các bài hát đã phát trong máy chủ |
| `/stop` | *Không* | Dừng phát nhạc, xóa toàn bộ hàng đợi và rời kênh thoại |

---

## 🏗️ Cấu trúc thư mục

```text
Discord-Music-Bot/
├── index.js                     # Điểm khởi chạy chính: Express Health Server, Discord client & Event router
├── package.json                 # Khai báo dependency (Discord.js, Kazagumo, Shoukaku, Express)
├── Dockerfile                   # Cấu hình container Docker chạy trên Render / Linux
├── .env.example                 # Mẫu cấu hình biến môi trường
└── src/
    ├── commands/                # Khai báo Slash Commands
    │   ├── play.js              # Lệnh /play
    │   ├── playskip.js          # Lệnh /playskip
    │   ├── playtop.js           # Lệnh /playtop
    │   ├── nowplaying.js        # Lệnh /nowplaying & /np
    │   ├── pause.js             # Lệnh /pause
    │   ├── resume.js            # Lệnh /resume
    │   ├── skip.js              # Lệnh /skip & /skipto
    │   ├── stop.js              # Lệnh /stop
    │   ├── queue.js             # Lệnh /queue
    │   ├── repeat.js            # Lệnh /repeat
    │   ├── shuffle.js           # Lệnh /shuffle
    │   ├── volume.js            # Lệnh /volume
    │   ├── history.js           # Lệnh /history
    │   └── previous.js          # Lệnh /previous
    ├── config/
    │   └── lavalink.js          # Cấu hình danh sách Node Lavalink v4 & tự động failover
    ├── models/
    │   └── Track.js             # Chuẩn hóa cấu trúc dữ liệu Track
    ├── services/
    │   ├── player/
    │   │   ├── PlayerService.js # Điều phối vòng đời phát nhạc, fallback tìm kiếm
    │   │   └── PlayerState.js   # Quản lý trạng thái playback, generation guard, lịch sử
    │   ├── queue/
    │   │   └── QueueService.js  # Quản lý hàng đợi tập trung (add, remove, move, shuffle)
    │   └── ui/
    │       ├── NowPlayingUI.js  # Tạo giao diện Embed Now Playing + nút tương tác
    │       └── QueueUI.js       # Tạo giao diện Embed Queue phân trang
    └── utils/
        └── permissions.js       # Tiện ích kiểm tra quyền kênh thoại & trạng thái kết nối
```

---

## ⚙️ Biến môi trường (Environment Variables)

| Biến | Bắt buộc | Mặc định | Mô tả |
| :--- | :---: | :---: | :--- |
| `DISCORD_TOKEN` | ✅ | - | Token của Discord Bot tạo từ Discord Developer Portal |
| `PORT` | ❌ | `8080` | Port chạy máy chủ Express phục vụ Health Check (Render) |
| `SPOTIFY_CLIENT_ID` | ❌ | Rỗng | Client ID Spotify (tùy chọn) |
| `SPOTIFY_CLIENT_SECRET` | ❌ | Rỗng | Client Secret Spotify (tùy chọn) |
| `LAVALINK_HOST` | ❌ | Tự động | Địa chỉ máy chủ Lavalink v4 tùy chỉnh (VD: `my-lavalink.com:2333`) |
| `LAVALINK_AUTH` | ❌ | `youshallnotpass` | Mật khẩu kết nối Lavalink tùy chỉnh |
| `LAVALINK_SECURE` | ❌ | `false` | `true` nếu dùng SSL/WSS, `false` nếu dùng HTTP/WS |

---

## 🚀 Hướng dẫn triển khai

### 1. Triển khai lên Render.com (Khuyên dùng)
1. Fork hoặc đẩy dự án lên repository GitHub của bạn.
2. Đăng nhập vào [Render.com](https://render.com) -> Chọn **New Web Service**.
3. Kết nối với GitHub Repository của bạn.
4. Chọn **Docker** làm môi trường chạy (*Render sẽ tự động dùng file `Dockerfile` đã có sẵn*).
5. Thêm các biến môi trường vào mục **Environment**:
   - `DISCORD_TOKEN`: Token của bot Discord.
   - `PORT`: `8080`.
6. Bấm **Create Web Service**. Bot sẽ tự động build, khởi chạy HTTP Health Server và kết nối đến Discord trong ~1-2 phút!

### 2. Chạy trên máy tính cá nhân / VPS
Yêu cầu: **Node.js 18 trở lên**.

```bash
# 1. Clone repository
git clone https://github.com/Mod3r3d/Discord-Music-Bot.git
cd Discord-Music-Bot

# 2. Cài đặt các gói phụ thuộc
npm install

# 3. Tạo file .env và điền thông tin
cp .env.example .env
# Chỉnh sửa file .env với DISCORD_TOKEN của bạn

# 4. Khởi chạy bot
node index.js
```

---

## 🛡️ Bản quyền & Giấy phép
Dự án được phát triển và tối ưu cho cộng đồng sử dụng.
