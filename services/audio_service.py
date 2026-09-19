"""
services/audio_service.py
---------------------------
Mục 1.3: Quản lý Vòng đời Tiến trình FFmpeg (Process Lifecycle & Zombie Cleanup).

discord.py mặc định SIGKILL tiến trình FFmpeg ngay khi cleanup(), điều này có
thể cắt ngang khi FFmpeg đang flush buffer/socket, để lại tiến trình con hoặc
socket dở dang trong một số trường hợp trên Linux. GracefulFFmpegPCMAudio gửi
SIGTERM trước, chỉ SIGKILL nếu FFmpeg không tự thoát trong khoảng thời gian
cấu hình (FFMPEG_TERMINATE_TIMEOUT).
"""
from __future__ import annotations

import time

import discord

from core import config
from core.logger import get_logger

log = get_logger("services.audio")


class GracefulFFmpegPCMAudio(discord.FFmpegPCMAudio):
    def __init__(self, source: str, *, filter_name: str | None = None, **kwargs):
        before_options = config.BASE_FFMPEG_BEFORE_OPTIONS
        options = config.BASE_FFMPEG_OPTIONS

        af = config.AUDIO_FILTERS.get(filter_name) if filter_name else None
        if af:
            options = f"{options} -af \"{af}\""

        super().__init__(
            source,
            before_options=before_options,
            options=options,
            **kwargs,
        )
        self.started_at = time.monotonic()

    @property
    def pid(self):
        proc = getattr(self, "_process", None)
        return proc.pid if proc else None

    def cleanup(self) -> None:
        proc = getattr(self, "_process", None)
        if proc is None:
            return

        pid = proc.pid
        if proc.poll() is None:
            try:
                proc.terminate()  # SIGTERM — cho FFmpeg cơ hội tự dọn dẹp.
                proc.wait(timeout=config.FFMPEG_TERMINATE_TIMEOUT)
                log.debug("FFmpeg PID %s thoát êm sau SIGTERM", pid)
            except Exception:  # noqa: BLE001 - Timeout hoặc process đã mất
                try:
                    proc.kill()  # SIGKILL — ép buộc nếu SIGTERM không hiệu quả.
                    proc.wait(timeout=1.0)
                    log.warning("FFmpeg PID %s không phản hồi SIGTERM, đã SIGKILL", pid)
                except Exception as exc:  # noqa: BLE001
                    log.error("Không thể dọn tiến trình FFmpeg PID %s: %s", pid, exc)

        # Đóng các pipe còn mở để tránh rò rỉ file descriptor.
        for stream in (proc.stdout, proc.stderr, getattr(proc, "stdin", None)):
            try:
                if stream:
                    stream.close()
            except Exception:  # noqa: BLE001
                pass

        self._process = None
