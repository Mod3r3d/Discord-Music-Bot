# FlaviBot/JMusicBot Feature Port Plan — Queue, Now Playing & Random Play

> **Nguồn tham khảo:** `MusicBot-master.zip` (JMusicBot Java/LavaPlayer).
>
> **Mục tiêu:** lấy các ý tưởng đã có sẵn trong project tham khảo — Queue, Now Playing, Shuffle/Fair Queue, Repeat và Requester metadata — rồi port sang Discord Music Bot hiện tại (Node.js + discord.js + Kazagumo/Shoukaku + Lavalink) theo hướng phù hợp với kiến trúc hiện tại.
>
> **Nguyên tắc:** học kiến trúc và hành vi, không copy nguyên code Java sang Node.js.

---

# 1. Những gì project tham khảo đã làm tốt

Project tham khảo đã có sẵn các thành phần:

```text
commands/music/
├── QueueCmd.java
├── NowplayingCmd.java
├── ShuffleCmd.java
├── PlayCmd.java
├── RemoveCmd.java
├── SkipCmd.java
└── SearchCmd.java

audio/
├── AudioHandler.java
├── NowplayingHandler.java
├── QueuedTrack.java
└── RequestMetadata.java

queue/
├── AbstractQueue.java
├── LinearQueue.java
├── FairQueue.java
└── Queueable.java

settings/
├── QueueType.java
└── RepeatMode.java
```

Điểm đáng port:

```text
Queue abstraction
Requester metadata
Queue pagination
Current queue summary
Now Playing embed
Progress bar
Shuffle
Fair Queue
Repeat mode
Track history/state
```

---

# 2. Mapping sang bot Node hiện tại

## Project tham khảo

```text
AudioHandler
QueueCmd
NowplayingCmd
ShuffleCmd
QueuedTrack
FairQueue
RepeatMode
```

## Bot hiện tại

Nên chuyển thành:

```text
PlayerService
QueueService
NowPlayingService
Track model
FairQueue strategy
RepeatMode
```

Kiến trúc:

```text
discord.js command
       │
       ▼
  PlayerService
       │
   ┌───┴────┐
   ▼        ▼
QueueService AudioService
   │        │
   │        ▼
   │      Lavalink
   ▼
Track[]
```

---

# 3. PlayerState

Tạo một state trung tâm cho từng guild:

```js
class PlayerState {
    constructor(guildId) {
        this.guildId = guildId;

        this.current = null;
        this.queue = [];

        this.history = [];

        this.repeat = "off";
        this.shuffle = false;

        this.volume = 100;

        this.nowPlayingMessageId = null;
        this.nowPlayingChannelId = null;

        this.playbackGeneration = 0;
    }
}
```

Không để command tự giữ state riêng.

---

# 4. Track model

Port ý tưởng `QueuedTrack` + `RequestMetadata`.

```js
class Track {
    constructor({
        title,
        author,
        url,
        duration,
        thumbnail,
        requesterId,
        source,
        sourceId
    }) {
        this.title = title;
        this.author = author;
        this.url = url;
        this.duration = duration;
        this.thumbnail = thumbnail;

        this.requesterId = requesterId;

        this.source = source;
        this.sourceId = sourceId;
    }
}
```

Các field này sẽ được dùng bởi:

```text
Queue
Now Playing
History
Requester display
Remove permission
Shuffle
Playlist
```

---

# 5. Queue Service

Tạo:

```text
services/
└── queue/
    ├── queue_service.js
    ├── queue_strategy.js
    ├── linear_queue.js
    ├── fair_queue.js
    └── shuffle.js
```

API:

```js
queue.add(track)
queue.addNext(track)
queue.remove(index)
queue.move(from, to)
queue.clear()
queue.shuffle()
queue.next()
queue.peek(index)
queue.size()
queue.totalDuration()
```

---

# 6. Queue command

## Command

```text
/queue
```

Optional:

```text
/queue 2
```

→ page 2.

---

# 7. Queue UI

Project tham khảo hiển thị:

```text
Current Queue
10 entries
Total duration
Current track
Repeat mode
Queue type
```

Port sang embed:

```text
🎵 Current Queue

▶ Now Playing:
Blinding Lights — The Weeknd

1. Starboy — 03:50
2. Save Your Tears — 03:35
3. Die For You — 04:20
4. After Hours — 06:01

📦 4 tracks
⏱ 17:46
🔁 Queue Loop
🔢 Fair Queue
```

---

# 8. Queue pagination

Không đưa toàn bộ queue vào một message.

Đề xuất:

```text
10 tracks/page
```

hoặc:

```text
15 tracks/page
```

UI:

```text
[◀ Previous] [Page 1/4] [Next ▶]
```

Nếu queue > 100:

```text
Không tạo 100 button.
```

Dùng:

```text
Previous
Next
First
Last
```

---

# 9. Queue item format

Mỗi entry:

```text
01. `[03:21]` Blinding Lights
    👤 Huy
```

Hoặc:

```text
01. Blinding Lights — The Weeknd
    03:21 • requested by Huy
```

Không chỉ hiển thị title.

---

# 10. Queue total duration

Tính:

```js
const total = queue.reduce(
    (sum, track) => sum + track.duration,
    0
);
```

Hiển thị:

```text
📦 37 tracks
⏱ 2h 14m 32s
```

Có thể tách:

```text
Current remaining:
01:42

Queue:
02:14:32
```

---

# 11. Now Playing

Tạo:

```text
services/player/now_playing_service.js
```

API:

```js
getNowPlaying(guildId)
createMessage(player)
updateMessage(player)
clearMessage(player)
```

---

# 12. Now Playing Embed

Đề xuất:

```text
🎵 NOW PLAYING

Blinding Lights
The Weeknd

Requested by: Huy

▶ ███████████░░░ 02:11 / 03:20
🔊 80%
```

Thumbnail:

```text
YouTube thumbnail
```

---

# 13. Progress bar

Port ý tưởng từ project tham khảo:

```text
progress =
    currentPosition / duration
```

Tạo utility:

```js
function progressBar(position, duration, length = 14) {
    ...
}
```

Ví dụ:

```text
████████░░░░░░  02:11 / 03:20
```

---

# 14. Progress update strategy

Không edit message mỗi 1 giây.

Dùng:

```text
5–10 seconds
```

hoặc event-driven.

Update khi:

```text
track start
track end
pause
resume
seek
volume
filter
```

Progress timer chỉ update coarse.

---

# 15. Now Playing controls

Đây là phần nên làm theo hướng FlaviBot.

Buttons:

```text
⏮ Previous
⏸ Pause
▶ Resume
⏭ Skip
🔀 Shuffle
🔁 Repeat
```

Thêm:

```text
📜 Queue
❤️ Favorite
🎤 Lyrics
```

---

# 16. Button architecture

Không đặt business logic trong button handler.

Đúng:

```text
Button
  ↓
PlayerService
  ↓
QueueService
  ↓
Lavalink
  ↓
Update UI
```

Sai:

```text
Button
  ↓
trực tiếp player.skip()
```

---

# 17. Now Playing message persistence

PlayerState lưu:

```js
nowPlayingMessageId
nowPlayingChannelId
```

Khi restart:

```text
message tồn tại
→ edit lại
```

Nếu message bị xóa:

```text
create new message
```

---

# 18. Current track

`PlayerService` phải có:

```js
getCurrentTrack()
```

Không đọc trực tiếp `player.queue`.

Ví dụ:

```js
const current = playerState.current;
```

---

# 19. Track History

Project tham khảo có logic để quản lý track hiện tại và metadata.

Bot Node nên thêm:

```js
history.push(currentTrack)
```

Giới hạn:

```env
HISTORY_SIZE=50
```

---

# 20. Commands History

```text
/history
/previous
/replay
```

`/previous`:

```text
history.pop()
↓
queue.addNext()
↓
play
```

Không làm:

```text
queue.unshift(lastTrack)
```

mà không cập nhật history.

---

# 21. Shuffle — học từ ShuffleCmd

Project tham khảo có:

```text
shuffle songs you have added
```

Tức shuffle có thể theo requester, không nhất thiết đảo toàn bộ queue.

Bot Node nên hỗ trợ hai mode:

```text
/shuffle
```

→ shuffle toàn queue.

Và:

```text
/shuffle mine
```

→ chỉ shuffle bài do requester thêm.

---

# 22. Random Play — feature mới

Cần tách rõ hai khái niệm:

```text
Shuffle
=
đảo thứ tự queue hiện có

Random Play
=
chọn một bài ngẫu nhiên để phát
```

Không nên gộp thành một feature.

---

# 23. `/random` — MVP

Đề xuất:

```text
/random
```

Bot chọn một bài từ:

```text
available random source
```

MVP có thể dùng:

```text
YouTube search
```

với từ khóa random.

Nhưng kiểu:

```text
/random
→ random() từ kết quả YouTube
```

có tính không ổn định.

Tốt hơn là xây:

```text
RandomSource
```

---

# 24. RandomSource

Interface:

```js
class RandomSource {
    async getRandomTrack(context) {
        ...
    }
}
```

Implement:

```text
QueueRandomSource
HistoryRandomSource
PlaylistRandomSource
YouTubeDiscoverySource
SpotifyDiscoverySource
```

---

# 25. `/random queue`

Mode an toàn nhất:

```text
/random queue
```

chọn một track đang nằm trong queue.

Ví dụ:

```text
Queue:
A B C D E

/random queue
→ C
```

Sau đó:

```text
remove C
→ play C
```

---

# 26. `/random history`

```text
/random history
```

chọn một track từ history.

Không cho chọn current track.

```js
history.filter(t => t.id !== current.id)
```

---

# 27. `/random playlist`

```text
/random playlist <name>
```

chọn random trong saved playlist.

Đây là mode rất hữu ích khi sau này có:

```text
Saved Playlists
```

---

# 28. `/random spotify`

```text
/random spotify <playlist/url>
```

Không tải toàn playlist chỉ để chọn một bài.

Thay:

```text
fetch collection metadata
↓
random offset
↓
fetch page containing offset
↓
choose track
```

Đặc biệt hữu ích cho playlist hàng nghìn bài.

---

# 29. `/random discover`

Đây là mode nâng cao:

```text
/random discover
```

Bot tìm bài mới dựa trên:

```text
current artist
history
liked tracks
genre
```

MVP có thể dùng search heuristics.

Sau này:

```text
Spotify recommendations
```

---

# 30. Random anti-repeat

Không để:

```text
A
A
A
B
A
```

Tạo history blacklist:

```text
recentRandomIds
```

Ví dụ:

```env
RANDOM_NO_REPEAT=10
```

Random candidate:

```js
candidates.filter(
    track => !recentRandomIds.includes(track.id)
)
```

---

# 31. Random cooldown

Nếu:

```text
/random
/random
/random
```

liên tục:

```text
rate limit
```

Có thể:

```env
RANDOM_COOLDOWN=5
```

per user.

---

# 32. Random requester

Ghi:

```js
requesterId
```

để Now Playing hiển thị:

```text
🎲 Random Track

Blinding Lights
The Weeknd

Requested by:
Huy
```

---

# 33. Fair Queue — học từ project tham khảo

Project tham khảo có:

```text
LinearQueue
FairQueue
QueueType
```

Port:

```text
QueueStrategy
├── Linear
└── Fair
```

---

# 34. Linear Queue

```text
A1
A2
A3
B1
B2
```

Đây là default đơn giản.

---

# 35. Fair Queue

```text
A1
B1
C1
A2
B2
A3
```

Kết hợp:

```text
requesterId
```

để phân phối bài công bằng.

---

# 36. Queue Mode Setting

Thêm server setting:

```text
/queue-mode linear
/queue-mode fair
```

UI:

```text
Queue Mode
○ Linear
● Fair
```

---

# 37. Repeat

Port `RepeatMode`:

```text
OFF
SINGLE
ALL
```

Commands:

```text
/repeat off
/repeat track
/repeat queue
```

UI:

```text
🔁 OFF
🔂 TRACK
🔁 QUEUE
```

---

# 38. Repeat implementation

## Track repeat

```text
current
 ↓
clone/replay
 ↓
same current
```

## Queue repeat

```text
A B C

A → B → C
      ↓
A → B → C
```

Không nên mutate history sai.

---

# 39. Play command integration

Luồng:

```text
/play song
      ↓
resolve
      ↓
Track
      ↓
QueueService.add()
      ↓
PlayerService
      ↓
NowPlayingService
```

Nếu đang idle:

```text
add
↓
play immediately
```

Nếu đang playing:

```text
add queue
```

---

# 40. `/playtop`

Port ý tưởng priority insert:

```text
/playtop <query>
```

→ queue position 1.

---

# 41. `/playskip`

Thêm:

```text
/playskip <query>
```

Flow:

```text
current A
queue B C

/playskip D

A stops
D plays
B C remain
```

Generation guard bắt buộc.

---

# 42. `/queue remove`

```text
/queue remove 4
```

Validate:

```text
1 <= index <= queue.size
```

Sau đó:

```text
queue.remove(index - 1)
```

---

# 43. `/queue move`

```text
/queue move 8 2
```

Port trực tiếp ý tưởng `moveItem()`:

```js
queue.move(from, to)
```

---

# 44. `/queue clear`

Giữ current:

```text
current = A
queue = B C D

/queue clear

current = A
queue = []
```

Không stop current nếu user chỉ muốn clear queue.

---

# 45. `/queue remove-mine`

Dựa trên requester metadata:

```text
/queue remove-mine
```

Xóa các track do user hiện tại thêm.

Port ý tưởng:

```text
removeAll(identifier)
```

---

# 46. Permissions

## Everyone

```text
/queue
/nowplaying
/history
```

## Same voice users

```text
/skip
/pause
/resume
/random
/shuffle
```

## DJ/Admin

```text
/queue clear
/queue remove others
/playtop
/playskip
/force skip
```

---

# 47. Now Playing + Queue synchronization

Khi:

```text
track start
```

phải:

```text
update current
→ update Now Playing
→ update queue UI
```

Khi:

```text
queue mutation
```

chỉ cần:

```text
update queue UI
```

Không recreate player message nếu không cần.

---

# 48. Event-driven design

Lavalink/Kazagumo events:

```text
playerStart
playerEnd
playerPause
playerResume
playerEmpty
playerError
```

Mapping:

```text
playerStart
→ NowPlayingService.update()

playerEnd
→ HistoryService.add()
→ QueueService.next()

playerEmpty
→ autoplay / disconnect
```

---

# 49. Recommended files

```text
src/
├── services/
│   ├── player/
│   │   ├── player_service.js
│   │   ├── player_state.js
│   │   └── playback_events.js
│   │
│   ├── queue/
│   │   ├── queue_service.js
│   │   ├── linear_queue.js
│   │   ├── fair_queue.js
│   │   └── shuffle.js
│   │
│   ├── nowplaying/
│   │   └── now_playing_service.js
│   │
│   ├── history/
│   │   └── history_service.js
│   │
│   └── random/
│       ├── random_service.js
│       └── random_sources.js
│
├── models/
│   ├── track.js
│   └── player_state.js
│
└── commands/
    ├── queue.js
    ├── nowplaying.js
    ├── random.js
    ├── shuffle.js
    ├── repeat.js
    └── playback.js
```

---

# 50. Command roadmap

## Queue

```text
/queue
/queue remove <position>
/queue move <from> <to>
/queue clear
/queue remove-mine
```

## Playback

```text
/play
/playtop
/playskip
/pause
/resume
/skip
/stop
```

## Now Playing

```text
/nowplaying
```

## Queue control

```text
/shuffle
/repeat
```

## Random

```text
/random
/random queue
/random history
/random playlist
/random spotify
/random discover
```

---

# 51. MVP scope

Không làm tất cả cùng lúc.

## MVP-1

```text
[ ] PlayerState
[ ] Track model
[ ] QueueService
[ ] /queue
[ ] /nowplaying
[ ] /shuffle
[ ] /random queue
```

## MVP-2

```text
[ ] queue pagination
[ ] /queue remove
[ ] /queue move
[ ] /queue clear
[ ] /repeat
[ ] history
[ ] /previous
```

## MVP-3

```text
[ ] fair queue
[ ] /playtop
[ ] /playskip
[ ] random playlist
[ ] anti-repeat
```

## MVP-4

```text
[ ] live Now Playing buttons
[ ] search-and-add
[ ] favorites
[ ] saved playlists
```

---

# 52. Acceptance Criteria

## Queue

```text
✓ /queue hiển thị current + queue
✓ Pagination hoạt động
✓ Tổng duration chính xác
✓ Requester hiển thị
✓ Remove hoạt động
✓ Move hoạt động
✓ Clear không stop current
```

## Now Playing

```text
✓ title
✓ artist
✓ requester
✓ thumbnail
✓ duration
✓ current position
✓ progress bar
✓ volume/status
✓ tự update khi đổi track
```

## Random

```text
✓ /random queue chọn đúng một track
✓ /random không lặp liên tục
✓ current track không tự chọn lại
✓ random luôn đi qua PlayerService
✓ requester metadata đúng
✓ permission đúng
```

## Concurrency

```text
✓ /skip + /random không tạo double playback
✓ /queue move + /skip không corrupt queue
✓ stale playback generation bị bỏ
```

---

# 53. Benchmark

Test:

```text
Queue 10
Queue 100
Queue 500
Queue 1000
```

Đo:

```text
/queue response latency
Now Playing update latency
shuffle latency
random latency
memory
```

Không serialize toàn queue vào:

```text
Discord message
```

---

# 54. FlaviBot-style next step

Sau khi MVP ổn định:

```text
Discord
  +
Web Player
```

Web UI:

```text
Now Playing
Queue
Search
Drag/Drop
Volume
Seek
Shuffle
Repeat
```

Dùng chung:

```text
PlayerService
QueueService
```

Không tạo player engine thứ hai cho web.

---

# 55. Final architecture

```text
                       Discord Commands
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                    Queue         Playback
                      │               │
                      ▼               ▼
                QueueService    PlayerService
                      │               │
        ┌─────────────┼───────────────┤
        ▼             ▼               ▼
      Linear        Fair          RandomService
                      │               │
                      └───────┬───────┘
                              ▼
                          Lavalink
                              │
                              ▼
                         Discord Voice

                         │
                         ▼
                   NowPlayingService
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
          Discord Embed         WebSocket
                                   │
                                   ▼
                               Web Player
```

---

# 56. Kết luận

Từ project tham khảo, ba phần nên port đầu tiên là:

```text
1. QueueService
2. NowPlayingService
3. RandomService
```

Trong đó:

```text
QueueService
```

là nền tảng cho:

```text
queue
shuffle
fair queue
repeat
history
playtop
move/remove
```

`NowPlayingService` là nền tảng cho:

```text
progress
controls
web player
```

`RandomService` nên tách khỏi `Shuffle`:

```text
Shuffle:
đảo queue

Random:
chọn nguồn và chọn track ngẫu nhiên
```

Với bot hiện tại, thứ tự triển khai tối ưu là:

```text
PlayerState
   ↓
Track model
   ↓
QueueService
   ↓
/queue
   ↓
NowPlayingService
   ↓
/nowplaying
   ↓
/shuffle
   ↓
/random queue
   ↓
History + Previous
   ↓
Fair Queue
   ↓
Random Playlist/Spotify
   ↓
Interactive Now Playing
   ↓
Web Player
```

Mục tiêu cuối cùng là có trải nghiệm gần kiểu FlaviBot nhưng giữ backend hiện tại của bot: **Kazagumo + Shoukaku + Lavalink**, thay vì thay toàn bộ hệ thống.
