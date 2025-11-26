import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # API Keys
    mistral_api_key: str = Field(..., env='MISTRAL_API_KEY')
    
    # LangSmith Configuration (optional)
    langsmith_tracing: bool = Field(default=False, env='LANGSMITH_TRACING')
    langsmith_endpoint: Optional[str] = Field(default=None, env='LANGSMITH_ENDPOINT')
    langsmith_api_key: Optional[str] = Field(default=None, env='LANGSMITH_API_KEY')
    langsmith_project: Optional[str] = Field(default=None, env='LANGSMITH_PROJECT')
    
    # Model Configuration
    mistral_model: str = Field(default="mistral-large-latest", env='MISTRAL_MODEL')
    temperature: float = Field(default=0.1, env='TEMPERATURE')  # Low temperature for medical accuracy
    max_tokens: int = Field(default=4096, env='MAX_TOKENS')
    
    # Retry Configuration
    max_retries: int = Field(default=3, env='MAX_RETRIES')
    retry_delay: float = Field(default=1.0, env='RETRY_DELAY')
    
    # Timeout Configuration
    api_timeout: int = Field(default=60, env='API_TIMEOUT')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Global settings instance
def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
