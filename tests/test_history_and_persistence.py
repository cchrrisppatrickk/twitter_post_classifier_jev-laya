"""
test_history_and_persistence.py - Pruebas unitarias de persistencia dual JSON e historial de clasificaciones (Fase 5.12).
Verifica:
1. Migración DDL y columnas en tabla 'posts' y 'post_classification_history'.
2. Inserción y deserialización fiel de 'raw_json' y 'classification_json'.
3. Ciclo de vida de archivado en historial y versionado secuencial.
4. Rollback seguro de clasificaciones archivadas.
5. Inferencia individual persistente en API con retorno de JSONs completos.
"""

import asyncio
import json
import os
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import (
    archive_classification_history,
    find_post_by_id,
    get_db,
    get_history_entry_by_id,
    get_post_history,
    init_db,
    insert_or_replace_post,
    rollback_post_classification,
)
from backend.app.main import app


class TestHistoryAndPersistence(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Asegurar inicialización y migraciones
        await init_db()
        self.test_tweet_id = "test_persistence_tweet_99901"

    async def asyncTearDown(self):
        # Limpiar datos de prueba
        async with get_db() as db:
            await db.execute("DELETE FROM post_classification_history WHERE tweet_id = ?;", (self.test_tweet_id,))
            await db.execute("DELETE FROM posts WHERE tweet_id = ?;", (self.test_tweet_id,))
            await db.commit()

    async def test_01_schema_columns_and_history_table(self):
        """Verifica que 'posts' tenga las 4 nuevas columnas y exista 'post_classification_history'."""
        async with get_db() as db:
            async with db.execute("PRAGMA table_info(posts);") as cursor:
                cols = {r["name"] for r in await cursor.fetchall()}
                self.assertIn("raw_json", cols)
                self.assertIn("classification_json", cols)
                self.assertIn("taxonomy_version", cols)
                self.assertIn("reclassification_count", cols)

            async with db.execute("PRAGMA table_info(post_classification_history);") as cursor:
                hist_cols = {r["name"] for r in await cursor.fetchall()}
                self.assertIn("id", hist_cols)
                self.assertIn("tweet_id", hist_cols)
                self.assertIn("version_number", hist_cols)
                self.assertIn("taxonomy_version", hist_cols)
                self.assertIn("primary_category", hist_cols)
                self.assertIn("classification_json", hist_cols)
                self.assertIn("trigger_type", hist_cols)
                self.assertIn("status", hist_cols)

    async def test_02_insert_and_retrieve_dual_json(self):
        """Verifica la inserción y recuperación fiel de raw_json y classification_json."""
        raw_metadata = {
            "tweet_id": self.test_tweet_id,
            "text": "Probando Ollama 0.5 con DeepSeek R1 en GPU local",
            "author": {"name": "LocalAIFan", "followers": 1420},
            "metrics": {"likes": 350, "retweets": 45},
            "custom_scraper_flag": "meridian_v2_export"
        }
        laya_output = {
            "primary_category": "ia_local",
            "affinity_score": 0.94,
            "secondary_categories": [{"id": "ia_modelos", "score": 0.81}],
            "raw_answers": {
                "category": {"choice": "ia_local", "confidence": 0.94},
                "domain_boosts": {"ollama": 0.15}
            },
            "engine_used": "laya-cpu",
            "inference_latency_ms": 28.5
        }

        post_data = {
            "tweet_id": self.test_tweet_id,
            "post_url": f"https://x.com/LocalAIFan/status/{self.test_tweet_id}",
            "author_name": "LocalAIFan",
            "content": raw_metadata["text"],
            "date": "2026-10-15",
            "favorite_count": 350,
            "primary_category": "ia_local",
            "secondary_categories": [{"id": "ia_modelos", "score": 0.81}],
            "affinity_score": 0.94,
            "format": "technical_tutorial",
            "status": "CLASSIFIED",
            "raw_json": raw_metadata,
            "classification_json": laya_output,
            "taxonomy_version": "2.1.0",
            "reclassification_count": 0
        }

        async with get_db() as db:
            await insert_or_replace_post(db, post_data)
            await db.commit()

            retrieved = await find_post_by_id(db, self.test_tweet_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["tweet_id"], self.test_tweet_id)
            self.assertEqual(retrieved["primary_category"], "ia_local")
            self.assertEqual(retrieved["taxonomy_version"], "2.1.0")
            self.assertEqual(retrieved["reclassification_count"], 0)

            # Validar deserialización de raw_json
            self.assertIsInstance(retrieved["raw_json"], dict)
            self.assertEqual(retrieved["raw_json"]["author"]["followers"], 1420)
            self.assertEqual(retrieved["raw_json"]["custom_scraper_flag"], "meridian_v2_export")

            # Validar deserialización de classification_json
            self.assertIsInstance(retrieved["classification_json"], dict)
            self.assertEqual(retrieved["classification_json"]["raw_answers"]["domain_boosts"]["ollama"], 0.15)
            self.assertEqual(retrieved["classification_json"]["engine_used"], "laya-cpu")

    async def test_03_archive_history_and_version_increment(self):
        """Verifica el archivado secuencial en post_classification_history."""
        async with get_db() as db:
            # 1. Crear post inicial en versión 1
            await insert_or_replace_post(db, {
                "tweet_id": self.test_tweet_id,
                "post_url": f"https://x.com/dev/status/{self.test_tweet_id}",
                "author_name": "dev",
                "content": "Post original con primera categorización",
                "date": "2026-10-14",
                "primary_category": "ia_modelos",
                "affinity_score": 0.75,
                "status": "CLASSIFIED",
                "taxonomy_version": "2.0.0",
                "reclassification_count": 0
            })
            await db.commit()

            # 2. Archivar versión inicial antes de reclasificar
            hist_id_1 = await archive_classification_history(
                db,
                tweet_id=self.test_tweet_id,
                trigger_type="manual_reclassify",
                reason="Reclasificación por actualización de preguntas en Registry Studio"
            )
            self.assertIsNotNone(hist_id_1)

            # Verificar contador en tabla posts
            post_after = await find_post_by_id(db, self.test_tweet_id)
            self.assertEqual(post_after["reclassification_count"], 1)

            # 3. Aplicar nueva clasificación hacia 'ia_local'
            await insert_or_replace_post(db, {
                "tweet_id": self.test_tweet_id,
                "primary_category": "ia_local",
                "affinity_score": 0.92,
                "taxonomy_version": "2.1.0",
                "reclassification_count": 1
            })
            await db.commit()

            # 4. Archivar versión 2 antes de un override manual
            hist_id_2 = await archive_classification_history(
                db,
                tweet_id=self.test_tweet_id,
                trigger_type="manual_override",
                reason="Ajuste por supervisor humano"
            )
            self.assertIsNotNone(hist_id_2)

            # 5. Consultar historial completo
            history = await get_post_history(db, self.test_tweet_id)
            self.assertEqual(len(history), 2)

            # La más reciente (v2) debe ser la primera en orden cronológico inverso
            self.assertEqual(history[0]["version_number"], 2)
            self.assertEqual(history[0]["primary_category"], "ia_local")
            self.assertEqual(history[0]["trigger_type"], "manual_override")

            # La primera (v1)
            self.assertEqual(history[1]["version_number"], 1)
            self.assertEqual(history[1]["primary_category"], "ia_modelos")
            self.assertEqual(history[1]["taxonomy_version"], "2.0.0")

    async def test_04_rollback_classification(self):
        """Verifica la restauración (rollback) de una versión anterior desde el historial."""
        async with get_db() as db:
            # 1. Crear post original (v1)
            await insert_or_replace_post(db, {
                "tweet_id": self.test_tweet_id,
                "post_url": f"https://x.com/dev/status/{self.test_tweet_id}",
                "author_name": "dev",
                "content": "Tweet de prueba para rollback",
                "date": "2026-10-14",
                "primary_category": "ia_modelos",
                "affinity_score": 0.80,
                "format": "news_update",
                "status": "CLASSIFIED",
                "taxonomy_version": "2.0.0"
            })
            await db.commit()

            # 2. Archivar v1
            h_id = await archive_classification_history(
                db,
                tweet_id=self.test_tweet_id,
                trigger_type="manual_reclassify",
                reason="Previa a reclasificación"
            )

            # 3. Modificar a nueva categoría (ia_agentes)
            await insert_or_replace_post(db, {
                "tweet_id": self.test_tweet_id,
                "primary_category": "ia_agentes",
                "affinity_score": 0.65,
                "format": "general_discussion",
                "taxonomy_version": "2.1.0",
                "reclassification_count": 1
            })
            await db.commit()

            curr_post = await find_post_by_id(db, self.test_tweet_id)
            self.assertEqual(curr_post["primary_category"], "ia_agentes")

            # 4. Ejecutar rollback hacia la v1 (h_id)
            rollback_success = await rollback_post_classification(db, self.test_tweet_id, h_id)
            self.assertTrue(rollback_success)

            # 5. Comprobar que el post en la tabla posts fue restaurado
            restored_post = await find_post_by_id(db, self.test_tweet_id)
            self.assertEqual(restored_post["primary_category"], "ia_modelos")
            self.assertEqual(restored_post["affinity_score"], 0.80)
            self.assertEqual(restored_post["format"], "news_update")
            self.assertEqual(restored_post["status"], "CLASSIFIED_MANUAL")

            # 6. Comprobar que el item en historial quedó marcado como ROLLED_BACK
            hist_item = await get_history_entry_by_id(db, h_id)
            self.assertEqual(hist_item["status"], "ROLLED_BACK")

    def test_05_api_analyze_with_dual_json(self):
        """Verifica que POST /api/posts/analyze devuelva y persista raw_json y classification_json."""
        client = TestClient(app)
        payload = {
            "text": "Nuevo lanzamiento de ComfyUI Desktop con aceleración CPU ONNX",
            "id": self.test_tweet_id,
            "author": "ComfyDev",
            "likes": 500,
            "retweets": 80,
            "date": "2026-10-15",
            "persist": True
        }

        response = client.post("/api/posts/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["tweet_id"], self.test_tweet_id)
        self.assertIn("raw_json", data)
        self.assertIn("classification_json", data)
        self.assertEqual(data["taxonomy_version"], settings.APP_VERSION)
        self.assertEqual(data["reclassification_count"], 0)

        # Verificar consulta profunda GET /api/posts/{tweet_id}
        get_resp = client.get(f"/api/posts/{self.test_tweet_id}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()

        self.assertIsNotNone(get_data["raw_json"])
        self.assertIsNotNone(get_data["classification_json"])
        self.assertEqual(get_data["author_name"], "ComfyDev")
        self.assertEqual(get_data["raw_json"]["author"], "ComfyDev")
        self.assertEqual(get_data["taxonomy_version"], settings.APP_VERSION)


if __name__ == "__main__":
    unittest.main()
