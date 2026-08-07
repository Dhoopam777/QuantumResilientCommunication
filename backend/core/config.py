"""
Configuration Management for Quantum-Resilient Communication System

This module handles application configuration using Pydantic Settings.
All settings are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Project Information
    PROJECT_NAME: str = "Quantum-Resilient Communication System"
    API_VERSION: str = "v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-use-openssl-rand-hex-32"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/quantum_resilient_db"
    
    # JWT Token Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI/LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Optional Settings
    CHROMA_DIRECTORY: str = "chroma_db"
    TOP_K: int = 2

    # Attachment Security
    ATTACHMENT_STORAGE_PATH: str = "./storage/attachments"
    ATTACHMENT_MAX_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ATTACHMENT_MAX_FILENAME_LENGTH: int = 255
    ATTACHMENT_MAX_METADATA_LENGTH: int = 256
    ATTACHMENT_UPLOAD_RATE_LIMIT: int = 10  # uploads per minute per user
    ATTACHMENT_MAX_CONCURRENT_UPLOADS: int = 3
    ATTACHMENT_THUMBNAIL_WIDTH: int = 200
    ATTACHMENT_THUMBNAIL_HEIGHT: int = 200

    # Message Edit Security
    MESSAGE_EDIT_RATE_LIMIT: int = 30  # edits per minute per user

    # Message Delete Security
    MESSAGE_DELETE_RATE_LIMIT: int = 30  # deletes per minute per user
    MESSAGE_REACTION_RATE_LIMIT: int = 60  # reaction mutations per minute per user
    CONVERSATION_REQUESTS_PER_DAY: int = 20


# Create a singleton settings instance
settings = Settings()


# Export for easy importing
__all__ = ["settings", "Settings"]