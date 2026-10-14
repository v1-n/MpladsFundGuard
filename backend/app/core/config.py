from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "MPLADS FundGuard API"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    CLEAN_DATA_DIR: Path = BASE_DIR / "data" / "clean"
    
    # Server / Security
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    LOG_LEVEL: str = "INFO"
    
    # Pagination
    PAGE_SIZE_DEFAULT: int = 50
    PAGE_SIZE_MAX: int = 200
    
    # App semantics
    REBUILD_COMMAND: str = "python -m src.rebuild"
    DISCLAIMER: str = (
        "Flags and ranks are screening signals for manual review. "
        "They are not evidence of fraud or wrongdoing."
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
