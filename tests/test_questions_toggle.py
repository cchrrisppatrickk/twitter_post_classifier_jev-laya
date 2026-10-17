#!/usr/bin/env python3
"""
test_questions_toggle.py - Validación de Activación/Desactivación de Preguntas Tipadas (System 1)
Verifica que las preguntas tipadas puedan activarse/desactivarse mediante API y que el
compilador del esquema Laya filtre coherentemente las dimensiones evaluadas.
"""

import json
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.api.endpoints_categories import list_supplementary_questions
from app.main import app
from app.registry import build_decision_schema, load_registry_data


class TestQuestionsToggle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_list_supplementary_questions_has_active_field(self):
        """Verifica que el endpoint GET exponga el flag 'active' en cada pregunta."""
        resp = self.client.get("/api/categories/questions/supplementary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("supplementary_questions", data)
        supp = data["supplementary_questions"]
        self.assertGreater(len(supp), 0)
        for q_id, q_cfg in supp.items():
            self.assertIn("active", q_cfg)
            self.assertIsInstance(q_cfg["active"], bool)

    def test_toggle_supplementary_question_endpoint(self):
        """Verifica que PATCH /toggle alterne el estado y actualice el esquema en caliente."""
        q_id = "is_uncensored_or_nsfw"

        # 1. Obtener estado inicial
        resp1 = self.client.get("/api/categories/questions/supplementary")
        initial_state = resp1.json()["supplementary_questions"][q_id]["active"]

        # 2. Alternar (toggle)
        patch_resp = self.client.patch(f"/api/categories/questions/supplementary/{q_id}/toggle")
        self.assertEqual(patch_resp.status_code, 200)
        patch_data = patch_resp.json()
        self.assertEqual(patch_data["status"], "success")
        self.assertEqual(patch_data["active"], not initial_state)

        # 3. Comprobar que build_decision_schema() refleja el cambio
        schema = build_decision_schema()
        if not initial_state:
            self.assertIn(q_id, schema)
        else:
            self.assertNotIn(q_id, schema)

        # 4. Restaurar estado original mediante segundo toggle
        restore_resp = self.client.patch(f"/api/categories/questions/supplementary/{q_id}/toggle")
        self.assertEqual(restore_resp.status_code, 200)
        self.assertEqual(restore_resp.json()["active"], initial_state)

        # Confirmar restauración en esquema
        schema_restored = build_decision_schema()
        if initial_state:
            self.assertIn(q_id, schema_restored)
        else:
            self.assertNotIn(q_id, schema_restored)

    def test_build_decision_schema_with_active_questions_subset(self):
        """Valida que pasar active_questions=['category', 'is_local_first'] filtre estrictamente."""
        subset = ["category", "is_local_first"]
        filtered_schema = build_decision_schema(active_questions=subset)

        self.assertIn("category", filtered_schema)
        self.assertIn("is_local_first", filtered_schema)
        self.assertNotIn("content_format", filtered_schema)
        self.assertNotIn("technical_depth", filtered_schema)
        self.assertNotIn("reproducible_asset_type", filtered_schema)


if __name__ == "__main__":
    unittest.main()
