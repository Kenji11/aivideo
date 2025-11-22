FROM python:3.11-slim

# Install FFmpeg, system dependencies, and AWS CLI v2
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libxrender-dev \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

WORKDIR /app

# Copy requirements.txt first (for better Docker layer caching)
COPY requirements.txt .

# Install PyTorch CPU version first (smaller image, faster install)
# Must install from PyTorch's CPU index to get CPU-only version
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch>=2.0.0 \
    torchvision>=0.15.0

# Verify torch is installed
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed successfully')"

# Install remaining Python dependencies
# torch and torchvision are already installed above, so they're not in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set CLIP model environment variables
ENV CLIP_MODEL=ViT-B/32
ENV CLIP_MODEL_CACHE=/mnt/models

# Use entrypoint script (will download model from S3 if needed, then run command)
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
