import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    
    # Security - No hardcoded defaults for secrets
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Monitoring
    PROMETHEUS_METRICS: bool = True
    
    # Blockchain Settings
    WEB3_PROVIDER_URL: str = os.getenv("WEB3_PROVIDER_URL", "http://localhost:8545")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    ORACLE_PRIVATE_KEY: str = os.getenv("ORACLE_PRIVATE_KEY", "")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v, info):
        if not v and os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("SECRET_KEY must be set in production environment")
        if not v:
            # Generate a warning-worthy default for development only
            import secrets
            return secrets.token_urlsafe(32)
        return v

settings = Settings()

