"""
models/track.py
----------------
Domain model cho một bài hát trong hàng đợi (mục 1.2 - Domain Models layer).
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Track:
    title: str
    webpage_url: Optional[str] = None
    artist: str = ""
    stream_url: Optional[str] = None
    duration: int = 0
    thumbnail: Optional[str] = None
    requester_id: Optional[int] = None
    source: str = "youtube"  # youtube | soundcloud | ytmusic
    resolved: bool = False  # đã có stream_url thật hay còn là "lazy" entry

    def display_name(self) -> str:
        if self.artist:
            return f"{self.title} — {self.artist}"
        return self.title

    def as_markdown_link(self) -> str:
        if self.webpage_url:
            return f"[{self.title}]({self.webpage_url})"
        return self.title

    def update_from_resolved(self, data: dict) -> None:
        """Gộp dữ liệu vừa resolve (stream thật) vào track hiện có."""
        self.title = data.get("title", self.title)
        self.webpage_url = data.get("webpage_url", self.webpage_url)
        self.stream_url = data.get("stream_url", self.stream_url)
        self.duration = data.get("duration", self.duration) or self.duration
        self.thumbnail = data.get("thumbnail", self.thumbnail)
        self.source = data.get("source", self.source)
        self.resolved = True
