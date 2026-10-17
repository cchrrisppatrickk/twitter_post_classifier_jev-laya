"""
test_batch_duplicates.py - Pruebas unitarias de detección de duplicados e ingesta masiva (Subfase 5.12.2).
Verifica:
1. IngestService: estrategia 'skip' actualiza métricas (0ms CPU) y no encola para System 1.
2. IngestService: estrategia 'reclassify' encola posts existentes y reporta reclassified_posts_queued.
3. NDJSON Streaming /api/posts/analyze-batch-stream:
   - 'skip': retorna post existente con telemetry.skipped=True, latency=0.0ms y preserva categoría.
   - 'reclassify': ejecuta Laya, archiva snapshot previo en post_classification_history e incrementa reclassification_count.
4. BatchService: _commit_buffer archiva automáticamente el historial de posts preexistentes.
"""

import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import (
    find_post_by_id,
    get_db,
    get_post_history,
    init_db,
    insert_or_replace_post,
)
from backend.app.main import app
from backend.app.services.batch_service import BatchService
from backend.app.services.ingest_service import IngestService


class TestBatchDuplicates(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.tweet_id_existing = "test_dup_tweet_88801"
        self.tweet_id_new = "test_dup_tweet_88802"

        # Crear post inicial en base de datos
        async with get_db() as db:
            initial_post = {
                "tweet_id": self.tweet_id_existing,
                "post_url": f"https://x.com/dev/status/{self.tweet_id_existing}",
                "author_name": "original_author",
                "author_id": "author_1",
                "content": "Publicación inicial sobre inteligencia artificial",
                "preview_text": "Publicación inicial...",
                "date": "2026-10-10",
                "favorite_count": 10,
                "retweet_count": 2,
                "reply_count": 1,
                "bookmark_count": 0,
                "media_urls": [],
                "media_count": 0,
                "media_type": "none",
                "lang": "es",
                "primary_category": "ia_modelos",
                "secondary_categories": [],
                "affinity_score": 0.82,
                "format": "general_discussion",
                "format_confidence": 0.85,
                "technical_depth": 1.5,
                "assets": [],
                "is_local_first": 0,
                "is_nsfw": 0,
                "is_outlier": 0,
                "status": "CLASSIFIED",
                "engine_used": "laya",
                "inference_latency_ms": 25.0,
                "raw_json": {"initial": "raw_data", "tweet_id": self.tweet_id_existing},
                "classification_json": {"initial": "classification", "primary_category": "ia_modelos"},
                "taxonomy_version": "2.0.0",
                "reclassification_count": 0
            }
            await insert_or_replace_post(db, initial_post)
            await db.commit()

    async def asyncTearDown(self):
        async with get_db() as db:
            for tid in [self.tweet_id_existing, self.tweet_id_new]:
                await db.execute("DELETE FROM post_classification_history WHERE tweet_id = ?;", (tid,))
                await db.execute("DELETE FROM posts WHERE tweet_id = ?;", (tid,))
            await db.commit()

    async def test_01_ingest_service_skip_strategy(self):
        """Verifica que 'skip' solo actualiza métricas de post existente sin encolarlo para Laya."""
        dump_data = {
            "metadata": {"engine": "meridian_twitter_scraper_v2"},
            "posts": [
                {
                    "tweet_id": self.tweet_id_existing,
                    "content": "Texto duplicado pero con más likes",
                    "author": "original_author",
                    "likes": 95,
                    "retweets": 30
                },
                {
                    "tweet_id": self.tweet_id_new,
                    "content": "Completamente nuevo post sobre Python",
                    "author": "new_author",
                    "likes": 5,
                    "retweets": 1
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(dump_data, f)
            tmp_path = Path(f.name)

        try:
            resp, clean_queue = await IngestService.process_ingest_payload(tmp_path, duplicate_strategy="skip")
            self.assertEqual(resp.total_posts_in_file, 2)
            self.assertEqual(resp.new_posts_queued, 1)
            self.assertEqual(resp.reclassified_posts_queued, 0)
            self.assertEqual(resp.existing_posts_updated, 1)

            # Solo el post nuevo debe estar en la cola para clasificación
            self.assertEqual(len(clean_queue), 1)
            self.assertEqual(clean_queue[0].tweet_id, self.tweet_id_new)

            # Verificar que las métricas del post existente se actualizaron en SQLite
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id_existing)
                self.assertIsNotNone(p)
                self.assertEqual(p["favorite_count"], 95)
                self.assertEqual(p["retweet_count"], 30)
                self.assertEqual(p["primary_category"], "ia_modelos")  # Categoría intacta

                # No debe haber historial registrado
                hist = await get_post_history(db, self.tweet_id_existing)
                self.assertEqual(len(hist), 0)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    async def test_02_ingest_service_reclassify_strategy(self):
        """Verifica que 'reclassify' encola tanto nuevos como duplicados para re-evaluación."""
        dump_data = {
            "posts": [
                {
                    "tweet_id": self.tweet_id_existing,
                    "content": "Ollama local execution on RTX 4090",
                    "author": "original_author",
                    "likes": 120
                },
                {
                    "tweet_id": self.tweet_id_new,
                    "content": "TypeScript tutorial release",
                    "author": "new_author",
                    "likes": 12
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(dump_data, f)
            tmp_path = Path(f.name)

        try:
            resp, clean_queue = await IngestService.process_ingest_payload(tmp_path, duplicate_strategy="reclassify")
            self.assertEqual(resp.total_posts_in_file, 2)
            self.assertEqual(resp.new_posts_queued, 1)
            self.assertEqual(resp.reclassified_posts_queued, 1)
            self.assertEqual(len(clean_queue), 2)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_03_analyze_batch_stream_skip(self):
        """Verifica que /api/posts/analyze-batch-stream con duplicate_strategy='skip' omita inferencia."""
        client = TestClient(app)
        payload = {
            "posts": [
                {
                    "id": self.tweet_id_existing,
                    "text": "Nuevo texto sobre computación cuántica",
                    "author": "original_author",
                    "likes": 250,
                    "retweets": 80
                }
            ],
            "persist": True,
            "duplicate_strategy": "skip"
        }

        with client.stream("POST", "/api/posts/analyze-batch-stream", json=payload) as resp:
            self.assertEqual(resp.status_code, 200)
            lines = [line for line in resp.iter_lines() if line]
            self.assertGreaterEqual(len(lines), 2)

            item_data = json.loads(lines[0])
            self.assertEqual(item_data["event"], "item_completed")
            self.assertTrue(item_data["telemetry"]["skipped"])
            self.assertEqual(item_data["telemetry"]["latency_ms"], 0.0)

            post_obj = item_data["post"]
            self.assertEqual(post_obj["tweet_id"], self.tweet_id_existing)
            self.assertEqual(post_obj["primary_category"], "ia_modelos")  # Mantiene original
            self.assertEqual(post_obj["reclassification_count"], 0)

        # En DB, métricas actualizadas pero 0 historial
        loop = asyncio.get_event_loop()
        async def verify_db():
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id_existing)
                self.assertEqual(p["favorite_count"], 250)
                hist = await get_post_history(db, self.tweet_id_existing)
                self.assertEqual(len(hist), 0)
        loop.run_until_complete(verify_db())

    def test_04_analyze_batch_stream_reclassify(self):
        """Verifica que /api/posts/analyze-batch-stream con duplicate_strategy='reclassify' archive historial."""
        client = TestClient(app)
        payload = {
            "posts": [
                {
                    "id": self.tweet_id_existing,
                    "text": "ollama run llama3 on RTX 4090 local hardware offline",
                    "author": "original_author",
                    "likes": 300,
                    "retweets": 90
                }
            ],
            "persist": True,
            "duplicate_strategy": "reclassify"
        }

        with client.stream("POST", "/api/posts/analyze-batch-stream", json=payload) as resp:
            self.assertEqual(resp.status_code, 200)
            lines = [line for line in resp.iter_lines() if line]
            item_data = json.loads(lines[0])

            self.assertEqual(item_data["event"], "item_completed")
            self.assertTrue(item_data["telemetry"]["reclassified"])
            post_obj = item_data["post"]
            self.assertEqual(post_obj["reclassification_count"], 1)

        # En DB, debe haber 1 registro en historial con versión anterior
        loop = asyncio.get_event_loop()
        async def verify_history():
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id_existing)
                self.assertEqual(p["reclassification_count"], 1)

                hist = await get_post_history(db, self.tweet_id_existing)
                self.assertEqual(len(hist), 1)
                self.assertEqual(hist[0]["trigger_type"], "bulk_reclassify")
                self.assertEqual(hist[0]["primary_category"], "ia_modelos")  # La que tenía antes
                self.assertEqual(hist[0]["version_number"], 1)
        loop.run_until_complete(verify_history())

    async def test_05_batch_service_commit_buffer_archives_history(self):
        """Verifica que _commit_buffer en BatchService archive automáticamente el historial."""
        batch_svc = BatchService.get_instance()
        batch_id = "test_batch_commit_1"
        batch_svc.latencies[batch_id] = [28.0]
        batch_svc.processed_items[batch_id] = 1

        new_post_dict = {
            "tweet_id": self.tweet_id_existing,
            "post_url": f"https://x.com/dev/status/{self.tweet_id_existing}",
            "author_name": "original_author",
            "content": "Reclasificado vía BatchService",
            "date": "2026-10-15",
            "favorite_count": 500,
            "retweet_count": 100,
            "reply_count": 2,
            "bookmark_count": 5,
            "media_urls": [],
            "media_count": 0,
            "media_type": "none",
            "lang": "es",
            "primary_category": "ia_local",
            "secondary_categories": [],
            "affinity_score": 0.94,
            "format": "technical_deepdive",
            "format_confidence": 0.90,
            "technical_depth": 3.0,
            "assets": ["github"],
            "is_local_first": 1,
            "is_nsfw": 0,
            "is_outlier": 0,
            "status": "CLASSIFIED",
            "engine_used": "laya",
            "inference_latency_ms": 22.0,
            "raw_json": {"second": "run"},
            "classification_json": {"new": "classification", "primary_category": "ia_local"},
            "taxonomy_version": "2.1.0",
            "reclassification_count": 0
        }

        # Ejecutar commit_buffer
        await batch_svc._commit_buffer(batch_id, [new_post_dict], self.tweet_id_existing)

        # Comprobar que en la base de datos se archivó el post previo
        async with get_db() as db:
            p = await find_post_by_id(db, self.tweet_id_existing)
            self.assertEqual(p["primary_category"], "ia_local")
            self.assertEqual(p["reclassification_count"], 1)

            hist = await get_post_history(db, self.tweet_id_existing)
            self.assertGreaterEqual(len(hist), 1)
            self.assertEqual(hist[0]["primary_category"], "ia_modelos")


if __name__ == "__main__":
    unittest.main()
