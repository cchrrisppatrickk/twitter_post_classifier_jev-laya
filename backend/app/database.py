"""
database.py - Conexión asíncrona SQLite en modo WAL y esquemas DDL.
Optimizado para alto rendimiento local, transacciones seguras y soporte multi-hilo.
"""

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import aiosqlite

from .config import settings

logger = logging.getLogger("database")
logging.basicConfig(level=logging.INFO)

# DDL de Tablas Principales
DDL_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    tweet_id TEXT PRIMARY KEY,
    post_url TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_id TEXT,
    content TEXT NOT NULL,
    preview_text TEXT,
    date TEXT NOT NULL,
    favorite_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    bookmark_count INTEGER DEFAULT 0,
    media_urls TEXT,                    -- JSON array: ["https://..."]
    media_count INTEGER DEFAULT 0,
    media_type TEXT DEFAULT 'none',     -- 'video', 'photo', 'none'
    lang TEXT DEFAULT 'en',
    
    -- Clasificación System 1 (Laya / Jev)
    primary_category TEXT NOT NULL,
    secondary_categories TEXT,          -- JSON array con scores o ids
    affinity_score REAL DEFAULT 0.0,
    format TEXT,
    format_confidence REAL DEFAULT 0.0,
    technical_depth REAL DEFAULT 1.0,
    assets TEXT,                        -- JSON array: ["github_repo", ...]
    is_local_first INTEGER DEFAULT 0,
    is_nsfw INTEGER DEFAULT 0,
    is_outlier INTEGER DEFAULT 0,
    
    -- Control de Ciclo de Vida y Auditoría
    status TEXT NOT NULL,               -- 'CLASSIFIED', 'PENDING', 'CLASSIFIED_MANUAL', 'DISCARDED'
    engine_used TEXT DEFAULT 'laya',
    inference_latency_ms REAL DEFAULT 0.0,

    -- Persistencia Dual JSON y Versionado Taxonómico (Subfase 5.12.1)
    raw_json TEXT,                      -- JSON original completo del post / scraper
    classification_json TEXT,           -- JSON completo de inferencia generado por Laya
    taxonomy_version TEXT DEFAULT '2.1.0',
    reclassification_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_posts_primary ON posts(primary_category);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date DESC);
CREATE INDEX IF NOT EXISTS idx_posts_affinity ON posts(affinity_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_lang ON posts(lang);
CREATE INDEX IF NOT EXISTS idx_posts_outlier ON posts(is_outlier);
CREATE INDEX IF NOT EXISTS idx_posts_likes ON posts(favorite_count DESC);
"""

DDL_BATCH_CHECKPOINTS = """
CREATE TABLE IF NOT EXISTS batch_checkpoints (
    batch_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    total_items INTEGER NOT NULL,
    processed_items INTEGER DEFAULT 0,
    updated_metrics_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    last_processed_tweet_id TEXT,
    status TEXT NOT NULL,               -- 'PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED'
    checkpoint_interval INTEGER DEFAULT 25,
    avg_latency_ms REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_TAXONOMY_FEEDBACK = """
CREATE TABLE IF NOT EXISTS taxonomy_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    original_content TEXT NOT NULL,
    laya_suggested_category TEXT,
    laya_confidence REAL,
    resolved_category TEXT NOT NULL,
    resolved_by TEXT NOT NULL,          -- 'manual_user' o 'llm_fallback'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_POST_CLASSIFICATION_HISTORY = """
CREATE TABLE IF NOT EXISTS post_classification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    taxonomy_version TEXT NOT NULL,
    primary_category TEXT NOT NULL,
    secondary_categories TEXT,
    affinity_score REAL DEFAULT 0.0,
    format TEXT,
    technical_depth REAL DEFAULT 1.0,
    assets TEXT,
    raw_answers TEXT,
    classification_json TEXT NOT NULL,
    trigger_type TEXT NOT NULL,          -- 'initial_ingest', 'bulk_reclassify', 'manual_reclassify', 'manual_override', 'pre_rollback'
    reason TEXT,
    status TEXT DEFAULT 'ARCHIVED',      -- 'ARCHIVED', 'ACTIVE_SUPERSEDED', 'ROLLED_BACK'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tweet_id) REFERENCES posts(tweet_id) ON DELETE CASCADE
);
"""

DDL_HISTORY_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_history_tweet ON post_classification_history(tweet_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON post_classification_history(created_at DESC);
"""

DEFAULT_POST_VALUES: Dict[str, Any] = {
    "tweet_id": "",
    "post_url": "",
    "author_name": "unknown",
    "author_id": None,
    "content": "",
    "preview_text": None,
    "date": "",
    "favorite_count": 0,
    "retweet_count": 0,
    "reply_count": 0,
    "bookmark_count": 0,
    "media_urls": "[]",
    "media_count": 0,
    "media_type": "none",
    "lang": "en",
    "primary_category": "otros",
    "secondary_categories": "[]",
    "affinity_score": 0.0,
    "format": "other",
    "format_confidence": 0.0,
    "technical_depth": 1.0,
    "assets": "[]",
    "is_local_first": 0,
    "is_nsfw": 0,
    "is_outlier": 0,
    "status": "CLASSIFIED",
    "engine_used": "laya",
    "inference_latency_ms": 0.0,
    "raw_json": None,
    "classification_json": None,
    "taxonomy_version": "2.1.0",
    "reclassification_count": 0,
}



async def get_connection() -> aiosqlite.Connection:
    """
    Crea una conexión asíncrona a la base de datos SQLite
    aplicando los PRAGMAs óptimos para modo WAL y concurrencia.
    """
    db_path = settings.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row

    # PRAGMAs de rendimiento SQLite
    if settings.SQLITE_WAL_MODE:
        await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute(f"PRAGMA synchronous = {settings.SQLITE_SYNCHRONOUS};")
    await db.execute(f"PRAGMA busy_timeout = {settings.SQLITE_BUSY_TIMEOUT_MS};")
    await db.execute(f"PRAGMA cache_size = {settings.SQLITE_CACHE_SIZE};")
    await db.execute("PRAGMA foreign_keys = ON;")

    return db


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Generador contextual asíncrono para 'async with get_db() as db:' en workers y servicios."""
    conn = await get_connection()
    try:
        yield conn
    finally:
        await conn.close()


async def get_db_session() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Generador asíncrono para inyección de dependencias en FastAPI (Depends(get_db_session))."""
    async with get_db() as conn:
        yield conn


async def init_db() -> None:
    """Inicializa la base de datos, ejecuta DDL, migraciones automáticas y verifica modo WAL."""
    logger.info(f"Inicializando SQLite WAL en {settings.DATABASE_PATH}...")
    async with get_db() as db:
        await db.execute(DDL_POSTS_TABLE)
        for idx_query in DDL_INDEXES.strip().split(";"):
            if idx_query.strip():
                await db.execute(idx_query)
        await db.execute(DDL_BATCH_CHECKPOINTS)
        await db.execute(DDL_TAXONOMY_FEEDBACK)
        await db.execute(DDL_POST_CLASSIFICATION_HISTORY)
        for idx_query in DDL_HISTORY_INDEXES.strip().split(";"):
            if idx_query.strip():
                await db.execute(idx_query)

        # Migración automática de columnas para tablas ya creadas (idempotente)
        async with db.execute("PRAGMA table_info(posts);") as cursor:
            columns_info = await cursor.fetchall()
            existing_cols = {row["name"] for row in columns_info}

        if "raw_json" not in existing_cols:
            await db.execute("ALTER TABLE posts ADD COLUMN raw_json TEXT;")
            logger.info("Migración SQLite: columna 'raw_json' añadida a 'posts'.")
        if "classification_json" not in existing_cols:
            await db.execute("ALTER TABLE posts ADD COLUMN classification_json TEXT;")
            logger.info("Migración SQLite: columna 'classification_json' añadida a 'posts'.")
        if "taxonomy_version" not in existing_cols:
            await db.execute("ALTER TABLE posts ADD COLUMN taxonomy_version TEXT DEFAULT '2.1.0';")
            logger.info("Migración SQLite: columna 'taxonomy_version' añadida a 'posts'.")
        if "reclassification_count" not in existing_cols:
            await db.execute("ALTER TABLE posts ADD COLUMN reclassification_count INTEGER DEFAULT 0;")
            logger.info("Migración SQLite: columna 'reclassification_count' añadida a 'posts'.")

        await db.commit()

        # Verificar modo WAL
        async with db.execute("PRAGMA journal_mode;") as cursor:
            row = await cursor.fetchone()
            current_mode = row[0] if row else "unknown"
            logger.info(f"SQLite modo de diario actual: {current_mode.upper()}")


# ==============================================================================
# Operaciones CRUD Especializadas
# ==============================================================================

async def find_post_by_id(db: aiosqlite.Connection, tweet_id: str) -> Optional[Dict[str, Any]]:
    """Busca un post por su tweet_id canónico deserializando campos JSON."""
    query = "SELECT * FROM posts WHERE tweet_id = ? LIMIT 1;"
    async with db.execute(query, (str(tweet_id),)) as cursor:
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            # Deserializar campos JSON
            if data.get("media_urls"):
                try:
                    data["media_urls"] = json.loads(data["media_urls"])
                except Exception:
                    data["media_urls"] = []
            if data.get("secondary_categories"):
                try:
                    data["secondary_categories"] = json.loads(data["secondary_categories"])
                except Exception:
                    data["secondary_categories"] = []
            if data.get("assets"):
                try:
                    data["assets"] = json.loads(data["assets"])
                except Exception:
                    data["assets"] = []
            if data.get("raw_json"):
                try:
                    data["raw_json"] = json.loads(data["raw_json"])
                except Exception:
                    pass
            if data.get("classification_json"):
                try:
                    data["classification_json"] = json.loads(data["classification_json"])
                except Exception:
                    pass
            return data
    return None


async def update_social_metrics(
    db: aiosqlite.Connection,
    tweet_id: str,
    favorite_count: int,
    retweet_count: int,
    reply_count: int,
    bookmark_count: int
) -> bool:
    """
    Ruta rápida de deduplicación (ADR-005): actualiza únicamente las métricas sociales
    y fecha de actualización, sin consumir CPU del motor System 1.
    """
    query = """
    UPDATE posts
    SET favorite_count = ?,
        retweet_count = ?,
        reply_count = ?,
        bookmark_count = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE tweet_id = ?;
    """
    cursor = await db.execute(
        query,
        (favorite_count, retweet_count, reply_count, bookmark_count, str(tweet_id))
    )
    return cursor.rowcount > 0


async def insert_or_replace_post(db: aiosqlite.Connection, post: Dict[str, Any]) -> None:
    """Inserta o reemplaza una publicación completamente clasificada asegurando defaults y persistencia JSON."""
    query = """
    INSERT INTO posts (
        tweet_id, post_url, author_name, author_id, content, preview_text,
        date, favorite_count, retweet_count, reply_count, bookmark_count,
        media_urls, media_count, media_type, lang,
        primary_category, secondary_categories, affinity_score, format,
        format_confidence, technical_depth, assets, is_local_first,
        is_nsfw, is_outlier, status, engine_used, inference_latency_ms,
        raw_json, classification_json, taxonomy_version, reclassification_count,
        created_at, updated_at
    ) VALUES (
        :tweet_id, :post_url, :author_name, :author_id, :content, :preview_text,
        :date, :favorite_count, :retweet_count, :reply_count, :bookmark_count,
        :media_urls, :media_count, :media_type, :lang,
        :primary_category, :secondary_categories, :affinity_score, :format,
        :format_confidence, :technical_depth, :assets, :is_local_first,
        :is_nsfw, :is_outlier, :status, :engine_used, :inference_latency_ms,
        :raw_json, :classification_json, :taxonomy_version, :reclassification_count,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
    ON CONFLICT(tweet_id) DO UPDATE SET
        post_url = excluded.post_url,
        author_name = excluded.author_name,
        author_id = excluded.author_id,
        content = excluded.content,
        preview_text = excluded.preview_text,
        date = excluded.date,
        favorite_count = excluded.favorite_count,
        retweet_count = excluded.retweet_count,
        reply_count = excluded.reply_count,
        bookmark_count = excluded.bookmark_count,
        media_urls = excluded.media_urls,
        media_count = excluded.media_count,
        media_type = excluded.media_type,
        lang = excluded.lang,
        primary_category = excluded.primary_category,
        secondary_categories = excluded.secondary_categories,
        affinity_score = excluded.affinity_score,
        format = excluded.format,
        format_confidence = excluded.format_confidence,
        technical_depth = excluded.technical_depth,
        assets = excluded.assets,
        is_local_first = excluded.is_local_first,
        is_nsfw = excluded.is_nsfw,
        is_outlier = excluded.is_outlier,
        status = excluded.status,
        engine_used = excluded.engine_used,
        inference_latency_ms = excluded.inference_latency_ms,
        raw_json = COALESCE(excluded.raw_json, posts.raw_json),
        classification_json = COALESCE(excluded.classification_json, posts.classification_json),
        taxonomy_version = excluded.taxonomy_version,
        reclassification_count = excluded.reclassification_count,
        updated_at = CURRENT_TIMESTAMP;
    """
    payload = dict(DEFAULT_POST_VALUES)
    payload.update(post)

    # Autogenerar preview_text si no fue provisto
    if not payload.get("preview_text") and payload.get("content"):
        content = str(payload["content"])
        payload["preview_text"] = content[:120] + ("..." if len(content) > 120 else "")

    # Serializar JSON fields
    if isinstance(payload.get("media_urls"), (list, dict)):
        payload["media_urls"] = json.dumps(payload["media_urls"], ensure_ascii=False)
    if isinstance(payload.get("secondary_categories"), (list, dict)):
        payload["secondary_categories"] = json.dumps(payload["secondary_categories"], ensure_ascii=False)
    if isinstance(payload.get("assets"), (list, dict)):
        payload["assets"] = json.dumps(payload["assets"], ensure_ascii=False)
    if isinstance(payload.get("raw_json"), (list, dict)):
        payload["raw_json"] = json.dumps(payload["raw_json"], ensure_ascii=False)
    if isinstance(payload.get("classification_json"), (list, dict)):
        payload["classification_json"] = json.dumps(payload["classification_json"], ensure_ascii=False)

    await db.execute(query, payload)


async def resolve_pending_post(
    db: aiosqlite.Connection,
    tweet_id: str,
    primary_category: str,
    secondary_categories: List[str],
    resolved_by: str = "manual_user"
) -> bool:
    """
    Resuelve un post en estado PENDING:
    - Archiva la versión previa en historial
    - Actualiza posts -> CLASSIFIED_MANUAL, primary_category, secondary_categories
    - Registra el desempate en taxonomy_feedback para aprendizaje activo
    """
    post = await find_post_by_id(db, tweet_id)
    if not post:
        return False

    # Archivar en historial antes de modificar
    await archive_classification_history(
        db,
        tweet_id=tweet_id,
        trigger_type="manual_override",
        reason=f"Resolución manual hacia '{primary_category}' por {resolved_by}"
    )

    update_query = """
    UPDATE posts
    SET primary_category = ?,
        secondary_categories = ?,
        status = 'CLASSIFIED_MANUAL',
        affinity_score = 1.0,
        updated_at = CURRENT_TIMESTAMP
    WHERE tweet_id = ?;
    """
    await db.execute(
        update_query,
        (primary_category, json.dumps(secondary_categories, ensure_ascii=False), str(tweet_id))
    )

    feedback_query = """
    INSERT INTO taxonomy_feedback (
        tweet_id, original_content, laya_suggested_category,
        laya_confidence, resolved_category, resolved_by
    ) VALUES (?, ?, ?, ?, ?, ?);
    """
    await db.execute(
        feedback_query,
        (
            str(tweet_id),
            post.get("content", ""),
            post.get("primary_category", "otros"),
            post.get("affinity_score", 0.0),
            primary_category,
            resolved_by
        )
    )
    await db.commit()
    return True


# ==============================================================================
# Operaciones de Historial de Clasificación y Versionado (Fase 5.12)
# ==============================================================================

async def archive_classification_history(
    db: aiosqlite.Connection,
    tweet_id: Optional[str] = None,
    trigger_type: str = "manual_reclassify",
    reason: Optional[str] = None,
    existing_post: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> Optional[int]:
    """
    Archiva el estado de clasificación actual de un post en 'post_classification_history'
    antes de aplicar una nueva clasificación o reclasificación.
    Soporta pasar tweet_id o directly existing_post (dict).
    Retorna el ID del registro de historial creado o None si el post no existía.
    """
    post = existing_post
    if not post and tweet_id:
        post = await find_post_by_id(db, tweet_id)
    if not post:
        return None

    actual_tweet_id = str(tweet_id or post.get("tweet_id"))
    final_reason = reason or notes or f"Archivado previo a nueva clasificación ({trigger_type})"

    # Determinar el siguiente número de versión para este tweet_id
    count_query = "SELECT COUNT(*) FROM post_classification_history WHERE tweet_id = ?;"
    async with db.execute(count_query, (actual_tweet_id,)) as cursor:
        row = await cursor.fetchone()
        version_number = (row[0] if row else 0) + 1

    # Preparar el JSON de clasificación a archivar
    class_json = post.get("classification_json")
    if not class_json:
        class_json = {
            "tweet_id": post.get("tweet_id"),
            "primary_category": post.get("primary_category"),
            "secondary_categories": post.get("secondary_categories", []),
            "affinity_score": post.get("affinity_score", 0.0),
            "format": post.get("format"),
            "format_confidence": post.get("format_confidence", 0.0),
            "technical_depth": post.get("technical_depth", 1.0),
            "assets": post.get("assets", []),
            "is_local_first": bool(post.get("is_local_first")),
            "is_nsfw": bool(post.get("is_nsfw")),
            "is_outlier": bool(post.get("is_outlier")),
            "status": post.get("status"),
            "engine_used": post.get("engine_used"),
            "inference_latency_ms": post.get("inference_latency_ms")
        }

    raw_answers = class_json.get("raw_answers") if isinstance(class_json, dict) else None

    history_query = """
    INSERT INTO post_classification_history (
        tweet_id, version_number, taxonomy_version, primary_category,
        secondary_categories, affinity_score, format, technical_depth,
        assets, raw_answers, classification_json, trigger_type, reason, status
    ) VALUES (
        :tweet_id, :version_number, :taxonomy_version, :primary_category,
        :secondary_categories, :affinity_score, :format, :technical_depth,
        :assets, :raw_answers, :classification_json, :trigger_type, :reason, 'ARCHIVED'
    );
    """
    params = {
        "tweet_id": actual_tweet_id,
        "version_number": version_number,
        "taxonomy_version": post.get("taxonomy_version") or settings.APP_VERSION,
        "primary_category": post.get("primary_category", "otros"),
        "secondary_categories": json.dumps(post.get("secondary_categories", []), ensure_ascii=False),
        "affinity_score": float(post.get("affinity_score") or 0.0),
        "format": post.get("format"),
        "technical_depth": float(post.get("technical_depth") or 1.0),
        "assets": json.dumps(post.get("assets", []), ensure_ascii=False),
        "raw_answers": json.dumps(raw_answers, ensure_ascii=False) if raw_answers else None,
        "classification_json": json.dumps(class_json, ensure_ascii=False) if isinstance(class_json, (dict, list)) else str(class_json),
        "trigger_type": trigger_type,
        "reason": final_reason
    }
    cursor = await db.execute(history_query, params)
    history_id = cursor.lastrowid

    # Actualizar contador de reclasificaciones en el post activo
    await db.execute(
        "UPDATE posts SET reclassification_count = reclassification_count + 1 WHERE tweet_id = ?;",
        (actual_tweet_id,)
    )
    return history_id



async def get_post_history(db: aiosqlite.Connection, tweet_id: str) -> List[Dict[str, Any]]:
    """Obtiene el historial cronológico completo de clasificaciones para un post."""
    query = """
    SELECT * FROM post_classification_history
    WHERE tweet_id = ?
    ORDER BY version_number DESC, created_at DESC;
    """
    history_items: List[Dict[str, Any]] = []
    async with db.execute(query, (str(tweet_id),)) as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            item = dict(r)
            if item.get("secondary_categories"):
                try:
                    item["secondary_categories"] = json.loads(item["secondary_categories"])
                except Exception:
                    item["secondary_categories"] = []
            if item.get("assets"):
                try:
                    item["assets"] = json.loads(item["assets"])
                except Exception:
                    item["assets"] = []
            if item.get("raw_answers"):
                try:
                    item["raw_answers"] = json.loads(item["raw_answers"])
                except Exception:
                    item["raw_answers"] = None
            if item.get("classification_json"):
                try:
                    item["classification_json"] = json.loads(item["classification_json"])
                except Exception:
                    pass
            history_items.append(item)
    return history_items


async def get_history_entry_by_id(db: aiosqlite.Connection, history_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una entrada de historial específica por su ID primario."""
    query = "SELECT * FROM post_classification_history WHERE id = ? LIMIT 1;"
    async with db.execute(query, (int(history_id),)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        if item.get("secondary_categories"):
            try:
                item["secondary_categories"] = json.loads(item["secondary_categories"])
            except Exception:
                item["secondary_categories"] = []
        if item.get("assets"):
            try:
                item["assets"] = json.loads(item["assets"])
            except Exception:
                item["assets"] = []
        if item.get("classification_json"):
            try:
                item["classification_json"] = json.loads(item["classification_json"])
            except Exception:
                pass
        return item


async def rollback_post_classification(
    db: aiosqlite.Connection,
    tweet_id: str,
    history_id: int
) -> bool:
    """
    Restaura una clasificación anterior desde 'post_classification_history':
    - Archiva el estado activo actual como nuevo registro con trigger 'pre_rollback'.
    - Restaura en 'posts' la categoría, afinidad, formato, assets y classification_json del history_id seleccionado.
    - Marca el registro histórico restaurado con status 'ROLLED_BACK'.
    """
    hist_entry = await get_history_entry_by_id(db, history_id)
    if not hist_entry or str(hist_entry.get("tweet_id")) != str(tweet_id):
        return False

    # Archivar el estado activo antes del rollback
    await archive_classification_history(
        db,
        tweet_id=tweet_id,
        trigger_type="pre_rollback",
        reason=f"Archivado antes de restaurar la versión #{hist_entry['version_number']} (hist_id: {history_id})"
    )

    # Restaurar en posts
    update_query = """
    UPDATE posts
    SET primary_category = :primary_category,
        secondary_categories = :secondary_categories,
        affinity_score = :affinity_score,
        format = :format,
        technical_depth = :technical_depth,
        assets = :assets,
        classification_json = :classification_json,
        taxonomy_version = :taxonomy_version,
        status = 'CLASSIFIED_MANUAL',
        updated_at = CURRENT_TIMESTAMP
    WHERE tweet_id = :tweet_id;
    """
    sec_cats_val = hist_entry.get("secondary_categories")
    if isinstance(sec_cats_val, (list, dict)):
        sec_cats_val = json.dumps(sec_cats_val, ensure_ascii=False)

    assets_val = hist_entry.get("assets")
    if isinstance(assets_val, (list, dict)):
        assets_val = json.dumps(assets_val, ensure_ascii=False)

    class_json_val = hist_entry.get("classification_json")
    if isinstance(class_json_val, (dict, list)):
        class_json_val = json.dumps(class_json_val, ensure_ascii=False)

    params = {
        "tweet_id": str(tweet_id),
        "primary_category": hist_entry["primary_category"],
        "secondary_categories": sec_cats_val or "[]",
        "affinity_score": hist_entry.get("affinity_score", 0.0),
        "format": hist_entry.get("format") or "other",
        "technical_depth": hist_entry.get("technical_depth", 1.0),
        "assets": assets_val or "[]",
        "classification_json": class_json_val or "{}",
        "taxonomy_version": hist_entry.get("taxonomy_version", settings.APP_VERSION)
    }
    await db.execute(update_query, params)

    # Marcar el registro histórico restaurado
    await db.execute(
        "UPDATE post_classification_history SET status = 'ROLLED_BACK' WHERE id = ?;",
        (history_id,)
    )
    await db.commit()
    return True


# ==============================================================================
# Operaciones de Mantenimiento, Estadísticas y Backup (Fase 5.13)
# ==============================================================================

def format_bytes(size: int) -> str:
    """Formatea bytes a KB, MB o GB para visualización humana."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"


async def get_database_stats(db: aiosqlite.Connection) -> Dict[str, Any]:
    """Obtiene métricas y estado en tiempo real de la base de datos SQLite WAL."""
    counts = {}
    for table in ["posts", "post_classification_history", "batch_checkpoints", "taxonomy_feedback"]:
        try:
            async with db.execute(f"SELECT COUNT(*) FROM {table};") as cursor:
                row = await cursor.fetchone()
                counts[table] = row[0] if row else 0
        except Exception:
            counts[table] = 0

    # Versión de SQLite
    sqlite_ver = "unknown"
    try:
        async with db.execute("SELECT sqlite_version();") as cursor:
            row = await cursor.fetchone()
            sqlite_ver = row[0] if row else "unknown"
    except Exception:
        pass

    # Journal mode
    journal_mode = "unknown"
    try:
        async with db.execute("PRAGMA journal_mode;") as cursor:
            row = await cursor.fetchone()
            journal_mode = row[0] if row else "unknown"
    except Exception:
        pass

    # Tamaños de archivos en disco
    db_path = settings.DATABASE_PATH
    db_size = db_path.stat().st_size if db_path.exists() else 0
    wal_path = Path(str(db_path) + "-wal")
    wal_size = wal_path.stat().st_size if wal_path.exists() else 0

    return {
        "status": "HEALTHY",
        "posts_count": counts.get("posts", 0),
        "history_count": counts.get("post_classification_history", 0),
        "checkpoints_count": counts.get("batch_checkpoints", 0),
        "feedback_count": counts.get("taxonomy_feedback", 0),
        "db_size_bytes": db_size,
        "db_size_formatted": format_bytes(db_size),
        "wal_size_bytes": wal_size,
        "wal_size_formatted": format_bytes(wal_size),
        "sqlite_version": str(sqlite_ver),
        "journal_mode": str(journal_mode).upper(),
        "taxonomy_version": settings.APP_VERSION,
        "database_file": db_path.name
    }


async def reset_database_data(
    db: aiosqlite.Connection,
    clear_posts: bool = True,
    clear_history: bool = True,
    clear_checkpoints: bool = True,
    clear_feedback: bool = False,
    vacuum: bool = True
) -> Dict[str, Any]:
    """
    Limpia selectivamente los registros de prueba de la base de datos SQLite WAL.
    Preserva estrictamente categories.json y la taxonomía del sistema.
    """
    deleted_counts = {
        "posts": 0,
        "history": 0,
        "checkpoints": 0,
        "feedback": 0
    }

    if clear_history:
        async with db.execute("SELECT COUNT(*) FROM post_classification_history;") as c:
            deleted_counts["history"] = (await c.fetchone())[0]
        await db.execute("DELETE FROM post_classification_history;")

    if clear_posts:
        async with db.execute("SELECT COUNT(*) FROM posts;") as c:
            deleted_counts["posts"] = (await c.fetchone())[0]
        await db.execute("DELETE FROM posts;")

    if clear_checkpoints:
        async with db.execute("SELECT COUNT(*) FROM batch_checkpoints;") as c:
            deleted_counts["checkpoints"] = (await c.fetchone())[0]
        await db.execute("DELETE FROM batch_checkpoints;")

    if clear_feedback:
        async with db.execute("SELECT COUNT(*) FROM taxonomy_feedback;") as c:
            deleted_counts["feedback"] = (await c.fetchone())[0]
        await db.execute("DELETE FROM taxonomy_feedback;")

    # Resetear secuencias autoincrementables
    try:
        tables_to_reset = []
        if clear_history:
            tables_to_reset.append("'post_classification_history'")
        if clear_feedback:
            tables_to_reset.append("'taxonomy_feedback'")
        if tables_to_reset:
            await db.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({','.join(tables_to_reset)});")
    except Exception:
        pass

    await db.commit()

    if vacuum:
        try:
            await db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            async with get_db() as fresh_db:
                await fresh_db.execute("VACUUM;")
        except Exception as e:
            logger.warning(f"Aviso durante VACUUM post-reset: {e}")

    new_size = settings.DATABASE_PATH.stat().st_size if settings.DATABASE_PATH.exists() else 0

    return {
        "status": "SUCCESS",
        "message": "Base de datos reiniciada selectivamente con éxito. Taxonomía preservada.",
        "deleted_posts": deleted_counts["posts"],
        "deleted_history": deleted_counts["history"],
        "deleted_checkpoints": deleted_counts["checkpoints"],
        "deleted_feedback": deleted_counts["feedback"],
        "new_db_size_formatted": format_bytes(new_size)
    }


async def export_database_data(db: aiosqlite.Connection, include_history: bool = True) -> Dict[str, Any]:
    """Genera un volcado JSON estructurado de todos los posts, clasificaciones duales e historial."""
    from datetime import datetime, timezone

    # 1. Posts completos
    posts = []
    async with db.execute("SELECT * FROM posts ORDER BY created_at ASC;") as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            data = dict(r)
            # Deserializar campos JSON
            for field in ["media_urls", "secondary_categories", "assets", "raw_json", "classification_json"]:
                if data.get(field) and isinstance(data[field], str):
                    try:
                        data[field] = json.loads(data[field])
                    except Exception:
                        pass
            posts.append(data)

    # 2. Historial si se solicitó
    history = []
    if include_history:
        async with db.execute("SELECT * FROM post_classification_history ORDER BY id ASC;") as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                item = dict(r)
                for field in ["secondary_categories", "assets", "raw_answers", "classification_json"]:
                    if item.get(field) and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except Exception:
                            pass
                history.append(item)

    # 3. Checkpoints
    checkpoints = []
    async with db.execute("SELECT * FROM batch_checkpoints ORDER BY created_at ASC;") as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            checkpoints.append(dict(r))

    # 4. Feedback
    feedback = []
    async with db.execute("SELECT * FROM taxonomy_feedback ORDER BY id ASC;") as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            feedback.append(dict(r))

    return {
        "metadata": {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "posts_count": len(posts),
            "history_count": len(history),
            "checkpoints_count": len(checkpoints),
            "feedback_count": len(feedback)
        },
        "posts": posts,
        "history": history,
        "checkpoints": checkpoints,
        "feedback": feedback
    }


async def import_database_data(
    db: aiosqlite.Connection,
    backup_data: Dict[str, Any],
    mode: str = "merge"
) -> Dict[str, Any]:
    """
    Importa / restaura un volcado JSON en SQLite WAL.
    mode='replace': limpia posts e historial antes de insertar.
    mode='merge': inserta o actualiza posts preservando datos existentes.
    """
    if mode == "replace":
        await db.execute("DELETE FROM post_classification_history;")
        await db.execute("DELETE FROM posts;")
        await db.commit()

    posts = backup_data.get("posts", [])
    history = backup_data.get("history", [])
    feedback = backup_data.get("feedback", [])

    imported_posts_cnt = 0
    imported_history_cnt = 0
    imported_feedback_cnt = 0

    # Importar posts
    for post in posts:
        if isinstance(post, dict) and (post.get("tweet_id") or post.get("id")):
            if not post.get("tweet_id") and post.get("id"):
                post["tweet_id"] = str(post["id"])
            await insert_or_replace_post(db, post)
            imported_posts_cnt += 1

    # Importar historial
    for hist in history:
        if isinstance(hist, dict) and hist.get("tweet_id"):
            sec_cats = hist.get("secondary_categories")
            if isinstance(sec_cats, (list, dict)):
                sec_cats = json.dumps(sec_cats, ensure_ascii=False)
            assets_val = hist.get("assets")
            if isinstance(assets_val, (list, dict)):
                assets_val = json.dumps(assets_val, ensure_ascii=False)
            class_json = hist.get("classification_json")
            if isinstance(class_json, (list, dict)):
                class_json = json.dumps(class_json, ensure_ascii=False)
            raw_answers = hist.get("raw_answers")
            if isinstance(raw_answers, (list, dict)):
                raw_answers = json.dumps(raw_answers, ensure_ascii=False)

            query = """
            INSERT OR REPLACE INTO post_classification_history (
                tweet_id, version_number, taxonomy_version, primary_category,
                secondary_categories, affinity_score, format, technical_depth,
                assets, raw_answers, classification_json, trigger_type, reason, status
            ) VALUES (
                :tweet_id, :version_number, :taxonomy_version, :primary_category,
                :secondary_categories, :affinity_score, :format, :technical_depth,
                :assets, :raw_answers, :classification_json, :trigger_type, :reason, :status
            );
            """
            params = {
                "tweet_id": str(hist["tweet_id"]),
                "version_number": hist.get("version_number", 1),
                "taxonomy_version": hist.get("taxonomy_version", settings.APP_VERSION),
                "primary_category": hist.get("primary_category", "otros"),
                "secondary_categories": sec_cats or "[]",
                "affinity_score": float(hist.get("affinity_score") or 0.0),
                "format": hist.get("format") or "other",
                "technical_depth": float(hist.get("technical_depth") or 1.0),
                "assets": assets_val or "[]",
                "raw_answers": raw_answers,
                "classification_json": class_json or "{}",
                "trigger_type": hist.get("trigger_type", "import_backup"),
                "reason": hist.get("reason", "Restaurado desde backup JSON"),
                "status": hist.get("status", "ARCHIVED")
            }
            await db.execute(query, params)
            imported_history_cnt += 1

    # Importar feedback si viene en el backup
    for fb in feedback:
        if isinstance(fb, dict) and fb.get("tweet_id"):
            query = """
            INSERT INTO taxonomy_feedback (
                tweet_id, original_content, laya_suggested_category,
                laya_confidence, resolved_category, resolved_by
            ) VALUES (?, ?, ?, ?, ?, ?);
            """
            await db.execute(
                query,
                (
                    str(fb.get("tweet_id")),
                    fb.get("original_content", ""),
                    fb.get("laya_suggested_category"),
                    float(fb.get("laya_confidence") or 0.0),
                    fb.get("resolved_category", "otros"),
                    fb.get("resolved_by", "backup_import")
                )
            )
            imported_feedback_cnt += 1

    await db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Restauración completada ({imported_posts_cnt} posts, {imported_history_cnt} snapshots históricos).",
        "imported_posts": imported_posts_cnt,
        "imported_history": imported_history_cnt,
        "imported_feedback": imported_feedback_cnt
    }


async def optimize_database(db: aiosqlite.Connection) -> Dict[str, Any]:
    """Ejecuta mantenimiento proactivo: WAL checkpoint truncado, optimización de índices y VACUUM."""
    db_path = settings.DATABASE_PATH
    initial_size = db_path.stat().st_size if db_path.exists() else 0

    await db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    await db.execute("PRAGMA optimize;")
    await db.execute("VACUUM;")

    final_size = db_path.stat().st_size if db_path.exists() else 0
    reclaimed = max(0, initial_size - final_size)

    return {
        "status": "SUCCESS",
        "message": "Mantenimiento y optimización de SQLite completados.",
        "initial_size_formatted": format_bytes(initial_size),
        "final_size_formatted": format_bytes(final_size),
        "bytes_reclaimed": reclaimed
    }

