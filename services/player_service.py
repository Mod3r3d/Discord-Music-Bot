"""
services/player_service.py
---------------------------
Core Service Layer:
  - Quản lý vòng đời audio stream & FFmpeg process.
  - Watchdog timeout và tự động phục hồi kết nối.
  - Áp dụng playback_generation để chặn race-condition.
"""
import asyncio
from typing import Optional

import discord

from core import config
from core.logger import get_logger
from models.guild_state import PlayerState, guild_states
from models.track import Track
from services.youtube_service import youtube_service

log = get_logger("services.player")


class PlayerService:
    def __init__(self, bot: Optional[discord.Client] = None):
        self.bot = bot

    def bind_bot(self, bot: discord.Client):
        self.bot = bot

    async def play_next(self, guild: discord.Guild, vc: discord.VoiceClient):
        state = guild_states.get(guild.id)

        async with state.lock:
            state.cancel_prefetch()
            state.cancel_auto_disconnect()

            # Nếu lặp lại bài hát hiện tại
            if state.loop and state.current:
                track = state.current
            elif state.filter_reapply and state.current:
                state.filter_reapply = False
                track = state.current
            else:
                if not state.queue:
                    state.current = None
                    state.state = PlayerState.IDLE
                    self._schedule_auto_disconnect(guild, vc)
                    await self._notify(state, "⏹️ Đã phát hết danh sách chờ trong server.")
                    return

                track = state.queue.popleft() if not state.random_mode else self._pop_random(state)
                state.current = track

            # Tăng generation để vô hiệu hóa mọi tác vụ resolve cũ đang chạy
            gen = state.advance_generation()
            state.state = PlayerState.RESOLVING

        # Giải mã stream URL nếu chưa có
        if not track.stream_url:
            try:
                resolved_data = await youtube_service.resolve_stream(track)
                track.stream_url = resolved_data["stream_url"]
                track.duration = resolved_data.get("duration", track.duration)
                
                # KHẮC PHỤC LỖI HIỂN THỊ SAI TÊN: Chỉ ghi đè tên nếu nguồn không phải là Spotify
                if track.source != "spotify":
                    track.thumbnail = resolved_data.get("thumbnail", track.thumbnail)
                    track.title = resolved_data.get("title", track.title)
            except Exception as exc:  # noqa: BLE001
                log.error("Lỗi resolve track '%s': %s", track.title, exc)
                await self._notify(state, f"❌ Lỗi phát bài **{track.title}**: `{exc}`")
                state.state = PlayerState.ERROR
                await self.play_next(guild, vc)
                return

        # Kiểm tra huỷ luồng (nếu user bấm /skip hoặc /stop trong lúc đang resolve)
        if gen != state.playback_generation:
            log.info("Bỏ qua bài '%s' do lệch generation (%d != %d)", track.title, gen, state.playback_generation)
            return

        # Cấu hình FFmpeg watchdog timeout
        ffmpeg_before = (
            "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
            "-rw_timeout 10000000 -nostdin"
        )
        ffmpeg_options = "-vn"
        if state.active_filter and state.active_filter in config.AUDIO_FILTERS:
            ffmpeg_options += f' -af "{config.AUDIO_FILTERS[state.active_filter]}"'

        def after_callback(error: Optional[Exception]):
            if error:
                log.error("FFmpeg error on guild %d: %s", guild.id, error)
            fut = asyncio.run_coroutine_threadsafe(self.play_next(guild, vc), self.bot.loop)
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001
                log.error("Lỗi trong after_callback: %s", e)

        try:
            source = discord.FFmpegPCMAudio(
                track.stream_url,
                before_options=ffmpeg_before,
                options=ffmpeg_options,
            )
            vc.play(source, after=after_callback)
            state.state = PlayerState.PLAYING
            state.reset_skip_votes()
            await self._send_now_playing(guild, state, track)
        except Exception as exc:  # noqa: BLE001
            log.error("Không thể khởi chạy phát nhạc: %s", exc)
            state.state = PlayerState.ERROR
            await self._notify(state, f"❌ Không thể phát audio: `{exc}`")
            await self.play_next(guild, vc)

    def _pop_random(self, state) -> Track:
        import random
        idx = random.randrange(len(state.queue))
        queue_list = list(state.queue)
        track = queue_list.pop(idx)
        state.queue.clear()
        state.queue.extend(queue_list)
        return track

    async def _send_now_playing(self, guild: discord.Guild, state, track: Track):
        mins, secs = divmod(int(track.duration or 0), 60)
        embed = discord.Embed(
            title=f"🎶 Đang phát tại [{guild.name}]",
            description=track.as_markdown_link(),
            color=discord.Color.green(),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.set_footer(text=f"Thời lượng: {mins:02d}:{secs:02d} | Còn lại: {len(state.queue)} bài")
        await self._notify(state, embed=embed)

    async def _notify(self, state, message: str = "", embed: Optional[discord.Embed] = None):
        if not state.text_channel_id or not self.bot:
            return
        channel = self.bot.get_channel(state.text_channel_id)
        if channel:
            try:
                if embed:
                    await channel.send(embed=embed)
                elif message:
                    await channel.send(message)
            except discord.HTTPException:
                pass

    def _schedule_auto_disconnect(self, guild: discord.Guild, vc: discord.VoiceClient):
        state = guild_states.get(guild.id)

        async def _disconnect_later():
            await asyncio.sleep(config.AUTO_DISCONNECT_DELAY)
            if not vc.is_playing() and not state.queue:
                await vc.disconnect(force=True)
                guild_states.drop(guild.id)
                log.info("Tự động ngắt kết nối tại guild %d do hàng đợi trống", guild.id)

        state._disconnect_task = asyncio.create_task(_disconnect_later())


player_service = PlayerService()


def init_player_service(bot: discord.Client):
    player_service.bind_bot(bot)