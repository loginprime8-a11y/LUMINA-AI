# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg \
    git curl ca-certificates unzip \
    libvulkan1 vulkan-tools \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python deps
COPY backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy app code
COPY backend /app

# Expose port
EXPOSE 8000

# Runtime env
ENV PYTHONUNBUFFERED=1
ENV STORAGE_ROOT=/app/storage
ENV TMP_ROOT=/app/tmp
ENV MODELS_ROOT=/app/models
ENV RIFE_MODELS_DIR=/app/models/rife
ENV CODEFORMER_MODELS_DIR=/app/models/codeformer
ENV GFPGAN_MODELS_DIR=/app/models/gfpgan
ENV REALESRGAN_MODELS_DIR=/app/models/realesrgan
ENV NCNN_THREADS=4
# Default to CPU for broad compatibility; set to 1 at runtime if GPU available
ENV NCNN_GPU=0
ENV REALESRGAN_MODELS_DIR=/app/models/realesrgan

# Create storage dirs
RUN mkdir -p /app/storage/input /app/storage/output /app/tmp/frames \
    && mkdir -p /app/models/rife /app/models/codeformer /app/models/gfpgan /app/models/realesrgan /usr/local/bin

# Install NCNN Vulkan CLIs (rife/codeformer/gfpgan) with model caches
# Note: URLs and versions below are examples and may change; update as needed.
RUN set -eux; \
    ARCH=$(uname -m); \
    cd /tmp; \
    # RIFE
    curl -L -o rife.zip https://github.com/nihui/rife-ncnn-vulkan/releases/download/20220729/rife-ncnn-vulkan-20220729-ubuntu.zip; \
    unzip rife.zip -d rife && cp rife/rife-ncnn-vulkan /usr/local/bin/ || true; \
    if [ -d rife/models ]; then cp -r rife/models/* /app/models/rife/; fi; \
    # CodeFormer
    curl -L -o codeformer.zip https://github.com/nihui/codeformer-ncnn-vulkan/releases/download/20220728/codeformer-ncnn-vulkan-20220728-ubuntu.zip; \
    unzip codeformer.zip -d codeformer && cp codeformer/codeformer-ncnn-vulkan /usr/local/bin/ || true; \
    if [ -d codeformer/models ]; then cp -r codeformer/models/* /app/models/codeformer/; fi; \
    # GFPGAN
    curl -L -o gfpgan.zip https://github.com/nihui/gfpgan-ncnn-vulkan/releases/download/20220728/gfpgan-ncnn-vulkan-20220728-ubuntu.zip; \
    unzip gfpgan.zip -d gfpgan && cp gfpgan/gfpgan-ncnn-vulkan /usr/local/bin/ || true; \
    if [ -d gfpgan/models ]; then cp -r gfpgan/models/* /app/models/gfpgan/; fi; \
    # Real-ESRGAN
    curl -L -o realesrgan.zip https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip; \
    unzip realesrgan.zip -d realesrgan && cp realesrgan/realesrgan-ncnn-vulkan /usr/local/bin/ || true; \
    if [ -d realesrgan/models ]; then cp -r realesrgan/models/* /app/models/realesrgan/; fi; \
    rm -rf /tmp/*; \
    chmod +x /usr/local/bin/*-ncnn-vulkan || true

# Start server with gunicorn (better for production)
ENV WEB_CONCURRENCY=2
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app.main:app"]
