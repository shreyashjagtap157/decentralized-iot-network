import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PROMETHEUS_METRICS: bool = True
    
    # Blockchain Settings
    WEB3_PROVIDER_URL: str = os.getenv("WEB3_PROVIDER_URL", "http://localhost:8545")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    ORACLE_PRIVATE_KEY: str = os.getenv("ORACLE_PRIVATE_KEY", "")

settings = Settings()
