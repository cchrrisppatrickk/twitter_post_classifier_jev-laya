#!/usr/bin/env python3
"""
test_smart_pending_batch.py - Verificación de Cola Inteligente de Pendientes (Smart Pending Queue)
Valida que el sistema permita procesar lotes controlados (ej. 2 o 10 posts) omitiendo
los posts ya registrados y avanzando de forma automática y consecutiva sobre los pendientes.
"""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import settings
from app.database import init_db
from app.main import app


class TestSmartPendingBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        cls.test_db_path = Path(cls.test_dir) / "test_smart_pending.sqlite"

        cls._original_db_path = settings.DATABASE_PATH
        settings.DATABASE_PATH = cls.test_db_path

        import asyncio
        asyncio.run(init_db())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        settings.DATABASE_PATH = cls._original_db_path
        if Path(cls.test_dir).exists():
            shutil.rmtree(cls.test_dir)

    def test_smart_pending_consecutive_batches(self):
        """
        Prueba el flujo de lotes consecutivos:
        1. Lote 1: posts A y B -> se analizan e ingresan.
        2. Endpoint /api/posts/ids retorna A y B.
        3. Lote 2: envía [A, B, C, D] con max_new_posts=2 -> A y B se omiten, C y D se analizan.
        4. Endpoint /api/posts/ids ahora retorna [A, B, C, D].
        5. Lote 3: envía [A, B, C, D, E] con max_new_posts=1 -> A, B, C, D se omiten, E se analiza.
        """
        # Paso 1: Clasificar lote 1 con posts A y B
        payload_1 = {
            "posts": [
                {
                    "id": "tweet_alpha_101",
                    "text": "New Python framework for asynchronous web scraping with beautiful soup and asyncio",
                    "author": "dev_one",
                    "likes": 120
                },
                {
                    "id": "tweet_beta_102",
                    "text": "Released Blender 4.2 plugin for procedural geometry nodes and real-time animation",
                    "author": "blender_guru",
                    "likes": 450
                }
            ],
            "persist": True,
            "duplicate_strategy": "skip"
        }

        with self.client.stream("POST", "/api/posts/analyze-batch-stream", json=payload_1) as resp:
            self.assertEqual(resp.status_code, 200)
            events = [json.loads(line) for line in resp.iter_lines() if line.strip()]

        # Verificar que A y B se procesaron
        completed_items = [e for e in events if e.get("event") == "item_completed"]
        self.assertEqual(len(completed_items), 2)
        self.assertFalse(completed_items[0]["telemetry"]["reclassified"])

        # Paso 2: Verificar /api/posts/ids
        ids_resp = self.client.get("/api/posts/ids")
        self.assertEqual(ids_resp.status_code, 200)
        ids_data = ids_resp.json()
        self.assertEqual(ids_data["total"], 2)
        self.assertIn("tweet_alpha_101", ids_data["tweet_ids"])
        self.assertIn("tweet_beta_102", ids_data["tweet_ids"])

        # Paso 3: Lote 2 con [A, B, C, D] y max_new_posts=2
        payload_2 = {
            "posts": [
                {
                    "id": "tweet_alpha_101",
                    "text": "New Python framework for asynchronous web scraping with beautiful soup and asyncio",
                    "author": "dev_one",
                    "likes": 130 # likes actualizados
                },
                {
                    "id": "tweet_beta_102",
                    "text": "Released Blender 4.2 plugin for procedural geometry nodes and real-time animation",
                    "author": "blender_guru",
                    "likes": 460
                },
                {
                    "id": "tweet_gamma_103",
                    "text": "ComfyUI workflow for character consistency using IP-Adapter and ControlNet",
                    "author": "ai_artist",
                    "likes": 890
                },
                {
                    "id": "tweet_delta_104",
                    "text": "Unreal Engine 5.4 Nanite tessellation performance benchmark on RTX 4090",
                    "author": "tech_lead",
                    "likes": 2100
                }
            ],
            "persist": True,
            "duplicate_strategy": "skip",
            "max_new_posts": 2
        }

        with self.client.stream("POST", "/api/posts/analyze-batch-stream", json=payload_2) as resp:
            self.assertEqual(resp.status_code, 200)
            events_2 = [json.loads(line) for line in resp.iter_lines() if line.strip()]

        completed_items_2 = [e for e in events_2 if e.get("event") == "item_completed"]
        # Debe haber procesado los 4 (2 skipped + 2 new)
        self.assertEqual(len(completed_items_2), 4)

        # Los dos primeros fueron skipped (0 ms)
        self.assertTrue(completed_items_2[0]["telemetry"].get("skipped", False))
        self.assertTrue(completed_items_2[1]["telemetry"].get("skipped", False))

        # Los dos siguientes fueron clasificados
        self.assertFalse(completed_items_2[2]["telemetry"].get("skipped", False))
        self.assertFalse(completed_items_2[3]["telemetry"].get("skipped", False))

        # Paso 4: Verificar /api/posts/ids con los 4 registrados
        ids_resp_2 = self.client.get("/api/posts/ids")
        self.assertEqual(ids_resp_2.status_code, 200)
        ids_data_2 = ids_resp_2.json()
        self.assertEqual(ids_data_2["total"], 4)
        for expected_id in ["tweet_alpha_101", "tweet_beta_102", "tweet_gamma_103", "tweet_delta_104"]:
            self.assertIn(expected_id, ids_data_2["tweet_ids"])

        # Paso 5: Lote 3 con [A, B, C, D, E, F] y max_new_posts=1
        # Debe detenerse tras procesar E, sin procesar F
        payload_3 = {
            "posts": [
                {"id": "tweet_alpha_101", "text": "Framework", "author": "dev_one", "likes": 140},
                {"id": "tweet_beta_102", "text": "Blender", "author": "blender_guru", "likes": 470},
                {"id": "tweet_gamma_103", "text": "ComfyUI", "author": "ai_artist", "likes": 900},
                {"id": "tweet_delta_104", "text": "Unreal", "author": "tech_lead", "likes": 2200},
                {"id": "tweet_epsilon_105", "text": "Building a local Claude coding assistant agent in TypeScript", "author": "agent_smith", "likes": 1500},
                {"id": "tweet_zeta_106", "text": "Godot 4 2D platformer physics guide", "author": "gamedev", "likes": 320}
            ],
            "persist": True,
            "duplicate_strategy": "skip",
            "max_new_posts": 1
        }

        with self.client.stream("POST", "/api/posts/analyze-batch-stream", json=payload_3) as resp:
            self.assertEqual(resp.status_code, 200)
            events_3 = [json.loads(line) for line in resp.iter_lines() if line.strip()]

        completed_items_3 = [e for e in events_3 if e.get("event") == "item_completed"]
        # Debe haber procesado los 4 existentes (skip) + 1 nuevo (epsilon_105), y detenido antes de zeta_106!
        self.assertEqual(len(completed_items_3), 5)
        self.assertEqual(completed_items_3[4]["post"]["tweet_id"], "tweet_epsilon_105")

        # Verificar que zeta_106 NO fue procesado ni añadido a BD
        ids_resp_3 = self.client.get("/api/posts/ids")
        ids_data_3 = ids_resp_3.json()
        self.assertEqual(ids_data_3["total"], 5)
        self.assertIn("tweet_epsilon_105", ids_data_3["tweet_ids"])
        self.assertNotIn("tweet_zeta_106", ids_data_3["tweet_ids"])


if __name__ == "__main__":
    unittest.main()
