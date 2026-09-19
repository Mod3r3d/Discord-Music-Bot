"""
cogs/voice_events.py
---------------------
Mục 2.5: Lắng nghe Trạng thái Kênh thoại — tự ngắt kết nối sau N giây khi
không còn thành viên thật nào trong kênh voice (chỉ còn bot).
"""
import asyncio

import discord
from discord.ext import commands

from core import config
from core.logger import get_logger
from models.guild_state import guild_states

log = get_logger("cogs.voice_events")


class VoiceEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _humans_in_channel(self, channel: discord.VoiceChannel) -> int:
        return len([m for m in channel.members if not m.bot])

    async def _auto_disconnect_countdown(self, guild: discord.Guild):
        state = guild_states.get(guild.id)
        try:
            await asyncio.sleep(config.AUTO_DISCONNECT_SECONDS)
            vc = guild.voice_client
            if not vc or not vc.channel:
                return
            if self._humans_in_channel(vc.channel) == 0:
                log.info("Tự ngắt kết nối tại '%s' do phòng trống.", guild.name)
                state.clear_queue()
                await vc.disconnect(force=True)
                guild_states.drop(guild.id)
        except asyncio.CancelledError:
            pass

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        guild = member.guild
        vc = guild.voice_client
        if not vc or not vc.channel:
            return

        # Chỉ quan tâm sự kiện xảy ra ngay trong kênh bot đang đứng.
        if before.channel != vc.channel and after.channel != vc.channel:
            return

        state = guild_states.get(guild.id)
        humans_left = self._humans_in_channel(vc.channel)

        if humans_left == 0:
            state.cancel_auto_disconnect()
            state.auto_disconnect_task = asyncio.create_task(
                self._auto_disconnect_countdown(guild)
            )
        else:
            # Có người quay lại trước khi hết giờ đếm ngược -> huỷ đếm ngược.
            state.cancel_auto_disconnect()


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceEvents(bot))
