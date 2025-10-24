# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg \
    git \
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

# Create storage dirs
RUN mkdir -p /app/storage/input /app/storage/output /app/tmp/frames

# Start server
CMD ["python3", "-m", "app.main"]
