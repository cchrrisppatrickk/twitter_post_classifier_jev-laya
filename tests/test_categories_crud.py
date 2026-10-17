"""
test_categories_crud.py - Pruebas unitarias para Subfase 5.10.1 (CRUD de Categorías,
Ajustes Globales y Banco de Preguntas Tipadas Laya).
"""

import json
import shutil
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


class TestCategoriesCRUD(unittest.TestCase):
    def setUp(self):
        # Crear copia de seguridad de categories.json para restaurar tras el test
        self.cat_path = settings.CATEGORIES_PATH
        self.backup_path = Path(str(self.cat_path) + ".backup_test")
        shutil.copyfile(self.cat_path, self.backup_path)

    def tearDown(self):
        # Restaurar categories.json original
        if self.backup_path.exists():
            shutil.copyfile(self.backup_path, self.cat_path)
            self.backup_path.unlink()

    def test_01_list_and_get_category(self):
        # Listar
        res = client.get("/api/categories")
        self.assertEqual(res.status_code, 200)
        cats = res.json()
        self.assertGreaterEqual(len(cats), 48)

        # Verificar campos enriquecidos
        first_cat = cats[0]
        self.assertIn("examples", first_cat)
        self.assertIn("exclusions", first_cat)
        self.assertIn("boosters", first_cat)
        self.assertIn("is_family", first_cat)

        # Obtener detalle específico de 'ia_local'
        res_single = client.get("/api/categories/ia_local")
        self.assertEqual(res_single.status_code, 200)
        data = res_single.json()
        self.assertEqual(data["id"], "ia_local")
        self.assertEqual(data["parent_id"], "ia")

    def test_02_update_category(self):
        # Actualizar directiva y keywords de 'ia_local'
        payload = {
            "description": "Nueva descripción de prueba para inferencia de Laya AI.",
            "keywords": ["ollama", "lmstudio", "test_keyword_crud"],
            "threshold": 0.85
        }
        res = client.put("/api/categories/ia_local", json=payload)
        self.assertEqual(res.status_code, 200)
        updated = res.json()
        self.assertEqual(updated["description"], payload["description"])
        self.assertIn("test_keyword_crud", updated["keywords"])
        self.assertEqual(updated["threshold"], 0.85)

        # Comprobar persistencia con GET
        res_check = client.get("/api/categories/ia_local")
        self.assertEqual(res_check.status_code, 200)
        self.assertEqual(res_check.json()["threshold"], 0.85)

    def test_03_create_and_delete_subcategory(self):
        # 1. Crear subcategoría temporal
        create_payload = {
            "name": "Shader Math Pro",
            "id": "shader_math_temp",
            "parent_id": "modelado_3d",
            "code": "SMP",
            "description": "Cálculos matemáticos para shaders HLSL y GLSL.",
            "keywords": ["shader", "glsl", "raymarching"],
            "threshold": 0.78,
            "priority": 25
        }
        res_create = client.post("/api/categories", json=create_payload)
        self.assertEqual(res_create.status_code, 201)
        created = res_create.json()
        self.assertEqual(created["id"], "shader_math_temp")

        # Verificar que existe
        res_get = client.get("/api/categories/shader_math_temp")
        self.assertEqual(res_get.status_code, 200)

        # 2. Eliminar la subcategoría
        res_del = client.delete("/api/categories/shader_math_temp")
        self.assertEqual(res_del.status_code, 200)
        del_data = res_del.json()
        self.assertEqual(del_data["status"], "success")
        self.assertEqual(del_data["deleted_id"], "shader_math_temp")

        # Verificar que ya no existe (404)
        res_after = client.get("/api/categories/shader_math_temp")
        self.assertEqual(res_after.status_code, 404)

    def test_04_protection_of_root_families(self):
        # Intentar eliminar la familia raíz 'ia' debe fallar con HTTP 400
        res = client.delete("/api/categories/ia")
        self.assertEqual(res.status_code, 400)
        self.assertIn("protegida", res.json()["detail"].lower())

        # Intentar eliminar la familia raíz 'blender' debe fallar con HTTP 400
        res2 = client.delete("/api/categories/blender")
        self.assertEqual(res2.status_code, 400)

    def test_05_global_settings(self):
        # Leer ajustes globales
        res = client.get("/api/categories/settings/globals")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("global_settings", data)
        self.assertIn("default_threshold", data["global_settings"])

        # Actualizar default_threshold y min_confidence_abstain
        update_payload = {
            "default_threshold": 0.77,
            "min_confidence_abstain": 0.58
        }
        res_put = client.put("/api/categories/settings/globals", json=update_payload)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["global_settings"]["default_threshold"], 0.77)

    def test_06_supplementary_questions(self):
        # Leer banco de preguntas
        res = client.get("/api/categories/questions/supplementary")
        self.assertEqual(res.status_code, 200)
        questions = res.json()["supplementary_questions"]
        self.assertIn("content_format", questions)
        self.assertIn("technical_depth", questions)

        # Crear pregunta suplementaria personalizada
        new_q = {
            "id": "target_persona_test",
            "type": "choice",
            "instructions": "¿A qué perfil técnico se dirige la publicación?",
            "criteria": {
                "engineers": "Desarrolladores y arquitectos de software.",
                "designers": "Modeladores 3D y artistas visuales."
            }
        }
        res_post = client.post("/api/categories/questions/supplementary", json=new_q)
        self.assertEqual(res_post.status_code, 201)

        # Modificar pregunta creada
        update_q = {
            "type": "choice",
            "instructions": "¿A qué perfil técnico se orienta principalmente el tweet?",
            "criteria": new_q["criteria"]
        }
        res_put = client.put("/api/categories/questions/supplementary/target_persona_test", json=update_q)
        self.assertEqual(res_put.status_code, 200)

        # Eliminar pregunta personalizada
        res_del = client.delete("/api/categories/questions/supplementary/target_persona_test")
        self.assertEqual(res_del.status_code, 200)

        # Intentar eliminar pregunta protegida ('content_format') debe fallar con 400
        res_del_prot = client.delete("/api/categories/questions/supplementary/content_format")
        self.assertEqual(res_del_prot.status_code, 400)


if __name__ == "__main__":
    unittest.main()
