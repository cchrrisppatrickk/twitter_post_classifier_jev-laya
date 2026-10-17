"""
ingest_service.py - Ingesta Inteligente y Deduplicación Estricta (ADR-005).
Procesa volcados JSON de meridian_twitter_scraper_v2 mediante streaming con ijson,
ejecuta la bifurcación en 0 ms para tweets existentes (solo actualiza métricas sociales)
y encola tweets nuevos para clasificación System 1.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union
import uuid

import aiosqlite
import ijson

from ..config import settings
from ..database import find_post_by_id, get_db, update_social_metrics
from ..registry import detect_asset_domains
from ..schema import CleanPost, IngestResponse, RawPost, SocialMetrics

logger = logging.getLogger("ingest_service")
logging.basicConfig(level=logging.INFO)


def normalize_raw_item(item: Dict[str, Any]) -> Optional[RawPost]:
    """
    Normaliza de forma elástica las variantes de volcados de Twitter:
    - Soporta meridian_twitter_scraper_v2, exportadores directos de X y JSONs planos.
    """
    tweet_id = str(item.get("tweet_id") or item.get("id") or "").strip()
    if not tweet_id:
        return None

    content = str(item.get("content") or item.get("text") or item.get("full_text") or "").strip()
    if not content:
        content = "[Sin contenido textual]"

    # Autor
    author_raw = item.get("author")
    if isinstance(author_raw, dict):
        author_name = str(author_raw.get("name") or author_raw.get("nick") or author_raw.get("username") or author_raw.get("screen_name") or "unknown")
        author_id = str(author_raw.get("id") or "") or None
    else:
        author_name = str(item.get("author_name") or item.get("author") or "unknown")
        author_id = str(item.get("author_id") or "") or None

    # URL
    post_url = str(item.get("post_url") or item.get("url") or f"https://x.com/{author_name}/status/{tweet_id}")

    # Fecha
    date = str(item.get("date") or item.get("created_at") or "")

    # Idioma
    lang = str(item.get("lang") or "en")

    # Métricas
    metrics_raw = item.get("metrics")
    if isinstance(metrics_raw, dict):
        social_metrics = SocialMetrics(
            favorite_count=int(metrics_raw.get("favorite_count") or metrics_raw.get("likes") or 0),
            retweet_count=int(metrics_raw.get("retweet_count") or metrics_raw.get("retweets") or 0),
            reply_count=int(metrics_raw.get("reply_count") or metrics_raw.get("replies") or 0),
            bookmark_count=int(metrics_raw.get("bookmark_count") or metrics_raw.get("bookmarks") or 0),
        )
    else:
        social_metrics = SocialMetrics(
            favorite_count=int(item.get("favorite_count") or item.get("likes") or 0),
            retweet_count=int(item.get("retweet_count") or item.get("retweets") or 0),
            reply_count=int(item.get("reply_count") or item.get("replies") or 0),
            bookmark_count=int(item.get("bookmark_count") or item.get("bookmarks") or 0),
        )

    # Medios (imágenes / videos)
    media_urls: List[str] = []
    media_type = "none"

    raw_media = item.get("media_urls") or item.get("media") or []
    if isinstance(raw_media, list):
        for m in raw_media:
            if isinstance(m, dict) and "url" in m:
                media_urls.append(str(m["url"]))
            elif isinstance(m, str):
                media_urls.append(m)

    cat_field = str(item.get("category") or "").lower()
    if item.get("media_type") in ["video", "photo", "animated_gif", "none"]:
        media_type = item["media_type"]
    elif cat_field == "video":
        media_type = "video"
    elif cat_field in ["image", "photo"]:
        media_type = "photo"
    elif any(u.endswith((".mp4", ".mov", ".m3u8")) or "video" in u for u in media_urls) or item.get("has_video"):
        media_type = "video"
    elif media_urls:
        media_type = "photo"

    return RawPost(
        tweet_id=tweet_id,
        post_url=post_url,
        author_name=author_name,
        author_id=author_id,
        content=content,
        date=date,
        lang=lang,
        metrics=social_metrics,
        media_urls=media_urls,
        media_type=media_type,
        raw_source_json=item
    )


def convert_raw_to_clean(raw: RawPost) -> CleanPost:
    """Prepara el objeto CleanPost con detección determinista de dominios y URLs."""
    detected_assets, found_urls = detect_asset_domains(f"{raw.content} {raw.post_url or ''}")
    # Extraer dominios únicos
    detected_domains: List[str] = []
    for u in found_urls:
        try:
            from urllib.parse import urlparse
            netloc = urlparse(u).netloc
            if netloc and netloc not in detected_domains:
                detected_domains.append(netloc)
        except Exception:
            pass

    return CleanPost(
        tweet_id=raw.tweet_id,
        clean_text=raw.content,
        original_content=raw.content,
        author_name=raw.author_name or "unknown",
        author_id=raw.author_id,
        post_url=raw.post_url or f"https://x.com/i/status/{raw.tweet_id}",
        date=raw.date or "",
        lang=raw.lang or "en",
        metrics=raw.metrics,
        media_urls=raw.media_urls,
        media_count=len(raw.media_urls),
        media_type=raw.media_type,
        detected_assets=detected_assets,
        detected_domains=detected_domains,
        raw_source_json=raw.raw_source_json
    )


class IngestService:
    @staticmethod
    async def parse_posts_from_file(file_path: Union[str, Path]) -> AsyncGenerator[RawPost, None]:
        """
        Generador asíncrono streaming con ijson:
        Lee archivos de cualquier tamaño sin cargarlos completos en memoria RAM (< 40 MB).
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        # Intentar streaming con ijson
        try:
            with open(path, "rb") as f:
                # Comprobar si es un dict con clave 'posts'
                items_iter = ijson.items(f, "posts.item")
                found_any = False
                for item in items_iter:
                    raw = normalize_raw_item(item)
                    if raw:
                        found_any = True
                        yield raw

                # Si no había clave 'posts', probar si es una lista directa en la raíz
                if not found_any:
                    f.seek(0)
                    items_iter = ijson.items(f, "item")
                    for item in items_iter:
                        raw = normalize_raw_item(item)
                        if raw:
                            yield raw
        except Exception as e:
            logger.warning(f"ijson streaming falló o archivo pequeño ({e}). Leyendo con fallback json.load...")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("posts", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            raw = normalize_raw_item(item)
                            if raw:
                                yield raw

    @staticmethod
    async def process_ingest_payload(
        file_path: Union[str, Path],
        duplicate_strategy: str = "skip"
    ) -> Tuple[IngestResponse, List[CleanPost]]:
        """
        Ejecuta el pipeline completo de deduplicación y reclasificación (ADR-005 / Fase 5.12):
        - Para cada post en el volcado:
          * ¿Existe en SQLite?
            - duplicate_strategy == "skip":
              Si métricas cambiaron -> UPDATE métricas (0 ms CPU Laya).
              Si no cambiaron -> Omitir (Unchanged).
            - duplicate_strategy == "reclassify":
              Si métricas cambiaron -> UPDATE métricas.
              Se convierte a CleanPost y se añade a la cola para reclasificar con Laya actual.
            - No existe: Es un post nuevo -> Se convierte a CleanPost y se encola para clasificación.
        """
        batch_id = str(uuid.uuid4())
        total_in_file = 0
        new_posts_queued = 0
        reclassified_posts_queued = 0
        existing_updated = 0
        unchanged_skipped = 0

        new_clean_posts: List[CleanPost] = []

        async with get_db() as db:
            async for raw_post in IngestService.parse_posts_from_file(file_path):
                total_in_file += 1
                tweet_id = raw_post.tweet_id

                existing = await find_post_by_id(db, tweet_id)
                if existing is not None:
                    # RUTA 1: Post ya existente
                    m = raw_post.metrics
                    changed = (
                        existing.get("favorite_count", 0) != m.favorite_count or
                        existing.get("retweet_count", 0) != m.retweet_count or
                        existing.get("reply_count", 0) != m.reply_count or
                        existing.get("bookmark_count", 0) != m.bookmark_count
                    )
                    if changed:
                        await update_social_metrics(
                            db,
                            tweet_id=tweet_id,
                            favorite_count=m.favorite_count,
                            retweet_count=m.retweet_count,
                            reply_count=m.reply_count,
                            bookmark_count=m.bookmark_count
                        )
                        existing_updated += 1
                    else:
                        unchanged_skipped += 1

                    if duplicate_strategy == "reclassify":
                        clean = convert_raw_to_clean(raw_post)
                        new_clean_posts.append(clean)
                        reclassified_posts_queued += 1
                else:
                    # RUTA 2: Post completamente nuevo -> Encolar para System 1
                    clean = convert_raw_to_clean(raw_post)
                    new_clean_posts.append(clean)
                    new_posts_queued += 1

            await db.commit()

        # Tiempo estimado: 2.5s por post en CPU pura Intel Core i5
        total_to_process = new_posts_queued + reclassified_posts_queued
        estimated_time = round(total_to_process * 2.5, 1)

        response = IngestResponse(
            batch_id=batch_id,
            total_posts_in_file=total_in_file,
            new_posts_queued=new_posts_queued,
            reclassified_posts_queued=reclassified_posts_queued,
            existing_posts_updated=existing_updated,
            unchanged_posts_skipped=unchanged_skipped,
            estimated_time_seconds=estimated_time
        )

        logger.info(
            f"Ingesta completada [Batch {batch_id}]: {total_in_file} posts en total. "
            f"Nuevos: {new_posts_queued}, Reclasificar: {reclassified_posts_queued}, "
            f"Actualizados: {existing_updated}, Sin cambios: {unchanged_skipped} (Estrategia: {duplicate_strategy})."
        )
        return response, new_clean_posts

