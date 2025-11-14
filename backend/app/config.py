from pydantic_settings import BaseSettings
from functools import lru_cache

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
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
