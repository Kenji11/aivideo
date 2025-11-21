#!/usr/bin/env python3
"""
Script to fix Content-Type metadata for video files in S3.

Usage:
    python scripts/fix_video_content_type.py <s3_key> [content_type]
    
Examples:
    python scripts/fix_video_content_type.py "ZsYJBAsr58dmcUSykPsDsuMOv8h2/videos/4152e7f5-2c9c-4b95-a32b-8fb8169aa334/final_draft.mp4"
    python scripts/fix_video_content_type.py "ZsYJBAsr58dmcUSykPsDsuMOv8h2/videos/4152e7f5-2c9c-4b95-a32b-8fb8169aa334/final_draft.mp4" "video/mp4"
"""

import sys
import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_content_type(s3_key: str, content_type: str = 'video/mp4'):
    """Fix Content-Type for an S3 object"""
    
    # Get AWS credentials from environment
    aws_region = os.getenv('AWS_REGION', 'us-east-2')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    s3_bucket = os.getenv('S3_BUCKET', 'vincent-ai-vid-storage')
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("❌ AWS credentials not found in environment variables")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    
    try:
        # Check if object exists
        try:
            s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
        except s3_client.exceptions.NoSuchKey:
            print(f"❌ Object not found: s3://{s3_bucket}/{s3_key}")
            return False
        
        # Copy object to itself with updated metadata
        copy_source = {'Bucket': s3_bucket, 'Key': s3_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=s3_bucket,
            Key=s3_key,
            ContentType=content_type,
            MetadataDirective='REPLACE'
        )
        
        print(f"✅ Successfully updated Content-Type for s3://{s3_bucket}/{s3_key}")
        print(f"   Content-Type: {content_type}")
        
        # Generate new presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_bucket, 'Key': s3_key},
            ExpiresIn=3600 * 24 * 7  # 7 days
        )
        print(f"📎 New presigned URL (7 days):")
        print(f"   {presigned_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Content-Type: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_video_content_type.py <s3_key> [content_type]")
        print("\nExample:")
        print('  python scripts/fix_video_content_type.py "ZsYJBAsr58dmcUSykPsDsuMOv8h2/videos/4152e7f5-2c9c-4b95-a32b-8fb8169aa334/final_draft.mp4"')
        sys.exit(1)
    
    s3_key = sys.argv[1]
    content_type = sys.argv[2] if len(sys.argv) > 2 else 'video/mp4'
    
    print(f"🔧 Fixing Content-Type for: {s3_key}")
    success = fix_content_type(s3_key, content_type)
    
    sys.exit(0 if success else 1)

