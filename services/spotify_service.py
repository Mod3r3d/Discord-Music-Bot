"""
services/spotify_service.py
---------------------------
Spotify Resolver (Anonymous Web Token - HTML Extraction).
Trích xuất token ẩn danh từ HTML trang chủ để né block IP của Render.
Có cơ chế fallback sang Embed scraping.
"""
import json
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

# Giả lập trình duyệt chuẩn để tránh Cloudflare/Spotify block IP Render
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

class SpotifyService:
    def __init__(self):
        self._matching_cache: Dict[str, str] = {}
        self._anon_token: Optional[str] = None
        self._token_expires_at: float = 0

    async def _get_anonymous_token(self) -> Optional[str]:
        if self._anon_token and time.time() < self._token_expires_at:
            return self._anon_token

        # Chiến thuật mới: Lấy Token trực tiếp từ mã HTML của trang chủ Spotify
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get("https://open.spotify.com", timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        token_match = re.search(r'"accessToken":"(.*?)"', html)
                        if token_match:
                            self._anon_token = token_match.group(1)
                            exp_match = re.search(r'"accessTokenExpirationTimestampMs":(\d+)', html)
                            if exp_match:
                                self._token_expires_at = (int(exp_match.group(1)) / 1000) - 60
                            else:
                                self._token_expires_at = time.time() + 900
                            
                            log.info("Đã trích xuất thành công Anonymous Token từ HTML.")
                            return self._anon_token
        except Exception as exc:  # noqa: BLE001
            log.warning("Lỗi trích xuất token Spotify từ HTML: %s", exc)
        return None

    async def _fetch_embed_fallback(self, type_: str, item_id: str, requester_id: int) -> Tuple[str, List[Track]]:
        """Dự phòng scraping Embed HTML nếu token bị lỗi (Lấy được max 100 bài)."""
        embed_url = f"https://open.spotify.com/embed/{type_}/{item_id}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(embed_url, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError("Spotify từ chối kết nối (HTTP 403/429).")
                html = await resp.text()

        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if not match:
            raise RuntimeError("Không thể giải mã dữ liệu Spotify Embed.")

        data = json.loads(match.group(1))
        entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity") or {}
        
        title = entity.get("title") or entity.get("name") or f"Spotify {type_.capitalize()}"
        track_list = entity.get("trackList") or entity.get("tracks", {}).get("items") or []
        images = entity.get("coverArt", {}).get("sources", [])
        default_thumb = images[0].get("url") if images else None

        tracks = []
        for item in track_list:
            t_name = item.get("title") or item.get("name")
            if not t_name:
                continue
            t_artist = item.get("subtitle") or ", ".join(a.get("name", "") for a in item.get("artists", [])) if isinstance(item.get("artists"), list) else ""
            duration_sec = int(item.get("duration", 0)) // 1000
            uri = item.get("uri", "")
            t_id = uri.split(":")[-1] if ":" in uri else ""
            
            tracks.append(Track(
                title=t_name,
                artist=t_artist,
                duration=duration_sec,
                webpage_url=f"https://open.spotify.com/track/{t_id}" if t_id else f"https://open.spotify.com/{type_}/{item_id}",
                thumbnail=default_thumb,
                requester_id=requester_id,
                source="spotify",
            ))
        return title, tracks

    def is_spotify_url(self, query: str) -> bool:
        return bool(SPOTIFY_URL_REGEX.search(query))

    def parse_url(self, query: str) -> Optional[Tuple[str, str]]:
        match = SPOTIFY_URL_REGEX.search(query)
        if not match:
            return None
        return match.group(2) or match.group(4), match.group(3) or match.group(5)

    async def fetch_track(self, track_id: str, requester_id: int) -> Optional[Track]:
        token = await self._get_anonymous_token()
        if not token:
            log.warning("Token thất bại, dùng Embed Fallback cho track.")
            _, tracks = await self._fetch_embed_fallback("track", track_id, requester_id)
            return tracks[0] if tracks else None
        
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        async with aiohttp.ClientSession(headers={**HEADERS, "Authorization": f"Bearer {token}"}) as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    _, tracks = await self._fetch_embed_fallback("track", track_id, requester_id)
                    return tracks[0] if tracks else None
                t = await resp.json()
                
                artists = ", ".join(a.get("name", "") for a in t.get("artists", []))
                images = (t.get("album") or {}).get("images", [])
                
                return Track(
                    title=t.get("name", "Unknown Title"),
                    artist=artists,
                    duration=int(t.get("duration_ms") or 0) // 1000,
                    webpage_url=t.get("external_urls", {}).get("spotify") or f"https://open.spotify.com/track/{track_id}",
                    thumbnail=images[0].get("url") if images else None,
                    requester_id=requester_id,
                    source="spotify",
                )

    async def fetch_collection(self, type_: str, item_id: str, requester_id: int) -> Tuple[str, List[Track]]:
        token = await self._get_anonymous_token()
        if not token:
            log.warning("Lấy Token thất bại. Kích hoạt Embed Fallback.")
            return await self._fetch_embed_fallback(type_, item_id, requester_id)
        
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        tracks: List[Track] = []
        title = f"Spotify {type_.capitalize()}"

        async with aiohttp.ClientSession(headers=headers) as session:
            if type_ == "album":
                async with session.get(f"https://api.spotify.com/v1/albums/{item_id}", timeout=10) as resp:
                    if resp.status != 200: return await self._fetch_embed_fallback(type_, item_id, requester_id)
                    data = await resp.json()
                    title = data.get("name", title)
                    for t in data.get("tracks", {}).get("items", []):
                        if t and t.get("name"):
                            tracks.append(Track(
                                title=t.get("name"),
                                artist=", ".join(a.get("name", "") for a in t.get("artists", [])),
                                duration=int(t.get("duration_ms") or 0) // 1000,
                                webpage_url=t.get("external_urls", {}).get("spotify") or "",
                                thumbnail=(data.get("images", []) or [{}])[0].get("url"),
                                requester_id=requester_id,
                                source="spotify",
                            ))

            elif type_ == "playlist":
                base_url = f"https://api.spotify.com/v1/playlists/{item_id}"
                async with session.get(f"{base_url}?fields=name,tracks.total", timeout=10) as resp:
                    if resp.status != 200: return await self._fetch_embed_fallback(type_, item_id, requester_id)
                    meta = await resp.json()
                    title = meta.get("name", title)
                    total = meta.get("tracks", {}).get("total", 0)

                offset = 0
                max_cap = min(total, config.SPOTIFY_QUEUE_LIMIT)
                while offset < max_cap:
                    items_url = f"{base_url}/tracks?offset={offset}&limit=100&fields=items(track(name,duration_ms,artists,external_urls,album(images)))"
                    async with session.get(items_url, timeout=10) as resp:
                        if resp.status != 200: break
                        data = await resp.json()
                        items = data.get("items", [])
                        if not items: break
                        
                        for entry in items:
                            t = entry.get("track")
                            if t and t.get("name"):
                                images = (t.get("album") or {}).get("images", [])
                                tracks.append(Track(
                                    title=t.get("name"),
                                    artist=", ".join(a.get("name", "") for a in t.get("artists", [])),
                                    duration=int(t.get("duration_ms") or 0) // 1000,
                                    webpage_url=t.get("external_urls", {}).get("spotify") or "",
                                    thumbnail=images[0].get("url") if images else None,
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