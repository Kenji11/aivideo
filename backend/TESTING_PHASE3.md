# Phase 3 Testing Guide

## 🧪 Testing Options

### Option 1: Local Testing (Without Docker) - **FASTEST**

**Best for:** Quick testing of Phase 3 service logic

#### Prerequisites:
```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Install Pillow for image processing
pip install Pillow requests
```

#### Required Environment Variables:
Create or update `backend/.env`:
```bash
# Required for Phase 3
REPLICATE_API_TOKEN=your-replicate-token-here

# Required for S3 uploads (can use local S3 or mock for testing)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_BUCKET=videogen-outputs-dev
AWS_REGION=us-east-2
```

#### Run Tests:

**1. Simple Service Test (No S3 - Just API calls):**
```bash
cd backend
export REPLICATE_API_TOKEN="your-token"
python test_phase3.py
```

**2. Unit Tests:**
```bash
cd backend
pytest app/tests/test_phase3/ -v
```

**3. Test Asset Handler Only:**
```python
# In Python shell
from app.phases.phase3_references.asset_handler import AssetHandler
from PIL import Image
import tempfile

handler = AssetHandler()
# Create test image
img = Image.new('RGB', (1024, 1024), color='red')
temp = tempfile.mktemp(suffix='.png')
img.save(temp)
print(handler.validate_image(temp))  # Should print True
```

---

### Option 2: Local Testing with Docker - **FULL STACK**

**Best for:** Testing complete pipeline with Redis, Postgres, Celery

#### Prerequisites:
- Docker & Docker Compose installed
- `.env` file configured (see above)

#### Start Services:
```bash
cd backend

# Start all services (Postgres, Redis, API, Worker)
docker-compose up --build -d

# Check logs
docker-compose logs -f api worker

# Wait for services to be healthy
# You should see:
# ✅ postgres: healthy
# ✅ redis: healthy
# ✅ api: Uvicorn running
# ✅ worker: celery ready
```

#### Run Tests:

**1. Manual Test Script:**
```bash
docker-compose exec api python test_phase3.py
```

**2. Unit Tests:**
```bash
docker-compose exec api pytest app/tests/test_phase3/ -v
```

**3. Test via API Endpoint:**
```bash
# First, run Phase 1 to get a spec
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a luxury watch commercial with cinematic visuals",
    "assets": []
  }'

# Then test Phase 3 directly (if you have video_id and spec)
# Or use the pipeline which calls Phase 3 automatically
```

---

### Option 3: AWS Testing - **PRODUCTION-LIKE**

**Best for:** Testing with real S3, production-like environment

#### Prerequisites:
1. AWS Account with S3 bucket created
2. IAM user with S3 permissions
3. `.env` file with real AWS credentials

#### Setup AWS Resources:

**1. Create S3 Bucket:**
```bash
aws s3 mb s3://videogen-outputs-dev --region us-east-2
```

**2. Create IAM User:**
```bash
# Create user with S3 access
aws iam create-user --user-name videogen-s3-user

# Attach S3 policy
aws iam attach-user-policy \
  --user-name videogen-s3-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create access keys
aws iam create-access-key --user-name videogen-s3-user
```

**3. Update `.env`:**
```bash
AWS_ACCESS_KEY_ID=AKIA...  # From IAM user
AWS_SECRET_ACCESS_KEY=...  # From IAM user
S3_BUCKET=videogen-outputs-dev
AWS_REGION=us-east-2
REPLICATE_API_TOKEN=your-token
```

#### Run Tests:

**Same as Option 1 or 2**, but now files will upload to real S3:

```bash
cd backend
python test_phase3.py

# Check S3 bucket
aws s3 ls s3://videogen-outputs-dev/references/ --recursive
```

---

## 🎯 Quick Test Scenarios

### Test 1: Style Guide Only
```python
from app.phases.phase3_references.service import ReferenceAssetService

service = ReferenceAssetService()
spec = {
    'style': {
        'aesthetic': 'cinematic',
        'color_palette': ['gold', 'black'],
        'mood': 'elegant',
        'lighting': 'soft'
    },
    'product': None,
    'uploaded_assets': []
}

result = service.generate_all_references('test_video_1', spec)
print(f"Style Guide: {result['style_guide_url']}")
print(f"Cost: ${result['total_cost']:.4f}")
```

### Test 2: With Product Reference
```python
spec = {
    'style': {
        'aesthetic': 'modern',
        'color_palette': ['blue', 'white'],
        'mood': 'energetic',
        'lighting': 'bright'
    },
    'product': {
        'name': 'Luxury Watch',
        'category': 'accessories'
    },
    'uploaded_assets': []
}

result = service.generate_all_references('test_video_2', spec)
print(f"Style Guide: {result['style_guide_url']}")
print(f"Product Ref: {result['product_reference_url']}")
```

### Test 3: With Uploaded Assets
```python
spec = {
    'style': {...},
    'product': {...},
    'uploaded_assets': [
        {'url': 'https://example.com/image.jpg'},
        {'s3_key': 's3://bucket/path/to/image.png'}
    ]
}

result = service.generate_all_references('test_video_3', spec)
print(f"Processed Assets: {len(result['uploaded_assets'])}")
```

---

## 🔍 Troubleshooting

### Issue: "REPLICATE_API_TOKEN not found"
**Fix:** Add token to `.env` file:
```bash
echo "REPLICATE_API_TOKEN=your-token" >> backend/.env
```

### Issue: "AWS credentials invalid"
**Fix:** 
- Check `.env` file has correct AWS keys
- Verify IAM user has S3 permissions
- Test with: `aws s3 ls s3://your-bucket`

### Issue: "ModuleNotFoundError: No module named 'PIL'"
**Fix:**
```bash
pip install Pillow
```

### Issue: "S3 upload fails"
**Fix:**
- Check bucket exists: `aws s3 ls s3://your-bucket`
- Check IAM permissions
- Verify region matches: `AWS_REGION=us-east-2`

---

## 📊 Expected Output

**Successful test output:**
```
======================================================================
PHASE 3 REFERENCE GENERATION TEST
======================================================================

======================================================================
TEST 1: Luxury Product
======================================================================
Video ID: test_video_1
Style: cinematic
Product: Chronos Elite Watch

✅ SUCCESS!
Style Guide URL: s3://videogen-outputs-dev/references/test_video_1/style_guide.png
Product Reference URL: s3://videogen-outputs-dev/references/test_video_1/product_reference.png
Total Cost: $0.0110
Uploaded Assets: 0

💾 Saved results to: test_references_output.json
```

---

## 🚀 Recommended Testing Flow

1. **Start Simple:** Test service directly (Option 1)
2. **Add S3:** Test with local S3 or AWS (Option 3)
3. **Full Stack:** Test with Docker + Celery (Option 2)
4. **Integration:** Test via API endpoint

---

## 💰 Cost Estimation

**Per Test Run:**
- Style Guide: $0.0055 (SDXL)
- Product Reference: $0.0055 (SDXL)
- **Total per test:** ~$0.011

**For 3 test scenarios:** ~$0.033

---

## ✅ Verification Checklist

After testing, verify:
- [ ] Style guide image generated and uploaded to S3
- [ ] Product reference generated (if product exists)
- [ ] Uploaded assets processed correctly
- [ ] Cost tracked accurately
- [ ] S3 URLs are accessible
- [ ] Images are valid (can open/download)

---

**Ready to test!** Choose the option that fits your setup! 🎯

