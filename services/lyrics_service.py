"""
services/lyrics_service.py
---------------------------
Mục 2.4: Tích hợp Lời bài hát Đồng bộ, dùng LRCLIB (https://lrclib.net) —
API mở, miễn phí, không cần API key, có cả lời tĩnh (plain) và lời đồng bộ (synced).
"""
import re
from dataclasses import dataclass
from typing import List, Optional

import aiohttp

from core.logger import get_logger

log = get_logger("services.lyrics")

LRCLIB_ENDPOINT = "https://lrclib.net/api/get"
LRCLIB_SEARCH_ENDPOINT = "https://lrclib.net/api/search"

_LRC_LINE_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")


@dataclass
class LyricLine:
    timestamp: float  # giây
    text: str


@dataclass
class LyricsResult:
    plain: Optional[str]
    synced: Optional[List[LyricLine]]
    source_title: str
    source_artist: str


def _parse_synced_lyrics(raw_lrc: str) -> List[LyricLine]:
    lines: List[LyricLine] = []
    for raw_line in raw_lrc.splitlines():
        match = _LRC_LINE_RE.match(raw_line.strip())
        if not match:
            continue
        minutes, seconds, frac, text = match.groups()
        frac = frac.ljust(3, "0")[:3]
        ts = int(minutes) * 60 + int(seconds) + int(frac) / 1000.0
        lines.append(LyricLine(timestamp=ts, text=text.strip()))
    lines.sort(key=lambda line: line.timestamp)
    return lines


class LyricsService:
    async def fetch(
        self, title: str, artist: str = "", duration: int = 0
    ) -> Optional[LyricsResult]:
        params = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        if duration:
            params["duration"] = str(duration)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    LRCLIB_ENDPOINT, params=params, timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    if resp.status == 404:
                        return await self._fallback_search(session, title, artist)
                    if resp.status != 200:
                        log.warning("LRCLIB trả về mã %s cho '%s'", resp.status, title)
                        return None
                    data = await resp.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("Không thể lấy lyrics cho '%s': %s", title, exc)
            return None

        return self._to_result(data, title, artist)

    async def _fallback_search(self, session, title: str, artist: str) -> Optional[LyricsResult]:
        try:
            async with session.get(
                LRCLIB_SEARCH_ENDPOINT,
                params={"q": f"{artist} {title}".strip()},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status != 200:
                    return None
                results = await resp.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("LRCLIB search fallback lỗi cho '%s': %s", title, exc)
            return None

        if not results:
            return None
        return self._to_result(results[0], title, artist)

    def _to_result(self, data: dict, title: str, artist: str) -> Optional[LyricsResult]:
        plain = data.get("plainLyrics") or None
        synced_raw = data.get("syncedLyrics") or None
        synced = _parse_synced_lyrics(synced_raw) if synced_raw else None
        if not plain and not synced:
            return None
        return LyricsResult(
            plain=plain,
            synced=synced,
            source_title=data.get("trackName", title),
            source_artist=data.get("artistName", artist),
        )


lyrics_service = LyricsService()
