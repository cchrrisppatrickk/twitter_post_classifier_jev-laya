"""
test_hybrid_classification.py - Pruebas del Pipeline Neuro-Simbólico Híbrido en 2 Pasadas,
Overrides Deterministas y Mitigación de Sesgo de Etiqueta.
"""

from __future__ import annotations
from pathlib import Path
import sys
import unittest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.engine import LayaEngine
from app.registry import (
    build_pass1_schema,
    build_pass2_schema,
    detect_deterministic_override,
)
from app.schema import CleanPost, SocialMetrics


class TestHybridClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = LayaEngine.get_instance()

    def test_01_deterministic_override_flux_hf(self):
        """Verifica que un post de Flux con enlace a Hugging Face active el override a mod_image."""
        text = "Introducing Flux.1 [dev], a 12B parameter rectified flow transformer for text-to-image synthesis."
        urls = ["https://huggingface.co/black-forest-labs/FLUX.1-dev", "https://fal.ai"]
        modality, asset = detect_deterministic_override(text, urls)
        self.assertEqual(modality, "mod_image")
        self.assertEqual(asset, "huggingface_model")

    def test_02_deterministic_override_civitai(self):
        """Verifica que un post con enlace a Civitai active el override a mod_image y asset civitai_lora."""
        text = "Check out this new anime style LoRA for SDXL!"
        urls = ["https://civitai.com/models/12345/anime-style-lora"]
        modality, asset = detect_deterministic_override(text, urls)
        self.assertEqual(modality, "mod_image")
        self.assertEqual(asset, "civitai_lora")

    def test_03_deterministic_override_comfyui_workflow(self):
        """Verifica que un workflow de ComfyUI active el override a mod_image y asset comfyui_workflow."""
        text = "Download my modular upscaling pipeline workflow."
        urls = ["https://openart.ai/workflows/my-upscaler-workflow"]
        modality, asset = detect_deterministic_override(text, urls)
        self.assertEqual(modality, "mod_image")
        self.assertEqual(asset, "comfyui_workflow")

    def test_04_pass_schemas_generation(self):
        """Verifica que build_pass1_schema y build_pass2_schema compilen correctamente."""
        pass1 = build_pass1_schema()
        self.assertIn("gen_modality", pass1)
        self.assertIn("content_format", pass1)
        self.assertIn("technical_depth", pass1)
        self.assertIn("is_local_first", pass1)
        self.assertIn("is_uncensored_or_nsfw", pass1)
        # No debe contener preguntas de familias en Pasada 1
        self.assertNotIn("model_family_image", pass1)
        self.assertNotIn("model_family_video", pass1)

        # Pasada 2 condicional
        pass2_img = build_pass2_schema("mod_image")
        self.assertIn("model_family_image", pass2_img)
        self.assertEqual(len(pass2_img), 1)

        pass2_vid = build_pass2_schema("mod_video")
        self.assertIn("model_family_video", pass2_vid)
        self.assertEqual(len(pass2_vid), 1)

        pass2_none = build_pass2_schema("mod_code_web3d")
        self.assertEqual(len(pass2_none), 0)

    def test_05_flux_post_end_to_end_classification(self):
        """
        Prueba E2E: El post de Flux.1 [dev] debe clasificarse en gen_imagenes o modelos_huggingface,
        sin ser secuestrado por dev_tools ni mod_code gracias a los overrides deterministas.
        """
        post = CleanPost(
            tweet_id="test_flux_001",
            clean_text="Introducing Flux.1 [dev], a 12B parameter rectified flow transformer for text-to-image synthesis. Weights available on Hugging Face with open weights guidance. Demo live on Replicate and Fal.",
            original_content="Introducing Flux.1 [dev]...",
            author_name="BlackForestLabs",
            author_id="bfl_official",
            post_url="https://x.com/BlackForestLabs/status/123456789",
            date="2026-10-18T12:00:00Z",
            lang="en",
            metrics=SocialMetrics(favorite_count=1500, retweet_count=400),
            media_urls=[],
            media_count=0,
            media_type="none",
            detected_assets=["huggingface_model"],
            detected_domains=["huggingface.co/black-forest-labs/FLUX.1-dev"]
        )

        result = self.engine.classify_post(post)
        self.assertIn(result.primary_category, ["gen_imagenes", "modelos_huggingface", "ia_generativa", "ia"])
        self.assertEqual(result.status, "CLASSIFIED")
        self.assertGreaterEqual(result.affinity_score, 0.70)
        self.assertIn("deterministic_override", result.raw_answers)
        self.assertEqual(result.raw_answers["deterministic_override"]["modality"], "mod_image")


if __name__ == "__main__":
    unittest.main()
