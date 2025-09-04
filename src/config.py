"""Configuration settings for the distributed job scheduler."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Database Configuration
    database_url: str = "sqlite:///./job_scheduler.db"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    grpc_port: int = 50051
    
    # Worker Configuration
    worker_concurrency: int = 4
    worker_pool_size: int = 2
    
    # Job Configuration
    default_max_retries: int = 3
    default_timeout_seconds: int = 300
    job_ttl_seconds: int = 86400  # 24 hours
    
    # Queue Configuration
    queue_name: str = "job_queue"
    dead_letter_queue: str = "dead_letter_queue"
    retry_queue: str = "retry_queue"
    
    # Monitoring
    metrics_port: int = 9090
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
