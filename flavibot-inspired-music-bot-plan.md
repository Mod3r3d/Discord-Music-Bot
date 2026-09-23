# Discord Music Bot — FlaviBot-inspired Upgrade Plan

> **Mục tiêu:** thiết kế lại hệ thống Music Bot hiện tại theo mô hình trải nghiệm của FlaviBot, đặc biệt ở **live player, queue management, playlist, search-and-add, drag-to-reorder, playback controls, history, saved playlists, autoplay/radio và multi-source playback**.
>
> **Lưu ý nguồn:** hiện chưa có source code FlaviBot chính thức được cung cấp trong project. Plan này dựa trên các tính năng FlaviBot được mô tả trong tài liệu/tham khảo công khai mà mình đã tra cứu, sau đó điều chỉnh cho phù hợp với kiến trúc hiện tại **Node.js + discord.js + Kazagumo + Shoukaku + Lavalink**. Không sao chép code hoặc giả định implementation nội bộ của FlaviBot.

---

# 1. Mục tiêu cuối cùng

Bot không chỉ là:

```text
/play
→ search
→ play
```

mà trở thành:

```text
                Discord / Web
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
      Discord UI              Web Player
          │                       │
          └───────────┬───────────┘
                      ▼
               Player Service
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
     Queue Manager            Playback
          │                       │
          ▼                       ▼
   Playlist / History        Lavalink
          │
          ▼
      Source Resolver
    ┌─────┼─────┬─────┐
    ▼     ▼     ▼     ▼
 YouTube Spotify SoundCloud Direct
```

Mục tiêu UX:

```text
Nhanh
Ổn định
Không dừng ở 100 track
Queue dễ quản lý
Có live player
Có playlist cá nhân
Có autoplay/radio
Có history
Có search-and-add
Có seek/volume/filter
```

---

# 2. FlaviBot-inspired feature baseline

Các đặc điểm nên lấy làm baseline UX:

```text
[Core]
✓ Live queue
✓ Search-and-add
✓ Drag-to-reorder
✓ Skip
✓ Seek
✓ Volume
✓ Now Playing

[Playlist]
✓ Saved playlists
✓ Personal playlists
✓ Playlist/history workflow
✓ Multi-server profile

[Playback]
✓ Autoplay
✓ Radio
✓ Repeat
✓ Shuffle
✓ Filters

[Web]
✓ Live player
✓ Queue visualization
✓ Real-time playback controls
```

Định hướng này phù hợp với mô hình "live-player" hơn là một bot chỉ dùng command.

---

# 3. Kiến trúc mục tiêu

```text
src/
├── commands/
│   ├── play.js
│   ├── queue.js
│   ├── playlist.js
│   ├── playback.js
│   └── settings.js
│
├── services/
│   ├── player/
│   │   ├── player_manager.js
│   │   ├── player_state.js
│   │   ├── playback_service.js
│   │   └── player_events.js
│   │
│   ├── queue/
│   │   ├── queue_manager.js
│   │   ├── shuffle.js
│   │   ├── history.js
│   │   └── fair_queue.js
│   │
│   ├── spotify/
│   │   ├── spotify_client.js
│   │   ├── spotify_auth.js
│   │   ├── spotify_paginator.js
│   │   └── spotify_mapper.js
│   │
│   ├── resolver/
│   │   ├── source_detector.js
│   │   ├── youtube_resolver.js
│   │   ├── spotify_resolver.js
│   │   ├── soundcloud_resolver.js
│   │   └── direct_url_resolver.js
│   │
│   ├── playlist/
│   │   ├── playlist_import.js
│   │   ├── playlist_store.js
│   │   └── playlist_jobs.js
│   │
│   ├── cache/
│   │   ├── metadata_cache.js
│   │   ├── match_cache.js
│   │   └── search_cache.js
│   │
│   └── recommendation/
│       ├── autoplay.js
│       └── radio.js
│
├── ui/
│   ├── now_playing.js
│   ├── queue_view.js
│   ├── controls.js
│   └── playlist_view.js
│
├── web/
│   ├── api/
│   ├── websocket/
│   └── dashboard/
│
└── database/
    ├── sqlite.js
    ├── migrations/
    └── repositories/
```

---

# 4. P0 — Playback Core

Không triển khai web UI trước khi playback state ổn định.

## 4.1 Player State Machine

```text
IDLE
 ↓
RESOLVING
 ↓
PLAYING
 ↕
PAUSED
 ↓
STOPPING
 ↓
IDLE
```

Error:

```text
RESOLVING → ERROR → IDLE/RETRY
PLAYING   → ERROR → RESOLVE NEXT
```

---

# 5. P0 — Playback Generation

Mọi async resolve phải có generation:

```js
const generation = player.state.playbackGeneration;
```

Trước khi play:

```js
if (generation !== player.state.playbackGeneration) {
    return;
}
```

Ngăn:

```text
Track A resolving
↓
/skip
↓
Track B playing
↓
A resolve xong
↓
A không được play lại
```

---

# 6. P0 — Queue Manager

Không cho command trực tiếp:

```js
player.queue.add(...)
player.queue.clear(...)
```

ở nhiều nơi.

Thay:

```js
queueManager.enqueue()
queueManager.remove()
queueManager.move()
queueManager.clear()
queueManager.shuffle()
queueManager.next()
```

Tất cả mutation tập trung ở một service.

---

# 7. P0 — Voice Ownership

Quy tắc:

```text
Bot chưa kết nối
→ join requester

Bot cùng voice
→ OK

Bot ở voice khác
→ reject

DJ/Admin
→ có thể /movehere
```

Không tự chuyển bot sang channel khác chỉ vì một user dùng `/play`.

---

# 8. P0 — Interaction Response

Với command có network:

```text
deferReply()
      ↓
voice connect
      ↓
Spotify/YouTube resolve
      ↓
reply/editReply
```

Không:

```text
voice connect
 ↓
resolve
 ↓
deferReply
```

---

# 9. P0 — Render Stability

Health server phải độc lập với Discord `ready` event.

Sai:

```text
onReady()
→ start health server
```

Đúng:

```text
application startup
→ start HTTP health server
→ start Discord client
```

Health:

```text
/health
/status
```

---

# 10. P0 — Resolver Concurrency

Không để nhiều playlist làm:

```text
1000 YouTube searches
```

đồng thời.

Đặt:

```env
YOUTUBE_RESOLVE_CONCURRENCY=3
SPOTIFY_CONCURRENCY=3
```

---

# 11. P0 — Priority Queue

```text
HIGH
├── current track
├── user /play
└── interactive search

NORMAL
└── playlist import

LOW
└── prefetch/autoplay
```

Playlist background không được làm `/play` của user mới chậm đi đáng kể.

---

# 12. P0 — Spotify Playlist Unlimited

Không sử dụng:

```text
fixed page count
fixed 100 tracks
playlistPageLimit
```

làm điều kiện kết thúc.

Phải theo:

```text
Spotify page
 ↓
items
 ↓
next
 ↓
next
 ↓
...
 ↓
next = null
```

---

# 13. P0 — Spotify Async Pagination

Đề xuất:

```js
async function* iteratePlaylist(playlistId) {
    let url = buildFirstPageUrl(playlistId);

    while (url) {
        const page = await spotifyClient.fetch(url);

        for (const item of page.items ?? []) {
            const track = mapSpotifyTrack(item);

            if (track) {
                yield track;
            }
        }

        url = page.next;
    }
}
```

Điểm quan trọng:

```text
Không tạo allTracks[]
```

để giữ toàn bộ playlist trong RAM.

---

# 14. P0 — Spotify Chunked Import

Ví dụ:

```env
SPOTIFY_IMPORT_CHUNK=25
```

Flow:

```text
Spotify page
     ↓
25 tracks
     ↓
Queue
     ↓
25 tracks
     ↓
next page
```

User không phải chờ playlist hoàn thành toàn bộ mới thấy queue.

---

# 15. P0 — Background Playlist Job

```text
/play Spotify playlist
        ↓
deferReply
        ↓
fetch first chunk
        ↓
enqueue
        ↓
reply
        ↓
background import
```

UI:

```text
🎵 Spotify playlist

✅ Added 25 tracks
📚 Total: 847
🔄 Importing in background...
```

---

# 16. P0 — Playlist Job State

```js
class PlaylistJob {
    id;
    guildId;
    userId;
    source;
    sourceId;

    total;
    imported;
    skipped;

    status;

    cancelled;

    createdAt;
    startedAt;
    finishedAt;
}
```

State:

```text
QUEUED
FETCHING
IMPORTING
PAUSED
RETRYING
COMPLETED
FAILED
CANCELLED
```

---

# 17. P0 — Cancellation

Thêm:

```text
/playlist-cancel
```

và button:

```text
🛑 Cancel Import
```

`/stop` và `/leave` phải cancel import đang chạy.

Không để:

```text
/stop
 ↓
queue.clear()
 ↓
background import
 ↓
tracks tự quay lại queue
```

---

# 18. P0 — Backpressure

Nếu queue quá lớn:

```text
Queue >= MAX_PENDING
        ↓
pause import
```

Ví dụ:

```env
MAX_PENDING_PLAYLIST_TRACKS=300
```

Khi queue giảm:

```text
resume import
```

---

# 19. P0 — Lazy Resolution

Spotify playlist không resolve toàn bộ YouTube ngay.

Queue:

```text
Spotify metadata
```

Playback:

```text
current
next 1
next 2
next 3
```

mới resolve.

```env
YOUTUBE_PRE_RESOLVE_AHEAD=3
```

---

# 20. P0 — Spotify → YouTube Matching

```text
Spotify metadata
      ↓
artist + title
      ↓
YouTube search
      ↓
candidate scoring
      ↓
best match
      ↓
Lavalink
```

Scoring:

```text
title similarity
artist similarity
duration
official/topic
```

Penalty:

```text
karaoke
cover
live
slowed
nightcore
lofi
```

nếu không phù hợp với metadata gốc.

---

# 21. P0 — Match Cache

```text
spotifyTrackId
       ↓
youtubeVideoId
```

Lưu cache:

```js
{
    youtubeId,
    score,
    matchedAt
}
```

Sau đó playlist dùng lại:

```text
Spotify → cache HIT → không search YouTube
```

---

# 22. P1 — Live Queue

Đây là phần nên học mạnh từ mô hình FlaviBot.

Discord:

```text
🎵 Now Playing

1. Song A
2. Song B
3. Song C
4. Song D
...
```

Buttons:

```text
⏮
⏸
▶
⏭
🔀
🔁
🔊
```

---

# 23. P1 — Queue Pagination

Không gửi 500 track trong một embed.

```text
Page 1 / 10

1. Song A
2. Song B
...
50. Song AX

[Previous] [Next]
```

---

# 24. P1 — Search-and-Add

Flow:

```text
/search
     ↓
Top 5 candidates
     ↓
Select menu
     ↓
Add to queue
```

Có thể thêm:

```text
➕ Add
▶ Play Now
📌 Add to Top
```

---

# 25. P1 — Queue Reordering

Discord:

```text
/move 8 2
```

Web:

```text
Drag Track 8
      ↓
Track 2
```

Backend:

```js
queueManager.move(from, to)
```

UI chỉ gửi intent; backend là source of truth.

---

# 26. P1 — Play Top / Play Skip

Thêm:

```text
/playtop
/playskip
```

Semantics:

```text
/playtop
→ add next

/playskip
→ interrupt current
→ play immediately
```

---

# 27. P1 — Previous / History

Lưu:

```text
history[0]
history[1]
...
```

Commands:

```text
/previous
/replay
/history
```

---

# 28. P1 — Personal Playlists

FlaviBot-inspired workflow:

```text
User
 ↓
My Playlists
 ├── Favorites
 ├── Workout
 ├── Chill
 └── Anime
```

Commands:

```text
/playlist create
/playlist add
/playlist remove
/playlist play
/playlist delete
/playlist list
```

---

# 29. P1 — Saved Playlists Across Servers

Playlist nên thuộc:

```text
user account
```

thay vì chỉ:

```text
guild
```

Ví dụ:

```text
User Huy
 ├── Favourites
 ├── Coding
 └── Anime
```

Huy có thể sử dụng playlist ở server A/B/C.

---

# 30. P1 — Favorites

Thêm:

```text
/like
/unlike
/likes
```

Now Playing:

```text
❤️ Like
```

---

# 31. P1 — Duplicate Management

Thêm:

```text
/removedupes
```

Logic có thể dựa trên:

```text
Spotify ID
YouTube video ID
canonical URL
```

Không chỉ title.

---

# 32. P1 — Leave Cleanup

Nếu user rời voice:

```text
user leaves
 ↓
optional cleanup
 ↓
remove tracks requested by user
```

Command:

```text
/leavecleanup on
```

---

# 33. P1 — Fair Queue

Nếu A import:

```text
500 tracks
```

và B thêm:

```text
1 track
```

không nên để B chờ 500 bài.

Tùy server policy:

```text
A1
B1
A2
A3
...
```

Kết hợp với:

```env
USER_QUEUE_CAP=5
```

---

# 34. P1 — Autoplay

Khi queue hết:

```text
Queue empty
    ↓
Autoplay enabled?
    ↓
Find related track
    ↓
Queue
    ↓
Continue
```

Toggle:

```text
/autoplay
```

---

# 35. P1 — Recommendation Strategy

MVP:

```text
current artist
current genre
similar title
recent history
```

Sau này:

```text
Spotify recommendations
```

Autoplay không được ưu tiên cao hơn user `/play`.

---

# 36. P1 — Radio Mode

FlaviBot-style:

```text
/radio <artist>
/radio <genre>
```

Ví dụ:

```text
/radio The Weeknd
```

Bot liên tục tạo queue từ seed.

State:

```text
RADIO
```

thoát:

```text
/radio stop
```

---

# 37. P1 — Volume

```text
/volume 50
```

Web:

```text
Volume Slider
────────●────
    60%
```

Backend:

```text
player.setVolume()
```

---

# 38. P1 — Seek

Hỗ trợ:

```text
/seek 1:30
/seek 90
```

Web:

```text
██████████░░░░
       ●
```

---

# 39. P1 — Progress Bar

```text
01:23 / 04:12

████████░░░░░░
```

Update event-driven.

Không edit Discord message mỗi giây.

---

# 40. P1 — Filters

Lavalink filters:

```text
bassboost
nightcore
vaporwave
8d
karaoke
tremolo
vibrato
distortion
lowpass
rotation
timescale
equalizer
```

FlaviBot-inspired:

```text
speed
pitch
```

Có:

```text
/filter reset
```

---

# 41. P1 — Filter Presets

```text
/filters
```

Presets:

```text
Normal
Nightcore
Bass Boost
Vaporwave
8D
Anime
Party
```

Không hard-code filter logic trong command.

---

# 42. P1 — Loop

```text
loop off
loop track
loop queue
```

UI:

```text
🔁
```

Cycles:

```text
OFF
↓
TRACK
↓
QUEUE
↓
OFF
```

---

# 43. P1 — Shuffle

Tách:

```text
queue shuffle
```

khỏi:

```text
random next
```

Mục tiêu:

```text
shuffle once
→ play sequentially
```

Không:

```text
random choice every track
```

để tránh lặp.

---

# 44. P2 — Web Player

Đây là feature lớn nhất theo hướng FlaviBot.

## Mục tiêu

```text
Browser
   ↓
Discord OAuth2
   ↓
User guilds
   ↓
Select guild
   ↓
Live player
```

---

# 45. Web Dashboard

```text
┌──────────────────────────────────────┐
│ 🎵 MUSIC PLAYER                     │
├──────────────────────────────────────┤
│                                      │
│        Album Art                     │
│                                      │
│      Blinding Lights                 │
│      The Weeknd                      │
│                                      │
│ ███████████░░░  02:11 / 03:20       │
│                                      │
│   ⏮    ▶    ⏭    🔀    🔁           │
│                                      │
├──────────────────────────────────────┤
│ QUEUE                                │
│                                      │
│ 1. Starboy                           │
│ 2. Save Your Tears                   │
│ 3. Die For You                       │
│                                      │
└──────────────────────────────────────┘
```

---

# 46. Web Queue Drag & Drop

Frontend:

```text
Track A
Track B
Track C
```

User:

```text
drag C → top
```

API:

```http
PATCH /api/guild/:id/queue/reorder
```

Payload:

```json
{
    "from": 3,
    "to": 1
}
```

Backend:

```text
validate
↓
permission
↓
queueManager.move()
↓
broadcast state
```

---

# 47. WebSocket Live Sync

Không polling mỗi giây.

```text
Discord Bot
     ↓
Event Bus
     ↓
WebSocket
     ↓
Browser
```

Events:

```text
PLAYER_UPDATE
QUEUE_UPDATE
TRACK_START
TRACK_END
PAUSE
RESUME
VOLUME_CHANGE
FILTER_CHANGE
```

---

# 48. Web Playback Controls

Browser:

```text
Play
Pause
Skip
Previous
Seek
Volume
Loop
Shuffle
```

Backend phải dùng cùng `PlayerService`.

Không viết một playback engine riêng cho Web.

---

# 49. Search from Browser

```text
Search
 ↓
YouTube/Spotify
 ↓
Results
 ↓
Add to Queue
```

Ví dụ:

```text
The Weeknd

[Blinding Lights]        [+]
[Starboy]                [+]
[Save Your Tears]        [+]
```

---

# 50. P2 — Web Playlist Manager

```text
My Playlists

Favorites
Workout
Coding
Anime Songs
```

Actions:

```text
Play
Rename
Delete
Share
Add Track
Remove Track
```

---

# 51. P2 — Saved Playlist Sharing

```text
/playlist share <name>
```

Tạo:

```text
share_id
```

Web:

```text
/music/playlist/abc123
```

Có quyền:

```text
Private
Unlisted
Public
```

---

# 52. P2 — History

Web:

```text
Recently Played

Today
Yesterday
Last 7 Days
```

Có:

```text
Play again
Add to playlist
Like
```

---

# 53. P2 — Radio/Autoplay UI

Browser:

```text
Autoplay    [ON]
Radio       [OFF]

Seed:
[The Weeknd            ]
```

---

# 54. P2 — Player Permissions

Web action phải kiểm tra:

```text
User logged in
User has guild
User is in voice
User is same voice channel
User has DJ permission
```

Không tin frontend.

---

# 55. P2 — OAuth2

Flow:

```text
Browser
 ↓
Discord OAuth2
 ↓
callback
 ↓
session
 ↓
guild authorization
```

Không lưu bot token ở frontend.

---

# 56. P2 — Database

SQLite MVP.

Tables:

```text
users
guilds
user_playlists
playlist_tracks
favorites
history
guild_settings
saved_filters
playlist_import_jobs
spotify_match_cache
```

---

# 57. P2 — Playlist Track Schema

```text
playlist_tracks
-------------------------
id
playlist_id
position
source
source_track_id
title
artist
duration
thumbnail
youtube_id
created_at
```

Position phải có index:

```text
playlist_id + position
```

---

# 58. P2 — Playlist Import Persistence

```text
playlist_import_jobs
-------------------------
job_id
user_id
guild_id
source
source_id
total
processed
failed
cursor
status
updated_at
```

Nếu Render restart:

```text
job saved
 ↓
restart
 ↓
resume cursor
```

---

# 59. P2 — Spotify Cursor Persistence

Không chỉ lưu:

```text
processed = 250
```

mà lưu:

```text
next URL/cursor
```

Vì Spotify pagination phải tiếp tục từ đúng vị trí đã đọc.

---

# 60. P2 — Rate Limit

Spotify:

```text
429
 ↓
Retry-After
 ↓
delay
 ↓
retry
```

YouTube:

```text
429/403
 ↓
retry strategy
 ↓
alternate resolver/cache
```

---

# 61. P2 — Cache Layers

```text
                   Query
                     │
                     ▼
              Search Cache
                     │
                     ▼
             Metadata Cache
                     │
                     ▼
              Match Cache
                     │
                     ▼
              Stream Cache
```

Stream URL có:

```text
expiresAt
```

Không cache vĩnh viễn.

---

# 62. P2 — Single-flight

Nếu 10 user yêu cầu:

```text
Blinding Lights
```

Không chạy:

```text
10 searches
```

Chỉ:

```text
1 resolver job
   ↓
10 callers receive result
```

---

# 63. P2 — Playlist Job Fairness

Global:

```text
MAX_ACTIVE_PLAYLIST_JOBS=10
```

Per guild:

```text
MAX_ACTIVE_PLAYLIST_IMPORTS_PER_GUILD=1
```

Per user:

```text
MAX_ACTIVE_SPOTIFY_IMPORTS_PER_USER=1
```

---

# 64. P2 — Abuse Limits

```text
MAX_PLAYLIST_SIZE=5000
MAX_QUEUE_SIZE=5000
MAX_IMPORTS_PER_10_MIN=5
```

Nếu muốn "unlimited" UX:

> Không hard-limit 100 track; nhưng vẫn phải có safety limit đủ lớn để ngăn abuse và bảo vệ tài nguyên.

---

# 65. P2 — Diagnostics

```text
/diagnose
```

Hiển thị:

```text
Discord latency
Lavalink latency
Spotify status
Resolver queue
Active imports
Queue size
CPU
Memory
Cache hit
Current track
```

---

# 66. P2 — Metrics

```text
spotify_api_latency
spotify_pages
spotify_tracks
spotify_429
playlist_import_duration

youtube_search_latency
match_cache_hit
match_failures

time_to_first_audio
track_gap
queue_size
active_players
```

---

# 67. P2 — Observability Dashboard

Web:

```text
SYSTEM

Players       12
Active Guilds  18
Spotify Jobs   3
Resolver       2/3
Cache Hit      87%
429            0

CPU            38%
RAM            412 MB
```

---

# 68. P3 — Advanced Playlist Features

## Playlist Sync

Cho phép:

```text
Spotify Playlist
       ↕
Saved Bot Playlist
```

Có mode:

```text
One-time import
Sync manually
Auto-sync
```

Không nên triển khai auto-sync trước persistence và rate-limit handling.

---

# 69. P3 — Playlist Versioning

Lưu:

```text
snapshot #1
snapshot #2
snapshot #3
```

Có thể phát hiện:

```text
added tracks
removed tracks
reordered tracks
```

---

# 70. P3 — Smart Autoplay

Nguồn:

```text
current track
recent history
liked tracks
artist
genre
```

Tạo:

```text
autofill queue
```

Nhưng luôn ưu tiên:

```text
user queue > autoplay
```

---

# 71. P3 — Group Listening

Mở rộng FlaviBot-style live player:

```text
Web users
+
Discord users
      ↓
same guild player
```

Có thể thêm:

```text
listener count
shared controls
```

---

# 72. P3 — Multi-node Lavalink

Khi scale:

```text
Discord Bot
      │
      ▼
Player Router
 ┌────┼────┐
 ▼    ▼    ▼
Node1 Node2 Node3
```

Node selection:

```text
load
latency
guild count
CPU
```

---

# 73. Testing Matrix

## Spotify playlist

```text
[ ] 1
[ ] 10
[ ] 99
[ ] 100
[ ] 101
[ ] 250
[ ] 500
[ ] 1000
[ ] 2000
[ ] 5000
```

---

## Concurrent operations

```text
[ ] playlist import + /play
[ ] playlist import + /skip
[ ] playlist import + /stop
[ ] playlist import + /leave
[ ] two playlist imports
[ ] search + prefetch
```

---

## Web

```text
[ ] Discord login
[ ] guild selection
[ ] live queue
[ ] drag reorder
[ ] play/pause
[ ] seek
[ ] volume
[ ] websocket reconnect
```

---

# 74. Performance Targets

## Interaction

```text
deferReply < 1s
initial response < 3s
```

## Playlist

```text
first queue chunk: ASAP
background import: bounded
```

## Memory

Không tạo:

```text
1000 Track resolve promises
```

## Audio

```text
No duplicate playback
No stale callback
No indefinite FFmpeg hang
```

---

# 75. Priority Matrix

## P0 — bắt buộc

```text
✓ FSM
✓ playback generation
✓ QueueManager
✓ voice ownership
✓ defer timing
✓ Spotify pagination
✓ background playlist import
✓ lazy resolution
✓ backpressure
✓ concurrency limits
✓ Render health lifecycle
```

## P1 — FlaviBot core experience

```text
✓ live queue
✓ search-and-add
✓ reorder
✓ previous/history
✓ saved playlists
✓ favorites
✓ volume
✓ seek
✓ filters
✓ loop
✓ shuffle
✓ autoplay
✓ radio
```

## P2 — Full platform

```text
✓ Web player
✓ OAuth
✓ WebSocket
✓ drag-to-reorder
✓ web search
✓ web playlists
✓ persistent history
✓ diagnostics
✓ metrics
```

## P3 — Scale

```text
✓ playlist sync
✓ recommendation engine
✓ multi-node Lavalink
✓ group listening
✓ advanced analytics
```

---

# 76. Migration Roadmap từ bot hiện tại

## Phase A — Spotify Hotfix

```text
[ ] SpotifyAuthManager
[ ] SpotifyClient
[ ] SpotifyPaginator
[ ] SpotifyTrackMapper
[ ] playlist import job
[ ] chunk enqueue
[ ] cancellation
```

## Phase B — Playback Hardening

```text
[ ] FSM
[ ] generation
[ ] queue manager
[ ] voice ownership
[ ] concurrency
[ ] backpressure
[ ] retry
```

## Phase C — FlaviBot Queue UX

```text
[ ] live queue
[ ] search-and-add
[ ] move
[ ] remove
[ ] history
[ ] previous
[ ] favorites
[ ] saved playlists
```

## Phase D — Playback Features

```text
[ ] volume
[ ] seek
[ ] loop
[ ] shuffle
[ ] filters
[ ] autoplay
[ ] radio
```

## Phase E — Web Player

```text
[ ] OAuth
[ ] dashboard
[ ] player
[ ] live queue
[ ] websocket
[ ] drag/reorder
[ ] web search
[ ] playlists
```

## Phase F — Scale

```text
[ ] persistence
[ ] metrics
[ ] cache
[ ] multi-node
[ ] load test
```

---

# 77. Không nên làm

```text
✗ Chỉ tăng playlistPageLimit để cố vượt 100
✗ Resolve YouTube 1000 bài cùng lúc
✗ Tạo 1000 promise resolver
✗ Cho playlist background chiếm resolver pool
✗ Cho frontend tự quyết định queue state
✗ Cho /stop nhưng playlist worker vẫn tiếp tục add
✗ Cache stream URL vô hạn
✗ Copy nguyên implementation của FlaviBot
✗ Xây Web Player trước khi playback backend ổn định
✗ Thêm Redis/Kafka chỉ vì "scale"
```

---

# 78. Target User Experience

Người dùng nhập:

```text
/play https://open.spotify.com/playlist/...
```

Bot:

```text
🎵 My Playlist

847 tracks detected

✅ Added 25 tracks
🔄 Loading remaining tracks...

[Cancel Import]
```

Trong nền:

```text
25 / 847
50 / 847
100 / 847
...
847 / 847
```

Trong khi bài hiện tại vẫn phát:

```text
Now Playing
─────────────────
Blinding Lights
The Weeknd

02:11 / 03:20
██████████░░░
```

User khác có thể:

```text
/search Starboy
     ↓
Add
```

Playlist lớn không cản trở.

Trên Web:

```text
Queue
────────────────
1. Blinding Lights
2. Starboy
3. Save Your Tears
4. Die For You

        ↕ drag
```

---

# 79. Kiến trúc cuối cùng

```text
                         Discord
                            │
                         Web UI
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        Discord Controls             Web Controls
              │                           │
              └─────────────┬─────────────┘
                            ▼
                    ┌───────────────┐
                    │ PlayerService │
                    │ FSM + Gen ID  │
                    └───────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        QueueManager    History       Autoplay/Radio
             │
             ▼
      PlaylistService
             │
      ┌──────┴───────┐
      ▼              ▼
 SpotifyImport    SavedPlaylists
      │
      ▼
 SpotifyPaginator
      │
      ▼
 Source Resolver
 ┌────┼────────┬─────────┐
 ▼    ▼        ▼         ▼
YT Spotify   SC        Direct
 │
 ▼
Match Cache
 │
 ▼
Lavalink
 │
 ▼
Discord Voice
```

---

# 80. Definition of Done

Bot được coi là đạt FlaviBot-inspired baseline khi:

```text
✅ Spotify playlist > 100 không dừng
✅ Pagination chạy tới hết collection
✅ Playlist import chạy nền
✅ Có cancel
✅ Có backpressure
✅ Không resolve 1000 bài cùng lúc
✅ Có YouTube matching cache
✅ Queue mutation tập trung
✅ Playback có FSM
✅ Playback generation chống stale task

✅ Live queue
✅ Search-and-add
✅ Reorder
✅ Remove
✅ Shuffle
✅ Loop
✅ Previous
✅ History
✅ Favorites
✅ Saved playlists
✅ Volume
✅ Seek
✅ Filters
✅ Autoplay
✅ Radio

✅ Web player
✅ OAuth
✅ WebSocket
✅ Drag-and-drop queue
✅ Web search
✅ Web playlist
```

---

# 81. Kết luận

Hướng nâng cấp theo FlaviBot không nên hiểu là:

```text
"làm giống FlaviBot bằng cách copy code"
```

mà nên là:

```text
FlaviBot UX
      +
Bot hiện tại
      +
Lavalink/Kazagumo architecture
      +
Spotify API pagination
      +
Scalable async pipeline
```

Trong đó **Spotify playlist >100 bài** là bài toán nền tảng cần giải quyết đầu tiên:

```text
Spotify API Pagination
        ↓
Async Generator
        ↓
Chunked Import
        ↓
Background Job
        ↓
Backpressure
        ↓
Queue Manager
        ↓
Lazy YouTube Resolution
        ↓
Lavalink
```

Sau khi pipeline này ổn định mới xây Live Web Player.

Đây là hướng cho một bot có trải nghiệm kiểu FlaviBot nhưng backend hiện đại, dễ scale và không bị khóa bởi giới hạn 100 track của adapter hiện tại.
