import os
import asyncio
import random
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import yt_dlp

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 '
        '-reconnect_streamed 1 '
        '-reconnect_delay_max 5 '
        '-user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"'
    ),
    'options': '-vn'
}

# 1. Trình trích xuất nhanh thông tin/danh sách (không tải audio ngay)
YTDL_FLAT_OPTIONS = {
    'format': 'bestaudio/best',
    'extract_flat': 'in_playlist',
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'js_runtimes': {
        'deno': {'path': r'C:\Users\Admin\.deno\bin\deno.exe'}
    },
    'extractor_args': {
        'youtube': {'player_client': ['web', 'mweb']}
    }
}

# 2. Trình lấy link phát âm thanh thực tế
YTDL_STREAM_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'js_runtimes': {
        'deno': {'path': r'C:\Users\Admin\.deno\bin\deno.exe'}
    },
    'extractor_args': {
        'youtube': {'player_client': ['web', 'mweb']}
    }
}

ytdl_flat = yt_dlp.YoutubeDL(YTDL_FLAT_OPTIONS)
ytdl_stream = yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS)

# Quản lý hàng đợi và các chế độ phát
class GuildMusicState:
    def __init__(self):
        self.queue = []         # Danh sách các bài hát đang chờ
        self.current = None     # Bài đang phát
        self.loop = False       # Lặp lại bài hiện tại
        self.random_mode = False # Tự động bốc ngẫu nhiên bài tiếp theo

guild_states = {}

def get_guild_state(guild_id: int) -> GuildMusicState:
    if guild_id not in guild_states:
        guild_states[guild_id] = GuildMusicState()
    return guild_states[guild_id]

def get_user_voice_context(ctx):
    if ctx.guild and ctx.author.voice:
        return ctx.guild, ctx.author.voice.channel

    for guild in bot.guilds:
        member = guild.get_member(ctx.author.id)
        if member and member.voice and member.voice.channel:
            return guild, member.voice.channel

    return None, None

# Trích xuất link âm thanh thực tế khi chuẩn bị phát
async def resolve_stream(track: dict) -> dict:
    loop = asyncio.get_running_loop()
    query = track.get('stream_url') or track.get('webpage_url') or f"{track.get('title')} {track.get('artist', '')}"
    
    data = await loop.run_in_executor(None, lambda: ytdl_stream.extract_info(query, download=False))
    if 'entries' in data and data['entries']:
        data = data['entries'][0]

    return {
        'title': data.get('title', track.get('title', 'Unknown')),
        'webpage_url': data.get('webpage_url', track.get('webpage_url')),
        'stream_url': data.get('url'),
        'duration': data.get('duration', 0),
        'thumbnail': data.get('thumbnail') or track.get('thumbnail')
    }

async def play_next(ctx, guild, voice_client):
    state = get_guild_state(guild.id)

    if not voice_client or not voice_client.is_connected():
        return

    # Kiểm tra bài cần phát
    if state.loop and state.current:
        track = state.current
    else:
        if not state.queue:
            state.current = None
            embed = discord.Embed(
                description="⏹️ **Đã phát hết danh sách chờ trong server.**", 
                color=discord.Color.light_grey()
            )
            await ctx.send(embed=embed)
            return

        # Chọn bài theo chế độ Ngẫu nhiên hoặc Theo thứ tự
        if state.random_mode:
            rand_index = random.randrange(len(state.queue))
            track = state.queue.pop(rand_index)
        else:
            track = state.queue.pop(0)

        state.current = track

    def after_playing(error):
        if error:
            print(f"Lỗi Player: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx, guild, voice_client), bot.loop)

    try:
        # Lấy link stream audio trực tiếp
        resolved_track = await resolve_stream(track)
        state.current.update(resolved_track)

        source = FFmpegPCMAudio(resolved_track['stream_url'], **FFMPEG_OPTIONS)
        voice_client.play(source, after=after_playing)

        mode_badge = " [🔁 Lặp]" if state.loop else (" [🔀 Random]" if state.random_mode else "")
        embed = discord.Embed(
            title=f"🎶 Đang phát tại [{guild.name}]{mode_badge}",
            description=f"[{resolved_track['title']}]({resolved_track['webpage_url']})",
            color=discord.Color.green()
        )
        if resolved_track.get('thumbnail'):
            embed.set_thumbnail(url=resolved_track['thumbnail'])
        
        mins, secs = divmod(resolved_track.get('duration', 0), 60)
        embed.set_footer(text=f"Thời lượng: {mins:02d}:{secs:02d} | Còn lại: {len(state.queue)} bài")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ **Lỗi phát bài `{track.get('title')}`:** `{e}`")
        asyncio.run_coroutine_threadsafe(play_next(ctx, guild, voice_client), bot.loop)

# ----------------- CÁC LỆNH ĐIỀU KHIỂN -----------------

@bot.event
async def on_ready():
    print(f"Bot đã sẵn sàng: {bot.user} (Nhận lệnh qua DM)")

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query: str = None):
    guild, voice_channel = get_user_voice_context(ctx)

    if not guild or not voice_channel:
        return await ctx.send("❌ Bạn cần tham gia vào một **Phòng Thoại** trước khi dùng lệnh!")

    voice_client = guild.voice_client
    if not voice_client:
        voice_client = await voice_channel.connect(timeout=30.0, reconnect=True)
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    if not query:
        if voice_client.is_paused():
            voice_client.resume()
            return await ctx.send("▶️ Đã tiếp tục phát nhạc.")
        return await ctx.send("❌ Vui lòng nhập link hoặc tên bài hát (`!play <tên bài/link Spotify/YouTube>`).")

    state = get_guild_state(guild.id)
    
    async with ctx.typing():
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: ytdl_flat.extract_info(query, download=False))
            
            # Xử lý nếu là Playlist (Spotify hoặc YouTube Playlist)
            if 'entries' in data and data['entries']:
                entries = list(data['entries'])
                for entry in entries:
                    state.queue.append({
                        'title': entry.get('title') or entry.get('track') or 'Unknown Title',
                        'artist': entry.get('artist') or entry.get('uploader') or '',
                        'webpage_url': entry.get('url') or entry.get('webpage_url')
                    })
                
                playlist_title = data.get('title', 'Danh sách phát')
                await ctx.send(f"📚 Đã thêm Playlist **{playlist_title}** ({len(entries)} bài hát) vào hàng đợi!")

            else:
                # Xử lý bài hát đơn lẻ
                track = {
                    'title': data.get('title', 'Unknown Title'),
                    'webpage_url': data.get('webpage_url') or query,
                    'stream_url': data.get('url'),
                    'thumbnail': data.get('thumbnail')
                }
                state.queue.append(track)
                
                if voice_client.is_playing() or voice_client.is_paused():
                    embed = discord.Embed(
                        title=f"📥 Đã thêm vào hàng đợi ({guild.name})",
                        description=f"[{track['title']}]({track['webpage_url']})",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)

            # Nếu chưa phát thì bắt đầu phát ngay
            if not voice_client.is_playing() and not voice_client.is_paused():
                await play_next(ctx, guild, voice_client)

        except Exception as e:
            await ctx.send(f"❌ Lỗi tải dữ liệu bài hát: `{e}`")

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Bỏ qua bài hiện tại và phát bài tiếp theo."""
    guild, _ = get_user_voice_context(ctx)
    if not guild or not guild.voice_client:
        return await ctx.send("❌ Bot chưa kết nối voice.")

    vc = guild.voice_client
    state = get_guild_state(guild.id)
    state.loop = False  # Bỏ qua thì hủy lặp bài hiện tại

    if vc.is_playing() or vc.is_paused():
        vc.stop()
        await ctx.send(f"⏭️ Đã chuyển sang bài tiếp theo.")
    else:
        await ctx.send("❌ Hiện không có bài nào đang phát.")

@bot.command(name='skipto')
async def skipto(ctx, index: int):
    """Nhảy đến một bài bất kỳ trong hàng đợi: !skipto <số thứ tự>"""
    guild, _ = get_user_voice_context(ctx)
    if not guild or not guild.voice_client:
        return await ctx.send("❌ Bot chưa kết nối voice.")

    state = get_guild_state(guild.id)
    if not (1 <= index <= len(state.queue)):
        return await ctx.send(f"❌ Số thứ tự không hợp lệ! Hàng đợi hiện có `{len(state.queue)}` bài (xem `!q`).")

    # Xóa các bài phía trước bài được chọn và đặt bài đó lên đầu
    chosen_track = state.queue.pop(index - 1)
    state.queue = state.queue[index - 1:] # Bỏ các bài trước đó
    state.queue.insert(0, chosen_track)

    state.loop = False
    guild.voice_client.stop()
    await ctx.send(f"⏭️ Đã nhảy đến bài số **{index}**: `{chosen_track['title']}`")

@bot.command(name='shuffle')
async def shuffle_queue(ctx):
    """Xáo trộn ngẫu nhiên toàn bộ danh sách chờ hiện tại một lần."""
    guild, _ = get_user_voice_context(ctx)
    if not guild:
        return await ctx.send("❌ Bạn cần ở trong phòng voice.")

    state = get_guild_state(guild.id)
    if len(state.queue) < 2:
        return await ctx.send("❌ Cần ít nhất 2 bài hát trong danh sách chờ để xáo trộn.")

    random.shuffle(state.queue)
    await ctx.send(f"🔀 Đã xáo trộn ngẫu nhiên **{len(state.queue)}** bài hát trong hàng đợi.")

@bot.command(name='random')
async def toggle_random(ctx):
    """Bật/Tắt chế độ tự động bốc bài ngẫu nhiên từ hàng đợi."""
    guild, _ = get_user_voice_context(ctx)
    if not guild:
        return await ctx.send("❌ Bạn cần ở trong phòng voice.")

    state = get_guild_state(guild.id)
    state.random_mode = not state.random_mode
    status = "BẬT 🔀 (Phát bài ngẫu nhiên)" if state.random_mode else "TẮT ➡️ (Phát lần lượt theo thứ tự)"
    await ctx.send(f"Chế độ chọn bài ngẫu nhiên: **{status}**")

@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """Xem danh sách hàng đợi kèm trạng thái phát."""
    guild, _ = get_user_voice_context(ctx)
    if not guild:
        return await ctx.send("❌ Bạn cần ở trong phòng voice.")

    state = get_guild_state(guild.id)
    if not state.queue and not state.current:
        return await ctx.send("📭 Hàng đợi hiện đang trống.")

    description = ""
    if state.current:
        description += f"**Đang phát:** [{state.current.get('title', 'Unknown')}]({state.current.get('webpage_url', '#')})\n\n**Hàng đợi:**\n"

    items = state.queue[:10]
    if not items:
        description += "_Không còn bài nào tiếp theo._"
    else:
        for idx, track in enumerate(items, 1):
            description += f"`{idx}.` {track.get('title')}\n"

    total_left = len(state.queue)
    if total_left > 10:
        description += f"\n_...và còn {total_left - 10} bài nữa._"

    embed = discord.Embed(
        title=f"📋 Hàng đợi nhạc ({guild.name})",
        description=description,
        color=discord.Color.purple()
    )
    status_mode = []
    if state.loop: status_mode.append("Lặp bài: BẬT 🔁")
    if state.random_mode: status_mode.append("Chế độ ngẫu nhiên: BẬT 🔀")
    if not status_mode: status_mode.append("Trình tự: Tuần tự ➡️")

    embed.set_footer(text=" | ".join(status_mode))
    await ctx.send(embed=embed)

@bot.command(name='pause')
async def pause(ctx):
    guild, _ = get_user_voice_context(ctx)
    if guild and guild.voice_client and guild.voice_client.is_playing():
        guild.voice_client.pause()
        await ctx.send("⏸️ Đã tạm dừng phát nhạc.")

@bot.command(name='resume')
async def resume(ctx):
    guild, _ = get_user_voice_context(ctx)
    if guild and guild.voice_client and guild.voice_client.is_paused():
        guild.voice_client.resume()
        await ctx.send("▶️ Đã tiếp tục phát nhạc.")

@bot.command(name='stop')
async def stop(ctx):
    guild, _ = get_user_voice_context(ctx)
    if not guild or not guild.voice_client:
        return await ctx.send("❌ Bot không kết nối voice.")

    state = get_guild_state(guild.id)
    state.queue.clear()
    state.current = None
    state.loop = False

    guild.voice_client.stop()
    await ctx.send(f"⏹️ Đã xóa hàng đợi và dừng nhạc tại **{guild.name}**.")

@bot.command(name='leave', aliases=['dc'])
async def leave(ctx):
    guild, _ = get_user_voice_context(ctx)
    if guild and guild.voice_client:
        await stop(ctx)
        await guild.voice_client.disconnect()
        await ctx.send(f"👋 Bot đã rời khỏi phòng voice.")

@bot.command(name='loop')
async def toggle_loop(ctx):
    guild, _ = get_user_voice_context(ctx)
    if not guild:
        return await ctx.send("❌ Bạn cần ở trong voice.")
    state = get_guild_state(guild.id)
    state.loop = not state.loop
    status = "BẬT 🔁" if state.loop else "TẮT ➡️"
    await ctx.send(f"Chế độ lặp bài ({guild.name}): **{status}**")

if __name__ == '__main__':
    if not TOKEN:
        raise ValueError("Chưa cấu hình DISCORD_TOKEN trong file .env")
    bot.run(TOKEN)