"""
test_reclassification_and_history_api.py - Pruebas de integración de Reclasificación Individual, Historial y Rollback (Subfase 5.12.3).
Verifica:
1. POST /api/posts/{id}/reclassify con dry_run=True: Inferencia en memoria, comparativa A/B calculada, no muta SQLite ni crea historial.
2. POST /api/posts/{id}/reclassify con confirm=True: Persiste la nueva clasificación, archiva snapshot en post_classification_history e incrementa reclassification_count.
3. GET /api/posts/{id}/history: Retorna historial ordenado cronológicamente con deserialización completa.
4. POST /api/posts/{id}/history/{history_id}/rollback: Restaura clasificación anterior y genera snapshot pre_rollback.
5. Validación de errores HTTP 404 para posts o registros de historial inexistentes.
"""

import asyncio
import json
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


class TestReclassificationAndHistoryApi(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.client = TestClient(app)
        self.tweet_id = "test_single_reclass_77701"

        # Crear post de prueba inicial
        async with get_db() as db:
            initial_post = {
                "tweet_id": self.tweet_id,
                "post_url": f"https://x.com/dev/status/{self.tweet_id}",
                "author_name": "ai_researcher",
                "author_id": "author_77",
                "content": "Running quantized DeepSeek-R1 locally with llama.cpp and Ollama on Mac M3 Max",
                "preview_text": "Running quantized DeepSeek-R1 locally...",
                "date": "2026-10-12",
                "favorite_count": 450,
                "retweet_count": 85,
                "reply_count": 22,
                "bookmark_count": 60,
                "media_urls": [],
                "media_count": 0,
                "media_type": "none",
                "lang": "en",
                "primary_category": "ia_modelos",
                "secondary_categories": [{"id": "software_ia", "score": 0.4}],
                "affinity_score": 0.72,
                "format": "technical_deepdive",
                "format_confidence": 0.88,
                "technical_depth": 3.0,
                "assets": ["github", "tool"],
                "is_local_first": 1,
                "is_nsfw": 0,
                "is_outlier": 0,
                "status": "CLASSIFIED",
                "engine_used": "laya",
                "inference_latency_ms": 26.5,
                "raw_json": {
                    "tweet_id": self.tweet_id,
                    "content": "Running quantized DeepSeek-R1 locally with llama.cpp and Ollama on Mac M3 Max",
                    "author_name": "ai_researcher"
                },
                "classification_json": {
                    "primary_category": "ia_modelos",
                    "affinity_score": 0.72
                },
                "taxonomy_version": "2.0.0",
                "reclassification_count": 0
            }
            await insert_or_replace_post(db, initial_post)
            await db.commit()

    async def asyncTearDown(self):
        async with get_db() as db:
            await db.execute("DELETE FROM post_classification_history WHERE tweet_id = ?;", (self.tweet_id,))
            await db.execute("DELETE FROM posts WHERE tweet_id = ?;", (self.tweet_id,))
            await db.commit()

    def test_01_reclassify_dry_run_does_not_mutate_db(self):
        """Verifica que dry_run=True retorne el Diff A/B sin modificar la BD."""
        resp = self.client.post(
            f"/api/posts/{self.tweet_id}/reclassify",
            json={"dry_run": True, "confirm": False}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["tweet_id"], self.tweet_id)
        self.assertIn("previous", data)
        self.assertIn("current", data)
        self.assertIn("has_changed", data)
        self.assertIn("delta_affinity", data)

        self.assertEqual(data["previous"]["primary_category"], "ia_modelos")
        self.assertEqual(data["previous"]["reclassification_count"], 0)
        self.assertEqual(data["current"]["reclassification_count"], 0)  # No incrementa en dry_run

        # Comprobar en SQLite que NO hubo cambios ni registros en historial
        loop = asyncio.get_event_loop()
        async def verify_db():
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id)
                self.assertEqual(p["primary_category"], "ia_modelos")
                self.assertEqual(p["reclassification_count"], 0)
                hist = await get_post_history(db, self.tweet_id)
                self.assertEqual(len(hist), 0)
        loop.run_until_complete(verify_db())

    def test_02_reclassify_confirm_persists_and_archives_history(self):
        """Verifica que confirm=True persista la nueva clasificación y cree entrada en historial."""
        resp = self.client.post(
            f"/api/posts/{self.tweet_id}/reclassify",
            json={"dry_run": False, "confirm": True, "reason": "Aceptado cambio a taxonomía v2.1.0"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["tweet_id"], self.tweet_id)
        self.assertEqual(data["previous"]["primary_category"], "ia_modelos")
        self.assertEqual(data["current"]["reclassification_count"], 1)

        # Comprobar en SQLite que sí hubo persistencia e historial
        loop = asyncio.get_event_loop()
        async def verify_db():
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id)
                self.assertEqual(p["reclassification_count"], 1)

                hist = await get_post_history(db, self.tweet_id)
                self.assertEqual(len(hist), 1)
                self.assertEqual(hist[0]["version_number"], 1)
                self.assertEqual(hist[0]["primary_category"], "ia_modelos")
                self.assertEqual(hist[0]["trigger_type"], "single_reclassify")
        loop.run_until_complete(verify_db())

    def test_03_get_post_history_endpoint(self):
        """Verifica que GET /api/posts/{id}/history liste todas las versiones archivadas."""
        # Primero ejecutar reclassify confirm=True para generar historial
        self.client.post(
            f"/api/posts/{self.tweet_id}/reclassify",
            json={"confirm": True, "reason": "Versión 1"}
        )

        resp = self.client.get(f"/api/posts/{self.tweet_id}/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["tweet_id"], self.tweet_id)
        self.assertEqual(data["total_versions"], 1)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["version_number"], 1)
        self.assertEqual(data["history"][0]["primary_category"], "ia_modelos")

    def test_04_rollback_endpoint(self):
        """Verifica que POST /api/posts/{id}/history/{id}/rollback restaure la versión previa."""
        # 1. Primera reclasificación (v1 guardada en historial)
        self.client.post(f"/api/posts/{self.tweet_id}/reclassify", json={"confirm": True})

        # Obtener history_id
        hist_resp = self.client.get(f"/api/posts/{self.tweet_id}/history")
        history_id = hist_resp.json()["history"][0]["id"]

        # 2. Ejecutar Rollback
        rollback_resp = self.client.post(f"/api/posts/{self.tweet_id}/history/{history_id}/rollback")
        self.assertEqual(rollback_resp.status_code, 200)
        rb_data = rollback_resp.json()

        self.assertEqual(rb_data["status"], "success")
        self.assertEqual(rb_data["restored_version"], 1)
        self.assertEqual(rb_data["primary_category"], "ia_modelos")
        self.assertIsNotNone(rb_data["post"])
        self.assertEqual(rb_data["post"]["primary_category"], "ia_modelos")

        # Comprobar en SQLite
        loop = asyncio.get_event_loop()
        async def verify_db():
            async with get_db() as db:
                p = await find_post_by_id(db, self.tweet_id)
                self.assertEqual(p["primary_category"], "ia_modelos")

                # El historial ahora debe tener 2 entradas: la v1 (marcada ROLLED_BACK) y la pre_rollback
                hist = await get_post_history(db, self.tweet_id)
                self.assertEqual(len(hist), 2)
        loop.run_until_complete(verify_db())

    def test_05_errors_404(self):
        """Verifica errores 404 para post o historial inexistente."""
        # Post no encontrado
        resp = self.client.post("/api/posts/nonexistent_tweet_9999/reclassify", json={"dry_run": True})
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get("/api/posts/nonexistent_tweet_9999/history")
        self.assertEqual(resp.status_code, 404)

        # Historial no encontrado
        resp = self.client.post(f"/api/posts/{self.tweet_id}/history/999999/rollback")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
