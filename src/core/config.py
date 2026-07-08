from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    db_user: str
    db_password: str
    db_name: str
    db_port: int = 5432

    # Application
    app_port: int = 8000

    # API Keys
    anthropic_api_key: str
    voyage_api_key: str

    # RAG Parameters
    chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_top_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
