"""
services/spotify_service.py
---------------------------
Spotify Resolver (Anonymous Web Token).
Không cần API Key. Không cần Spotify Premium.
Hỗ trợ phân trang vét cạn danh sách phát > 100 bài.
"""
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from core import config
from core.logger import get_logger
from models.track import Track

log = get_logger("services.spotify")

SPOTIFY_URL_REGEX = re.compile(
    r"(https?:\/\/open\.spotify\.com\/(track|album|playlist)\/([a-zA-Z0-9]+)|spotify:(track|album|playlist):([a-zA-Z0-9]+))"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

class SpotifyService:
    def __init__(self):
        self._matching_cache: Dict[str, str] = {}
        self._anon_token: Optional[str] = None
        self._token_expires_at: float = 0

    async def _get_anonymous_token(self) -> Optional[str]:
        # Tự động lấy "Giấy thông hành" dưới danh nghĩa khách truy cập web
        if self._anon_token and time.time() < self._token_expires_at:
            return self._anon_token

        url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._anon_token = data.get("accessToken")
                        exp_ms = data.get("accessTokenExpirationTimestampMs", 0)
                        self._token_expires_at = (exp_ms / 1000) - 60 if exp_ms else (time.time() + 1800)
                        return self._anon_token
        except Exception as exc:  # noqa: BLE001
            log.warning("Lỗi lấy token ẩn danh Spotify: %s", exc)
        return None

    def is_spotify_url(self, query: str) -> bool:
        return bool(SPOTIFY_URL_REGEX.search(query))

    def parse_url(self, query: str) -> Optional[Tuple[str, str]]:
        match = SPOTIFY_URL_REGEX.search(query)
        if not match:
            return None
        type_ = match.group(2) or match.group(4)
        id_ = match.group(3) or match.group(5)
        return type_, id_

    async def fetch_track(self, track_id: str, requester_id: int) -> Optional[Track]:
        token = await self._get_anonymous_token()
        if not token:
            raise RuntimeError("Không thể kết nối máy chủ Spotify.")
        
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Spotify từ chối truy cập (HTTP {resp.status})")
                t = await resp.json()
                
                artists = ", ".join(a.get("name", "") for a in t.get("artists", []))
                images = (t.get("album") or {}).get("images", [])
                thumb = images[0].get("url") if images else None
                duration_sec = int(t.get("duration_ms") or 0) // 1000
                
                return Track(
                    title=t.get("name", "Unknown Title"),
                    artist=artists,
                    duration=duration_sec,
                    webpage_url=t.get("external_urls", {}).get("spotify") or f"https://open.spotify.com/track/{track_id}",
                    thumbnail=thumb,
                    requester_id=requester_id,
                    source="spotify",
                )

    async def fetch_collection(self, type_: str, item_id: str, requester_id: int) -> Tuple[str, List[Track]]:
        token = await self._get_anonymous_token()
        if not token:
            raise RuntimeError("Không thể kết nối máy chủ Spotify.")
        
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        tracks: List[Track] = []
        title = f"Spotify {type_.capitalize()}"

        async with aiohttp.ClientSession(headers=headers) as session:
            if type_ == "album":
                base_url = f"https://api.spotify.com/v1/albums/{item_id}"
                async with session.get(base_url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        title = data.get("name", title)
                        items = data.get("tracks", {}).get("items", [])
                        for t in items:
                            if t and t.get("name"):
                                artists = ", ".join(a.get("name", "") for a in t.get("artists", []))
                                images = data.get("images", [])
                                thumb = images[0].get("url") if images else None
                                duration_sec = int(t.get("duration_ms") or 0) // 1000
                                
                                tracks.append(Track(
                                    title=t.get("name"),
                                    artist=artists,
                                    duration=duration_sec,
                                    webpage_url=t.get("external_urls", {}).get("spotify") or "",
                                    thumbnail=thumb,
                                    requester_id=requester_id,
                                    source="spotify",
                                ))

            elif type_ == "playlist":
                base_url = f"https://api.spotify.com/v1/playlists/{item_id}"
                async with session.get(f"{base_url}?fields=name,tracks.total", timeout=10) as resp:
                    if resp.status == 200:
                        meta = await resp.json()
                        title = meta.get("name", title)
                        total = meta.get("tracks", {}).get("total", 0)
                    else:
                        total = config.SPOTIFY_QUEUE_LIMIT

                offset = 0
                limit = 100 # Phân trang mỗi lần lấy 100 bài
                max_cap = min(total, config.SPOTIFY_QUEUE_LIMIT)

                while offset < max_cap:
                    items_url = f"{base_url}/tracks?offset={offset}&limit={limit}&fields=items(track(name,duration_ms,artists,external_urls,album(images)))"
                    async with session.get(items_url, timeout=10) as resp:
                        if resp.status != 200:
                            break
                        data = await resp.json()
                        items = data.get("items", [])
                        if not items:
                            break
                        
                        for entry in items:
                            t = entry.get("track")
                            if t and t.get("name"):
                                artists = ", ".join(a.get("name", "") for a in t.get("artists", []))
                                images = (t.get("album") or {}).get("images", [])
                                thumb = images[0].get("url") if images else None
                                duration_sec = int(t.get("duration_ms") or 0) // 1000
                                
                                tracks.append(Track(
                                    title=t.get("name"),
                                    artist=artists,
                                    duration=duration_sec,
                                    webpage_url=t.get("external_urls", {}).get("spotify") or "",
                                    thumbnail=thumb,
                                    requester_id=requester_id,
                                    source="spotify",
                                ))
                        offset += len(items)

        return title, tracks

    def get_cached_match(self, spotify_url: str) -> Optional[str]:
        return self._matching_cache.get(spotify_url)

    def set_cached_match(self, spotify_url: str, youtube_url: str):
        self._matching_cache[spotify_url] = youtube_url


spotify_service = SpotifyService()