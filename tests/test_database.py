"""
test_database.py - Pruebas automatizadas de persistencia SQLite WAL y deduplicación.
"""

import asyncio
import json
from pathlib import Path
import sys
import unittest

# Inyectar backend en path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import (
    find_post_by_id,
    get_connection,
    init_db,
    insert_or_replace_post,
    resolve_pending_post,
    update_social_metrics,
)


class TestDatabaseWAL(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Usar base de datos temporal de pruebas
        self._original_db_path = settings.DATABASE_PATH
        self.test_db_path = settings.DATA_DIR / "test_database.sqlite"
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        
        # Override de la ruta para los tests
        settings.DATABASE_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        # Limpiar archivos temporales
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        wal_file = Path(str(self.test_db_path) + "-wal")
        shm_file = Path(str(self.test_db_path) + "-shm")
        if wal_file.exists():
            wal_file.unlink()
        if shm_file.exists():
            shm_file.unlink()
        settings.DATABASE_PATH = self._original_db_path

    async def test_wal_mode_active(self):
        """Verifica que SQLite opera efectivamente en modo WAL."""
        db = await get_connection()
        try:
            async with db.execute("PRAGMA journal_mode;") as cursor:
                row = await cursor.fetchone()
                self.assertEqual(row[0].lower(), "wal")
        finally:
            await db.close()

    async def test_insert_and_find_post(self):
        """Verifica la inserción y consulta de una publicación clasificada."""
        db = await get_connection()
        try:
            sample_post = {
                "tweet_id": "2108516129110921241",
                "post_url": "https://x.com/author/status/2108516129110921241",
                "author_name": "TestAuthor",
                "author_id": "12345",
                "content": "Geometry nodes v2 in Blender are amazing! Free open source mixamo tool.",
                "preview_text": "Geometry nodes v2 in Blender...",
                "date": "2026-10-13 14:00:00",
                "favorite_count": 150,
                "retweet_count": 25,
                "reply_count": 5,
                "bookmark_count": 80,
                "media_urls": ["https://video.twimg.com/demo.mp4"],
                "media_count": 1,
                "media_type": "video",
                "lang": "en",
                "primary_category": "blender_geometry_nodes",
                "secondary_categories": [{"id": "modelado_3d", "score": 0.45}],
                "affinity_score": 0.94,
                "format": "launch",
                "format_confidence": 0.92,
                "technical_depth": 3.0,
                "assets": ["github_repo"],
                "is_local_first": 1,
                "is_nsfw": 0,
                "is_outlier": 0,
                "status": "CLASSIFIED",
                "engine_used": "laya",
                "inference_latency_ms": 78.4
            }
            await insert_or_replace_post(db, sample_post)
            await db.commit()

            fetched = await find_post_by_id(db, "2108516129110921241")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["author_name"], "TestAuthor")
            self.assertEqual(fetched["primary_category"], "blender_geometry_nodes")
            self.assertEqual(fetched["media_urls"], ["https://video.twimg.com/demo.mp4"])
            self.assertEqual(fetched["assets"], ["github_repo"])
            self.assertEqual(fetched["favorite_count"], 150)
        finally:
            await db.close()

    async def test_deduplication_social_metrics_update(self):
        """Verifica la ruta rápida de deduplicación (ADR-005): actualización de likes sin tocar inferencia."""
        db = await get_connection()
        try:
            sample_post = {
                "tweet_id": "2108516129110921242",
                "post_url": "https://x.com/author/status/2108516129110921242",
                "author_name": "TestAuthor",
                "author_id": "12345",
                "content": "Old tweet content",
                "preview_text": "Old tweet content",
                "date": "2026-10-10 10:00:00",
                "favorite_count": 10,
                "retweet_count": 2,
                "reply_count": 0,
                "bookmark_count": 1,
                "primary_category": "ia_local",
                "status": "CLASSIFIED",
                "affinity_score": 0.88
            }
            await insert_or_replace_post(db, sample_post)
            await db.commit()

            # Simular re-ingesta con métricas sociales aumentadas
            updated = await update_social_metrics(
                db,
                tweet_id="2108516129110921242",
                favorite_count=850,
                retweet_count=120,
                reply_count=35,
                bookmark_count=410
            )
            await db.commit()
            self.assertTrue(updated)

            # Verificar que las métricas cambiaron pero la categoría y contenido original quedaron intactos
            fetched = await find_post_by_id(db, "2108516129110921242")
            self.assertEqual(fetched["favorite_count"], 850)
            self.assertEqual(fetched["retweet_count"], 120)
            self.assertEqual(fetched["bookmark_count"], 410)
            self.assertEqual(fetched["primary_category"], "ia_local")
            self.assertEqual(fetched["status"], "CLASSIFIED")
        finally:
            await db.close()

    async def test_resolve_pending_workflow(self):
        """Verifica la resolución de un post en PENDING y su auditoría en taxonomy_feedback (ADR-007)."""
        db = await get_connection()
        try:
            pending_post = {
                "tweet_id": "2108516129110921243",
                "post_url": "https://x.com/author/status/2108516129110921243",
                "author_name": "AmbiguousAuthor",
                "author_id": "99999",
                "content": "Spider adventure test. What do you think?",
                "date": "2026-10-12 12:00:00",
                "primary_category": "otros",
                "status": "PENDING",
                "affinity_score": 0.45
            }
            await insert_or_replace_post(db, pending_post)
            await db.commit()

            # Resolver manualmente el post a 'gen_video'
            success = await resolve_pending_post(
                db,
                tweet_id="2108516129110921243",
                primary_category="gen_video",
                secondary_categories=["humor_meme"],
                resolved_by="manual_user"
            )
            self.assertTrue(success)

            # Verificar actualización del post
            fetched = await find_post_by_id(db, "2108516129110921243")
            self.assertEqual(fetched["primary_category"], "gen_video")
            self.assertEqual(fetched["status"], "CLASSIFIED_MANUAL")
            self.assertEqual(fetched["affinity_score"], 1.0)

            # Verificar registro en taxonomy_feedback
            async with db.execute("SELECT * FROM taxonomy_feedback WHERE tweet_id = ?;", ("2108516129110921243",)) as cursor:
                fb = await cursor.fetchone()
                self.assertIsNotNone(fb)
                self.assertEqual(fb["resolved_category"], "gen_video")
                self.assertEqual(fb["resolved_by"], "manual_user")
        finally:
            await db.close()


if __name__ == "__main__":
    unittest.main()
