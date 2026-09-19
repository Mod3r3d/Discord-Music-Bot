"""
services/youtube_service.py
----------------------------
Service Layer chuyên trách yt-dlp.
Tối giản hoá: Tin tưởng tuyệt đối vào thuật toán Top 1 của YouTube để luôn lấy bản Official.
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
    opts.update({
        "format": "bestaudio/best",
        "extract_flat": "in_playlist",
        "extractor_args": _build_extractor_args(),
    })
    cookie_path = os.getenv("YTDLP_COOKIES_FILE")
    if cookie_path: opts["cookiefile"] = cookie_path
    return opts

def _stream_options(player_clients: Optional[List[str]] = None) -> dict:
    opts = config.build_common_ytdlp_options()
    extractor_args = _build_extractor_args()
    if player_clients:
        extractor_args = dict(extractor_args)
        extractor_args["youtube"] = {"player_client": player_clients}
    opts.update({
        "format": "bestaudio/best",
        "noplaylist": True,
        "extractor_args": extractor_args,
    })
    cookie_path = os.getenv("YTDLP_COOKIES_FILE")
    if cookie_path: opts["cookiefile"] = cookie_path
    return opts

_PLAYER_CLIENT_FALLBACK_CHAINS = [["android", "ios"], ["tv_embedded"]]


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
        data = await self._run(lambda: self._ytdl_flat.extract_info(f"ytsearch{count}:{query}", download=False))
        results = []
        for entry in (data.get("entries") or []):
            if entry:
                results.append(Track(
                    title=entry.get("title") or "Unknown",
                    webpage_url=entry.get("url") or entry.get("webpage_url"),
                    artist=entry.get("uploader") or "",
                    duration=entry.get("duration") or 0,
                    thumbnail=(entry.get("thumbnails") or [{}])[-1].get("url") if entry.get("thumbnails") else entry.get("thumbnail"),
                    source="youtube",
                ))
        return results

    async def _match_spotify_to_youtube(self, track: Track) -> str:
        """Sử dụng cơ chế tìm kiếm đơn giản: Lấy chính xác TOP 1 kết quả từ YouTube."""
        if track.webpage_url and track.webpage_url in self._matching_cache:
            return self._matching_cache[track.webpage_url]

        clean_artist = track.artist.split(",")[0].strip() if track.artist else ""
        
        # ytsearch1: Chỉ yêu cầu yt-dlp trả về đúng 1 kết quả đầu tiên (Top 1)
        search_query = f"ytsearch1:{track.title} {clean_artist}".strip()
        
        try:
            data = await self._run(lambda: self._ytdl_flat.extract_info(search_query, download=False))
            entries = data.get("entries") or []
            
            if entries and entries[0]:
                best_url = entries[0].get("url") or entries[0].get("webpage_url")
                if not best_url and entries[0].get("id"):
                    best_url = f"https://www.youtube.com/watch?v={entries[0].get('id')}"
                    
                if best_url:
                    if track.webpage_url:
                        self._matching_cache[track.webpage_url] = best_url
                    log.info("Lấy Top 1 YouTube cho Spotify '%s' -> '%s'", track.title, entries[0].get("title"))
                    return best_url
        except Exception as exc:  # noqa: BLE001
            log.warning("Lỗi tìm kiếm YouTube cho '%s': %s", track.title, exc)

        return f"{track.artist} - {track.title}".strip()

    async def resolve_stream(self, track: Track) -> dict:
        if track.source == "spotify" or (track.webpage_url and "spotify.com" in track.webpage_url):
            query = await self._match_spotify_to_youtube(track)
        else:
            query = track.stream_url or track.webpage_url or f"{track.title} {track.artist}".strip()

        last_error = None
        for player_clients in _PLAYER_CLIENT_FALLBACK_CHAINS:
            try:
                ytdl = yt_dlp.YoutubeDL(_stream_options(player_clients))
                data = await self._run(lambda: ytdl.extract_info(query, download=False))
                if "entries" in data and data["entries"]: data = data["entries"][0]
                if not data.get("url"): raise yt_dlp.utils.DownloadError("No stream URL")
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
                continue
        raise RuntimeError(f"Không thể lấy stream: {last_error}")

youtube_service = YouTubeService()