from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str
    # groq_model: str = "llama-3.3-70b-versatile"
    groq_model: str = "openai/gpt-oss-120b"

    chroma_db_path: str = "./data/chroma"
    collection_name: str = "cortex_docs"
    max_retrieval_retries: int = 2
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5

    frontend_origin: str = "http://localhost:5173"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./data/cortex.db"

    @property
    def frontend_origins(self) -> list[str]:
        """Supports a comma-separated list, e.g. for allowing both your
        local dev frontend and the deployed Vercel URL at once."""
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
