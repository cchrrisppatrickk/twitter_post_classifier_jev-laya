"""
test_subfase_5_13_1.py - Pruebas automatizadas para Subfase 5.13.1.
Verifica:
1. Corrección del error HTTP 422 con emojis únicos (surrogate pairs Unicode vs code points: '🫧', '🌆', '🌻').
2. Sanitización automática de textos vacíos o nulos en AnalyzePostRequest.
3. Validación exitosa del dataset completo de 1653 bookmarks contra AnalyzeBatchRequest.
4. Ejecución del endpoint /api/posts/analyze-batch-stream con emojis y límite controlado.
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
from app.schema import AnalyzePostRequest, AnalyzeBatchRequest


class TestSubfase5131(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        cls.test_db_path = settings.DATA_DIR / "test_subfase_5_13_1.sqlite"
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
        for p in [cls.test_db_path, cls.test_db_path.with_name("test_subfase_5_13_1.sqlite-wal"), cls.test_db_path.with_name("test_subfase_5_13_1.sqlite-shm")]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        settings.DATABASE_PATH = cls._original_db_path

    def test_single_emoji_and_short_texts_validation(self):
        """Verifica que posts con un único emoji o un solo carácter validen sin error HTTP 422."""
        emojis_and_shorts = ["🫧", "🌆", "🌻", "🚀", "k", "?"]
        for sample in emojis_and_shorts:
            req = AnalyzePostRequest(text=sample, author="emoji_tester")
            self.assertEqual(req.text, sample)
            self.assertGreaterEqual(len(req.text), 1)

    def test_whitespace_and_empty_text_sanitization(self):
        """Verifica que textos vacíos o con solo espacios sean sanitizados automáticamente."""
        req1 = AnalyzePostRequest(text="   ", author="space_user")
        self.assertEqual(req1.text, "[Sin contenido textual]")

        req2 = AnalyzePostRequest(text="", author="empty_user")
        self.assertEqual(req2.text, "[Sin contenido textual]")

    def test_full_bookmarks_dataset_validation(self):
        """Verifica que el dataset real de 1683 bookmarks / 1655 posts normalizados valide al 100%."""
        bookmarks_path = Path("/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/automations/output_files/twitter/extracted_links/extracted_data_https___x_com_i_bookmarks_bookmarks_20261013_101533.json")
        if not bookmarks_path.exists():
            self.skipTest("Archivo de bookmarks no disponible en ruta esperada")

        with open(bookmarks_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        posts_raw = raw_data.get("posts", [])
        self.assertGreater(len(posts_raw), 1000)

        normalized_posts = []
        for idx, item in enumerate(posts_raw):
            text = (item.get("text") or item.get("content") or item.get("full_text") or "").strip()
            if not text:
                continue
            author = "dev_user"
            if isinstance(item.get("author"), dict):
                author = item["author"].get("nick") or item["author"].get("name") or "dev_user"
            elif item.get("author"):
                author = str(item["author"])

            normalized_posts.append({
                "text": text,
                "id": str(item.get("tweet_id") or item.get("id") or f"post_{idx}"),
                "author": author,
                "date": item.get("date"),
                "post_url": item.get("post_url"),
                "likes": item.get("likes", 0),
                "retweets": item.get("retweets", 0),
                "media_urls": item.get("media_urls") or [],
                "media_type": item.get("media_type", "none"),
                "persist": True
            })

        self.assertGreater(len(normalized_posts), 1600)
        # Esto lanzaba HTTP 422 antes del fix en los posts 1077, 1306 y 1639
        batch_req = AnalyzeBatchRequest(posts=normalized_posts, persist=True)
        self.assertEqual(len(batch_req.posts), len(normalized_posts))

    def test_stream_batch_with_emojis_and_limit(self):
        """Verifica que el endpoint de streaming procese posts con emojis y textos breves."""
        payload = {
            "posts": [
                {"id": "emoji_1", "text": "🫧", "author": "bubble_user", "persist": False},
                {"id": "emoji_2", "text": "🌆", "author": "city_user", "persist": False},
                {"id": "normal_3", "text": "New Python framework release with ultra fast async endpoints", "author": "py_dev", "persist": False}
            ],
            "persist": False,
            "duplicate_strategy": "skip"
        }

        response = self.client.post("/api/posts/analyze-batch-stream", json=payload)
        self.assertEqual(response.status_code, 200, f"Error devuelto: {response.text}")

        lines = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
        self.assertEqual(len(lines), 4)  # 3 item_completed + 1 batch_completed

        item1 = json.loads(lines[0])
        self.assertEqual(item1["event"], "item_completed")
        self.assertEqual(item1["index"], 1)
        self.assertEqual(item1["post"]["tweet_id"], "emoji_1")

        final_item = json.loads(lines[-1])
        self.assertEqual(final_item["event"], "batch_completed")
        self.assertEqual(final_item["total"], 3)
        self.assertEqual(final_item["index"], 3)


if __name__ == "__main__":
    unittest.main()
