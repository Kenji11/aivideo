FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Accept DEV build argument (defaults to false for production)
ARG DEV=false

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$DEV" = "true" ] ; then \
        pip install --no-cache-dir -r requirements-dev.txt ; \
    else \
        pip install --no-cache-dir -r requirements.txt ; \
    fi

# Copy application code
COPY . .

# Default command (overridden in docker-compose for worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
