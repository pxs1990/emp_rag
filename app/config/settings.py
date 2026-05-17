from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DB_URL: str

    # LLM
    MODEL_PATH: str = "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    LLM_THREADS: int = 4

    # Embedding
    EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Documents
    TEMPLATE_PATH: str = "templates/template_answer.docx"
    OUTPUT_DIR: str = "output"

    class Config:
        env_file = ".env"


settings = Settings()
