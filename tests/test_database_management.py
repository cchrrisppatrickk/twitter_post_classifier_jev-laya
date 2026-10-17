"""
test_database_management.py - Pruebas automatizadas para Subfase 5.13.2.
Verifica:
1. GET /api/database/stats: Retorno de telemetría de almacenamiento, conteos y modo WAL.
2. GET /api/database/export: Descarga estructurada de copia de seguridad JSON.
3. POST /api/database/reset: Limpieza selectiva de datos de prueba y preservación de taxonomía.
4. POST /api/database/import: Restauración atómica de backup (merge y replace).
5. POST /api/database/optimize: Ejecución de WAL checkpoint y VACUUM.
"""

from pathlib import Path
import sys
import unittest
import json
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import init_db, insert_or_replace_post, archive_classification_history, get_db
from app.main import app


class TestDatabaseManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_db_path = settings.DATABASE_PATH
        cls.test_db_path = settings.DATA_DIR / "test_db_mgmt.sqlite"
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
        for p in [cls.test_db_path, cls.test_db_path.with_name("test_db_mgmt.sqlite-wal"), cls.test_db_path.with_name("test_db_mgmt.sqlite-shm")]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        settings.DATABASE_PATH = cls._original_db_path

    def test_01_stats_endpoint_empty(self):
        """Verifica que /api/database/stats retorne métricas válidas con la BD recién inicializada."""
        response = self.client.get("/api/database/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "HEALTHY")
        self.assertIn("posts_count", data)
        self.assertIn("history_count", data)
        self.assertIn("db_size_formatted", data)
        self.assertIn("journal_mode", data)
        self.assertEqual(data["journal_mode"], "WAL")

    def test_02_seed_export_and_stats(self):
        """Inserta registros de prueba, verifica stats actualizadas y exporta backup JSON."""
        import asyncio

        async def seed():
            async with get_db() as db:
                post_data = {
                    "tweet_id": "tweet_test_1001",
                    "post_url": "https://x.com/dev/status/1001",
                    "author_name": "ai_dev",
                    "content": "Building local-first AI agent in Python with SQLite WAL persistence",
                    "primary_category": "desarrollo_software",
                    "status": "CLASSIFIED",
                    "affinity_score": 0.95,
                    "raw_json": {"id": "1001", "text": "Building local-first AI agent..."},
                    "classification_json": {"primary_category": "desarrollo_software", "affinity_score": 0.95}
                }
                await insert_or_replace_post(db, post_data)
                await archive_classification_history(
                    db,
                    tweet_id="tweet_test_1001",
                    trigger_type="test_snapshot",
                    reason="Snapshot para prueba de backup"
                )
                await db.commit()

        asyncio.run(seed())

        # Verificar stats con datos
        stats_resp = self.client.get("/api/database/stats")
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.json()
        self.assertEqual(stats["posts_count"], 1)
        self.assertEqual(stats["history_count"], 1)

        # Exportar backup
        export_resp = self.client.get("/api/database/export?include_history=true")
        self.assertEqual(export_resp.status_code, 200)
        self.assertEqual(export_resp.headers.get("content-type"), "application/json")
        self.assertIn("attachment; filename=", export_resp.headers.get("content-disposition", ""))

        backup_json = export_resp.json()
        self.assertIn("metadata", backup_json)
        self.assertIn("posts", backup_json)
        self.assertIn("history", backup_json)
        self.assertEqual(len(backup_json["posts"]), 1)
        self.assertEqual(backup_json["posts"][0]["tweet_id"], "tweet_test_1001")
        self.assertEqual(len(backup_json["history"]), 1)

    def test_03_reset_preserves_taxonomy(self):
        """Verifica que POST /api/database/reset limpie posts e historial pero conserve la taxonomía."""
        # 1. Verificar que la taxonomía tiene categorías antes del reset
        cats_before = self.client.get("/api/categories").json()
        total_cats_before = len(cats_before) if isinstance(cats_before, list) else len(cats_before.get("topic_categories", []))
        self.assertEqual(total_cats_before, 48)

        # 2. Ejecutar reset
        reset_payload = {
            "clear_posts": True,
            "clear_history": True,
            "clear_checkpoints": True,
            "clear_feedback": True,
            "vacuum": True
        }
        reset_resp = self.client.post("/api/database/reset", json=reset_payload)
        self.assertEqual(reset_resp.status_code, 200)
        result = reset_resp.json()
        self.assertEqual(result["status"], "SUCCESS")
        self.assertGreaterEqual(result["deleted_posts"], 1)
        self.assertGreaterEqual(result["deleted_history"], 1)

        # 3. Comprobar que stats ahora tiene 0 posts y 0 historial
        stats_after = self.client.get("/api/database/stats").json()
        self.assertEqual(stats_after["posts_count"], 0)
        self.assertEqual(stats_after["history_count"], 0)

        # 4. COMPROBACIÓN CRÍTICA: La taxonomía NUNCA debe ser eliminada
        cats_after = self.client.get("/api/categories").json()
        total_cats_after = len(cats_after) if isinstance(cats_after, list) else len(cats_after.get("topic_categories", []))
        self.assertEqual(total_cats_after, 48, "La taxonomía de categories.json fue afectada por el reset")

    def test_04_import_backup(self):
        """Restaura un backup JSON mediante POST /api/database/import y verifica persistencia."""
        backup_payload = {
            "backup": {
                "metadata": {"version": "2.1.0"},
                "posts": [
                    {
                        "tweet_id": "tweet_restored_2001",
                        "post_url": "https://x.com/restored/status/2001",
                        "author_name": "restored_author",
                        "content": "Restored post after clean reset",
                        "primary_category": "ia_generativa",
                        "affinity_score": 0.88,
                        "raw_json": {"text": "Restored post after clean reset"},
                        "classification_json": {"primary_category": "ia_generativa"}
                    }
                ],
                "history": [
                    {
                        "tweet_id": "tweet_restored_2001",
                        "version_number": 1,
                        "primary_category": "otros",
                        "classification_json": {"primary_category": "otros"}
                    }
                ]
            },
            "mode": "merge"
        }

        import_resp = self.client.post("/api/database/import", json=backup_payload)
        self.assertEqual(import_resp.status_code, 200)
        res = import_resp.json()
        self.assertEqual(res["imported_posts"], 1)
        self.assertEqual(res["imported_history"], 1)

        # Verificar en stats
        stats = self.client.get("/api/database/stats").json()
        self.assertEqual(stats["posts_count"], 1)
        self.assertEqual(stats["history_count"], 1)

    def test_05_optimize_endpoint(self):
        """Verifica que POST /api/database/optimize ejecute checkpoint y vacuum sin errores."""
        resp = self.client.post("/api/database/optimize")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("initial_size_formatted", data)
        self.assertIn("final_size_formatted", data)


if __name__ == "__main__":
    unittest.main()
