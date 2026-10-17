"""
test_engine.py - Pruebas del motor de inferencia System 1 (Laya Local),
Family Gating, boosters deterministas y soporte multilingüe.
"""

from pathlib import Path
import sys
import unittest

# Inyectar backend en path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.engine import LayaEngine, normalize_multilingual_text
from app.registry import detect_asset_domains, get_root_family
from app.schema import CleanPost, SocialMetrics


class TestEngineSystem1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Inicializar el motor Laya (reutiliza el singleton)
        cls.engine = LayaEngine.get_instance()

    def test_multilingual_normalization_nfkc(self):
        """Verifica que la normalización Unicode NFKC convierta caracteres zenkaku a hankaku."""
        zenkaku_input = "ＣｏｍｆｙＵＩでＦｌｕｘのＬｏＲＡを自作！　１２３"
        normalized = normalize_multilingual_text(zenkaku_input)
        self.assertEqual(normalized, "ComfyUIでFluxのLoRAを自作! 123")

    def test_asset_domain_matcher(self):
        """Verifica la detección determinista de URLs de Hugging Face y GitHub."""
        text = "Check this model https://huggingface.co/lightx2v/Qwen-Image and repo https://github.com/blend/nodes"
        assets, urls = detect_asset_domains(text)
        self.assertIn("huggingface_model", assets)
        self.assertIn("github_repo", assets)
        self.assertEqual(len(urls), 2)

    def test_system_health(self):
        """Verifica la telemetría de hardware (CPU y RAM)."""
        health = self.engine.get_health()
        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.device, "cpu")
        self.assertGreater(health.ram_total_gb, 4.0)
        self.assertGreater(health.ram_available_gb, 0.0)
        self.assertGreater(health.ram_used_process_mb, 50.0)

    def test_inference_english_blender_tool(self):
        """Prueba de inferencia en post técnico en inglés con repo en GitHub."""
        assets, _ = detect_asset_domains("https://github.com/Motion2MixamoRig")
        post = CleanPost(
            tweet_id="2108516129110921241",
            clean_text="Free Open-Source Video-to-Animation for Mixamo Rigs, Now Inside Blender with Geometry Nodes! GitHub: https://github.com/Motion2MixamoRig",
            original_content="Free Open-Source Video-to-Animation for Mixamo Rigs...",
            author_name="BlenderArtist",
            post_url="https://x.com/BlenderArtist/status/2108516129110921241",
            date="2026-10-13 10:00:00",
            lang="en",
            metrics=SocialMetrics(favorite_count=450, retweet_count=80),
            media_urls=["https://video.twimg.com/demo.mp4"],
            media_type="video",
            media_count=1,
            detected_assets=assets,
            detected_domains=["github.com"]
        )

        result = self.engine.classify_post(post)
        root_fam = get_root_family(result.primary_category)
        self.assertIn(root_fam, ["blender", "modelado_3d", "dev_tools"])
        self.assertEqual(result.status, "CLASSIFIED")
        self.assertIn("github_repo", result.assets)
        self.assertGreater(result.affinity_score, 0.70)
        self.assertGreater(result.technical_depth, 1.5)

    def test_inference_japanese_post(self):
        """Prueba de inferencia nativa en japonés (sin traductor externo)."""
        post = CleanPost(
            tweet_id="2108516129110921242",
            clean_text="突然ウチにやって来た隣人 (1/6) SFW #創作漫画 #イラスト",
            original_content="突然ウチにやって来た隣人 (1/6) SFW",
            author_name="MangaCreator",
            post_url="https://x.com/MangaCreator/status/2108516129110921242",
            date="2026-10-13 11:00:00",
            lang="ja",
            metrics=SocialMetrics(favorite_count=1200, retweet_count=300),
            media_urls=[],
            media_type="none",
            media_count=0,
            detected_assets=[],
            detected_domains=[]
        )

        result = self.engine.classify_post(post)
        root_fam = get_root_family(result.primary_category)
        self.assertEqual(root_fam, "mangas")
        self.assertEqual(result.status, "CLASSIFIED")

    def test_inference_ambiguous_post_abstains_to_pending(self):
        """Prueba de abstención preventiva a PENDING ante un post críptico / informal."""
        post = CleanPost(
            tweet_id="2108516129110921243",
            clean_text="Waking up today with good coffee. What a weird day.",
            original_content="Waking up today with good coffee. What a weird day.",
            author_name="RandomUser",
            post_url="https://x.com/RandomUser/status/2108516129110921243",
            date="2026-10-13 12:00:00",
            lang="en",
            metrics=SocialMetrics(favorite_count=5, retweet_count=0),
            media_urls=[],
            media_type="none",
            media_count=0,
            detected_assets=[],
            detected_domains=[]
        )

        result = self.engine.classify_post(post)
        # Debe caer en 'otros' o estar en 'PENDING'
        self.assertTrue(result.status == "PENDING" or result.primary_category == "otros")


if __name__ == "__main__":
    unittest.main()
