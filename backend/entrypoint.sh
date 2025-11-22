#!/bin/bash
set -e

MODEL_DIR="/mnt/models"
S3_BUCKET="aivideo-outputs-971422717446"
S3_KEY="clip-models/openai-clip-vit-b32.tar.gz"
LOCAL_TAR="$MODEL_DIR/clip.tar.gz"

# Detect if we're in local dev (Docker volume) or production (ECS Fargate)
# In local dev, the volume is mounted and model should already be there
# In production, we need to download from S3
IS_LOCAL_DEV=false
if [ -n "$ENVIRONMENT" ] && [ "$ENVIRONMENT" = "development" ]; then
    IS_LOCAL_DEV=true
elif [ -z "$ENVIRONMENT" ] || [ "$ENVIRONMENT" = "" ]; then
    # If ENVIRONMENT is not set, assume local dev (docker-compose)
    IS_LOCAL_DEV=true
fi

echo "🔍 Checking for CLIP model..."
echo "   Environment: ${ENVIRONMENT:-development (assumed)}"
echo "   Model directory: $MODEL_DIR"

# Ensure model directory exists
mkdir -p "$MODEL_DIR"

# Check if model files already exist
# open_clip stores models in checkpoints/ or hub/ directories under HF_HOME/TORCH_HOME
MODEL_EXISTS=false

if [ -d "$MODEL_DIR/checkpoints" ] && [ -n "$(ls -A "$MODEL_DIR/checkpoints" 2>/dev/null)" ]; then
    echo "✓ Model checkpoints directory found"
    MODEL_EXISTS=true
elif [ -d "$MODEL_DIR/hub" ] && [ -n "$(ls -A "$MODEL_DIR/hub" 2>/dev/null)" ]; then
    echo "✓ Model hub directory found"
    MODEL_EXISTS=true
elif [ -f "$MODEL_DIR/ViT-B-32.pt" ] || [ -f "$MODEL_DIR/openai/ViT-B-32.pt" ]; then
    echo "✓ Model file found"
    MODEL_EXISTS=true
fi

if [ "$MODEL_EXISTS" = false ]; then
    if [ "$IS_LOCAL_DEV" = true ]; then
        echo "📥 Model missing in local dev – will download from HuggingFace on first use"
        echo "   (Docker volume will cache it for future runs)"
    else
        echo "📥 Model missing – downloading from S3..."
        
        # Check if AWS credentials are available
        if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
            echo "⚠️  AWS credentials not found in environment"
            echo "   Attempting to use IAM role credentials (for ECS tasks)..."
        fi
        
        # Download from S3
        if aws s3 cp "s3://$S3_BUCKET/$S3_KEY" "$LOCAL_TAR" 2>/dev/null; then
            echo "✓ Download complete, extracting..."
            # Extract directly to MODEL_DIR (archive contains checkpoints/, hub/, etc. at root)
            tar -xzf "$LOCAL_TAR" -C "$MODEL_DIR"
            rm -f "$LOCAL_TAR"
            echo "✅ Model extracted successfully"
            echo "   Model files should be in: $MODEL_DIR/checkpoints/ or $MODEL_DIR/hub/"
        else
            echo "❌ Failed to download model from S3"
            echo "   S3 path: s3://$S3_BUCKET/$S3_KEY"
            echo "   The model will be downloaded from HuggingFace on first use (slower)"
            echo "   To fix: ensure the model is uploaded to S3 and IAM permissions are correct"
        fi
    fi
else
    echo "✓ Model already present – skipping download"
fi

# Start the application
echo "🚀 Starting application..."
exec "$@"

