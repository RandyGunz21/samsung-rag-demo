"""Configuration management for RAG-tester service."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Service configuration
    service_name: str = "rag-tester"
    host: str = "0.0.0.0"
    port: int = 8001

    # Data storage
    data_dir: Path = Path("./data")
    datasets_dir: Path = Path("./data/test-datasets")
    results_dir: Path = Path("./data/evaluation-results")

    # Redis configuration (for Celery)
    redis_url: str = "redis://localhost:6379/0"

    # RAG Service configuration
    rag_service_url: str = "http://localhost:8000"
    rag_service_timeout: int = 30  # seconds per query

    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 3600  # 1 hour max per evaluation job

    # Evaluation defaults
    default_k_values: list[int] = [1, 3, 5, 10]
    max_queries_per_dataset: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
