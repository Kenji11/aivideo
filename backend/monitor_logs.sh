#!/bin/bash
# Monitor Docker container logs for video generation pipeline

echo "🔍 Starting Pipeline Log Monitor"
echo "================================"
echo ""
echo "Monitoring services:"
echo "  - API (FastAPI)"
echo "  - Worker (Celery)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Docker containers not running. Starting them..."
    docker-compose up -d
    sleep 5
fi

# Monitor both API and Worker logs
docker-compose logs -f --tail=100 api worker 2>&1 | grep -E "(Phase|🎬|✅|❌|⚠️|💰|🎵|📸|🔧|📥|📤|🎼|🎵|⏱️|📏|✂️|🎬|📊|🚀)" --color=always

