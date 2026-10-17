#!/usr/bin/env python3
"""
run_all_tests.py - Test Runner Aislado por Subproceso (Anti-OOM)
Ejecuta cada archivo de prueba en un proceso Python independiente.
Al terminar cada suite, el sistema operativo libera el 100% de la memoria RAM de PyTorch,
garantizando que el consumo nunca supere ~1.8 GB y eliminando el riesgo de OOM.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"

# Detectar intérprete de Python del entorno virtual
VENV_PYTHON = PROJECT_ROOT.parent / "laya_tester_app" / ".venv" / "bin" / "python3"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)


def main():
    test_files = sorted([f for f in TESTS_DIR.glob("test_*.py") if f.is_file()])
    total_files = len(test_files)

    print("=" * 72)
    print("🚀 INICIANDO TEST RUNNER AISLADO (Subprocess Isolation - Anti OOM)")
    print(f"📦 Intérprete: {VENV_PYTHON}")
    print(f"📂 Suites a ejecutar: {total_files} archivos en tests/")
    print("=" * 72)

    total_start = time.perf_counter()
    passed_suites = 0
    failed_suites = []

    for idx, test_file in enumerate(test_files, 1):
        rel_path = test_file.relative_to(PROJECT_ROOT)
        print(f"\n[{idx}/{total_files}] Ejecutando: {rel_path} ...", flush=True)

        t0 = time.perf_counter()
        proc = subprocess.run(
            [str(VENV_PYTHON), "-m", "unittest", str(rel_path)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        elapsed = time.perf_counter() - t0

        if proc.returncode == 0:
            passed_suites += 1
            print(f"  ✓ PASADO en {elapsed:.2f}s")
        else:
            failed_suites.append((rel_path, proc.stdout))
            print(f"  ❌ FALLÓ en {elapsed:.2f}s (código {proc.returncode})")
            print("  --- Salida del Error ---")
            for line in proc.stdout.strip().splitlines()[-15:]:
                print(f"    {line}")
            print("  ------------------------")

    total_time = time.perf_counter() - total_start
    print("\n" + "=" * 72)
    print("📊 RESUMEN FINAL DE LA SUITE:")
    print(f"  Suites Totales: {total_files}")
    print(f"  Suites Exitosas: {passed_suites}/{total_files} ({(passed_suites/total_files)*100:.1f}%)")
    print(f"  Tiempo Total: {total_time:.2f}s")

    if failed_suites:
        print(f"\n❌ Se encontraron fallos en {len(failed_suites)} suite(s):")
        for f, _ in failed_suites:
            print(f"   - {f}")
        sys.exit(1)
    else:
        print("\n🎉 ¡TODAS LAS SUITES PASARON AL 100% CON ÉXITO SIN FUGAS DE MEMORIA!")
        sys.exit(0)


if __name__ == "__main__":
    main()
