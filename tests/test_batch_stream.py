"""
test_batch_stream.py - Pruebas de integración para POST /api/posts/analyze-batch-stream (NDJSON streaming).
"""

from pathlib import Path
import sys
import unittest
import json
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import init_db
from app.main import app


class TestBatchStreamEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        cls.test_db_path = settings.DATA_DIR / "test_batch_stream.sqlite"
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
        for p in [cls.test_db_path, cls.test_db_path.with_name("test_batch_stream.sqlite-wal"), cls.test_db_path.with_name("test_batch_stream.sqlite-shm")]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        settings.DATABASE_PATH = cls._original_db_path

    def test_batch_stream_three_posts(self):
        """Verifica que un lote de 3 posts se transmita vía NDJSON progresivamente."""
        payload = {
            "posts": [
                {
                    "text": "New open-source LLM model weights released on HuggingFace with PyTorch implementation and local inference",
                    "author": "ai_researcher",
                    "likes": 500,
                    "retweets": 80
                },
                {
                    "text": "Procedural shaders tutorial in Blender 4.2 using geometry nodes and cycle render engine python script",
                    "author": "3d_artist",
                    "likes": 320,
                    "retweets": 40
                },
                {
                    "text": "Ultra-fast CLI tool written in Rust for log parsing and Linux server telemetry monitoring",
                    "author": "cli_dev",
                    "likes": 410,
                    "retweets": 95
                }
            ],
            "persist": True
        }

        response = self.client.post("/api/posts/analyze-batch-stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response.headers.get("content-type", ""))

        lines = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
        self.assertGreaterEqual(len(lines), 4, f"Se esperaban al menos 4 líneas (3 items + 1 batch_completed), recibidas: {len(lines)}")

        items = [json.loads(line) for line in lines]

        # Validar los 3 primeros items
        for i in range(3):
            item = items[i]
            self.assertEqual(item["event"], "item_completed")
            self.assertEqual(item["index"], i + 1)
            self.assertEqual(item["total"], 3)
            self.assertIsNotNone(item["post"])
            self.assertIn("primary_category", item["post"])
            self.assertIn("family_id", item["post"])
            self.assertIn("affinity_score", item["post"])
            self.assertTrue(item["post"]["persisted"])

        # Validar el evento final de batch_completed
        final_item = items[-1]
        self.assertEqual(final_item["event"], "batch_completed")
        self.assertEqual(final_item["total"], 3)
