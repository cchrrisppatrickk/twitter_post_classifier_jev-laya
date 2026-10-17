"""
test_analyze.py - Pruebas de integración para el endpoint de análisis interactivo POST /api/posts/analyze.
"""

from pathlib import Path
import sys
import unittest
from fastapi.testclient import TestClient

# Inyectar backend en sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import get_connection, init_db
from app.main import app


class TestAnalyzeEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        cls.test_db_path = settings.DATA_DIR / "test_analyze.sqlite"
        if cls.test_db_path.exists():
            cls.test_db_path.unlink()
        settings.DATABASE_PATH = cls.test_db_path

        import asyncio
        asyncio.run(init_db())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(0.1)
        for p in [cls.test_db_path, cls.test_db_path.with_name("test_analyze.sqlite-wal"), cls.test_db_path.with_name("test_analyze.sqlite-shm")]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        settings.DATABASE_PATH = cls._original_db_path

    def test_analyze_single_post_success(self):
        """Verifica la inferencia System 1 para un post en vivo sin persistencia."""
        payload = {
            "text": "Nuevo tutorial para crear procedural materials y shaders en Blender con python addon",
            "author": "blender_guru",
            "likes": 250,
            "retweets": 45,
            "persist": False
        }
        response = self.client.post("/api/posts/analyze", json=payload)
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()

        # Validar campos esenciales
        self.assertTrue(data["tweet_id"].startswith("manual_"))
        self.assertEqual(data["author_name"], "blender_guru")
        self.assertTrue(len(data["primary_category"]) > 0)
        self.assertTrue(len(data["category_label"]) > 0)
        self.assertTrue(len(data["family_id"]) > 0)
        self.assertTrue(data["color_hex"].startswith("#"))
        self.assertTrue(len(data["code"]) >= 2)
        self.assertGreaterEqual(data["affinity_score"], 0.0)
        self.assertLessEqual(data["affinity_score"], 1.0)
        self.assertGreater(data["inference_latency_ms"], 0.0)
        self.assertIsInstance(data["secondary_categories"], list)
        self.assertIsInstance(data["assets"], list)
        self.assertIsInstance(data["raw_answers"], dict)
        self.assertIn("category", data["raw_answers"])
        self.assertFalse(data["persisted"])

    def test_analyze_and_persist_to_sqlite(self):
        """Verifica que el análisis persista en SQLite WAL cuando persist=True."""
        tweet_id = "manual_persisted_9999"
        payload = {
            "id": tweet_id,
            "text": "Open source local-first AI coding agent released on github.com/test/agent with webgpu acceleration",
            "author": "open_dev",
            "likes": 1200,
            "retweets": 320,
            "persist": True
        }
        response = self.client.post("/api/posts/analyze", json=payload)
        self.assertEqual(response.status_code, 200, f"Error: {response.text}")
        data = response.json()

        self.assertEqual(data["tweet_id"], tweet_id)
        self.assertTrue(data["persisted"])

        # Verificar que se puede consultar inmediatamente por GET /api/posts/{tweet_id}
        get_res = self.client.get(f"/api/posts/{tweet_id}")
        self.assertEqual(get_res.status_code, 200)
        saved = get_res.json()
        self.assertEqual(saved["tweet_id"], tweet_id)
        self.assertEqual(saved["author_name"], "open_dev")
        self.assertEqual(saved["metrics"]["favorite_count"], 1200)

    def test_analyze_invalid_input(self):
        """Valida que una petición sin el campo obligatorio 'text' sea rechazada con 422."""
        response = self.client.post("/api/posts/analyze", json={})
        self.assertEqual(response.status_code, 422)

    def test_analyze_short_or_empty_text_sanitization(self):
        """Valida que textos con solo espacios sean sanitizados automáticamente a '[Sin contenido textual]'."""
        response = self.client.post("/api/posts/analyze", json={"text": "   "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "[Sin contenido textual]")


if __name__ == "__main__":
    unittest.main()
