"""Runtime settings. Environment variables override the defaults."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cite:cite@localhost:5432/cite"
    ollama_base_url: str = "http://localhost:11434/v1"
    chat_model: str = "qwen2.5:7b-instruct"
    embed_model: str = "nomic-embed-text"
    embed_dim: int = 768
    session_secret: str = "dev-only-change-me"
    file_storage_dir: str = "./data/files"
    cookie_secure: bool = False
    # Hybrid cutoff. See services/retrieval.py.
    min_score: float = 0.20
    keyword_pool: int = 20
    vector_pool: int = 20
    final_k: int = 5

    @property
    def ollama_base_url_normalized(self) -> str:
        return self.ollama_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
