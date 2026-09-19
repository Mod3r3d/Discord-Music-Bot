"""
services/youtube_service.py
----------------------------
Service Layer chuyên trách yt-dlp & Matching thông minh:
  - Tích hợp Semaphore giới hạn Concurrency.
  - Bổ sung thuật toán Scoring loại bỏ Remix/Lofi/Cover khi phát từ Spotify.
  - Cache kết quả khớp giữa Spotify và YouTube.
"""
import os
import asyncio
from typing import Any, Dict, List, Optional

import yt_dlp

from core import config
from core.logger import get_logger
from models.track import Track

log = get_logger("services.youtube")


def _build_extractor_args() -> dict:
    args = config.build_ytdl_extractor_args()
    if config.POT_PROVIDER_URL:
        args["youtubepot-bgutilhttp"] = {"base_url": [config.POT_PROVIDER_URL]}
    return args


def _flat_options() -> dict:
    opts = config.build_common_ytdlp_options()
    opts.update(
        {
            "format": "bestaudio/best",
            "extract_flat": "in_playlist",
            "extractor_args": _build_extractor_args(),
        }
    )
    cookie_path = os.getenv("YTDLP_COOKIES_FILE")
    if cookie_path:
        opts["cookiefile"] = cookie_path
    return opts


def _stream_options(player_clients: Optional[List[str]] = None) -> dict:
    opts = config.build_common_ytdlp_options()
    extractor_args = _build_extractor_args()
    if player_clients:
        extractor_args = dict(extractor_args)
        extractor_args["youtube"] = {"player_client": player_clients}
    opts.update(
        {
            "format": "bestaudio/best",
            "noplaylist": True,
            "extractor_args": extractor_args,
        }
    )
    cookie_path = os.getenv("YTDLP_COOKIES_FILE")
    if cookie_path:
        opts["cookiefile"] = cookie_path
    return opts


def _soundcloud_options() -> dict:
    opts = config.build_common_ytdlp_options()
    opts.update({"format": "bestaudio/best", "noplaylist": True, "default_search": "scsearch"})
    return opts


_PLAYER_CLIENT_FALLBACK_CHAINS = [
    ["android", "ios"],
    ["tv_embedded"],
]


def _score_candidate(candidate: dict, original_title: str, original_artist: str, target_duration: int) -> int:
    """Chấm điểm kết quả tìm kiếm YouTube để chọn đúng bản gốc (loại trừ Remix, Lofi, Cover)."""
    score = 0
    cand_title = (candidate.get("title") or "").lower()
    cand_uploader = (candidate.get("uploader") or "").lower()
    orig_title_lower = original_title.lower()
    orig_artist_lower = original_artist.lower()
    cand_duration = candidate.get("duration") or 0

    # 1. Trừ điểm nặng các biến thể nếu bản gốc Spotify không yêu cầu
    unwanted_tags = [
        "remix", "lofi", "lo-fi", "slowed", "speed up", "sped up",
        "cover", "karaoke", "live", "acoustic", "mashup", "parody", "beat", "instrumental"
    ]
    for tag in unwanted_tags:
        if tag not in orig_title_lower and tag in cand_title:
            score -= 120

    # 2. Ưu tiên kênh YouTube Music Topic hoặc kênh chính thức của nghệ sĩ
    if "topic" in cand_uploader:
        score += 60
    if orig_artist_lower and orig_artist_lower in cand_uploader:
        score += 40

    # 3. Ưu tiên video dán nhãn Official
    if "official audio" in cand_title:
        score += 50
    elif "official music video" in cand_title or "official mv" in cand_title:
        score += 35
    elif "official video" in cand_title:
        score += 30
    elif "audio" in cand_title:
        score += 15

    # 4. So khớp thời lượng (Bản Remix/Lofi thường lệch thời lượng rất nhiều so với bản gốc)
    if target_duration > 0 and cand_duration > 0:
        diff = abs(target_duration - cand_duration)
        if diff <= 3:
            score += 60
        elif diff <= 8:
            score += 35
        elif diff <= 15:
            score += 10
        elif diff > 35:
            score -= 50

    return score


class YouTubeService:
    def __init__(self):
        self._ytdl_flat = yt_dlp.YoutubeDL(_flat_options())
        self._semaphore = asyncio.Semaphore(2)
        self._matching_cache: Dict[str, str] = {}

    async def _run(self, func):
        loop = asyncio.get_running_loop()
        async with self._semaphore:
            return await loop.run_in_executor(None, func)

    async def extract_flat(self, query: str) -> dict:
        return await self._run(lambda: self._ytdl_flat.extract_info(query, download=False))

    async def search_candidates(self, query: str, count: int = 5) -> List[Track]:
        search_query = f"ytsearch{count}:{query}"
        data = await self._run(
            lambda: self._ytdl_flat.extract_info(search_query, download=False)
        )
        entries = data.get("entries") or []
        results = []
        for entry in entries:
            if not entry:
                continue
            duration = entry.get("duration") or 0
            results.append(
                Track(
                    title=entry.get("title") or "Unknown",
                    webpage_url=entry.get("url") or entry.get("webpage_url"),
                    artist=entry.get("uploader") or "",
                    duration=duration,
                    thumbnail=(entry.get("thumbnails") or [{}])[-1].get("url")
                    if entry.get("thumbnails")
                    else entry.get("thumbnail"),
                    source="youtube",
                )
            )
        return results

    async def _match_spotify_to_youtube(self, track: Track) -> str:
        """Tìm bản YouTube gốc phù hợp nhất theo siêu dữ liệu của Spotify."""
        if track.webpage_url and track.webpage_url in self._matching_cache:
            return self._matching_cache[track.webpage_url]

        clean_artist = track.artist.split(",")[0].strip() if track.artist else ""
        
        # KHẮC PHỤC LỖI LOFI/REMIX: Ép YouTube tìm bản Official Audio để tránh các bản chế
        search_query = f'ytsearch5:"{track.title}" {clean_artist} official audio'.strip()

        try:
            data = await self._run(lambda: self._ytdl_flat.extract_info(search_query, download=False))
            entries = [e for e in (data.get("entries") or []) if e]
        except Exception as exc:  # noqa: BLE001
            log.warning("Lỗi trích xuất ứng viên cho '%s': %s", track.title, exc)
            entries = []

        if not entries:
            # Fallback nếu không tìm thấy bản official
            fallback_query = f"ytsearch5:{track.title} {clean_artist}".strip()
            try:
                data = await self._run(lambda: self._ytdl_flat.extract_info(fallback_query, download=False))
                entries = [e for e in (data.get("entries") or []) if e]
            except Exception:
                entries = []

        if entries:
            best = max(entries, key=lambda c: _score_candidate(c, track.title, track.artist, track.duration))
            best_url = best.get("url") or best.get("webpage_url")
            if not best_url and best.get("id"):
                best_url = f"https://www.youtube.com/watch?v={best.get('id')}"
            if best_url:
                if track.webpage_url:
                    self._matching_cache[track.webpage_url] = best_url
                log.info("Khớp Spotify '%s' -> YouTube: '%s' (%s)", track.title, best.get("title"), best_url)
                return best_url

        return f"{track.artist} - {track.title}".strip()

    async def resolve_stream(self, track: Track) -> dict:
        # Nếu bài hát đến từ Spotify, chạy bộ lọc tìm kiếm video chuẩn trước khi lấy stream
        if track.source == "spotify" or (track.webpage_url and "spotify.com" in track.webpage_url):
            query = await self._match_spotify_to_youtube(track)
        else:
            query = track.stream_url or track.webpage_url or f"{track.title} {track.artist}".strip()

        last_error: Optional[Exception] = None
        for player_clients in _PLAYER_CLIENT_FALLBACK_CHAINS:
            try:
                ytdl = yt_dlp.YoutubeDL(_stream_options(player_clients))
                data = await self._run(lambda: ytdl.extract_info(query, download=False))
                if "entries" in data and data["entries"]:
                    data = data["entries"][0]
                if not data.get("url"):
                    raise yt_dlp.utils.DownloadError("Không lấy được URL stream")
                return {
                    "title": data.get("title", track.title),
                    "webpage_url": data.get("webpage_url", track.webpage_url),
                    "stream_url": data.get("url"),
                    "duration": data.get("duration", 0),
                    "thumbnail": data.get("thumbnail") or track.thumbnail,
                    "source": "youtube",
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log.warning(
                    "player_client %s thất bại cho '%s': %s", player_clients, track.title, exc
                )
                continue

        if config.ENABLE_SOUNDCLOUD_FALLBACK:
            try:
                log.info("Fallback sang SoundCloud cho '%s'", track.title)
                sc_ytdl = yt_dlp.YoutubeDL(_soundcloud_options())
                sc_query = f"{track.title} {track.artist}".strip() or track.title
                data = await self._run(lambda: sc_ytdl.extract_info(sc_query, download=False))
                if "entries" in data and data["entries"]:
                    data = data["entries"][0]
                if data.get("url"):
                    return {
                        "title": data.get("title", track.title),
                        "webpage_url": data.get("webpage_url", track.webpage_url),
                        "stream_url": data.get("url"),
                        "duration": data.get("duration", 0),
                        "thumbnail": data.get("thumbnail") or track.thumbnail,
                        "source": "soundcloud",
                    }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log.warning("Fallback SoundCloud cũng thất bại cho '%s': %s", track.title, exc)

        raise RuntimeError(
            f"Không thể lấy luồng phát cho '{track.title}': {last_error}"
        )


youtube_service = YouTubeService()