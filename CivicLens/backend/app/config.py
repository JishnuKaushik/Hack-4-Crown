from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite:///./civiclens.db"

    upload_dir: Path = Path("./uploads")
    max_upload_mb: int = 5
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    ai_enabled: bool = True
    dup_similarity_threshold: float = 0.86
    dup_radius_meters: float = 100
    dup_time_window_days: int = 30

    debug: bool = False
    environment: str = "development"

    @field_validator("secret_key")
    @classmethod
    def secret_key_not_placeholder(cls, v: str) -> str:
        if v.strip().lower() in {"replace_me_with_generated_random_string", "secret", "changeme", ""}:
            raise ValueError("SECRET_KEY is missing or a placeholder — generate a real one, see .env.example")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_image_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_image_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
