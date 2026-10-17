"""
test_categories.py - Pruebas de integración para endpoints de taxonomía (/api/categories)
y verificación de entrega de archivos estáticos del frontend.
"""

from __future__ import annotations
import json
from pathlib import Path
import shutil
import sys
import unittest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.main import app
from app.registry import load_registry_data


class TestCategoriesEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.cat_path = settings.CATEGORIES_PATH
        cls.backup_path = Path(str(cls.cat_path) + ".backup_test")
        # Hacer copia de seguridad de categories.json
        if cls.cat_path.exists():
            shutil.copyfile(cls.cat_path, cls.backup_path)

    @classmethod
    def tearDownClass(cls):
        # Restaurar copia original de categories.json
        if cls.backup_path.exists():
            shutil.copyfile(cls.backup_path, cls.cat_path)
            cls.backup_path.unlink()
            load_registry_data(reload=True)

    def test_01_get_categories_list(self):
        """Verifica que GET /api/categories retorne todas las categorías (47)."""
        response = self.client.get("/api/categories")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 47)

        # Validar estructura de un elemento
        item = data[0]
        self.assertIn("id", item)
        self.assertIn("code", item)
        self.assertIn("name", item)
        self.assertIn("family_id", item)
        self.assertIn("threshold", item)
        self.assertIn("color_hex", item)

    def test_02_filter_categories_by_family(self):
        """Verifica el filtrado por familia vía query param ?family=ia."""
        response = self.client.get("/api/categories?family=ia")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 5)
        for cat in data:
            self.assertEqual(cat["family_id"], "ia")

    def test_03_create_duplicate_category_fails(self):
        """Verifica que intentar crear una categoría con ID existente retorne 409 Conflict."""
        response = self.client.post("/api/categories", json={
            "name": "Inteligencia Artificial",
            "id": "ia",
            "parent_id": None
        })
        self.assertEqual(response.status_code, 409)
        self.assertIn("ya existe", response.json()["detail"])

    def test_04_create_category_persists_and_hot_reloads(self):
        """Verifica que crear una nueva categoría persista en disco y se recargue en vivo."""
        new_cat_data = {
            "name": "Quantum Computing",
            "id": "quantum_computing_test",
            "code": "QC",
            "parent_id": "dev_tools",
            "description": "Publicaciones y avances en computación cuántica y algoritmos Qiskit.",
            "keywords": ["quantum", "qubit", "qiskit", "superposition"],
            "threshold": 0.82
        }

        response = self.client.post("/api/categories", json=new_cat_data)
        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["id"], "quantum_computing_test")
        self.assertEqual(created["code"], "QC")
        self.assertEqual(created["family_id"], "dev_tools")
        self.assertEqual(created["threshold"], 0.82)

        # Verificar que GET /api/categories ahora la contiene
        res_list = self.client.get("/api/categories")
        ids = [c["id"] for c in res_list.json()]
        self.assertIn("quantum_computing_test", ids)

        # Verificar que el archivo categories.json en disco contiene la categoría
        with open(self.cat_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        disk_ids = [c["id"] for c in disk_data.get("topic_categories", [])]
        self.assertIn("quantum_computing_test", disk_ids)

    def test_05_frontend_static_serving(self):
        """Verifica que FastAPI sirva index.html, /css/styles.css y /js/modals.js."""
        # 1. Root index.html
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("text/html", res_root.headers.get("content-type", ""))
        self.assertIn("x-virality-checker", res_root.text)
        self.assertIn("taxonomyModal", res_root.text)

        # 2. CSS
        res_css = self.client.get("/css/styles.css")
        self.assertEqual(res_css.status_code, 200)

        # 3. JS
        res_js = self.client.get("/js/modals.js")
        self.assertEqual(res_js.status_code, 200)
        self.assertIn("Modals", res_js.text)


if __name__ == "__main__":
    unittest.main()
