"""
core/config.py
---------------
Đọc toàn bộ biến môi trường và cung cấp cấu hình dùng chung (FFmpeg, yt-dlp,
PO Token, DJ role, auto-disconnect, pre-fetch...) cho mọi module khác.
Tách riêng ra khỏi bot.py theo đúng mục 1.2 của plan (Utils/Core layer).
"""
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID") or None

DENO_PATH = os.getenv("DENO_PATH") or shutil.which("deno")
YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE") or None
POT_PROVIDER_URL = os.getenv("POT_PROVIDER_URL") or None
ENABLE_SOUNDCLOUD_FALLBACK = os.getenv("ENABLE_SOUNDCLOUD_FALLBACK", "true").lower() in (
    "1", "true", "yes", "on"
)

AUTO_DISCONNECT_SECONDS = int(os.getenv("AUTO_DISCONNECT_SECONDS", "60"))
PREFETCH_LEAD_SECONDS = int(os.getenv("PREFETCH_LEAD_SECONDS", "18"))

# Mục 1.3: giới hạn buffer pipe FFmpeg + tự dọn tiến trình.
FFMPEG_TERMINATE_TIMEOUT = 2.0  # giây chờ SIGTERM trước khi SIGKILL

BASE_FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 "
    "-reconnect_streamed 1 "
    "-reconnect_delay_max 5 "
    "-analyzeduration 0 -probesize 32k "
    '-user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"'
)
# -bufsize giới hạn lượng dữ liệu FFmpeg tích trữ tạm, tránh rò rỉ RAM khi
# skip/stop liên tục ở luồng bitrate cao (mục 1.3).
BASE_FFMPEG_OPTIONS = "-vn -bufsize 512k"

# Preset bộ lọc âm thanh (-af) — mục 2.3
AUDIO_FILTERS = {
    "none": None,
    "bassboost": "equalizer=f=60:width_type=h:width=50:g=12",
    "nightcore": "asetrate=48000*1.25,aresample=48000,atempo=1.06",
    "8d": "apulsator=hz=0.09",
    "slowedreverb": "asetrate=48000*0.85,aresample=48000,atempo=0.97,"
    "aecho=0.8:0.9:1000:0.3",
    "vaporwave": "asetrate=48000*0.8,aresample=48000,atempo=0.95",
}


def build_ytdl_extractor_args() -> dict:
    """Cấu hình player_client cho yt-dlp — Đảo thứ tự để né rào cản của YouTube Web"""
    # Ưu tiên Android và iOS (không bị ép giải mã JS phức tạp như mweb/web)
    args = {
        "youtube": {
            "player_client": ["android", "ios", "tv", "web"]
        }
    }
    return args


def build_js_runtimes() -> dict:
    if DENO_PATH:
        return {"deno": {"path": DENO_PATH}}
    return {}


def build_common_ytdlp_options() -> dict:
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "extractor_args": build_ytdl_extractor_args(),
        # Quan trọng: Cho phép yt-dlp tự động tải script giải mã JS từ GitHub để vượt qua thử thách chữ ký
        "remote_components": "ejs:github",
    }
    js_runtimes = build_js_runtimes()
    if js_runtimes:
        opts["js_runtimes"] = js_runtimes
    if YTDLP_COOKIES_FILE:
        opts["cookiefile"] = YTDLP_COOKIES_FILE
    return opts

# Cấu hình Spotify Web API (HOTFIX 3)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_MARKET = os.getenv("SPOTIFY_MARKET", "VN")
SPOTIFY_MAX_TRACKS_PER_REQUEST = int(os.getenv("SPOTIFY_MAX_TRACKS_PER_REQUEST", "100"))
SPOTIFY_QUEUE_LIMIT = int(os.getenv("SPOTIFY_QUEUE_LIMIT", "500"))