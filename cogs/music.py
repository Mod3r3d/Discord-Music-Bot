"""
cogs/music.py
--------------
Đã tích hợp HOTFIX 3: Hỗ trợ Spotify Track, Album và Playlist nền (Background Expansion).
"""
import asyncio
import math
import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core import config
from core.logger import get_logger
from models.guild_state import guild_states
from models.track import Track
from services.lyrics_service import lyrics_service
from services.player_service import player_service
from services.spotify_service import spotify_service
from services.youtube_service import youtube_service
from cogs.queue_view import QueuePaginatorView, SearchSelectView, build_queue_embed

log = get_logger("cogs.music")


def _humans_in_channel(channel: discord.VoiceChannel) -> int:
    return len([m for m in channel.members if not m.bot])


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_voice(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            msg = "❌ Bạn cần tham gia một **Phòng Thoại** trước!"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return None, None

        guild = interaction.guild
        channel = interaction.user.voice.channel
        vc = guild.voice_client

        if not vc:
            vc = await channel.connect(timeout=30.0, reconnect=True)
        elif vc.channel != channel:
            msg = f"❌ Bot đang phát nhạc ở kênh **{vc.channel.name}**. Hãy vào kênh đó hoặc dùng `/leave` trước!"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return None, None

        return guild, vc

    def _is_privileged(self, member: discord.Member, state) -> bool:
        if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
            return True
        if state.dj_role_id and any(r.id == state.dj_role_id for r in member.roles):
            return True
        return False

    def _state_channel_bind(self, state, interaction: discord.Interaction):
        state.text_channel_id = interaction.channel_id

    @app_commands.command(name="play", description="Phát nhạc từ tên bài hát, link YouTube hoặc Spotify")
    @app_commands.describe(query="Tên bài hát, link YouTube hoặc link Spotify")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)

        guild, vc = await self._ensure_voice(interaction)
        if not guild:
            return

        state = guild_states.get(guild.id)
        self._state_channel_bind(state, interaction)

        # Xử lý luồng riêng cho Spotify (Hướng 2: Không cần API Key)
        if spotify_service.is_spotify_url(query):
            parsed = spotify_service.parse_url(query)
            if not parsed:
                await interaction.followup.send("❌ Link Spotify không hợp lệ.")
                return

            sp_type, sp_id = parsed
            try:
                if sp_type == "track":
                    track = await spotify_service.fetch_track(sp_id, interaction.user.id)
                    state.queue.append(track)
                    artist_str = f" - {track.artist}" if track.artist else ""
                    await interaction.followup.send(f"🟢 Đã thêm bài hát Spotify: **{track.title}**{artist_str}")

                elif sp_type in ("album", "playlist"):
                    title, tracks = await spotify_service.fetch_collection(sp_type, sp_id, interaction.user.id)
                    if not tracks:
                        await interaction.followup.send(f"❌ Không tìm thấy bài hát nào trong {sp_type} này.")
                        return

                    state.queue.extend(tracks)
                    await interaction.followup.send(
                        f"🟢 Đã thêm Spotify {sp_type.capitalize()} **{title}** ({len(tracks)} bài hát) vào hàng đợi!"
                    )

            except Exception as exc:  # noqa: BLE001
                await interaction.followup.send(f"❌ Lỗi tải dữ liệu Spotify: `{exc}`")
                return

            if not vc.is_playing() and not vc.is_paused():
                await player_service.play_next(guild, vc)
            return
        
        # Luồng xử lý YouTube / Search thông thường
        try:
            data = await youtube_service.extract_flat(query)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"❌ Lỗi tải dữ liệu bài hát: `{exc}`")
            return

        if "entries" in data and data["entries"]:
            entries = [e for e in data["entries"] if e]
            for entry in entries:
                state.queue.append(
                    Track(
                        title=entry.get("title") or entry.get("track") or "Unknown Title",
                        artist=entry.get("artist") or entry.get("uploader") or "",
                        webpage_url=entry.get("url") or entry.get("webpage_url"),
                        duration=entry.get("duration") or 0,
                        requester_id=interaction.user.id,
                    )
                )
            playlist_title = data.get("title", "Danh sách phát")
            await interaction.followup.send(
                f"📚 Đã thêm Playlist **{playlist_title}** ({len(entries)} bài hát) vào hàng đợi!"
            )
        else:
            track = Track(
                title=data.get("title", "Unknown Title"),
                webpage_url=data.get("webpage_url") or query,
                stream_url=data.get("url"),
                thumbnail=data.get("thumbnail"),
                duration=data.get("duration") or 0,
                requester_id=interaction.user.id,
            )
            state.queue.append(track)
            if vc.is_playing() or vc.is_paused():
                embed = discord.Embed(
                    title=f"📥 Đã thêm vào hàng đợi ({guild.name})",
                    description=track.as_markdown_link(),
                    color=discord.Color.blue(),
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"✅ Đã thêm **{track.title}**, chuẩn bị phát...")

        if not vc.is_playing() and not vc.is_paused():
            await player_service.play_next(guild, vc)

    async def _expand_spotify_playlist_bg(self, playlist_id: str, requester_id: int, state, total: int):
        offset = 20
        limit = 50
        max_cap = min(total, config.SPOTIFY_QUEUE_LIMIT)

        while offset < max_cap:
            try:
                _, _, tracks = spotify_service.fetch_playlist_chunk(
                    playlist_id, requester_id, offset=offset, limit=limit
                )
                if not tracks:
                    break
                state.queue.extend(tracks)
                offset += len(tracks)
                await asyncio.sleep(1)  # Rate-limit thân thiện
            except Exception as exc:  # noqa: BLE001
                log.error("Lỗi khi mở rộng Spotify playlist: %s", exc)
                break

    @app_commands.command(name="search", description="Tìm kiếm và chọn chính xác bản thu muốn nghe")
    @app_commands.describe(query="Từ khoá tìm kiếm")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)

        guild, vc = await self._ensure_voice(interaction)
        if not guild:
            return
        state = guild_states.get(guild.id)
        self._state_channel_bind(state, interaction)

        try:
            results = await youtube_service.search_candidates(query, count=5)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"❌ Lỗi tìm kiếm: `{exc}`")
            return

        if not results:
            await interaction.followup.send("❌ Không tìm thấy kết quả nào phù hợp.")
            return

        async def on_choice(select_interaction: discord.Interaction, chosen: Track):
            chosen.requester_id = interaction.user.id
            state.queue.append(chosen)
            await select_interaction.response.edit_message(
                content=f"✅ Đã thêm **{chosen.title}** vào hàng đợi.", view=None
            )
            if not vc.is_playing() and not vc.is_paused():
                await player_service.play_next(guild, vc)

        view = SearchSelectView(results, on_choice)
        await interaction.followup.send("🔎 Chọn bản thu bạn muốn nghe:", view=view)

    @app_commands.command(name="pause", description="Tạm dừng bài hát đang phát")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Đã tạm dừng phát nhạc.")
        else:
            await interaction.response.send_message("❌ Không có bài nào đang phát.", ephemeral=True)

    @app_commands.command(name="resume", description="Tiếp tục phát nhạc")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Đã tiếp tục phát nhạc.")
        else:
            await interaction.response.send_message("❌ Không có bài nào đang tạm dừng.", ephemeral=True)

    @app_commands.command(name="stop", description="Dừng nhạc và xoá toàn bộ hàng đợi")
    async def stop(self, interaction: discord.Interaction):
        guild = interaction.guild
        state = guild_states.get(guild.id)
        vc = guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ Bot chưa kết nối voice.", ephemeral=True)
            return
        state.clear_queue()
        vc.stop()
        await interaction.response.send_message(f"⏹️ Đã xoá hàng đợi và dừng nhạc tại **{guild.name}**.")

    @app_commands.command(name="leave", description="Rời khỏi phòng voice")
    async def leave(self, interaction: discord.Interaction):
        guild = interaction.guild
        vc = guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ Bot chưa ở trong phòng voice nào.", ephemeral=True)
            return
        state = guild_states.get(guild.id)
        state.clear_queue()
        state.cancel_auto_disconnect()
        await vc.disconnect(force=True)
        guild_states.drop(guild.id)
        await interaction.response.send_message("👋 Bot đã rời khỏi phòng voice.")

    @app_commands.command(name="skip", description="Bỏ qua bài hiện tại (vote nếu phòng đông người)")
    async def skip(self, interaction: discord.Interaction):
        guild = interaction.guild
        vc = guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message("❌ Hiện không có bài nào đang phát.", ephemeral=True)
            return

        state = guild_states.get(guild.id)
        member = interaction.user

        if self._is_privileged(member, state):
            state.loop = False
            state.reset_skip_votes()
            vc.stop()
            await interaction.response.send_message("⏭️ (DJ/Admin) Đã chuyển sang bài tiếp theo.")
            return

        channel = member.voice.channel if member.voice else vc.channel
        total_humans = max(_humans_in_channel(channel), 1)
        needed = math.floor(total_humans / 2) + 1

        state.skip_votes.add(member.id)
        current_votes = len(state.skip_votes)

        if current_votes >= needed:
            state.loop = False
            state.reset_skip_votes()
            vc.stop()
            await interaction.response.send_message(
                f"⏭️ Đủ **{current_votes}/{needed}** phiếu — đã chuyển bài tiếp theo."
            )
        else:
            await interaction.response.send_message(
                f"🗳️ Đã ghi nhận phiếu skip (**{current_votes}/{needed}** cần thiết)."
            )

    @app_commands.command(name="skipto", description="Nhảy tới một bài cụ thể trong hàng đợi")
    @app_commands.describe(index="Số thứ tự bài hát trong /queue")
    async def skipto(self, interaction: discord.Interaction, index: int):
        guild = interaction.guild
        vc = guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ Bot chưa kết nối voice.", ephemeral=True)
            return
        state = guild_states.get(guild.id)
        if not (1 <= index <= len(state.queue)):
            await interaction.response.send_message(
                f"❌ Số thứ tự không hợp lệ! Hàng đợi hiện có `{len(state.queue)}` bài.", ephemeral=True
            )
            return

        queue_list = list(state.queue)
        chosen_track = queue_list[index - 1]
        remaining = queue_list[index - 1 :]
        remaining.remove(chosen_track)
        remaining.insert(0, chosen_track)
        state.queue.clear()
        state.queue.extend(remaining)

        state.loop = False
        state.cancel_prefetch()
        vc.stop()
        await interaction.response.send_message(f"⏭️ Đã nhảy đến bài **{chosen_track.title}**.")

    @app_commands.command(name="shuffle", description="Xáo trộn ngẫu nhiên hàng đợi hiện tại")
    async def shuffle(self, interaction: discord.Interaction):
        state = guild_states.get(interaction.guild.id)
        if len(state.queue) < 2:
            await interaction.response.send_message(
                "❌ Cần ít nhất 2 bài trong hàng đợi để xáo trộn.", ephemeral=True
            )
            return
        queue_list = list(state.queue)
        random.shuffle(queue_list)
        state.queue.clear()
        state.queue.extend(queue_list)
        state.cancel_prefetch()
        await interaction.response.send_message(f"🔀 Đã xáo trộn **{len(state.queue)}** bài hát.")

    @app_commands.command(name="randommode", description="Bật/tắt chế độ tự bốc bài ngẫu nhiên")
    async def randommode(self, interaction: discord.Interaction):
        state = guild_states.get(interaction.guild.id)
        state.random_mode = not state.random_mode
        state.cancel_prefetch()
        status = "BẬT 🔀" if state.random_mode else "TẮT ➡️"
        await interaction.response.send_message(f"Chế độ ngẫu nhiên: **{status}**")

    @app_commands.command(name="loopmode", description="Bật/tắt lặp lại bài hiện tại")
    async def loopmode(self, interaction: discord.Interaction):
        state = guild_states.get(interaction.guild.id)
        state.loop = not state.loop
        status = "BẬT 🔁" if state.loop else "TẮT ➡️"
        await interaction.response.send_message(f"Chế độ lặp bài: **{status}**")

    @app_commands.command(name="queue", description="Xem hàng đợi hiện tại")
    async def queue_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        state = guild_states.get(guild.id)
        if not state.queue and not state.current:
            await interaction.response.send_message("📭 Hàng đợi hiện đang trống.")
            return

        view = QueuePaginatorView(guild, state)
        status_line = view._status_line()
        embed, _, _ = build_queue_embed(guild.name, state.current, list(state.queue), 0, status_line)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="nowplaying", description="Xem bài đang phát")
    async def nowplaying(self, interaction: discord.Interaction):
        state = guild_states.get(interaction.guild.id)
        if not state.current:
            await interaction.response.send_message("❌ Không có bài nào đang phát.", ephemeral=True)
            return
        track = state.current
        embed = discord.Embed(
            title="🎶 Đang phát",
            description=track.as_markdown_link(),
            color=discord.Color.green(),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="filter", description="Bật bộ lọc âm thanh")
    @app_commands.choices(
        name=[
            app_commands.Choice(name=key, value=key)
            for key in config.AUDIO_FILTERS.keys()
        ]
    )
    async def filter_cmd(self, interaction: discord.Interaction, name: app_commands.Choice[str]):
        guild = interaction.guild
        vc = guild.voice_client
        state = guild_states.get(guild.id)
        state.active_filter = None if name.value == "none" else name.value

        await interaction.response.send_message(
            f"🎛️ Bộ lọc âm thanh: **{name.value}**"
            + (" (sẽ áp dụng từ bài tiếp theo / sau khi resume lại)" if vc and vc.is_playing() else "")
        )

        if vc and (vc.is_playing() or vc.is_paused()) and state.current and state.current.stream_url:
            state.filter_reapply = True
            vc.stop()

    @app_commands.command(name="lyrics", description="Xem lời bài hát đang phát")
    async def lyrics_cmd(self, interaction: discord.Interaction):
        state = guild_states.get(interaction.guild.id)
        if not state.current:
            await interaction.response.send_message("❌ Không có bài nào đang phát.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        track = state.current
        result = await lyrics_service.fetch(track.title, track.artist, track.duration)
        if not result:
            await interaction.followup.send("❌ Không tìm thấy lời bài hát cho bản này.")
            return

        text = result.plain
        if not text and result.synced:
            text = "\n".join(line.text for line in result.synced if line.text)
        if not text:
            await interaction.followup.send("❌ Không tìm thấy lời bài hát cho bản này.")
            return

        if len(text) > 3800:
            text = text[:3800] + "\n…"

        embed = discord.Embed(
            title=f"📜 Lời bài hát: {result.source_title}",
            description=text,
            color=discord.Color.gold(),
        )
        if result.source_artist:
            embed.set_author(name=result.source_artist)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setdj", description="[Quản trị] Đặt Role DJ có toàn quyền điều khiển nhạc")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setdj(self, interaction: discord.Interaction, role: discord.Role):
        state = guild_states.get(interaction.guild.id)
        state.dj_role_id = role.id
        await interaction.response.send_message(f"✅ Đã đặt Role DJ: {role.mention}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))