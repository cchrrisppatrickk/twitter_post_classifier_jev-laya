"""
test_meridian_format.py - Pruebas del formato nativo Meridian Twitter Scraper v2
"""
from pathlib import Path
import sys
import unittest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backend.app.services.ingest_service import normalize_raw_item, convert_raw_to_clean
from backend.app.engine import LayaEngine

SAMPLE_MERIDIAN_DATA = {
  "metadata": {
    "target": "https://x.com/i/bookmarks",
    "section": "bookmarks",
    "exported_at": "2026-10-13 10:15:33",
    "total_posts": 4,
    "engine": "meridian_twitter_scraper_v2"
  },
  "posts": [
    {
      "tweet_id": "2109989762899570828",
      "post_url": "https://x.com/Stefan_3D_AI/status/2109989762899570828",
      "author": {
        "name": "Stefan_3D_AI",
        "nick": "Stefan 3D AI",
        "id": 1381936011488411600,
        "verified": False,
        "profile_image": "https://pbs.twimg.com/profile_images/1929963548442275844/tQZfTm8T.jpg"
      },
      "content": "Free Open-Source Video-to-Animation for Mixamo Rigs, Now Inside Blender\n\nMotion2MixamoRig copies the motion of a person in a video onto a Mixamo-rigged character directly in Blender.",
      "date": "2026-10-11T14:48:42+00:00",
      "metrics": {
        "replies": 3,
        "retweets": 4,
        "likes": 50,
        "bookmarks": 68
      },
      "category": "video",
      "media_urls": [
        "https://video.twimg.com/amplify_video/2009989714392416256/vid/avc1/1280x720/Kx3k0.mp4"
      ]
    },
    {
      "tweet_id": "2109789182390358017",
      "post_url": "https://x.com/Ai_Art_Community/status/2109789182390358017",
      "author": {
        "name": "Ai_Art_Community",
        "nick": "AI Art Community",
        "id": 1459203847293849600,
        "verified": True,
        "profile_image": "https://pbs.twimg.com/profile_images/1709283749/art.jpg"
      },
      "content": "Flux 1.1 Pro is now available. Here is a comprehensive comparison of prompt adherence across 20 challenging benchmarks.",
      "date": "2026-10-11T01:31:39+00:00",
      "metrics": {
        "replies": 12,
        "retweets": 89,
        "likes": 640,
        "bookmarks": 312
      },
      "category": "image",
      "media_urls": [
        "https://pbs.twimg.com/media/example.jpg"
      ]
    }
  ]
}


class TestMeridianFormat(unittest.TestCase):
    def test_normalize_meridian_items(self):
        posts = SAMPLE_MERIDIAN_DATA["posts"]

        # Test Post 1
        norm1 = normalize_raw_item(posts[0])
        self.assertIsNotNone(norm1)
        self.assertEqual(norm1.tweet_id, "2109989762899570828")
        self.assertEqual(norm1.author_name, "Stefan_3D_AI")
        self.assertEqual(norm1.post_url, "https://x.com/Stefan_3D_AI/status/2109989762899570828")
        self.assertEqual(norm1.date, "2026-10-11T14:48:42+00:00")
        self.assertEqual(norm1.metrics.favorite_count, 50)
        self.assertEqual(norm1.metrics.retweet_count, 4)
        self.assertEqual(norm1.media_type, "video")
        self.assertIn("Motion2MixamoRig", norm1.content)

        # Test Post 2
        norm2 = normalize_raw_item(posts[1])
        self.assertIsNotNone(norm2)
        self.assertEqual(norm2.tweet_id, "2109789182390358017")
        self.assertEqual(norm2.author_name, "Ai_Art_Community")
        self.assertEqual(norm2.metrics.favorite_count, 640)
        self.assertEqual(norm2.media_type, "photo")

    def test_laya_inference_on_meridian_post(self):
        engine = LayaEngine.get_instance()
        post = SAMPLE_MERIDIAN_DATA["posts"][0]
        norm = normalize_raw_item(post)
        self.assertIsNotNone(norm)
        clean = convert_raw_to_clean(norm)

        res = engine.classify_post(clean)
        self.assertIsNotNone(res.primary_category)
        self.assertGreater(res.affinity_score, 0)


if __name__ == "__main__":
    unittest.main()
