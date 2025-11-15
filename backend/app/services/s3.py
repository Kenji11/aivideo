import boto3
import tempfile
import os
from app.config import get_settings

settings = get_settings()

class S3Client:
    def __init__(self):
        self.client = boto3.client(
            's3',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        self.bucket = settings.s3_bucket
    
    def upload_file(self, file_path: str, key: str) -> str:
        """Upload file to S3"""
        self.client.upload_file(file_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL"""
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expiration
        )
    
    def download_file(self, key: str, local_path: str = None) -> str:
        """Download file from S3 to local path
        
        Args:
            key: S3 key (e.g., 'chunks/video_id/file.mp4') or S3 URL (e.g., 's3://bucket/chunks/video_id/file.mp4')
            local_path: Optional local path to save file. If None, creates temp file.
        """
        # Extract key from S3 URL if needed
        if key.startswith('s3://'):
            # Remove s3:// prefix and bucket name
            key = key.replace(f's3://{self.bucket}/', '')
            # Also handle case where bucket is different (shouldn't happen, but be safe)
            if '/' in key and not key.startswith('s3://'):
                # Already extracted
                pass
        
        if local_path is None:
            # Create temp file
            suffix = os.path.splitext(key)[1] or '.tmp'
            local_path = tempfile.mktemp(suffix=suffix)
        
        self.client.download_file(self.bucket, key, local_path)
        return local_path
    
    def download_temp(self, key_or_url: str) -> str:
        """Download file from S3 to temporary file
        
        Args:
            key_or_url: S3 key or S3 URL (e.g., 's3://bucket/key' or 'key')
        """
        return self.download_file(key_or_url)

s3_client = S3Client()
