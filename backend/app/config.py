from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
import logging
import os
import sys

# Initialize basic logging early if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # External APIs
    replicate_api_token: str
    openai_api_key: str
    
    # AWS
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket: str
    aws_region: str = "us-east-2"
    
    # Application
    environment: str = "development"
    debug: bool = True
    
    # Firebase credentials
    # Option 1: JSON file path (with private_key from env var)
    firebase_credentials_path: str = Field(
        default="/app/firebase-credentials.json",
        env="FIREBASE_CREDENTIALS_PATH",
        description="Path to service account JSON file (without private_key, defaults to Docker mount path)"
    )
    firebase_private_key: str = Field(
        default="",
        env="FIREBASE_PRIVATE_KEY",
        description="Service account private key (from FIREBASE_PRIVATE_KEY env var, replaces private_key in JSON)"
    )
    # Option 2: Individual environment variables (alternative)
    firebase_project_id: str = Field(
        default="",
        env="FIREBASE_PROJECT_ID",
        description="Firebase project ID (from FIREBASE_PROJECT_ID env var)"
    )
    firebase_client_email: str = Field(
        default="",
        env="FIREBASE_CLIENT_EMAIL",
        description="Firebase service account client email (from FIREBASE_CLIENT_EMAIL env var)"
    )
    
    model_config = SettingsConfigDict(
        # .env file is optional - if it exists, use it (dev), otherwise use environment variables (prod)
        env_file=".env" if os.path.exists(".env") else None,
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables (e.g., typos, old variable names)
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._log_settings()
    
    def _log_settings(self):
        """Log loaded settings (masking sensitive values)"""
        logger.info("=" * 60)
        logger.info("Loading application settings...")
        logger.info("=" * 60)
        
        # Check if .env file exists
        env_file = ".env"
        env_exists = os.path.exists(env_file)
        logger.info(f"Configuration source: {'.env file' if env_exists else 'Environment variables'}")
        
        # Log non-sensitive settings
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Debug mode: {self.debug}")
        logger.info(f"AWS Region: {self.aws_region}")
        logger.info(f"S3 Bucket: {self.s3_bucket}")
        logger.info(f"Database URL: {self._mask_url(self.database_url)}")
        logger.info(f"Redis URL: {self._mask_url(self.redis_url)}")
        
        # Log API keys (masked)
        logger.info(f"OpenAI API Key: {self._mask_key(self.openai_api_key)}")
        logger.info(f"Replicate API Token: {self._mask_key(self.replicate_api_token)}")
        logger.info(f"AWS Access Key ID: {self._mask_key(self.aws_access_key_id)}")
        logger.info(f"AWS Secret Access Key: {self._mask_key(self.aws_secret_access_key)}")
        
        # Log Firebase config status
        google_app_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if google_app_creds:
            logger.info(f"Firebase credentials: Using GOOGLE_APPLICATION_CREDENTIALS")
            if self.firebase_private_key:
                logger.info("Firebase private key: Using FIREBASE_PRIVATE_KEY from environment")
        elif self.firebase_credentials_path:
            logger.info(f"Firebase credentials: Using firebase_credentials_path")
            if self.firebase_private_key:
                logger.info("Firebase private key: Using FIREBASE_PRIVATE_KEY from environment")
            else:
                logger.warning("FIREBASE_PRIVATE_KEY not set - will use private_key from JSON file")
        elif self.firebase_project_id and self.firebase_private_key and self.firebase_client_email:
            logger.info(f"Firebase project ID: {self.firebase_project_id}")
            logger.info(f"Firebase client email: {self._mask_key(self.firebase_client_email)}")
            logger.info("Firebase private key: *** (masked)")
        elif self.firebase_project_id:
            logger.info(f"Firebase project ID: {self.firebase_project_id}")
        else:
            logger.warning("Firebase credentials not configured - authentication will fail")
        
        # Check if values are set
        missing = []
        if not self.openai_api_key or self.openai_api_key == "":
            missing.append("openai_api_key")
        if not self.replicate_api_token or self.replicate_api_token == "":
            missing.append("replicate_api_token")
        if not self.aws_access_key_id or self.aws_access_key_id == "":
            missing.append("aws_access_key_id")
        if not self.aws_secret_access_key or self.aws_secret_access_key == "":
            missing.append("aws_secret_access_key")
        
        if missing:
            logger.warning(f"Missing or empty environment variables: {', '.join(missing)}")
        else:
            logger.info("All required environment variables are set")
        
        logger.info("=" * 60)
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for logging"""
        if not key or len(key) < 8:
            return "NOT SET" if not key else "***"
        return f"{key[:4]}...{key[-4:]}"
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive parts of URLs"""
        if not url:
            return "NOT SET"
        # Mask passwords in URLs
        if "@" in url:
            parts = url.split("@")
            if len(parts) == 2:
                user_pass = parts[0].split("://")[-1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    return url.replace(user_pass, f"{user}:***")
        return url

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    logger.info("Initializing settings...")
    settings = Settings()
    return settings
