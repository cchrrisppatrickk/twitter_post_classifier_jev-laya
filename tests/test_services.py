"""
test_services.py - Pruebas de integración de Servicios de Negocio:
Ingesta Inteligente con deduplicación, Batch Runner con checkpoints y Stats Service.
"""

import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Inyectar backend en path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import find_post_by_id, get_connection, init_db
from app.schema import CleanPost, SocialMetrics
from app.services.batch_service import BatchService
from app.services.ingest_service import IngestService
from app.services.stats_service import StatsService


class TestServicesIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Base de datos temporal
        self._original_db_path = settings.DATABASE_PATH
        self.test_db_path = settings.DATA_DIR / "test_services.sqlite"
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        settings.DATABASE_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        wal = Path(str(self.test_db_path) + "-wal")
        shm = Path(str(self.test_db_path) + "-shm")
        if wal.exists():
            wal.unlink()
        if shm.exists():
            shm.unlink()
        settings.DATABASE_PATH = self._original_db_path

    async def test_ingest_and_deduplication_flow(self):
        """Verifica la ingesta de JSON, deduplicación estricta y refresco de métricas."""
        # 1. Crear archivo JSON temporal con formato del scraper
        sample_dump = {
            "metadata": {"scraper": "meridian_twitter_scraper_v2", "count": 2},
            "posts": [
                {
                    "tweet_id": "3000000000000000001",
                    "content": "Check this new Flux LoRA on Civitai https://civitai.com/models/123",
                    "author": {"name": "LoRACreator", "id": "111"},
                    "date": "2026-10-13 10:00:00",
                    "metrics": {"favorite_count": 50, "retweet_count": 10, "reply_count": 2, "bookmark_count": 15},
                    "lang": "en"
                },
                {
                    "tweet_id": "3000000000000000002",
                    "content": "Godot 4.3 release candidate is out with improved render pipelines! https://github.com/godotengine/godot",
                    "author": {"name": "GameDevNews", "id": "222"},
                    "date": "2026-10-13 11:00:00",
                    "metrics": {"favorite_count": 200, "retweet_count": 45, "reply_count": 8, "bookmark_count": 90},
                    "lang": "en"
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(sample_dump, f)
            temp_path = f.name

        try:
            # 2. Primera ingesta: ambos posts deben ser detectados como nuevos
            res1, new_posts = await IngestService.process_ingest_payload(temp_path)
            self.assertEqual(res1.total_posts_in_file, 2)
            self.assertEqual(res1.new_posts_queued, 2)
            self.assertEqual(res1.existing_posts_updated, 0)
            self.assertEqual(res1.unchanged_posts_skipped, 0)
            self.assertEqual(len(new_posts), 2)

            # Simular que el batch runner clasifica e inserta los 2 posts
            db = await get_connection()
            try:
                from app.database import insert_or_replace_post
                for p in new_posts:
                    await insert_or_replace_post(db, {
                        "tweet_id": p.tweet_id,
                        "content": p.clean_text,
                        "author_name": p.author_name,
                        "date": p.date,
                        "favorite_count": p.metrics.favorite_count,
                        "retweet_count": p.metrics.retweet_count,
                        "reply_count": p.metrics.reply_count,
                        "bookmark_count": p.metrics.bookmark_count,
                        "primary_category": "gen_imagenes",
                        "status": "CLASSIFIED"
                    })
                await db.commit()
            finally:
                await db.close()

            # 3. Segunda ingesta del mismo archivo: ahora post 1 aumentó a 850 likes y post 2 sigue igual
            sample_dump["posts"][0]["metrics"]["favorite_count"] = 850
            sample_dump["posts"][0]["metrics"]["bookmark_count"] = 320

            with open(temp_path, "w") as f:
                json.dump(sample_dump, f)

            res2, new_posts2 = await IngestService.process_ingest_payload(temp_path)
            self.assertEqual(res2.total_posts_in_file, 2)
            self.assertEqual(res2.new_posts_queued, 0)  # Cero llamadas a Laya!
            self.assertEqual(res2.existing_posts_updated, 1)  # Solo post 1 cambió
            self.assertEqual(res2.unchanged_posts_skipped, 1)  # Post 2 sin cambios

            # Verificar que en base de datos el post 1 tiene los 850 likes actualizados
            db = await get_connection()
            try:
                p1 = await find_post_by_id(db, "3000000000000000001")
                self.assertEqual(p1["favorite_count"], 850)
                self.assertEqual(p1["bookmark_count"], 320)
            finally:
                await db.close()

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def test_stats_service_aggregation(self):
        """Verifica que StatsService genere la distribución completa de 47 categorías y 8 familias."""
        db = await get_connection()
        try:
            from app.database import insert_or_replace_post
            await insert_or_replace_post(db, {
                "tweet_id": "4000000000000000001",
                "content": "Blender geometry nodes procedural building tutorial.",
                "author_name": "3dWizard",
                "date": "2026-10-13 14:00:00",
                "favorite_count": 300,
                "primary_category": "blender_geometry_nodes",
                "affinity_score": 0.92,
                "status": "CLASSIFIED"
            })
            await insert_or_replace_post(db, {
                "tweet_id": "4000000000000000002",
                "content": "Casual thoughts on gaming.",
                "author_name": "Gamer12",
                "date": "2026-10-13 15:00:00",
                "favorite_count": 50,
                "primary_category": "otros",
                "affinity_score": 0.40,
                "status": "PENDING"
            })
            await db.commit()

            stats = await StatsService.get_dashboard_stats(db)
            self.assertEqual(stats.total_posts, 2)
            self.assertEqual(stats.classified_count, 1)
            self.assertEqual(stats.pending_count, 1)
            self.assertEqual(stats.outliers_count, 0)
            self.assertGreater(stats.avg_affinity_score, 0.0)

            # Las 48 categorías deben estar presentes en la Waffle Grid
            self.assertEqual(len(stats.categories_distribution), 48)
            # Las 8 familias raíz deben estar presentes
            self.assertEqual(len(stats.families_distribution), 8)
            # Puntos de scatter
            self.assertEqual(len(stats.scatter_points), 2)
            self.assertEqual(stats.scatter_points[0].primary in ["blender_geometry_nodes", "otros"], True)
        finally:
            await db.close()

    async def test_batch_service_execution(self):
        """Verifica la ejecución de un lote pequeño por el BatchService con telemetría."""
        batch_svc = BatchService.get_instance()
        batch_id = "test-batch-001"

        post = CleanPost(
            tweet_id="5000000000000000001",
            clean_text="Geometry nodes in Blender are amazing! Free open source repo https://github.com/blender/gn",
            original_content="Geometry nodes in Blender are amazing!",
            author_name="BlenderUser",
            post_url="https://x.com/BlenderUser/status/5000000000000000001",
            date="2026-10-13 16:00:00",
            lang="en",
            metrics=SocialMetrics(favorite_count=100),
            media_urls=[],
            media_type="none",
            media_count=0,
            detected_assets=["github_repo"],
            detected_domains=["github.com"]
        )

        # Encolar y ejecutar
        await batch_svc.enqueue_batch(batch_id, "test_file.json", [post], auto_start=True)

        # Esperar que la tarea termine
        if batch_id in batch_svc.active_tasks:
            await batch_svc.active_tasks[batch_id]

        self.assertEqual(batch_svc.status.get(batch_id), "COMPLETED")
        self.assertEqual(batch_svc.processed_items.get(batch_id), 1)

        # Verificar que el post fue persistido en SQLite
        db = await get_connection()
        try:
            persisted = await find_post_by_id(db, "5000000000000000001")
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted["status"], "CLASSIFIED")
            self.assertIn("github_repo", persisted["assets"])
        finally:
            await db.close()


if __name__ == "__main__":
    unittest.main()

