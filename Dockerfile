FROM python:3.11-slim

WORKDIR /app

# Cài đặt FFmpeg và các công cụ bổ trợ
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Deno runtime để hỗ trợ yt-dlp giải mã chữ ký YouTube
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Khởi chạy bot
CMD ["python", "main.py"]