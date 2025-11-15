#!/bin/bash

# Test Phase 3 on localhost
# This script will:
# 1. Submit a video generation request
# 2. Poll for status until Phase 3 completes
# 3. Display the generated reference assets

API_URL="http://localhost:8000"

echo "=========================================="
echo "Phase 3 Localhost Test"
echo "=========================================="
echo ""

# Test prompt
PROMPT="Create a luxury product showcase video for a premium watch with elegant gold and black colors, dramatic lighting, and cinematic style"

echo "📝 Test Prompt:"
echo "$PROMPT"
echo ""
echo "🚀 Submitting video generation request..."
echo ""

# Submit request
RESPONSE=$(curl -s -X POST "$API_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"$PROMPT\", \"assets\": []}")

VIDEO_ID=$(echo $RESPONSE | grep -o '"video_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$VIDEO_ID" ]; then
  echo "❌ Failed to create video generation"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "✅ Video generation started!"
echo "📹 Video ID: $VIDEO_ID"
echo ""
echo "⏳ Polling for status (checking every 3 seconds)..."
echo ""

# Poll for status
MAX_ATTEMPTS=60
ATTEMPT=0
PHASE3_COMPLETE=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  STATUS_RESPONSE=$(curl -s "$API_URL/api/status/$VIDEO_ID")
  
  STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  PROGRESS=$(echo $STATUS_RESPONSE | grep -o '"progress":[0-9.]*' | cut -d':' -f2)
  CURRENT_PHASE=$(echo $STATUS_RESPONSE | grep -o '"current_phase":"[^"]*' | cut -d'"' -f4)
  
  echo -ne "\r📊 Status: $STATUS | Progress: ${PROGRESS}% | Phase: ${CURRENT_PHASE:-N/A}"
  
  # Check if Phase 3 is complete (has reference_assets)
  if echo $STATUS_RESPONSE | grep -q "reference_assets"; then
    PHASE3_COMPLETE=true
    echo ""
    echo ""
    echo "✅ Phase 3 Complete! Reference assets generated."
    echo ""
    break
  fi
  
  # Check if failed
  if [ "$STATUS" = "failed" ]; then
    ERROR=$(echo $STATUS_RESPONSE | grep -o '"error":"[^"]*' | cut -d'"' -f4)
    echo ""
    echo ""
    echo "❌ Generation failed: $ERROR"
    exit 1
  fi
  
  # Check if complete
  if [ "$STATUS" = "complete" ]; then
    echo ""
    echo ""
    echo "✅ Video generation complete!"
    break
  fi
  
  sleep 3
  ATTEMPT=$((ATTEMPT + 1))
done

if [ "$PHASE3_COMPLETE" = false ] && [ "$STATUS" != "complete" ]; then
  echo ""
  echo ""
  echo "⏱️  Timeout waiting for Phase 3 completion"
  echo "Current status: $STATUS"
  exit 1
fi

echo "=========================================="
echo "Reference Assets"
echo "=========================================="
echo ""

# Extract and display reference assets
STYLE_GUIDE=$(echo $STATUS_RESPONSE | grep -o '"style_guide_url":"[^"]*' | cut -d'"' -f4)
PRODUCT_REF=$(echo $STATUS_RESPONSE | grep -o '"product_reference_url":"[^"]*' | cut -d'"' -f4)

if [ -n "$STYLE_GUIDE" ]; then
  echo "🎨 Style Guide URL:"
  echo "   $STYLE_GUIDE"
  echo ""
fi

if [ -n "$PRODUCT_REF" ]; then
  echo "📦 Product Reference URL:"
  echo "   $PRODUCT_REF"
  echo ""
fi

echo "=========================================="
echo "✅ Test Complete!"
echo "=========================================="
echo ""
echo "💡 You can view the images by opening the URLs above in your browser"
echo "💡 Or check your S3 bucket: videogen-outputs-dev/references/$VIDEO_ID/"
echo ""

