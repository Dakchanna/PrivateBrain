from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────
    app_name: str = "PrivateBrain"
    app_version: str = "1.0.0"
    environment: str = "development"

    # ── Database ─────────────────────────────────────────────
    database_url: str = ""

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── AI Agent / Reasoning ─────────────────────────────────
    agent_model: str = "qwen2.5:3b"
    model_base_url: str = "http://localhost:11434"

    # ── Task-specific models ─────────────────────────────────
    object_detection_model: str = "yolov8n.pt"
    image_classification_model: str = "mobilenet_v2"
    speech_model: str = "tiny"

    # ── Security ─────────────────────────────────────────────
    api_secret: str = "change_me_to_a_strong_random_secret_at_least_32_chars"
    jwt_secret: str = "change_me_to_another_strong_random_secret"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Scheduler ────────────────────────────────────────────
    max_workers: int = 4
    request_timeout: int = 60
    max_retries: int = 2

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
