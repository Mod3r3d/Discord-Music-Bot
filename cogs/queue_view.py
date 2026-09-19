"""
cogs/queue_view.py
--------------------
Thành phần giao diện (discord.ui) dùng chung cho Cogs:
  - QueuePaginatorView: mục 2.1 (Phân trang Hàng đợi, 10 bài/trang, nút điều hướng).
  - SearchSelectView: mục 2.2 (Trình chọn Kết quả Tìm kiếm Tương tác).
"""
from typing import List, Optional

import discord

from models.track import Track

PAGE_SIZE = 10


def build_queue_embed(guild_name: str, current: Optional[Track], queue: List[Track], page: int, status_line: str) -> discord.Embed:
    total_pages = max((len(queue) - 1) // PAGE_SIZE + 1, 1)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    items = queue[start : start + PAGE_SIZE]

    description = ""
    if current:
        description += f"**Đang phát:** {current.as_markdown_link()}\n\n**Hàng đợi:**\n"

    if not items:
        description += "_Không còn bài nào tiếp theo._"
    else:
        for idx, track in enumerate(items, start=start + 1):
            description += f"`{idx}.` {track.title}\n"

    embed = discord.Embed(
        title=f"📋 Hàng đợi nhạc ({guild_name})",
        description=description,
        color=discord.Color.purple(),
    )
    embed.set_footer(text=f"{status_line} | Trang {page + 1}/{total_pages} | Tổng {len(queue)} bài")
    return embed, page, total_pages


class QueuePaginatorView(discord.ui.View):
    """Mục 2.1: [⏮️ Đầu] [◀️ Trước] [Trang X/Y] [Sau ▶️] [Cuối ⏭️]"""

    def __init__(self, guild: discord.Guild, state, *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.guild = guild
        self.state = state
        self.page = 0

    async def _refresh(self, interaction: discord.Interaction):
        embed, self.page, total_pages = build_queue_embed(
            self.guild.name, self.state.current, list(self.state.queue), self.page, self._status_line()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    def _status_line(self) -> str:
        parts = []
        if self.state.loop:
            parts.append("Lặp bài: BẬT 🔁")
        if self.state.random_mode:
            parts.append("Ngẫu nhiên: BẬT 🔀")
        if self.state.active_filter:
            parts.append(f"Filter: {self.state.active_filter} 🎛️")
        if not parts:
            parts.append("Trình tự: Tuần tự ➡️")
        return " | ".join(parts)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await self._refresh(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self._refresh(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.page + 1
        await self._refresh(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = max((len(self.state.queue) - 1) // PAGE_SIZE + 1, 1)
        self.page = total_pages - 1
        await self._refresh(interaction)


class SearchSelect(discord.ui.Select):
    """Mục 2.2: Menu Dropdown 5 kết quả sát nhất kèm tên kênh & thời lượng."""

    def __init__(self, results: List[Track], on_choice):
        self._results = results
        self._on_choice = on_choice
        options = []
        for idx, track in enumerate(results):
            mins, secs = divmod(int(track.duration or 0), 60)
            duration_str = f"{mins:02d}:{secs:02d}" if track.duration else "??:??"
            label = track.title[:90] or "Unknown"
            description = f"{track.artist[:60]} • {duration_str}" if track.artist else duration_str
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        super().__init__(placeholder="🔎 Chọn bản thu bạn muốn nghe...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        chosen = self._results[idx]
        self.view.stop()
        await self._on_choice(interaction, chosen)


class SearchSelectView(discord.ui.View):
    def __init__(self, results: List[Track], on_choice, *, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.add_item(SearchSelect(results, on_choice))
