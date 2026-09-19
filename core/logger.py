"""
core/logger.py
---------------
Logger tập trung dùng chung cho toàn bộ dự án (mục 1.2 - Utils/Core layer),
thay vì rải rác print() khắp bot.py cũ.
"""
import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # đã cấu hình rồi, tránh nhân đôi log khi reload cogs

    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)

    # discord.py tự log khá nhiều ở mức INFO, hạ xuống WARNING cho gọn.
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
