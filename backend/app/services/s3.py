import boto3
import tempfile
import os
import mimetypes
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

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
    
    def upload_file(self, file_path: str, key: str, content_type: str = None) -> str:
        """Upload file to S3 with proper Content-Type metadata
        
        Args:
            file_path: Local path to file to upload
            key: S3 key (path) where file should be stored
            content_type: Optional MIME type. If not provided, will be guessed from file extension.
        """
        # Determine Content-Type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(key)
            if content_type is None:
                # Default based on extension
                ext = os.path.splitext(key)[1].lower()
                if ext == '.mp4':
                    content_type = 'video/mp4'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext == '.jpg' or ext == '.jpeg':
                    content_type = 'image/jpeg'
                elif ext == '.mp3':
                    content_type = 'audio/mpeg'
                elif ext == '.wav':
                    content_type = 'audio/wav'
                else:
                    content_type = 'application/octet-stream'
        
        # Upload with Content-Type metadata
        extra_args = {'ContentType': content_type}
        self.client.upload_file(file_path, self.bucket, key, ExtraArgs=extra_args)
        logger.debug(f"Uploaded {file_path} to s3://{self.bucket}/{key} with Content-Type: {content_type}")
        return f"s3://{self.bucket}/{key}"
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for secure temporary access (both uploads and downloads)"""
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
    
    def list_files(self, prefix: str) -> list:
        """List files in S3 with given prefix
        
        Args:
            prefix: S3 key prefix (e.g., 'user123/videos/video456/')
            
        Returns:
            List of S3 keys (full keys, not just filenames)
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append(obj['Key'])
            
            # Handle pagination if there are more than 1000 objects
            while response.get('IsTruncated'):
                response = self.client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix,
                    ContinuationToken=response.get('NextContinuationToken')
                )
                if 'Contents' in response:
                    for obj in response['Contents']:
                        files.append(obj['Key'])
            
            return files
        except Exception as e:
            print(f"⚠️  Error listing S3 files with prefix '{prefix}': {str(e)}")
            return []
    
    def delete_file(self, key: str) -> bool:
        """Delete a single file from S3
        
        Args:
            key: S3 key (e.g., 'user123/videos/video456/file.mp4') or S3 URL (e.g., 's3://bucket/user123/videos/video456/file.mp4')
            
        Returns:
            True on success, False on failure
        """
        try:
            # Extract key from S3 URL if needed
            if key.startswith('s3://'):
                # Remove s3:// prefix and bucket name
                key = key.replace(f's3://{self.bucket}/', '')
            
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted S3 file: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 file '{key}': {str(e)}")
            return False
    
    def update_content_type(self, key: str, content_type: str) -> bool:
        """Update Content-Type metadata for an existing S3 object
        
        Args:
            key: S3 key of the object to update
            content_type: MIME type to set (e.g., 'video/mp4')
            
        Returns:
            True on success, False on failure
        """
        try:
            # Extract key from S3 URL if needed
            if key.startswith('s3://'):
                key = key.replace(f's3://{self.bucket}/', '')
            
            # Copy object to itself with updated metadata
            copy_source = {'Bucket': self.bucket, 'Key': key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=key,
                ContentType=content_type,
                MetadataDirective='REPLACE'
            )
            logger.info(f"Updated Content-Type for {key} to {content_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Content-Type for '{key}': {str(e)}")
            return False
    
    def delete_directory(self, prefix: str) -> bool:
        """Delete all files with given prefix (e.g., user_id/videos/video_id/)
        
        Args:
            prefix: S3 key prefix (e.g., 'user123/videos/video456/')
            
        Returns:
            True if all deletions succeed, False otherwise
        """
        try:
            # Ensure prefix ends with / for directory-like behavior
            if not prefix.endswith('/'):
                prefix = prefix + '/'
            
            # List all files with this prefix
            files = self.list_files(prefix)
            
            if not files:
                logger.info(f"No files found with prefix '{prefix}'")
                return True
            
            # Delete files in batches (S3 allows up to 1000 objects per delete request)
            batch_size = 1000
            all_succeeded = True
            
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                try:
                    # Prepare delete objects
                    delete_objects = [{'Key': key} for key in batch]
                    
                    # Delete batch
                    response = self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': delete_objects}
                    )
                    
                    # Check for errors
                    if 'Errors' in response and response['Errors']:
                        for error in response['Errors']:
                            logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
                            all_succeeded = False
                    
                    deleted_count = len(response.get('Deleted', []))
                    logger.info(f"Deleted {deleted_count} files from prefix '{prefix}' (batch {i//batch_size + 1})")
                    
                except Exception as e:
                    logger.error(f"Failed to delete batch of files from prefix '{prefix}': {str(e)}")
                    all_succeeded = False
            
            logger.info(f"Deleted {len(files)} total files from prefix '{prefix}'")
            return all_succeeded
            
        except Exception as e:
            logger.error(f"Failed to delete directory with prefix '{prefix}': {str(e)}")
            return False

# Initialize with error handling - don't crash on import
try:
    s3_client = S3Client()
    logger.debug("S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}", exc_info=True)
    # Create a placeholder that will fail on use, but allow import to succeed
    class FailedClient:
        def __getattr__(self, name):
            raise RuntimeError(f"S3 client initialization failed: {e}")
    s3_client = FailedClient()
