"""
batch_service.py - Procesamiento Masivo, Colas y Checkpoints (ADR-006).
Worker asíncrono en segundo plano desacoplado de FastAPI vía asyncio.to_thread,
commits a disco cada 25 posts en SQLite WAL, soporte de pausa/reanudación y
telemetría en vivo Server-Sent Events (SSE).
"""

from __future__ import annotations
import asyncio
from datetime import datetime
import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
import uuid

import psutil

from ..config import settings
from ..database import (
    archive_classification_history,
    find_post_by_id,
    get_db,
    insert_or_replace_post,
)
from ..engine import LayaEngine
from ..schema import BatchCheckpointRecord, BatchTelemetry, ClassificationResult, CleanPost

logger = logging.getLogger("batch_service")
logging.basicConfig(level=logging.INFO)


class BatchService:
    _instance: Optional["BatchService"] = None

    def __init__(self):
        self.engine = LayaEngine.get_instance()
        self.queues: Dict[str, List[CleanPost]] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.status: Dict[str, str] = {}  # 'PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED'
        self.telemetry: Dict[str, BatchTelemetry] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.total_items: Dict[str, int] = {}
        self.processed_items: Dict[str, int] = {}
        self.start_times: Dict[str, float] = {}
        self.latencies: Dict[str, List[float]] = {}

    @classmethod
    def get_instance(cls) -> "BatchService":
        if cls._instance is None:
            cls._instance = BatchService()
        return cls._instance

    async def enqueue_batch(
        self,
        batch_id: str,
        file_name: str,
        posts: List[CleanPost],
        auto_start: bool = True
    ) -> str:
        """Encola un nuevo lote de posts a clasificar y registra el checkpoint inicial."""
        self.queues[batch_id] = list(posts)
        self.total_items[batch_id] = len(posts)
        self.processed_items[batch_id] = 0
        self.status[batch_id] = "PENDING"
        self.latencies[batch_id] = []
        self.subscribers[batch_id] = []

        # Registrar en la base de datos
        async with get_db() as db:
            query = """
            INSERT INTO batch_checkpoints (
                batch_id, file_name, total_items, processed_items,
                status, checkpoint_interval, avg_latency_ms
            ) VALUES (?, ?, ?, 0, 'PENDING', ?, 0.0)
            ON CONFLICT(batch_id) DO UPDATE SET
                total_items = excluded.total_items,
                status = excluded.status;
            """
            await db.execute(query, (batch_id, file_name, len(posts), settings.CHECKPOINT_INTERVAL))
            await db.commit()

        logger.info(f"Lote encolado [{batch_id}]: {len(posts)} posts nuevos. Auto-start: {auto_start}")
        if auto_start and len(posts) > 0:
            await self.start_batch(batch_id)
        elif len(posts) == 0:
            self.status[batch_id] = "COMPLETED"

        return batch_id

    async def start_batch(self, batch_id: str) -> bool:
        """Inicia o reanuda la ejecución del lote en un hilo en segundo plano."""
        if batch_id not in self.queues or not self.queues[batch_id]:
            logger.warning(f"No hay posts en la cola para el batch {batch_id}")
            self.status[batch_id] = "COMPLETED"
            return False

        if self.status.get(batch_id) == "RUNNING":
            logger.info(f"El batch {batch_id} ya se encuentra en ejecución.")
            return True

        self.status[batch_id] = "RUNNING"
        self.start_times[batch_id] = time.time()

        # Actualizar estado en BD
        async with get_db() as db:
            await db.execute("UPDATE batch_checkpoints SET status = 'RUNNING' WHERE batch_id = ?;", (batch_id,))
            await db.commit()

        # Lanzar tarea asíncrona desacoplada
        task = asyncio.create_task(self._batch_worker(batch_id))
        self.active_tasks[batch_id] = task
        return True

    async def pause_batch(self, batch_id: str) -> bool:
        """Pausa el procesamiento tras completar el ítem actual."""
        if self.status.get(batch_id) == "RUNNING":
            self.status[batch_id] = "PAUSED"
            async with get_db() as db:
                await db.execute("UPDATE batch_checkpoints SET status = 'PAUSED' WHERE batch_id = ?;", (batch_id,))
                await db.commit()
            logger.info(f"Batch {batch_id} pausado por el usuario.")
            return True
        return False

    async def _batch_worker(self, batch_id: str) -> None:
        """Worker principal que procesa la cola de posts sin bloquear el Event Loop de FastAPI."""
        logger.info(f"Iniciando worker de fondo para el lote: {batch_id}")
        posts_queue = self.queues[batch_id]
        total = self.total_items[batch_id]

        commit_buffer: List[Dict[str, Any]] = []
        last_tweet_id = None

        while posts_queue and self.status.get(batch_id) == "RUNNING":
            clean_post = posts_queue.pop(0)

            # Inferencia no bloqueante en hilo secundario de PyTorch
            t_start = time.perf_counter()
            try:
                res: ClassificationResult = await asyncio.to_thread(
                    self.engine.classify_post, clean_post
                )
            except Exception as e:
                logger.error(f"Error procesando tweet {clean_post.tweet_id}: {e}", exc_info=True)
                res = ClassificationResult(
                    primary_category="otros",
                    status="PENDING",
                    affinity_score=0.0
                )

            latency_ms = (time.perf_counter() - t_start) * 1000.0
            self.latencies[batch_id].append(latency_ms)

            # Construir dict para la tabla posts
            post_dict = {
                "tweet_id": clean_post.tweet_id,
                "post_url": clean_post.post_url,
                "author_name": clean_post.author_name,
                "author_id": clean_post.author_id,
                "content": clean_post.original_content,
                "preview_text": clean_post.original_content[:140],
                "date": clean_post.date,
                "favorite_count": clean_post.metrics.favorite_count,
                "retweet_count": clean_post.metrics.retweet_count,
                "reply_count": clean_post.metrics.reply_count,
                "bookmark_count": clean_post.metrics.bookmark_count,
                "media_urls": clean_post.media_urls,
                "media_count": clean_post.media_count,
                "media_type": clean_post.media_type,
                "lang": clean_post.lang,
                "primary_category": res.primary_category,
                "secondary_categories": [c.model_dump() for c in res.secondary_categories],
                "affinity_score": res.affinity_score,
                "format": res.format,
                "format_confidence": res.format_confidence,
                "technical_depth": res.technical_depth,
                "assets": res.assets,
                "is_local_first": 1 if res.is_local_first else 0,
                "is_nsfw": 1 if res.is_nsfw else 0,
                "is_outlier": 1 if res.is_outlier else 0,
                "status": res.status,
                "engine_used": res.engine_used,
                "inference_latency_ms": res.inference_latency_ms,
                "raw_json": clean_post.raw_source_json or clean_post.model_dump(),
                "classification_json": res.model_dump(),
                "taxonomy_version": settings.APP_VERSION,
                "reclassification_count": 0
            }

            commit_buffer.append(post_dict)
            self.processed_items[batch_id] += 1
            last_tweet_id = clean_post.tweet_id

            # Emitir telemetría cada tweet o lote
            await self._broadcast_telemetry(batch_id)

            # Checkpoint transaccional cada checkpoint_interval (25 posts)
            if len(commit_buffer) >= settings.CHECKPOINT_INTERVAL:
                await self._commit_buffer(batch_id, commit_buffer, last_tweet_id)
                commit_buffer = []

            # Micro-pausa (5 ms) para ceder CPU al servidor web y SSE
            await asyncio.sleep(settings.YIELD_SLEEP_SECONDS)

        # Commit final de remanentes
        if commit_buffer:
            await self._commit_buffer(batch_id, commit_buffer, last_tweet_id)

        # Si finalizó todos los posts
        if not posts_queue:
            self.status[batch_id] = "COMPLETED"
            avg_lat = sum(self.latencies[batch_id]) / max(len(self.latencies[batch_id]), 1)
            async with get_db() as db:
                await db.execute(
                    """
                    UPDATE batch_checkpoints
                    SET status = 'COMPLETED',
                        processed_items = ?,
                        avg_latency_ms = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE batch_id = ?;
                    """,
                    (self.processed_items[batch_id], round(avg_lat, 2), batch_id)
                )
                await db.commit()
            logger.info(f"Lote {batch_id} COMPLETADO con éxito ({self.processed_items[batch_id]} posts clasificados).")
            await self._broadcast_telemetry(batch_id)

    async def _commit_buffer(self, batch_id: str, buffer: List[Dict[str, Any]], last_id: Optional[str]) -> None:
        """Ejecuta un commit atómico en SQLite WAL archivando historial si es reclasificación."""
        async with get_db() as db:
            for item in buffer:
                tweet_id = item.get("tweet_id")
                if tweet_id:
                    existing = await find_post_by_id(db, tweet_id)
                    if existing:
                        await archive_classification_history(
                            db,
                            existing_post=existing,
                            trigger_type="bulk_reclassify",
                            notes=f"Reclasificación en lote batch_id={batch_id}"
                        )
                        item["reclassification_count"] = (existing.get("reclassification_count") or 0) + 1
                        if not item.get("raw_json") and existing.get("raw_json"):
                            item["raw_json"] = existing.get("raw_json")
                await insert_or_replace_post(db, item)

            avg_lat = sum(self.latencies[batch_id]) / max(len(self.latencies[batch_id]), 1)
            await db.execute(
                """
                UPDATE batch_checkpoints
                SET processed_items = ?,
                    last_processed_tweet_id = ?,
                    avg_latency_ms = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE batch_id = ?;
                """,
                (self.processed_items[batch_id], last_id, round(avg_lat, 2), batch_id)
            )
            await db.commit()
        logger.info(f"Checkpoint commit [{batch_id}]: {len(buffer)} posts persistidos en disco.")

        # Liberar memoria de PyTorch y compactar glibc heap en cada checkpoint
        if hasattr(self.engine, "check_memory_safety"):
            try:
                self.engine.check_memory_safety(force=True)
            except Exception as e:
                logger.warning(f"Error ejecutando check_memory_safety en commit_buffer: {e}")

    async def _broadcast_telemetry(self, batch_id: str) -> None:
        """Calcula métricas de hardware y emite el evento SSE a todos los suscriptores conectados."""
        processed = self.processed_items.get(batch_id, 0)
        total = max(self.total_items.get(batch_id, 1), 1)
        percentage = round((processed / total) * 100.0, 1)

        elapsed = time.time() - self.start_times.get(batch_id, time.time())
        speed_tps = round(processed / max(elapsed, 0.001), 2)

        lat_list = self.latencies.get(batch_id, [])
        avg_lat = round(sum(lat_list[-25:]) / max(len(lat_list[-25:]), 1), 1)

        remaining = max(total - processed, 0)
        # En CPU, cada tweet toma ~avg_lat ms
        eta_sec = round((remaining * max(avg_lat, 1000.0)) / 1000.0, 1)

        vm = psutil.virtual_memory()
        proc = psutil.Process(os.getpid())
        ram_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        cpu_pct = round(psutil.cpu_percent(interval=None), 1)

        telem = BatchTelemetry(
            batch_id=batch_id,
            status=self.status.get(batch_id, "PENDING"),
            processed=processed,
            total=total,
            percentage=percentage,
            speed_tps=speed_tps,
            avg_latency_ms=avg_lat,
            cpu_percent=cpu_pct,
            ram_mb=ram_mb,
            eta_seconds=eta_sec
        )
        self.telemetry[batch_id] = telem

        # Difundir a colas de suscriptores
        subs = self.subscribers.get(batch_id, [])
        for q in subs:
            try:
                q.put_nowait(telem)
            except Exception:
                pass

    async def subscribe_telemetry(self, batch_id: str) -> AsyncGenerator[BatchTelemetry, None]:
        """Generador asíncrono para endpoints SSE de FastAPI."""
        q: asyncio.Queue[BatchTelemetry] = asyncio.Queue()
        if batch_id not in self.subscribers:
            self.subscribers[batch_id] = []
        self.subscribers[batch_id].append(q)

        # Emitir estado actual si existe
        if batch_id in self.telemetry:
            yield self.telemetry[batch_id]

        try:
            while True:
                telem = await q.get()
                yield telem
                if telem.status in ["COMPLETED", "FAILED"]:
                    break
        finally:
            if batch_id in self.subscribers and q in self.subscribers[batch_id]:
                self.subscribers[batch_id].remove(q)

    def get_batch_status(self, batch_id: str) -> Optional[BatchTelemetry]:
        return self.telemetry.get(batch_id)
