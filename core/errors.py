"""
core/errors.py
---------------
Trình xử lý lỗi toàn cục cho App Commands (mục 1.2 - Utils/Core layer),
tránh mỗi lệnh phải tự try/except lặp lại và tránh traceback rơi thẳng ra
console mà người dùng không nhận được phản hồi nào trong Discord.
"""
import discord
from discord import app_commands

from core.logger import get_logger

log = get_logger("core.errors")


def setup_error_handler(tree: app_commands.CommandTree) -> None:
    async def on_app_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "❌ Bạn không có quyền dùng lệnh này."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"⏳ Vui lòng thử lại sau `{error.retry_after:.1f}s`."
        else:
            log.exception("Lỗi không xác định khi chạy slash command", exc_info=error)
            message = f"❌ Đã xảy ra lỗi: `{error}`"

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass

    tree.on_error = on_app_command_error
