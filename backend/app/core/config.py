from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    DATABASE_URL: str = "sqlite:///./radar_lab.db"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    SEARXNG_BASE_URL: str = "http://localhost:8080"
    MAX_QUERIES_PER_RESEARCH: int = 10
    MAX_SOURCES_PER_RESEARCH: int = 30
    LOG_LEVEL: str = "INFO"
settings = Settings()