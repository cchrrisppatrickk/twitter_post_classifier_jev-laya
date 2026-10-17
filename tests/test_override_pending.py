"""
test_override_pending.py - Pruebas unitarias para la resolución interactiva de posts PENDING (Subfase 5.8).
"""

import asyncio
import json
from pathlib import Path
import sys
import unittest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.config import settings
from app.database import get_connection, init_db, insert_or_replace_post
from app.main import app


class TestOverridePending(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        cls.test_db_path = settings.DATA_DIR / "test_override.sqlite"
        if cls.test_db_path.exists():
            cls.test_db_path.unlink()
        settings.DATABASE_PATH = cls.test_db_path

        asyncio.run(init_db())

        # Seed de un post en estado PENDING con video Meridian
        async def seed():
            db = await get_connection()
            try:
                await insert_or_replace_post(db, {
                    "tweet_id": "9999000000000000001",
                    "post_url": "https://x.com/Stefan_3D_AI/status/9999000000000000001",
                    "content": "Mixamo rigging tool released for Blender users.",
                    "author_name": "Stefan_3D_AI",
                    "date": "2026-10-14 12:00:00",
                    "favorite_count": 85,
                    "retweet_count": 12,
                    "media_urls": ["https://video.twimg.com/amplify_video/test.mp4"],
                    "media_type": "video",
                    "primary_category": "otros",
                    "secondary_categories": [{"id": "blender_addons", "score": 0.45}, {"id": "herramientas_ia", "score": 0.42}],
                    "affinity_score": 0.48,
                    "status": "PENDING",
                    "assets": ["mixamo", "blender"]
                })
                await db.commit()
            finally:
                await db.close()

        asyncio.run(seed())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(0.1)
        for p in [cls.test_db_path, cls.test_db_path.with_name("test_override.sqlite-wal"), cls.test_db_path.with_name("test_override.sqlite-shm")]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        settings.DATABASE_PATH = cls._original_db_path

    def test_override_pending_post_success(self):
        """Verifica que POST /api/posts/{id}/override reclasifique el post y devuelva el post enriquecido."""
        payload = {
            "primary_category": "blender_addons",
            "secondary_categories": ["herramientas_ia"],
            "status": "CLASSIFIED_MANUAL"
        }
        resp = self.client.post("/api/posts/9999000000000000001/override", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["primary_category"], "blender_addons")
        self.assertEqual(data["new_status"], "CLASSIFIED_MANUAL")
        self.assertIn("post", data)
        self.assertIsNotNone(data["post"])
        self.assertEqual(data["post"]["primary_category"], "blender_addons")
        self.assertEqual(data["post"]["status"], "CLASSIFIED_MANUAL")
        self.assertEqual(data["post"]["media_type"], "video")
        self.assertEqual(data["post"]["media_urls"], ["https://video.twimg.com/amplify_video/test.mp4"])
        print("✓ Respuesta de override contiene el modelo PostResponse enriquecido.")

        # Verificar persistencia en base de datos mediante GET /api/posts/{id}
        get_resp = self.client.get("/api/posts/9999000000000000001")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["primary_category"], "blender_addons")
        self.assertEqual(get_data["status"], "CLASSIFIED_MANUAL")
        self.assertEqual(get_data["affinity_score"], 1.0)
        print("✓ Persistencia en SQLite WAL verificada: status=CLASSIFIED_MANUAL, score=1.0.")

        # Verificar registro en taxonomy_feedback
        async def check_feedback():
            db = await get_connection()
            try:
                async with db.execute("SELECT * FROM taxonomy_feedback WHERE tweet_id = ?", ("9999000000000000001",)) as cursor:
                    row = await cursor.fetchone()
                    self.assertIsNotNone(row)
                    self.assertEqual(row["resolved_category"], "blender_addons")
                    self.assertEqual(row["resolved_by"], "manual_user")
            finally:
                await db.close()

        asyncio.run(check_feedback())
        print("✓ Registro en tabla taxonomy_feedback confirmado para Active Learning.")


if __name__ == "__main__":
    unittest.main()
