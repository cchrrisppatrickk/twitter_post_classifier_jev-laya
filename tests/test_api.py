"""
test_api.py - Pruebas de integración para los Endpoints REST de FastAPI.
"""

import json
from pathlib import Path
import sys
import unittest
from fastapi.testclient import TestClient

# Inyectar backend en path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import get_connection, init_db, insert_or_replace_post
from app.main import app


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        # Override de base de datos para pruebas API
        cls.test_db_path = settings.DATA_DIR / "test_api.sqlite"
        if cls.test_db_path.exists():
            cls.test_db_path.unlink()
        settings.DATABASE_PATH = cls.test_db_path

        import asyncio
        asyncio.run(init_db())

        # Seed de 1 post inicial
        async def seed():
            db = await get_connection()
            try:
                await insert_or_replace_post(db, {
                    "tweet_id": "9000000000000000001",
                    "content": "Blender 4.2 LTS Geometry Nodes Rigging tutorial https://github.com/blend/rig",
                    "author_name": "ArtistBlender",
                    "date": "2026-10-13 14:00:00",
                    "favorite_count": 350,
                    "primary_category": "blender_geometry_nodes",
                    "affinity_score": 0.94,
                    "status": "CLASSIFIED",
                    "assets": ["github_repo"]
                })
                await insert_or_replace_post(db, {
                    "tweet_id": "9000000000000000002",
                    "content": "Spider adventure test. What do you think?",
                    "author_name": "DrArcade",
                    "date": "2026-10-13 15:00:00",
                    "favorite_count": 80,
                    "primary_category": "otros",
                    "affinity_score": 0.45,
                    "status": "PENDING"
                })
                await insert_or_replace_post(db, {
                    "tweet_id": "9000000000000000003",
                    "content": "Another cryptic tweet test.",
                    "author_name": "TesterThree",
                    "date": "2026-10-13 15:30:00",
                    "favorite_count": 10,
                    "primary_category": "otros",
                    "affinity_score": 0.35,
                    "status": "PENDING"
                })
                await db.commit()
            finally:
                await db.close()

        asyncio.run(seed())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if cls.test_db_path.exists():
            cls.test_db_path.unlink()
        wal = Path(str(cls.test_db_path) + "-wal")
        shm = Path(str(cls.test_db_path) + "-shm")
        if wal.exists():
            wal.unlink()
        if shm.exists():
            shm.unlink()
        settings.DATABASE_PATH = cls._original_db_path

    def test_system_health_endpoint(self):
        """Verifica GET /api/system/health."""
        resp = self.client.get("/api/system/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["device"], "cpu")
        self.assertTrue("i5" in data["cpu_model"].lower() or "intel" in data["cpu_model"].lower() or len(data["cpu_model"]) > 0)

    def test_system_categories_endpoint(self):
        """Verifica GET /api/system/categories."""
        resp = self.client.get("/api/system/categories")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["registry_version"], "2.1.1")
        self.assertEqual(len(data["topic_categories"]), 48)

    def test_posts_stats_endpoint(self):
        """Verifica GET /api/posts/stats."""
        resp = self.client.get("/api/posts/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total_posts"], 2)
        self.assertEqual(len(data["categories_distribution"]), 48)
        self.assertEqual(len(data["families_distribution"]), 8)
        self.assertGreaterEqual(len(data["scatter_points"]), 2)

    def test_posts_ids_endpoint(self):
        """Verifica GET /api/posts/ids."""
        resp = self.client.get("/api/posts/ids")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("tweet_ids", data)
        self.assertGreaterEqual(data["total"], 2)
        self.assertIn("9000000000000000001", data["tweet_ids"])

    def test_posts_list_and_filter_endpoint(self):
        """Verifica GET /api/posts con filtros."""
        # 1. Sin filtros
        resp = self.client.get("/api/posts?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total"], 2)
        self.assertGreaterEqual(len(data["posts"]), 2)

        # 2. Filtro por status=PENDING
        resp_pending = self.client.get("/api/posts?status=PENDING")
        self.assertEqual(resp_pending.status_code, 200)
        data_pending = resp_pending.json()
        self.assertEqual(data_pending["total"], 1)
        self.assertEqual(data_pending["posts"][0]["tweet_id"], "9000000000000000002")

        # 3. Filtro por search=Blender
        resp_search = self.client.get("/api/posts?search=Blender")
        self.assertEqual(resp_search.status_code, 200)
        data_search = resp_search.json()
        self.assertEqual(data_search["total"], 1)
        self.assertEqual(data_search["posts"][0]["primary_category"], "blender_geometry_nodes")

    def test_override_pending_post_endpoint(self):
        """Verifica POST /api/posts/{tweet_id}/override."""
        payload = {
            "primary_category": "gen_video",
            "secondary_categories": ["humor_meme"],
            "status": "CLASSIFIED_MANUAL"
        }
        resp = self.client.post("/api/posts/9000000000000000003/override", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["primary_category"], "gen_video")

        # Verificar que GET /api/posts/9000000000000000003 ahora tiene el nuevo estado
        post_resp = self.client.get("/api/posts/9000000000000000003")
        self.assertEqual(post_resp.status_code, 200)
        post_data = post_resp.json()
        self.assertEqual(post_data["primary_category"], "gen_video")
        self.assertEqual(post_data["status"], "CLASSIFIED_MANUAL")
        self.assertEqual(post_data["affinity_score"], 1.0)

    def test_ingest_endpoint(self):
        """Verifica POST /api/ingest con carga de archivo JSON multipart."""
        sample_file_content = json.dumps({
            "posts": [
                {
                    "tweet_id": "9000000000000000099",
                    "content": "Check out this AI tool release!",
                    "author": {"name": "TestBot"},
                    "date": "2026-10-13 16:00:00",
                    "metrics": {"favorite_count": 120}
                }
            ]
        }).encode("utf-8")

        files = {"file": ("test_upload.json", sample_file_content, "application/json")}
        resp = self.client.post("/api/ingest?auto_start=false", files=files)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_posts_in_file"], 1)
        self.assertEqual(data["new_posts_queued"], 1)
        self.assertIn("batch_id", data)

    def test_favicon_endpoint(self):
        """Verifica GET /favicon.ico retorna HTTP 204 No Content para silenciar 404s."""
        resp = self.client.get("/favicon.ico")
        self.assertEqual(resp.status_code, 204)


if __name__ == "__main__":
    unittest.main()
