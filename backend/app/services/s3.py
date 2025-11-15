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
        """Download file from S3 to local path"""
        if local_path is None:
            # Create temp file
            suffix = os.path.splitext(key)[1] or '.tmp'
            local_path = tempfile.mktemp(suffix=suffix)
        
        self.client.download_file(self.bucket, key, local_path)
        return local_path
    
    def download_temp(self, key: str) -> str:
        """Download file from S3 to temporary file"""
        return self.download_file(key)

s3_client = S3Client()
