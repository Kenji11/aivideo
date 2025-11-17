FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create entrypoint script to run migrations before starting the app
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Run database migrations (continue even if migration fails due to revision mismatch)\n\
echo "Running database migrations..."\n\
if ! alembic upgrade head 2>&1; then\n\
    echo "Migration failed, but continuing startup..."\n\
    echo "This is OK if database schema is already up to date"\n\
fi\n\
\n\
# Execute the main command\n\
exec "$@"\n\
' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (overridden in docker-compose for worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
