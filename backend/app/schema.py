"""
schema.py - Modelos de Datos Pydantic v2 para validación, API, persistencia y telemetría.
Estructuras tipadas según ARCHITECTURE.md, CLASSIFIER_SERVICE.md y API_AND_DASHBOARD_SPEC.md.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, field_validator


# ==============================================================================
# Modelos de Ingesta y Datos Crudos
# ==============================================================================

class SocialMetrics(BaseModel):
    favorite_count: int = Field(default=0, ge=0)
    retweet_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    bookmark_count: int = Field(default=0, ge=0)


class RawPost(BaseModel):
    tweet_id: str
    post_url: Optional[str] = None
    author_name: Optional[str] = None
    author_id: Optional[str] = None
    content: str
    date: Optional[str] = None
    lang: Optional[str] = "en"
    metrics: SocialMetrics = Field(default_factory=SocialMetrics)
    media_urls: List[str] = Field(default_factory=list)
    media_type: Literal["video", "photo", "animated_gif", "none"] = "none"
    raw_source_json: Optional[Dict[str, Any]] = None

    @field_validator("tweet_id", mode="before")
    @classmethod
    def stringify_tweet_id(cls, v: Any) -> str:
        return str(v).strip()


class CleanPost(BaseModel):
    tweet_id: str
    clean_text: str
    original_content: str
    author_name: str
    author_id: Optional[str] = None
    post_url: str
    date: str
    lang: str
    metrics: SocialMetrics
    media_urls: List[str] = Field(default_factory=list)
    media_count: int = 0
    media_type: Literal["video", "photo", "animated_gif", "none"] = "none"
    detected_assets: List[str] = Field(default_factory=list)
    detected_domains: List[str] = Field(default_factory=list)
    raw_source_json: Optional[Dict[str, Any]] = None


# ==============================================================================
# Modelos de Inferencia System 1
# ==============================================================================

class SecondaryCategoryItem(BaseModel):
    id: str
    score: float = Field(ge=0.0, le=1.0)


class ClassificationResult(BaseModel):
    primary_category: str
    secondary_categories: List[SecondaryCategoryItem] = Field(default_factory=list)
    affinity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    format: str = "other"
    format_confidence: float = 0.0
    technical_depth: float = 1.0
    assets: List[str] = Field(default_factory=list)
    is_local_first: bool = False
    is_nsfw: bool = False
    is_outlier: bool = False
    status: Literal["CLASSIFIED", "PENDING", "CLASSIFIED_MANUAL", "DISCARDED"] = "CLASSIFIED"
    engine_used: str = "laya"
    inference_latency_ms: float = 0.0
    raw_answers: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# Modelos para Análisis Interactivo Individual
# ==============================================================================

class AnalyzePostRequest(BaseModel):
    text: str = Field(min_length=1, description="Texto o contenido del post")
    id: Optional[str] = Field(default=None, description="Identificador del tweet (opcional)")
    author: Optional[str] = Field(default="dev_user", description="Autor del post")
    likes: Optional[int] = Field(default=0)
    retweets: Optional[int] = Field(default=0)
    media_urls: Optional[List[str]] = Field(default_factory=list)
    media_type: Optional[str] = Field(default="none")
    date: Optional[str] = Field(default=None, description="Fecha de publicación original")
    post_url: Optional[str] = Field(default=None, description="URL del tweet original")
    persist: bool = Field(default=False, description="Si es True, se inserta en SQLite WAL")
    active_questions: Optional[List[str]] = Field(
        default=None,
        description="Lista opcional de IDs de preguntas tipadas para evaluar (None usa el conjunto activo por defecto)"
    )

    @field_validator("text", mode="before")
    @classmethod
    def sanitize_text(cls, v: Any) -> str:
        s = str(v) if v is not None else ""
        s = s.strip()
        return s if len(s) > 0 else "[Sin contenido textual]"


class AnalyzePostResponse(BaseModel):
    tweet_id: str
    content: str
    author_name: str
    primary_category: str
    category_label: str
    family_id: str
    color_hex: str
    code: str
    affinity_score: float
    secondary_categories: List[SecondaryCategoryItem] = Field(default_factory=list)
    format: str
    format_confidence: float
    technical_depth: float
    is_tool_or_code_release: bool = False
    is_local_first: bool = False
    is_nsfw: bool = False
    is_outlier: bool = False
    assets: List[str] = Field(default_factory=list)
    status: str
    engine_used: str
    inference_latency_ms: float
    raw_answers: Dict[str, Any] = Field(default_factory=dict)
    raw_json: Optional[Dict[str, Any]] = None
    classification_json: Optional[Dict[str, Any]] = None
    taxonomy_version: Optional[str] = "2.1.0"
    reclassification_count: int = 0
    persisted: bool = False


class PostIdsResponse(BaseModel):
    total: int = Field(description="Cantidad total de publicaciones registradas en base de datos")
    tweet_ids: List[str] = Field(description="Lista completa de tweet_ids indexados")


class AnalyzeBatchRequest(BaseModel):
    posts: List[AnalyzePostRequest] = Field(min_length=1, description="Lista de publicaciones para clasificar en lote")
    persist: bool = Field(default=True, description="Si es True, se persisten en SQLite WAL")
    duplicate_strategy: Literal["skip", "reclassify"] = Field(
        default="skip",
        description="Estrategia ante posts existentes: 'skip' (solo actualiza métricas) o 'reclassify' (archiva historial y reclasifica)"
    )
    max_new_posts: Optional[int] = Field(
        default=None,
        description="Si se especifica y duplicate_strategy='skip', procesa como máximo N posts nuevos deteniendo el lote"
    )
    active_questions: Optional[List[str]] = Field(
        default=None,
        description="Lista opcional de IDs de preguntas tipadas para evaluar en todo el lote"
    )


class BatchStreamItem(BaseModel):
    event: Literal["item_completed", "batch_completed", "error"] = "item_completed"
    index: int
    total: int
    post: Optional[AnalyzePostResponse] = None
    telemetry: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==============================================================================
# Modelos de Persistencia y Representación de Post
# ==============================================================================

class PostResponse(BaseModel):
    tweet_id: str
    post_url: str
    author_name: str
    author_id: Optional[str] = None
    content: str
    preview_text: Optional[str] = None
    date: str
    metrics: SocialMetrics
    media_urls: List[str] = Field(default_factory=list)
    media_count: int = 0
    media_type: str = "none"
    lang: str = "en"
    primary_category: str
    secondary_categories: List[SecondaryCategoryItem] = Field(default_factory=list)
    affinity_score: float = 0.0
    format: Optional[str] = "other"
    format_confidence: float = 0.0
    technical_depth: float = 1.0
    assets: List[str] = Field(default_factory=list)
    is_local_first: bool = False
    is_nsfw: bool = False
    is_outlier: bool = False
    status: str
    engine_used: str = "laya"
    inference_latency_ms: float = 0.0
    raw_json: Optional[Dict[str, Any]] = None
    classification_json: Optional[Dict[str, Any]] = None
    taxonomy_version: Optional[str] = "2.1.0"
    reclassification_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PostListResponse(BaseModel):
    total: int
    page: int
    limit: int
    posts: List[PostResponse]


# ==============================================================================
# Modelos de Historial de Clasificación y Comparativa A/B (Fase 5.12)
# ==============================================================================

class ClassificationHistoryItem(BaseModel):
    id: int
    tweet_id: str
    version_number: int
    taxonomy_version: str
    primary_category: str
    secondary_categories: List[SecondaryCategoryItem] = Field(default_factory=list)
    affinity_score: float = 0.0
    format: Optional[str] = None
    technical_depth: float = 1.0
    assets: List[str] = Field(default_factory=list)
    raw_answers: Optional[Dict[str, Any]] = None
    classification_json: Optional[Dict[str, Any]] = None
    trigger_type: str
    reason: Optional[str] = None
    status: str = "ARCHIVED"
    created_at: str


class PostHistoryResponse(BaseModel):
    tweet_id: str
    total_versions: int
    history: List[ClassificationHistoryItem]


class RollbackClassificationResponse(BaseModel):
    status: str
    tweet_id: str
    restored_history_id: int
    restored_version: int
    primary_category: str
    post: Optional[PostResponse] = None


class ReclassifyRequest(BaseModel):
    dry_run: bool = Field(
        default=True,
        description="Si es True, solo ejecuta la inferencia y retorna la comparativa A/B sin modificar la base de datos."
    )
    confirm: bool = Field(
        default=False,
        description="Si es True, archiva la versión anterior en historial y actualiza el post en SQLite."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Motivo o comentario analítico de la reclasificación."
    )


class PostComparisonResponse(BaseModel):
    tweet_id: str
    has_changed: bool
    delta_affinity: float
    previous: Dict[str, Any]
    current: Dict[str, Any]


class PostFilterParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=1000)
    family: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_outlier: Optional[bool] = None
    lang: Optional[str] = None
    search: Optional[str] = None
    sort_by: Literal["date_desc", "score_desc", "likes_desc"] = "date_desc"


# ==============================================================================
# Modelos de Dashboard y Visualización (Waffle & Scatter)
# ==============================================================================

class ScatterPoint(BaseModel):
    id: str
    x: float                     # affinity_score * 100 (0 a 100)
    y: int                       # favorite_count
    primary: str                 # primary_category
    secondary: Optional[str] = None
    outlier: bool = False
    author: str
    date: str


class CategoryDistributionItem(BaseModel):
    id: str
    name: str
    family_id: str
    color_hex: str
    count: int
    avg_score: float
    avg_likes: int


class FamilyDistributionItem(BaseModel):
    id: str
    name: str
    color_hex: str
    count: int


class DashboardStatsResponse(BaseModel):
    total_posts: int
    classified_count: int
    pending_count: int
    outliers_count: int
    avg_affinity_score: float
    avg_likes: float
    categories_distribution: List[CategoryDistributionItem]
    families_distribution: List[FamilyDistributionItem]
    scatter_points: List[ScatterPoint]


# ==============================================================================
# Modelos de Ingesta, Lotes y Telemetría SSE
# ==============================================================================

class IngestResponse(BaseModel):
    batch_id: str
    total_posts_in_file: int
    new_posts_queued: int
    reclassified_posts_queued: int = 0
    existing_posts_updated: int
    unchanged_posts_skipped: int
    estimated_time_seconds: float



class BatchCheckpointRecord(BaseModel):
    batch_id: str
    file_name: str
    total_items: int
    processed_items: int
    updated_metrics_items: int
    failed_items: int
    last_processed_tweet_id: Optional[str] = None
    status: Literal["PENDING", "RUNNING", "PAUSED", "COMPLETED", "FAILED"]
    checkpoint_interval: int = 25
    avg_latency_ms: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BatchTelemetry(BaseModel):
    batch_id: str
    status: str
    processed: int
    total: int
    percentage: float
    speed_tps: float
    avg_latency_ms: float
    cpu_percent: float
    ram_mb: float
    eta_seconds: float


class PendingOverrideRequest(BaseModel):
    primary_category: str
    secondary_categories: List[str] = Field(default_factory=list)
    status: Literal["CLASSIFIED_MANUAL", "DISCARDED"] = "CLASSIFIED_MANUAL"


class SystemHealthResponse(BaseModel):
    status: str
    device: str
    cpu_model: str
    ram_total_gb: float
    ram_available_gb: float
    ram_used_process_mb: float
    models_loaded: List[str]
    active_batches: int
    version: str


# ==============================================================================
# Modelos de Gestión y Configuración de Base de Datos (Fase 5.13)
# ==============================================================================

class DatabaseStatsResponse(BaseModel):
    status: str = "HEALTHY"
    posts_count: int
    history_count: int
    checkpoints_count: int
    feedback_count: int
    db_size_bytes: int
    db_size_formatted: str
    wal_size_bytes: int
    wal_size_formatted: str
    sqlite_version: str
    journal_mode: str
    taxonomy_version: str
    database_file: str


class DatabaseResetRequest(BaseModel):
    clear_posts: bool = True
    clear_history: bool = True
    clear_checkpoints: bool = True
    clear_feedback: bool = False
    vacuum: bool = True


class DatabaseResetResponse(BaseModel):
    status: str = "SUCCESS"
    message: str
    deleted_posts: int
    deleted_history: int
    deleted_checkpoints: int
    deleted_feedback: int
    new_db_size_formatted: str


class DatabaseImportRequest(BaseModel):
    backup: Dict[str, Any]
    mode: Literal["merge", "replace"] = "merge"


class DatabaseImportResponse(BaseModel):
    status: str = "SUCCESS"
    message: str
    imported_posts: int
    imported_history: int
    imported_feedback: int


class DatabaseOptimizeResponse(BaseModel):
    status: str = "SUCCESS"
    message: str
    initial_size_formatted: str
    final_size_formatted: str
    bytes_reclaimed: int
