"""
test_hardware_detection.py - Valida la autodetección inteligente de hardware CPU/GPU y telemetría de salud.
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.engine import LayaEngine, _detect_cpu_model, _detect_gpu_info, resolve_device
from backend.app.main import app


class TestHardwareDetection(unittest.TestCase):
    def test_resolve_device_logic(self):
        """Valida la resolución determinista de hardware."""
        # Test forzado de CPU
        self.assertEqual(resolve_device("cpu"), "cpu")
        
        # Test forzado de CUDA
        self.assertEqual(resolve_device("cuda"), "cuda")
        
        # Test modo 'auto'
        resolved = resolve_device("auto")
        self.assertIn(resolved, ["cpu", "cuda", "mps"])

    def test_detect_hardware_info(self):
        """Valida la detección de información de CPU y GPU."""
        cpu_info = _detect_cpu_model()
        self.assertIsInstance(cpu_info, str)
        self.assertTrue(len(cpu_info) > 0)

        gpu_info = _detect_gpu_info()
        self.assertIsInstance(gpu_info, dict)
        self.assertIn("cuda_available", gpu_info)
        self.assertIn("gpu_model", gpu_info)
        self.assertIn("vram_total_gb", gpu_info)
        self.assertIn("vram_used_mb", gpu_info)

    def test_system_health_endpoint(self):
        """Valida que el endpoint /api/system/health devuelva los campos enriquecidos de hardware."""
        client = TestClient(app)
        response = client.get("/api/system/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn(data["status"], ["healthy", "degraded"])
        self.assertIn("device", data)
        self.assertIn("cpu_model", data)
        self.assertIn("cuda_available", data)
        self.assertIn("device_display", data)
        self.assertIn("estimated_latency", data)
        self.assertIn("ram_total_gb", data)
        self.assertIn("ram_available_gb", data)
        self.assertIn("ram_used_process_mb", data)

        # Validar valores según dispositivo
        if data["device"] == "cpu":
            self.assertIn("~18s/post", data["estimated_latency"])
            self.assertIn("CPU (", data["device_display"])
        elif "cuda" in data["device"]:
            self.assertIn("~33ms/post", data["estimated_latency"])
            self.assertIn("GPU (", data["device_display"])


if __name__ == "__main__":
    unittest.main()
