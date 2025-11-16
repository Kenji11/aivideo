#!/bin/bash
# Start comprehensive monitoring for video generation pipeline

echo "🚀 Starting Video Generation Pipeline Monitor"
echo "=============================================="
echo ""

# Check if video_id is provided
if [ -z "$1" ]; then
    echo "Usage: ./start_monitoring.sh <video_id>"
    echo ""
    echo "Example:"
    echo "  ./start_monitoring.sh 123e4567-e89b-12d3-a456-426614174000"
    echo ""
    exit 1
fi

VIDEO_ID=$1

echo "📊 Monitoring Video ID: $VIDEO_ID"
echo ""
echo "Starting monitors..."
echo ""

# Start pipeline monitor in background
python3 monitor_pipeline.py "$VIDEO_ID" &
MONITOR_PID=$!

# Start log monitor in another terminal (if available)
echo "💡 Tip: Open another terminal and run:"
echo "   ./monitor_logs.sh"
echo ""
echo "   Or view logs directly:"
echo "   docker-compose logs -f worker"
echo ""

# Wait for monitor to complete
wait $MONITOR_PID

echo ""
echo "✅ Monitoring complete"

