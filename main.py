"""
main.py
--------
Điểm khởi chạy mới của bot (HOTFIX 1).
"""
import os
import asyncio
from aiohttp import web

import discord
from discord.ext import commands

from core import config
from core.errors import setup_error_handler
from core.logger import setup_logging, get_logger
from services.player_service import init_player_service

setup_logging()
log = get_logger("main")

INITIAL_EXTENSIONS = (
    "cogs.music",
    "cogs.voice_events",
)


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    return intents


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=build_intents(), help_command=None)

    async def setup_hook(self):
        init_player_service(self)
        setup_error_handler(self.tree)

        for extension in INITIAL_EXTENSIONS:
            await self.load_extension(extension)
            log.info("Đã nạp cog: %s", extension)

        if config.DEV_GUILD_ID:
            guild_obj = discord.Object(id=int(config.DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            log.info("Đã đồng bộ %d slash command tới guild dev %s", len(synced), config.DEV_GUILD_ID)
        else:
            synced = await self.tree.sync()
            log.info("Đã đồng bộ %d slash command (global, có thể mất tới 1h để lan toả)", len(synced))


bot = MusicBot()


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running!", status=200))
    app.router.add_get("/health", lambda r: web.Response(text="OK", status=200))

    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health check web server running on port {port}")


@bot.event
async def on_ready():
    print(f"Bot đã sẵn sàng: {bot.user}")


async def main_runner():
    if not config.TOKEN:
        raise ValueError("Chưa cấu hình DISCORD_TOKEN trong file .env")
    
    await start_web_server()
    await bot.start(config.TOKEN)


if __name__ == "__main__":
    asyncio.run(main_runner())