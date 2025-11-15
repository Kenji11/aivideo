# 🚀 Quick Start: Testing Phase 3

## Fastest Way to Test (No Docker, No AWS)

**Time:** ~2 minutes | **Cost:** ~$0.01 per test

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt Pillow requests
```

### Step 2: Set API Token
```bash
# Option A: Export in terminal
export REPLICATE_API_TOKEN="your-replicate-token-here"

# Option B: Add to .env file
echo "REPLICATE_API_TOKEN=your-token" >> backend/.env
echo "AWS_ACCESS_KEY_ID=dummy" >> backend/.env
echo "AWS_SECRET_ACCESS_KEY=dummy" >> backend/.env
echo "S3_BUCKET=dummy" >> backend/.env
echo "AWS_REGION=us-east-2" >> backend/.env
```

### Step 3: Run Simple Test (No S3)
```bash
cd backend
python test_phase3_simple.py
```

**Expected Output:**
```
✅ SUCCESS!
Image URL: https://replicate.delivery/...
Cost: $0.0055 (SDXL)
```

---

## Full Test with S3 Upload

### Step 1: Configure AWS
```bash
# Add real AWS credentials to .env
cat >> backend/.env << EOF
REPLICATE_API_TOKEN=your-token
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=your-bucket-name
AWS_REGION=us-east-2
EOF
```

### Step 2: Run Full Test
```bash
cd backend
python test_phase3.py
```

**This will:**
- ✅ Generate style guide
- ✅ Generate product reference
- ✅ Upload to S3
- ✅ Save results to `test_references_output.json`

---

## Test with Docker (Full Stack)

### Step 1: Start Services
```bash
cd backend
docker-compose up --build -d
```

### Step 2: Run Test
```bash
docker-compose exec api python test_phase3.py
```

---

## What Each Test Does

| Test Script | What It Tests | Requires |
|------------|---------------|----------|
| `test_phase3_simple.py` | Replicate API only | Replicate token |
| `test_phase3.py` | Full Phase 3 (API + S3) | Replicate + AWS |
| `pytest app/tests/test_phase3/` | Unit tests | Python deps |

---

## Get Your Replicate Token

1. Go to https://replicate.com
2. Sign up / Log in
3. Go to Account → API Tokens
4. Copy your token

---

## Troubleshooting

**"REPLICATE_API_TOKEN not found"**
```bash
export REPLICATE_API_TOKEN="your-token"
```

**"ModuleNotFoundError: No module named 'replicate'"**
```bash
pip install replicate
```

**"AWS credentials invalid" (for full test)**
- Use `test_phase3_simple.py` instead (no AWS needed)
- Or set dummy AWS vars in `.env` (S3 uploads will fail but API works)

---

**Ready! Start with `test_phase3_simple.py` for fastest testing!** ⚡

