# =====================================================================
# VieNeu TTS Web — Dockerfile
# - Nền Python 3.12-slim (tương thích wheel sẵn của mọi dep, gồm kaldi)
# - Cài engine `vieneu` đầy đủ + ffmpeg (xuất MP3) + libsndfile (ghi WAV)
# - Model tải 1 lần từ HuggingFace vào volume hf-cache, lần sau dùng tiếp
# Build:  docker compose build
# Chạy:   docker compose up -d  →  http://localhost:8000
# =====================================================================
FROM python:3.12-slim

# Tránh prompt tương tác + log Python ra ngay (tiện docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_ENABLE_HF_TRANSFER=0

WORKDIR /app

# 1) Gói hệ thống: âm thanh (sndfile, ffmpeg) + toolchain build cmake/C++
#    cho gói kaldi-native-fbank nếu pip không có wheel sẵn cho nền này.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 ffmpeg cmake build-essential \
    && rm -rf /var/lib/apt/lists

# 2) Thư viện Python (tách lớp riêng để tận dụng cache khi sửa code)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-input -r requirements.txt \
    && pip show vieneu | head -3

# 3) Code web + giao diện
COPY app.py .
COPY static/ ./static/

# Thư mục chứa file wav đã tạo
RUN mkdir -p outputs

EXPOSE 8000

# Chạy server (1 worker vì model nằm trong RAM tiến trình)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
