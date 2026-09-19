# 🎧 Discord Music Bot v2 — Đã tái cấu trúc theo `plan.md`

Bot đã được viết lại từ file `bot.py` (387 dòng, 1 file duy nhất) thành kiến
trúc phân tầng, bám theo đúng thứ tự ưu tiên trong `plan.md`. Bên dưới là
tình trạng thực hiện từng mục.

## Cấu trúc thư mục

```
discord-music-bot/
├── main.py                  # Entry point, chỉ nạp cogs + sync slash command
├── core/
│   ├── config.py             # Toàn bộ biến môi trường, FFmpeg/yt-dlp options, filter presets
│   ├── logger.py              # Logger tập trung
│   └── errors.py               # Global error handler cho slash command
├── models/
│   ├── track.py                # Domain model 1 bài hát
│   └── guild_state.py            # Domain model trạng thái phát nhạc / server
├── services/
│   ├── youtube_service.py         # yt-dlp: liệt kê nhanh, resolve stream, fallback đa nguồn
│   ├── audio_service.py            # GracefulFFmpegPCMAudio — quản lý vòng đời tiến trình FFmpeg
│   ├── player_service.py            # play_next() + pre-fetch — trung tâm điều phối phát nhạc
│   └── lyrics_service.py             # Tích hợp LRCLIB (lời bài hát tĩnh + đồng bộ)
└── cogs/
    ├── music.py                     # Toàn bộ slash command
    ├── queue_view.py                  # UI: pagination hàng đợi + search selector dropdown
    └── voice_events.py                 # Auto-disconnect khi phòng trống
```

## ✅ Mục 1 — Hiệu suất & Kiến trúc

| # | Hạng mục | Trạng thái |
|---|---|---|
| 1.1 | Pre-fetch / Gapless Playback | **Đã làm.** `player_service.schedule_prefetch()` chờ tới khi bài hiện tại còn `PREFETCH_LEAD_SECONDS` (mặc định 18s) rồi resolve trước link stream bài kế tiếp, `play_next()` ưu tiên dùng bài đã pre-fetch nếu hàng đợi chưa đổi. |
| 1.2 | Kiến trúc Cogs/Services/Models/Core | **Đã làm** — xem cây thư mục ở trên. |
| 1.3 | Vòng đời tiến trình FFmpeg | **Đã làm.** `GracefulFFmpegPCMAudio` (services/audio_service.py): SIGTERM trước, chỉ SIGKILL nếu FFmpeg không thoát trong `FFMPEG_TERMINATE_TIMEOUT` giây; đóng toàn bộ pipe stdout/stderr; giới hạn `-bufsize 512k` để tránh phình RAM khi stream bitrate cao. |
| 1.4 | Vượt rào YouTube & Rate limit | **Làm một phần.** `youtube_service.resolve_stream()` tự thử lần lượt 4 cấu hình `player_client` (web/mweb/android → android → ios → tv_embedded) trước khi fallback sang SoundCloud. Đã có sẵn chỗ cắm `POT_PROVIDER_URL` cho plugin `yt-dlp-get-pot-bgutils`, nhưng **bạn cần tự triển khai container `bgutils-ytdlp-pot-provider`** (đây là 1 service riêng chạy nền, không thể "viết sẵn" trong code Python của bot) và cài thêm gói `yt-dlp-get-pot-bgutils` — xem hướng dẫn chính thức: https://github.com/Brainicism/bgutils-ytdlp-pot-provider |
| 1.5 | Lavalink / Wavelink | **Chưa làm — cần hạ tầng riêng.** Đây là thay đổi kiến trúc lớn nhất: cần chạy một tiến trình Java (Lavalink server) độc lập với bot, không thể đóng gói trong vài file Python. Khuyến nghị: khi bot thật sự phục vụ 5-10 server đồng thời, cài package `wavelink`, tự host (hoặc thuê) 1 Lavalink node, rồi thay `services/player_service.py` bằng lớp gọi `wavelink.Player` thay vì `GracefulFFmpegPCMAudio`. Kiến trúc Cogs/Services hiện tại đã tách sẵn để việc này chỉ cần sửa 1 file. |

## ✅ Mục 2 — Tính năng & UX

| # | Hạng mục | Trạng thái |
|---|---|---|
| 2.1 | Slash Commands + Pagination | **Đã làm.** Toàn bộ lệnh chuyển sang `/`. `/queue` phân trang 10 bài/trang với nút `⏮️ ◀️ ▶️ ⏭️` (xem `cogs/queue_view.py`). |
| 2.2 | Search Selector | **Đã làm.** Lệnh `/search <từ khoá>` hiển thị Dropdown 5 kết quả kèm kênh + thời lượng. |
| 2.3 | Audio Filters | **Đã làm.** `/filter` với các preset `bassboost`, `nightcore`, `8d`, `slowedreverb`, `vaporwave`, `none` — áp dụng ngay lập tức bằng cách phát lại bài hiện tại với cờ FFmpeg `-af` mới. |
| 2.4 | Synced Lyrics | **Đã làm (lời tĩnh).** `/lyrics` dùng API mở LRCLIB (miễn phí, không cần key). Đã parse sẵn `LyricLine` có timestamp cho từng câu (`services/lyrics_service.py`), nhưng UI "cập nhật Embed real-time theo từng câu" **chưa nối vào Discord** vì Discord giới hạn edit message ~5 lần/5s/kênh — cần thêm hàng đợi throttle riêng nếu muốn dùng ở nhiều server cùng lúc. Có thể bật tiếp bằng cách gọi `interaction.edit_original_response()` theo `asyncio.sleep` giữa các `LyricLine`. |
| 2.5 | Vote-to-Skip & DJ Role | **Đã làm.** `/skip` cần > 50% người trong phòng vote (trừ khi bạn có quyền `Manage Server`/Admin hoặc giữ Role DJ — đặt bằng `/setdj @role`). `voice_events.py` tự đếm ngược `AUTO_DISCONNECT_SECONDS` (mặc định 60s) rồi rời phòng khi không còn ai. |

## ⚠️ Thay đổi hành vi so với bot cũ (cần biết)

- **Không còn điều khiển qua DM** — Discord slash command bắt buộc chạy trong
  ngữ cảnh server. Nếu bạn thực sự cần dùng lại tính năng DM, giữ song song
  `commands.Bot` prefix `!` cho vài lệnh cũ là khả thi nhưng đi ngược mục 2.1
  của plan (chuẩn hoá về Slash Command) nên mình không bật lại.
- **Trạng thái (DJ role, filter, queue...) chỉ lưu trong RAM** — restart bot
  sẽ mất. Nếu cần lưu bền, gắn thêm SQLite/Redis vào `models/guild_state.py`.
- Spotify: bot cũ dựa vào `yt-dlp` để "đọc" link Spotify — bản thân `yt-dlp`
  **không chính thức hỗ trợ trích xuất Spotify** (chỉ hoạt động nếu bạn cài
  thêm extractor/plugin bên thứ 3). Phần `youtube_service.extract_flat()`
  giữ nguyên hành vi gọi thẳng yt-dlp như bản cũ để không phá vỡ workflow
  hiện tại của bạn, nhưng nếu link Spotify không còn parse được, đó là do
  thay đổi phía yt-dlp/Spotify chứ không phải do lần tái cấu trúc này.

## Cài đặt & chạy

```bash
pip install -r requirements.txt
cp .env.example .env      # rồi điền DISCORD_TOKEN
sudo apt install ffmpeg   # Linux — thay ffmpeg.exe của bản Windows cũ
python3 main.py
```

Đặt `DEV_GUILD_ID` trong `.env` khi đang test để slash command đồng bộ tức
thì vào 1 server (thay vì chờ ~1 giờ lan toả toàn cục).

## Lộ trình còn lại (đúng theo mục 3 của plan)

- [x] Giai đoạn 1: Cogs, pre-fetch, dọn tiến trình FFmpeg, auto-disconnect.
- [x] Giai đoạn 2: Slash Commands, Search Selector, Pagination, Vote-to-Skip.
- [~] Giai đoạn 3: Đã có Audio Filters + Lyrics (tĩnh). **Còn thiếu**: Lavalink
      (cần hạ tầng Java riêng) và Live Synced Lyrics real-time (cần throttle
      edit message) — cả hai đều là hạng mục hạ tầng/UX nặng, khuyến nghị làm
      riêng sau khi Giai đoạn 1-2 đã chạy ổn định trên server thật.
