"""
endpoints_posts.py - Endpoints REST para consulta, filtrado, estadísticas y override manual de posts.
"""

from __future__ import annotations
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from ..config import settings
from ..database import (
    archive_classification_history,
    find_post_by_id,
    get_db,
    get_db_session,
    get_history_entry_by_id,
    get_post_history,
    insert_or_replace_post,
    resolve_pending_post,
    rollback_post_classification,
    update_social_metrics,
)
from ..engine import LayaEngine
from ..registry import get_categories_dict, get_root_family
from ..schema import (
    AnalyzeBatchRequest,
    AnalyzePostRequest,
    AnalyzePostResponse,
    BatchStreamItem,
    ClassificationHistoryItem,
    DashboardStatsResponse,
    PendingOverrideRequest,
    PostComparisonResponse,
    PostHistoryResponse,
    PostIdsResponse,
    PostListResponse,
    PostResponse,
    ReclassifyRequest,
    RollbackClassificationResponse,
    SecondaryCategoryItem,
    SocialMetrics,
)
from ..services.ingest_service import convert_raw_to_clean, normalize_raw_item
from ..services.stats_service import StatsService

logger = logging.getLogger("api_posts")
router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.post("/analyze", response_model=AnalyzePostResponse)
async def analyze_single_post(
    payload: AnalyzePostRequest,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Análisis interactivo System 1 en tiempo real para un post individual:
    - Normaliza el texto/objeto con NFKC y detección de assets
    - Ejecuta LayaEngine con Family Gating en hilo PyTorch CPU
    - Retorna el resumen analítico estructurado y el JSON de salida
    - Opcionalmente persiste en SQLite WAL si persist=True
    """
    tweet_id = (payload.id or "").strip()
    if not tweet_id:
        tweet_id = f"manual_{uuid.uuid4().hex[:10]}"

    raw_dict = {
        "tweet_id": tweet_id,
        "content": payload.text,
        "author": payload.author or "dev_user",
        "author_name": payload.author or "dev_user",
        "favorite_count": payload.likes or 0,
        "retweet_count": payload.retweets or 0,
        "media_urls": payload.media_urls or [],
        "media_type": payload.media_type or "none",
        "date": payload.date or "",
        "post_url": payload.post_url or ""
    }
    raw = normalize_raw_item(raw_dict)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo procesar el contenido del post proporcionado."
        )

    clean = convert_raw_to_clean(raw)
    engine = LayaEngine.get_instance()
    result = await asyncio.to_thread(engine.classify_post, clean, payload.active_questions)

    # Enriquecer con metadatos de categoría
    cats_dict = get_categories_dict()
    cat_info = cats_dict.get(result.primary_category, {})
    category_label = cat_info.get("label") or cat_info.get("name") or result.primary_category
    family_id = cat_info.get("parent_id") or get_root_family(result.primary_category)
    color_hex = cat_info.get("color_hex", "#64748b")
    code = cat_info.get("code")
    if not code:
        import re
        words = re.findall(r'[A-Za-z0-9]+', category_label)
        if len(words) >= 2:
            code = (words[0][0] + words[1][0]).upper()[:3]
        else:
            code = result.primary_category[:3].upper()

    # Persistir si fue solicitado
    raw_source = clean.raw_source_json or clean.model_dump()
    classification_dump = result.model_dump()
    taxonomy_ver = settings.APP_VERSION

    if payload.persist:
        post_dict = {
            "tweet_id": clean.tweet_id,
            "post_url": clean.post_url,
            "author_name": clean.author_name,
            "author_id": clean.author_id,
            "content": clean.original_content,
            "preview_text": clean.original_content[:140],
            "date": clean.date or "2026-10-14",
            "favorite_count": clean.metrics.favorite_count,
            "retweet_count": clean.metrics.retweet_count,
            "reply_count": clean.metrics.reply_count,
            "bookmark_count": clean.metrics.bookmark_count,
            "media_urls": clean.media_urls,
            "media_count": clean.media_count,
            "media_type": clean.media_type,
            "lang": clean.lang,
            "primary_category": result.primary_category,
            "secondary_categories": [c.model_dump() for c in result.secondary_categories],
            "affinity_score": result.affinity_score,
            "format": result.format,
            "format_confidence": result.format_confidence,
            "technical_depth": result.technical_depth,
            "assets": result.assets,
            "is_local_first": 1 if result.is_local_first else 0,
            "is_nsfw": 1 if result.is_nsfw else 0,
            "is_outlier": 1 if result.is_outlier else 0,
            "status": result.status,
            "engine_used": result.engine_used,
            "inference_latency_ms": result.inference_latency_ms,
            "raw_json": raw_source,
            "classification_json": classification_dump,
            "taxonomy_version": taxonomy_ver,
            "reclassification_count": 0
        }
        await insert_or_replace_post(db, post_dict)
        await db.commit()

    has_code_or_tool = any(a in ["github", "github.com", "huggingface", "colab", "npm", "pypi", "tool", "code_repo"] for a in result.assets)

    return AnalyzePostResponse(
        tweet_id=clean.tweet_id,
        content=clean.original_content,
        author_name=clean.author_name,
        primary_category=result.primary_category,
        category_label=category_label,
        family_id=family_id,
        color_hex=color_hex,
        code=code,
        affinity_score=result.affinity_score,
        secondary_categories=result.secondary_categories,
        format=result.format,
        format_confidence=result.format_confidence,
        technical_depth=result.technical_depth,
        is_tool_or_code_release=has_code_or_tool,
        is_local_first=result.is_local_first,
        is_nsfw=result.is_nsfw,
        is_outlier=result.is_outlier,
        assets=result.assets,
        status=result.status,
        engine_used=result.engine_used,
        inference_latency_ms=result.inference_latency_ms,
        raw_answers=result.raw_answers,
        raw_json=raw_source,
        classification_json=classification_dump,
        taxonomy_version=taxonomy_ver,
        reclassification_count=0,
        persisted=payload.persist
    )


@router.post("/analyze-batch-stream")
async def analyze_batch_stream(payload: AnalyzeBatchRequest):
    """
    Procesamiento masivo en lote con streaming NDJSON y desahogo cooperativo de CPU (ADR-006):
    - Transmite en tiempo real cada post clasificado en una única conexión HTTP persistente
    - Protege la CPU contra saturación térmica con micro-pausas adaptativas
    - Supervisa la memoria RAM y ejecuta recolección preventiva si se supera el umbral
    - Confirma transacciones en búfer a SQLite WAL cada 25 posts y al finalizar
    """
    engine = LayaEngine.get_instance()
    cats_dict = get_categories_dict()
    total_posts = len(payload.posts)

    async def batch_generator():
        commit_buffer: List[Dict[str, Any]] = []
        new_posts_processed = 0
        try:
            for idx, post_req in enumerate(payload.posts):
                tweet_id = (post_req.id or "").strip()
                if not tweet_id:
                    tweet_id = f"batch_{idx+1}_{uuid.uuid4().hex[:8]}"

                raw_dict = {
                    "tweet_id": tweet_id,
                    "content": post_req.text,
                    "author_name": post_req.author or "dev_user",
                    "favorite_count": post_req.likes or 0,
                    "retweet_count": post_req.retweets or 0,
                    "media_urls": post_req.media_urls or [],
                    "media_type": post_req.media_type or "none",
                    "date": post_req.date or "",
                    "post_url": post_req.post_url or ""
                }
                raw = normalize_raw_item(raw_dict)
                if not raw:
                    err_item = BatchStreamItem(
                        event="error",
                        index=idx + 1,
                        total=total_posts,
                        error=f"No se pudo normalizar el post #{idx+1}"
                    )
                    yield json.dumps(err_item.model_dump(), ensure_ascii=False) + "\n"
                    continue

                clean = convert_raw_to_clean(raw)

                # Detección de duplicado en SQLite (Fase 5.12.2)
                existing = None
                async with get_db() as db:
                    existing = await find_post_by_id(db, clean.tweet_id)

                if existing is not None and payload.duplicate_strategy == "skip":
                    # RUTA SKIP: Actualizar únicamente métricas de engagement si cambiaron (0 ms CPU)
                    m = clean.metrics
                    changed = (
                        existing.get("favorite_count", 0) != m.favorite_count or
                        existing.get("retweet_count", 0) != m.retweet_count or
                        existing.get("reply_count", 0) != m.reply_count or
                        existing.get("bookmark_count", 0) != m.bookmark_count
                    )
                    if changed:
                        async with get_db() as db:
                            await update_social_metrics(
                                db,
                                tweet_id=clean.tweet_id,
                                favorite_count=m.favorite_count,
                                retweet_count=m.retweet_count,
                                reply_count=m.reply_count,
                                bookmark_count=m.bookmark_count
                            )
                            await db.commit()

                    cat_id = existing.get("primary_category", "otros")
                    cat_info = cats_dict.get(cat_id, {})
                    category_label = cat_info.get("label") or cat_info.get("name") or cat_id
                    family_id = cat_info.get("parent_id") or get_root_family(cat_id)
                    color_hex = cat_info.get("color_hex", "#64748b")
                    code = cat_info.get("code")
                    if not code:
                        import re
                        words = re.findall(r'[A-Za-z0-9]+', category_label)
                        code = (words[0][0] + words[1][0]).upper()[:3] if len(words) >= 2 else cat_id[:3].upper()

                    has_code_or_tool = any(a in ["github", "github.com", "huggingface", "colab", "npm", "pypi", "tool", "code_repo"] for a in (existing.get("assets") or []))

                    sec_cats = existing.get("secondary_categories") or []
                    sec_models = []
                    if isinstance(sec_cats, list):
                        for s in sec_cats:
                            if isinstance(s, dict):
                                sec_models.append(SecondaryCategoryItem(**s))

                    resp_obj = AnalyzePostResponse(
                        tweet_id=existing.get("tweet_id") or clean.tweet_id,
                        content=existing.get("content") or clean.original_content,
                        author_name=existing.get("author_name") or clean.author_name,
                        primary_category=cat_id,
                        category_label=category_label,
                        family_id=family_id,
                        color_hex=color_hex,
                        code=code,
                        affinity_score=existing.get("affinity_score", 0.85),
                        secondary_categories=sec_models,
                        format=existing.get("format") or "other",
                        format_confidence=existing.get("format_confidence", 0.85),
                        technical_depth=existing.get("technical_depth", 1.0),
                        is_tool_or_code_release=has_code_or_tool,
                        is_local_first=bool(existing.get("is_local_first")),
                        is_nsfw=bool(existing.get("is_nsfw")),
                        is_outlier=bool(existing.get("is_outlier")),
                        assets=existing.get("assets") or [],
                        status=existing.get("status") or "CLASSIFIED",
                        engine_used=existing.get("engine_used") or "laya_cached",
                        inference_latency_ms=0.0,
                        raw_answers={},
                        raw_json=existing.get("raw_json") or clean.raw_source_json or clean.model_dump(),
                        classification_json=existing.get("classification_json"),
                        taxonomy_version=existing.get("taxonomy_version") or settings.APP_VERSION,
                        reclassification_count=existing.get("reclassification_count", 0),
                        persisted=True
                    )

                    stream_item = BatchStreamItem(
                        event="item_completed",
                        index=idx + 1,
                        total=total_posts,
                        post=resp_obj,
                        telemetry={
                            "latency_ms": 0.0,
                            "engine": "cache_skip",
                            "skipped": True
                        }
                    )
                    yield json.dumps(stream_item.model_dump(), ensure_ascii=False) + "\n"
                    await asyncio.sleep(0.005)
                    continue

                # RUTA INFERENCIA: Post nuevo O reclasificación solicitada
                result = await asyncio.to_thread(engine.classify_post, clean, payload.active_questions)

                # Si es reclasificación y persist=True, archivar la versión anterior en post_classification_history
                reclassification_count = 0
                if existing is not None:
                    reclassification_count = (existing.get("reclassification_count") or 0) + 1
                    if payload.persist:
                        async with get_db() as db:
                            await archive_classification_history(
                                db,
                                existing_post=existing,
                                trigger_type="bulk_reclassify",
                                notes="Reclasificación masiva por batch-stream"
                            )
                            await db.commit()

                # Metadatos de categoría
                cat_info = cats_dict.get(result.primary_category, {})
                category_label = cat_info.get("label") or cat_info.get("name") or result.primary_category
                family_id = cat_info.get("parent_id") or get_root_family(result.primary_category)
                color_hex = cat_info.get("color_hex", "#64748b")
                code = cat_info.get("code")
                if not code:
                    import re
                    words = re.findall(r'[A-Za-z0-9]+', category_label)
                    code = (words[0][0] + words[1][0]).upper()[:3] if len(words) >= 2 else result.primary_category[:3].upper()

                has_code_or_tool = any(a in ["github", "github.com", "huggingface", "colab", "npm", "pypi", "tool", "code_repo"] for a in result.assets)

                raw_source = clean.raw_source_json or (existing.get("raw_json") if existing else None) or clean.model_dump()
                classification_dump = result.model_dump()
                taxonomy_ver = settings.APP_VERSION

                resp_obj = AnalyzePostResponse(
                    tweet_id=clean.tweet_id,
                    content=clean.original_content,
                    author_name=clean.author_name,
                    primary_category=result.primary_category,
                    category_label=category_label,
                    family_id=family_id,
                    color_hex=color_hex,
                    code=code,
                    affinity_score=result.affinity_score,
                    secondary_categories=result.secondary_categories,
                    format=result.format,
                    format_confidence=result.format_confidence,
                    technical_depth=result.technical_depth,
                    is_tool_or_code_release=has_code_or_tool,
                    is_local_first=result.is_local_first,
                    is_nsfw=result.is_nsfw,
                    is_outlier=result.is_outlier,
                    assets=result.assets,
                    status=result.status,
                    engine_used=result.engine_used,
                    inference_latency_ms=result.inference_latency_ms,
                    raw_answers=result.raw_answers,
                    raw_json=raw_source,
                    classification_json=classification_dump,
                    taxonomy_version=taxonomy_ver,
                    reclassification_count=reclassification_count,
                    persisted=payload.persist
                )

                if payload.persist:
                    post_dict = {
                        "tweet_id": clean.tweet_id,
                        "post_url": clean.post_url,
                        "author_name": clean.author_name,
                        "author_id": clean.author_id,
                        "content": clean.original_content,
                        "preview_text": clean.original_content[:140],
                        "date": clean.date or "2026-10-14",
                        "favorite_count": clean.metrics.favorite_count,
                        "retweet_count": clean.metrics.retweet_count,
                        "reply_count": clean.metrics.reply_count,
                        "bookmark_count": clean.metrics.bookmark_count,
                        "media_urls": clean.media_urls,
                        "media_count": clean.media_count,
                        "media_type": clean.media_type,
                        "lang": clean.lang,
                        "primary_category": result.primary_category,
                        "secondary_categories": [c.model_dump() for c in result.secondary_categories],
                        "affinity_score": result.affinity_score,
                        "format": result.format,
                        "format_confidence": result.format_confidence,
                        "technical_depth": result.technical_depth,
                        "assets": result.assets,
                        "is_local_first": 1 if result.is_local_first else 0,
                        "is_nsfw": 1 if result.is_nsfw else 0,
                        "is_outlier": 1 if result.is_outlier else 0,
                        "status": result.status,
                        "engine_used": result.engine_used,
                        "inference_latency_ms": result.inference_latency_ms,
                        "raw_json": raw_source,
                        "classification_json": classification_dump,
                        "taxonomy_version": taxonomy_ver,
                        "reclassification_count": reclassification_count
                    }
                    commit_buffer.append(post_dict)

                    # Persistir cada post en lotes pequeños (<=5) o por bloques en lotes masivos
                    commit_threshold = 1 if total_posts <= 5 else settings.CHECKPOINT_INTERVAL
                    if len(commit_buffer) >= commit_threshold:
                        async with get_db() as db:
                            for p in commit_buffer:
                                await insert_or_replace_post(db, p)
                            await db.commit()
                        commit_buffer.clear()

                stream_item = BatchStreamItem(
                    event="item_completed",
                    index=idx + 1,
                    total=total_posts,
                    post=resp_obj,
                    telemetry={
                        "latency_ms": result.inference_latency_ms,
                        "engine": result.engine_used,
                        "reclassified": existing is not None,
                        "skipped": False
                    }
                )
                yield json.dumps(stream_item.model_dump(), ensure_ascii=False) + "\n"

                if existing is None:
                    new_posts_processed += 1

                # Comprobación de seguridad de memoria RAM
                engine.check_memory_safety()

                # Desahogo cooperativo de CPU (15ms)
                await asyncio.sleep(settings.BATCH_YIELD_SECONDS)

                # Corte anticipado si se configuró límite de nuevos posts
                if payload.max_new_posts and new_posts_processed >= payload.max_new_posts:
                    logger.info(f"Límite max_new_posts={payload.max_new_posts} alcanzado. Finalizando streaming cooperativo.")
                    break

            # Persistir remanentes finales si aplica
            if payload.persist and commit_buffer:
                async with get_db() as db:
                    for p in commit_buffer:
                        await insert_or_replace_post(db, p)
                    await db.commit()
                commit_buffer.clear()

            # Notificación de finalización de lote
            final_item = BatchStreamItem(
                event="batch_completed",
                index=total_posts,
                total=total_posts
            )
            yield json.dumps(final_item.model_dump(), ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error(f"Error en streaming de lote: {e}", exc_info=True)
            err_item = BatchStreamItem(
                event="error",
                index=total_posts,
                total=total_posts,
                error=str(e)
            )
            yield json.dumps(err_item.model_dump(), ensure_ascii=False) + "\n"

    return StreamingResponse(
        batch_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.get("/ids", response_model=PostIdsResponse)
async def get_all_post_ids(db: aiosqlite.Connection = Depends(get_db_session)):
    """
    Retorna la lista completa y ultraligera de todos los tweet_ids registrados en SQLite WAL.
    Permite al frontend conciliar instantáneamente publicaciones pendientes sin overhead.
    """
    cursor = await db.execute("SELECT tweet_id FROM posts ORDER BY created_at DESC;")
    rows = await cursor.fetchall()
    tweet_ids = [str(r["tweet_id"]) for r in rows]
    return PostIdsResponse(total=len(tweet_ids), tweet_ids=tweet_ids)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_stats(db: aiosqlite.Connection = Depends(get_db_session)):
    """Retorna métricas agregadas completas para la Waffle Grid y el Cuadrante Scatter Canvas 2D."""
    return await StatsService.get_dashboard_stats(db)


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=1000),
    family: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    is_outlier: Optional[bool] = Query(default=None),
    lang: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort_by: str = Query(default="date_desc", pattern="^(date_desc|score_desc|likes_desc)$"),
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """Consulta paginada de tweets con soporte de filtros por familia, categoría, idioma y búsqueda reactiva."""
    where_clauses = ["1=1"]
    params: List[Any] = []

    # Filtro por familia (busca todas las subcategorías que pertenecen a la familia raíz)
    if family:
        cats = get_categories_dict()
        matching_cats = [c_id for c_id in cats.keys() if get_root_family(c_id) == family]
        if matching_cats:
            placeholders = ",".join(["?"] * len(matching_cats))
            where_clauses.append(f"primary_category IN ({placeholders})")
            params.extend(matching_cats)
        else:
            where_clauses.append("primary_category = ?")
            params.append(family)

    # Filtro por categoría específica
    if category:
        where_clauses.append("primary_category = ?")
        params.append(category)

    # Filtro por estado del post
    if status_filter:
        where_clauses.append("status = ?")
        params.append(status_filter.upper())

    # Filtro por outlier
    if is_outlier is not None:
        where_clauses.append("is_outlier = ?")
        params.append(1 if is_outlier else 0)

    # Filtro por idioma
    if lang:
        where_clauses.append("lang = ?")
        params.append(lang.lower())

    # Búsqueda por texto (contenido o autor)
    if search:
        search_like = f"%{search.strip()}%"
        where_clauses.append("(content LIKE ? OR author_name LIKE ?)")
        params.extend([search_like, search_like])

    where_sql = " AND ".join(where_clauses)

    # Total de coincidencias
    count_sql = f"SELECT COUNT(*) FROM posts WHERE {where_sql};"
    async with db.execute(count_sql, params) as cursor:
        row = await cursor.fetchone()
        total = int(row[0]) if row else 0

    # Ordenamiento
    order_map = {
        "date_desc": "date DESC",
        "score_desc": "affinity_score DESC, date DESC",
        "likes_desc": "favorite_count DESC, date DESC"
    }
    order_sql = order_map.get(sort_by, "date DESC")

    # Paginación
    offset = (page - 1) * limit
    select_sql = f"""
    SELECT * FROM posts
    WHERE {where_sql}
    ORDER BY {order_sql}
    LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])

    posts_list: List[PostResponse] = []
    async with db.execute(select_sql, params) as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            # Deserializar medios
            media_urls = []
            if r["media_urls"]:
                try:
                    media_urls = json.loads(r["media_urls"])
                except Exception:
                    media_urls = []

            # Deserializar secundarias
            sec_cats = []
            if r["secondary_categories"]:
                try:
                    raw_secs = json.loads(r["secondary_categories"])
                    for s in raw_secs:
                        if isinstance(s, dict) and "id" in s:
                            sec_cats.append(SecondaryCategoryItem(id=s["id"], score=float(s.get("score", 0.0))))
                        elif isinstance(s, str):
                            sec_cats.append(SecondaryCategoryItem(id=s, score=0.5))
                except Exception:
                    sec_cats = []

            # Deserializar assets
            assets = []
            if r["assets"]:
                try:
                    assets = json.loads(r["assets"])
                except Exception:
                    assets = []

            posts_list.append(PostResponse(
                tweet_id=r["tweet_id"],
                post_url=r["post_url"],
                author_name=r["author_name"],
                author_id=r["author_id"],
                content=r["content"],
                preview_text=r["preview_text"],
                date=r["date"],
                metrics=SocialMetrics(
                    favorite_count=r["favorite_count"] or 0,
                    retweet_count=r["retweet_count"] or 0,
                    reply_count=r["reply_count"] or 0,
                    bookmark_count=r["bookmark_count"] or 0
                ),
                media_urls=media_urls,
                media_count=r["media_count"] or len(media_urls),
                media_type=r["media_type"] or "none",
                lang=r["lang"] or "en",
                primary_category=r["primary_category"],
                secondary_categories=sec_cats,
                affinity_score=round(float(r["affinity_score"] or 0.0), 3),
                format=r["format"] or "other",
                format_confidence=round(float(r["format_confidence"] or 0.0), 3),
                technical_depth=round(float(r["technical_depth"] or 1.0), 2),
                assets=assets,
                is_local_first=bool(r["is_local_first"]),
                is_nsfw=bool(r["is_nsfw"]),
                is_outlier=bool(r["is_outlier"]),
                status=r["status"],
                engine_used=r["engine_used"] or "laya",
                inference_latency_ms=round(float(r["inference_latency_ms"] or 0.0), 2),
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ))

    return PostListResponse(
        total=total,
        page=page,
        limit=limit,
        posts=posts_list
    )


def _format_post_response(post_data: Dict[str, Any]) -> PostResponse:
    sec_cats = []
    if post_data.get("secondary_categories"):
        for s in post_data["secondary_categories"]:
            if isinstance(s, dict) and "id" in s:
                sec_cats.append(SecondaryCategoryItem(id=s["id"], score=float(s.get("score", 0.0))))
            elif isinstance(s, str):
                sec_cats.append(SecondaryCategoryItem(id=s, score=0.5))

    return PostResponse(
        tweet_id=str(post_data["tweet_id"]),
        post_url=post_data.get("post_url") or f"https://x.com/{post_data.get('author_name', 'x')}/status/{post_data['tweet_id']}",
        author_name=post_data.get("author_name") or "dev_user",
        author_id=post_data.get("author_id"),
        content=post_data.get("content") or "",
        preview_text=post_data.get("preview_text") or (post_data.get("content", "")[:140]),
        date=post_data.get("date") or "",
        metrics=SocialMetrics(
            favorite_count=post_data.get("favorite_count") or 0,
            retweet_count=post_data.get("retweet_count") or 0,
            reply_count=post_data.get("reply_count") or 0,
            bookmark_count=post_data.get("bookmark_count") or 0
        ),
        media_urls=post_data.get("media_urls") or [],
        media_count=post_data.get("media_count") or len(post_data.get("media_urls") or []),
        media_type=post_data.get("media_type") or "none",
        lang=post_data.get("lang") or "en",
        primary_category=post_data["primary_category"],
        secondary_categories=sec_cats,
        affinity_score=round(float(post_data.get("affinity_score", 0.0)), 3),
        format=post_data.get("format", "other"),
        format_confidence=round(float(post_data.get("format_confidence", 0.0)), 3),
        technical_depth=round(float(post_data.get("technical_depth", 1.0)), 2),
        assets=post_data.get("assets") or [],
        is_local_first=bool(post_data.get("is_local_first")),
        is_nsfw=bool(post_data.get("is_nsfw")),
        is_outlier=bool(post_data.get("is_outlier")),
        status=post_data.get("status") or "CLASSIFIED",
        engine_used=post_data.get("engine_used", "laya"),
        inference_latency_ms=round(float(post_data.get("inference_latency_ms", 0.0)), 2),
        raw_json=post_data.get("raw_json"),
        classification_json=post_data.get("classification_json"),
        taxonomy_version=post_data.get("taxonomy_version", settings.APP_VERSION),
        reclassification_count=int(post_data.get("reclassification_count") or 0),
        created_at=post_data.get("created_at"),
        updated_at=post_data.get("updated_at")
    )


@router.get("/{tweet_id}", response_model=PostResponse)
async def get_post(tweet_id: str, db: aiosqlite.Connection = Depends(get_db_session)):
    """Inspección profunda de un tweet individual para el Drawer lateral."""
    post_data = await find_post_by_id(db, tweet_id)
    if not post_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tweet {tweet_id} no encontrado en la base de datos."
        )

    return _format_post_response(post_data)


@router.post("/{tweet_id}/override", response_model=Dict[str, Any])
async def override_post(
    tweet_id: str,
    payload: PendingOverrideRequest,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Resolución manual en 1 clic de posts en estado PENDING (ADR-007):
    - Actualiza el post a CLASSIFIED_MANUAL o DISCARDED.
    - Registra el desempate en taxonomy_feedback para aprendizaje activo.
    - Retorna el objeto post completamente actualizado para sincronización instantánea del frontend.
    """
    success = await resolve_pending_post(
        db=db,
        tweet_id=tweet_id,
        primary_category=payload.primary_category,
        secondary_categories=payload.secondary_categories,
        resolved_by="manual_user"
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tweet {tweet_id} no existe o no pudo ser reclasificado."
        )

    updated_post = await find_post_by_id(db, tweet_id)
    post_formatted = _format_post_response(updated_post) if updated_post else None

    logger.info(f"Post {tweet_id} resuelto manualmente hacia categoría: {payload.primary_category}")
    return {
        "status": "success",
        "tweet_id": tweet_id,
        "primary_category": payload.primary_category,
        "new_status": payload.status,
        "post": post_formatted.model_dump() if post_formatted else None
    }


# ==============================================================================
# Endpoints de Reclasificación Individual, Historial y Rollback (Fase 5.12.3)
# ==============================================================================

@router.post("/{tweet_id}/reclassify", response_model=PostComparisonResponse)
async def reclassify_single_post(
    tweet_id: str,
    payload: Optional[ReclassifyRequest] = None,
    dry_run: Optional[bool] = Query(default=None),
    confirm: Optional[bool] = Query(default=None),
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Reclasificación individual interactiva con inferencia Laya y comparativa A/B Diff (Fase 5.12):
    - dry_run=True (default): Inferencia en memoria, computa el diff y delta de afinidad sin modificar la BD.
    - confirm=True o dry_run=False: Archiva la clasificación previa en post_classification_history,
      actualiza el post en SQLite WAL con la nueva taxonomía e incrementa reclassification_count.
    """
    req = payload or ReclassifyRequest()
    is_confirm = confirm if confirm is not None else req.confirm
    is_dry_run = dry_run if dry_run is not None else req.dry_run

    # Si se envía confirm=True, se invalida el modo dry_run
    if is_confirm:
        is_dry_run = False

    post = await find_post_by_id(db, tweet_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tweet {tweet_id} no encontrado en la base de datos."
        )

    # Reconstruir datos para CleanPost
    raw_dict = post.get("raw_json") or {
        "tweet_id": post["tweet_id"],
        "content": post["content"],
        "author_name": post.get("author_name") or "dev_user",
        "favorite_count": post.get("favorite_count") or 0,
        "retweet_count": post.get("retweet_count") or 0,
        "reply_count": post.get("reply_count") or 0,
        "bookmark_count": post.get("bookmark_count") or 0,
        "media_urls": post.get("media_urls") or [],
        "media_type": post.get("media_type") or "none",
        "date": post.get("date") or "",
        "post_url": post.get("post_url") or ""
    }
    raw = normalize_raw_item(raw_dict)
    clean = convert_raw_to_clean(raw) if raw else convert_raw_to_clean(normalize_raw_item({
        "tweet_id": post["tweet_id"],
        "content": post["content"],
        "author_name": post.get("author_name") or "dev_user"
    }))

    engine = LayaEngine.get_instance()
    result = await asyncio.to_thread(engine.classify_post, clean)
    cats_dict = get_categories_dict()

    # Metadatos versión previa
    prev_cat = post.get("primary_category", "otros")
    prev_cat_info = cats_dict.get(prev_cat, {})
    prev_code = prev_cat_info.get("code")
    if not prev_code:
        prev_label = prev_cat_info.get("label") or prev_cat
        words = re.findall(r'[A-Za-z0-9]+', prev_label)
        prev_code = (words[0][0] + words[1][0]).upper()[:3] if len(words) >= 2 else prev_cat[:3].upper()

    previous_data = {
        "tweet_id": tweet_id,
        "primary_category": prev_cat,
        "category_label": prev_cat_info.get("label") or prev_cat_info.get("name") or prev_cat,
        "family_id": prev_cat_info.get("parent_id") or get_root_family(prev_cat),
        "color_hex": prev_cat_info.get("color_hex", "#64748b"),
        "code": prev_code,
        "affinity_score": round(float(post.get("affinity_score") or 0.0), 3),
        "secondary_categories": post.get("secondary_categories") or [],
        "format": post.get("format") or "other",
        "technical_depth": round(float(post.get("technical_depth") or 1.0), 2),
        "assets": post.get("assets") or [],
        "taxonomy_version": post.get("taxonomy_version") or "2.0.0",
        "reclassification_count": post.get("reclassification_count") or 0,
        "status": post.get("status") or "CLASSIFIED"
    }

    # Metadatos nueva versión inferida
    curr_cat = result.primary_category
    curr_cat_info = cats_dict.get(curr_cat, {})
    curr_code = curr_cat_info.get("code")
    curr_label = curr_cat_info.get("label") or curr_cat_info.get("name") or curr_cat
    if not curr_code:
        words = re.findall(r'[A-Za-z0-9]+', curr_label)
        curr_code = (words[0][0] + words[1][0]).upper()[:3] if len(words) >= 2 else curr_cat[:3].upper()

    new_count = (post.get("reclassification_count") or 0) + (1 if not is_dry_run else 0)

    current_data = {
        "tweet_id": tweet_id,
        "primary_category": curr_cat,
        "category_label": curr_label,
        "family_id": curr_cat_info.get("parent_id") or get_root_family(curr_cat),
        "color_hex": curr_cat_info.get("color_hex", "#64748b"),
        "code": curr_code,
        "affinity_score": round(float(result.affinity_score), 3),
        "secondary_categories": [s.model_dump() for s in result.secondary_categories],
        "format": result.format,
        "format_confidence": round(float(result.format_confidence), 3),
        "technical_depth": round(float(result.technical_depth), 2),
        "assets": result.assets,
        "is_local_first": result.is_local_first,
        "is_nsfw": result.is_nsfw,
        "is_outlier": result.is_outlier,
        "taxonomy_version": settings.APP_VERSION,
        "reclassification_count": new_count,
        "engine_used": result.engine_used,
        "inference_latency_ms": round(float(result.inference_latency_ms), 2),
        "status": result.status
    }

    has_changed = (prev_cat != curr_cat)
    delta_affinity = round(float(result.affinity_score) - float(post.get("affinity_score") or 0.0), 3)

    if not is_dry_run:
        # 1. Archivar versión previa en historial
        await archive_classification_history(
            db,
            tweet_id=tweet_id,
            trigger_type="single_reclassify",
            reason=req.reason or f"Reclasificación interactiva hacia '{curr_cat}'"
        )

        # 2. Persistir nueva clasificación en posts
        update_query = """
        UPDATE posts
        SET primary_category = :primary_category,
            secondary_categories = :secondary_categories,
            affinity_score = :affinity_score,
            format = :format,
            format_confidence = :format_confidence,
            technical_depth = :technical_depth,
            assets = :assets,
            is_local_first = :is_local_first,
            is_nsfw = :is_nsfw,
            is_outlier = :is_outlier,
            status = :status,
            engine_used = :engine_used,
            inference_latency_ms = :inference_latency_ms,
            classification_json = :classification_json,
            taxonomy_version = :taxonomy_version,
            updated_at = CURRENT_TIMESTAMP
        WHERE tweet_id = :tweet_id;
        """
        params = {
            "tweet_id": str(tweet_id),
            "primary_category": curr_cat,
            "secondary_categories": json.dumps([s.model_dump() for s in result.secondary_categories], ensure_ascii=False),
            "affinity_score": result.affinity_score,
            "format": result.format,
            "format_confidence": result.format_confidence,
            "technical_depth": result.technical_depth,
            "assets": json.dumps(result.assets, ensure_ascii=False),
            "is_local_first": 1 if result.is_local_first else 0,
            "is_nsfw": 1 if result.is_nsfw else 0,
            "is_outlier": 1 if result.is_outlier else 0,
            "status": result.status,
            "engine_used": result.engine_used,
            "inference_latency_ms": result.inference_latency_ms,
            "classification_json": json.dumps(result.model_dump(), ensure_ascii=False),
            "taxonomy_version": settings.APP_VERSION
        }
        await db.execute(update_query, params)
        await db.commit()
        logger.info(f"Post {tweet_id} reclasificado exitosamente a '{curr_cat}' (delta: {delta_affinity}). Historial archivado.")

    return PostComparisonResponse(
        tweet_id=tweet_id,
        has_changed=has_changed,
        delta_affinity=delta_affinity,
        previous=previous_data,
        current=current_data
    )


@router.get("/{tweet_id}/history", response_model=PostHistoryResponse)
async def get_post_classification_history(
    tweet_id: str,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """Obtiene el historial cronológico completo de clasificaciones para un post."""
    post = await find_post_by_id(db, tweet_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tweet {tweet_id} no encontrado en la base de datos."
        )

    history_rows = await get_post_history(db, tweet_id)
    history_items = []
    for r in history_rows:
        sec_cats = []
        if r.get("secondary_categories"):
            for s in r["secondary_categories"]:
                if isinstance(s, dict) and "id" in s:
                    sec_cats.append(SecondaryCategoryItem(id=s["id"], score=float(s.get("score", 0.0))))
                elif isinstance(s, str):
                    sec_cats.append(SecondaryCategoryItem(id=s, score=0.5))

        history_items.append(ClassificationHistoryItem(
            id=r["id"],
            tweet_id=r["tweet_id"],
            version_number=r["version_number"],
            taxonomy_version=r.get("taxonomy_version") or "2.0.0",
            primary_category=r["primary_category"],
            secondary_categories=sec_cats,
            affinity_score=round(float(r.get("affinity_score") or 0.0), 3),
            format=r.get("format"),
            technical_depth=round(float(r.get("technical_depth") or 1.0), 2),
            assets=r.get("assets") or [],
            raw_answers=r.get("raw_answers"),
            classification_json=r.get("classification_json"),
            trigger_type=r.get("trigger_type") or "manual",
            reason=r.get("reason"),
            status=r.get("status") or "ARCHIVED",
            created_at=r.get("created_at") or ""
        ))

    return PostHistoryResponse(
        tweet_id=tweet_id,
        total_versions=len(history_items),
        history=history_items
    )


@router.post("/{tweet_id}/history/{history_id}/rollback", response_model=RollbackClassificationResponse)
async def rollback_post(
    tweet_id: str,
    history_id: int,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Restaura una clasificación anterior desde post_classification_history:
    - Archiva la versión actual con trigger 'pre_rollback'.
    - Restaura la categoría, afinidad, formato, assets y taxonomy_version de history_id.
    - Marca el registro histórico restaurado con status 'ROLLED_BACK'.
    """
    post = await find_post_by_id(db, tweet_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tweet {tweet_id} no encontrado en la base de datos."
        )

    hist_entry = await get_history_entry_by_id(db, history_id)
    if not hist_entry or str(hist_entry.get("tweet_id")) != str(tweet_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de historial #{history_id} no pertenece al post {tweet_id} o no existe."
        )

    success = await rollback_post_classification(db, tweet_id, history_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al realizar rollback del post {tweet_id} a la versión #{history_id}."
        )

    updated_post = await find_post_by_id(db, tweet_id)
    post_formatted = _format_post_response(updated_post) if updated_post else None

    logger.info(f"Rollback exitoso para post {tweet_id} hacia historial #{history_id} (versión #{hist_entry['version_number']})")
    return RollbackClassificationResponse(
        status="success",
        tweet_id=tweet_id,
        restored_history_id=history_id,
        restored_version=hist_entry["version_number"],
        primary_category=hist_entry["primary_category"],
        post=post_formatted
    )


