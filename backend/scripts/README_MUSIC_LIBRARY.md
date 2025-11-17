# Music Library Setup Guide

This guide explains how to set up a free music library using Pixabay tracks.

## Option 1: Automatic Download (If Pixabay API Supports Audio)

### Step 1: Get Pixabay API Key

1. Go to https://pixabay.com/api/docs/
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add it to your `.env` file:
   ```
   PIXABAY_API_KEY=your-api-key-here
   ```

### Step 2: Run the Download Script

```bash
cd backend
python scripts/download_pixabay_music.py
```

This will:
- Download music tracks from Pixabay
- Organize them by genre (upbeat, cinematic, corporate, etc.)
- Upload them to your S3 bucket under `music-library/`

## Option 2: Manual Download (If API Doesn't Work)

If Pixabay's audio API isn't available, you can manually download tracks:

### Step 1: Download from Pixabay

1. Go to https://pixabay.com/music/
2. Browse and download tracks by genre
3. Organize them in folders:
   - `upbeat/` - Happy, energetic tracks
   - `cinematic/` - Epic, dramatic tracks
   - `corporate/` - Professional, business tracks
   - `calm/` - Peaceful, relaxing tracks
   - `energetic/` - Fast, intense tracks
   - `background/` - Ambient, atmospheric tracks
   - `advertising/` - Commercial, promotional tracks

### Step 2: Upload to S3

Use the upload script (to be created) or AWS CLI:

```bash
# Upload a single track
aws s3 cp local_track.mp3 s3://your-bucket/music-library/upbeat/track1.mp3

# Upload entire folder
aws s3 sync ./music-library/ s3://your-bucket/music-library/
```

## Music Genres Available

The system supports these genres:
- **upbeat** - Happy, positive, energetic
- **cinematic** - Epic, dramatic, orchestral
- **corporate** - Professional, business, modern
- **calm** - Peaceful, relaxing, ambient
- **energetic** - Fast, intense, action
- **background** - Ambient, atmospheric
- **advertising** - Commercial, promotional

## Using the Music Library

Once tracks are in S3, the Phase 5 service will:
1. Check if a genre is selected
2. Randomly select a track from that genre
3. Crop it to match video duration
4. Combine with video (no AI generation needed!)

## License

Pixabay music is free for personal and commercial use (check their license terms).
No attribution required for most tracks.

