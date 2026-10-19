"""
config.py - Configuración centralizada del sistema para twitter_post_classifier_master.
Basado en CONFIG.md (v2.1.0) y especificaciones System 1.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    # Metadatos del Sistema
    APP_NAME: str = "Twitter Post Classifier Master"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Rutas del Sistema de Archivos
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DATABASE_PATH: Path = BASE_DIR / "data" / "database.sqlite"
    CATEGORIES_PATH: Path = BASE_DIR / "data" / "categories.json"
    FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"

    # Base de Datos (SQLite WAL)
    SQLITE_WAL_MODE: bool = True
    SQLITE_SYNCHRONOUS: str = "NORMAL"
    SQLITE_BUSY_TIMEOUT_MS: int = 5000
    SQLITE_CACHE_SIZE: int = -64000  # ~64MB cache

    # Ingesta y Batch Runner
    CHECKPOINT_INTERVAL: int = 25
    STREAM_CHUNK_SIZE: int = 100
    MAX_BATCH_WORKERS: int = 1
    YIELD_SLEEP_SECONDS: float = 0.005  # 5ms de desahogo para Event Loop FastAPI
    BATCH_YIELD_SECONDS: float = 0.015  # 15ms de desahogo térmico entre inferencias de lotes

    # Taxonomía y Umbrales System 1 (Motor Dual Jev / Laya)
    DECISION_ENGINE: str = "laya"  # 'laya' (local CPU/GPU) o 'jev' (TypeSafe Cloud API)
    JEV_API_KEY: Optional[str] = None
    JEV_BASE_URL: str = "https://api.jev.dev"
    ENABLE_DETERMINISTIC_OVERRIDES: bool = True
    LAYA_THRESHOLD: float = 0.85
    LAYA_MIN_ABSTAIN: float = 0.70
    JEV_THRESHOLD: float = 0.75
    JEV_MIN_ABSTAIN: float = 0.55
    DEFAULT_THRESHOLD: float = 0.75
    MIN_CONFIDENCE_ABSTAIN: float = 0.55
    MIN_THRESHOLD_FOR_PRIMARY: float = 0.70
    MAX_LABELS_PER_POST: int = 4
    SUPPORTED_LANGUAGES: List[str] = Field(default_factory=lambda: ["en", "ja", "es", "zh", "ko"])

    # Hardware e Inferencia (Autodetección inteligente CPU/GPU: 'auto', 'cuda', 'mps' o 'cpu')
    DEVICE: str = "auto"
    PYTORCH_NUM_THREADS: int = 3
    PYTORCH_INTEROP_THREADS: int = 2
    MAX_LOADED_MODELS: int = 2
    PRIMARY_MODEL: str = "convaiinnovations/laya"
    MULTILINGUAL_MODEL: str = "convaiinnovations/laya-multilingual"

    # Red y Servidor Web
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instancia singleton de configuración
settings = Settings()
