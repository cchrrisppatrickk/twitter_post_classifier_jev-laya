#!/usr/bin/env python3
"""
profile_batch_memory.py - Perfilado de Hardware y Verificación Anti-Fugas de Memoria (Fase 6.2)
Ejecuta un lote piloto de 50 posts del dataset de Bookmarks, registrando la curva de RAM (RSS),
el comportamiento del recolector de basura / malloc_trim en los checkpoints (cada 25 posts)
y la latencia de inferencia en CPU.
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import settings
from app.database import get_db, init_db
from app.engine import LayaEngine
from app.schema import CleanPost
from app.services.batch_service import BatchService
from app.services.ingest_service import convert_raw_to_clean, normalize_raw_item

BOOKMARKS_DATASET_PATH = Path(
    "/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/automations/output_files/twitter/extracted_links/"
    "extracted_data_https___x_com_i_bookmarks_bookmarks_20261013_101533.json"
)


def get_process_memory_mb() -> float:
    """Retorna el RSS (Resident Set Size) del proceso actual en MB."""
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024 * 1024)


async def run_pilot_profile(num_posts: int = 50):
    print("=" * 78)
    print(f"🚀 FASE 6.2: EJECUCIÓN DE LOTE PILOTO ({num_posts} POSTS) Y PERFILADO DE HARDWARE")
    print(f"📂 Dataset: {BOOKMARKS_DATASET_PATH.name}")
    print(f"🎯 Tamaño del lote: {num_posts} posts (2 checkpoints de {settings.CHECKPOINT_INTERVAL} posts)")
    print("=" * 78)

    # 1. Asegurar base de datos inicializada
    await init_db()

    # 2. Cargar y seleccionar el lote piloto
    print(f"\n[1] CARGANDO Y PREPARANDO LOTE PILOTO DE {num_posts} PUBLICACIONES...")
    with open(BOOKMARKS_DATASET_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict):
        raw_posts = raw_data.get("posts", [])
    else:
        raw_posts = raw_data

    sample_raw = raw_posts[:num_posts]
    clean_posts = []
    for item in sample_raw:
        raw_p = normalize_raw_item(item)
        if raw_p:
            clean_posts.append(convert_raw_to_clean(raw_p))

    print(f"  ✓ {len(clean_posts)} publicaciones normalizadas a CleanPost exitosamente.")

    # 3. Medición de Memoria Pre-Carga de Modelo
    rss_pre_model = get_process_memory_mb()
    print(f"\n[2] ESTADO DE MEMORIA PREVIO:")
    print(f"  • RAM RSS Proceso (Pre-Modelo): {rss_pre_model:.2f} MB")

    # 4. Inicializar LayaEngine
    t_engine_start = time.perf_counter()
    engine = LayaEngine.get_instance()
    t_engine_ready = time.perf_counter() - t_engine_start
    rss_post_model = get_process_memory_mb()
    delta_model = rss_post_model - rss_pre_model
    print(f"  • Modelo Laya inicializado en {t_engine_ready:.2f}s sobre dispositivo: {engine.device}")
    print(f"  • RAM RSS Proceso (Con Modelo): {rss_post_model:.2f} MB (Delta: +{delta_model:.2f} MB)")

    # 5. Encolar e Iniciar Batch en BatchService
    batch_id = f"pilot_{int(time.time())}"
    batch_service = BatchService.get_instance()

    print(f"\n[3] INICIANDO PROCESAMIENTO ASÍNCRONO DEL LOTE: {batch_id}...")
    await batch_service.enqueue_batch(
        batch_id=batch_id,
        file_name="pilot_bookmarks_sample.json",
        posts=clean_posts,
        auto_start=True
    )

    # 6. Monitoreo Activo de la Tarea en Progreso
    ram_trajectory = []
    checkpoint_snapshots = []
    last_processed = 0

    t_start = time.perf_counter()
    while batch_service.status.get(batch_id) == "RUNNING":
        curr_proc = batch_service.processed_items.get(batch_id, 0)
        curr_rss = get_process_memory_mb()
        ram_trajectory.append((curr_proc, curr_rss, time.perf_counter() - t_start))

        # Detectar paso por checkpoint
        if curr_proc > 0 and curr_proc % settings.CHECKPOINT_INTERVAL == 0 and curr_proc != last_processed:
            last_processed = curr_proc
            checkpoint_snapshots.append({
                "checkpoint": curr_proc // settings.CHECKPOINT_INTERVAL,
                "posts_processed": curr_proc,
                "ram_rss_mb": curr_rss,
                "timestamp_sec": time.perf_counter() - t_start
            })
            print(f"  📌 Checkpoint #{curr_proc // settings.CHECKPOINT_INTERVAL} alcanzado ({curr_proc}/{num_posts} posts) | RAM RSS: {curr_rss:.1f} MB")

        await asyncio.sleep(0.1)

    t_total = time.perf_counter() - t_start
    final_status = batch_service.status.get(batch_id)
    rss_final = get_process_memory_mb()

    # 7. Forzar verificación y trim de memoria final
    engine.check_memory_safety(force=True)
    rss_after_trim = get_process_memory_mb()

    # 8. Analizar Métricas de Latencia y Rendimiento
    latencies = batch_service.latencies.get(batch_id, [])
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    min_lat = min(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0
    p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
    tps = len(clean_posts) / max(t_total, 0.001)

    print(f"\n[4] RESULTADOS DEL LOTE PILOTO:")
    print(f"  • Estado final del lote: {final_status}")
    print(f"  • Total posts procesados: {batch_service.processed_items.get(batch_id, 0)}/{num_posts}")
    print(f"  • Tiempo total de ejecución: {t_total:.2f} segundos")
    print(f"  • Throughput medio (TPS): {tps:.2f} posts/segundo")
    print(f"  • Latencia por post:")
    print(f"      - Mínima: {min_lat:.1f} ms")
    print(f"      - Media:   {avg_lat:.1f} ms")
    print(f"      - P95:     {p95_lat:.1f} ms")
    print(f"      - Máxima:  {max_lat:.1f} ms")

    print(f"\n[5] ANÁLISIS DE ESTABILIDAD DE MEMORIA (ANTI-FUGAS):")
    print(f"  • RAM RSS Base (Modelo cargado): {rss_post_model:.2f} MB")
    for cp in checkpoint_snapshots:
        print(f"  • Checkpoint #{cp['checkpoint']} ({cp['posts_processed']} posts): {cp['ram_rss_mb']:.2f} MB")
    print(f"  • RAM RSS Fin de Lote: {rss_final:.2f} MB")
    print(f"  • RAM RSS Post-Trim:   {rss_after_trim:.2f} MB")

    # Cálculo del Delta entre Checkpoints
    if len(checkpoint_snapshots) >= 2:
        delta_checkpoints = checkpoint_snapshots[-1]["ram_rss_mb"] - checkpoint_snapshots[0]["ram_rss_mb"]
        print(f"  • Delta de RAM entre Checkpoints ({checkpoint_snapshots[0]['posts_processed']} -> {checkpoint_snapshots[-1]['posts_processed']}): {delta_checkpoints:+.2f} MB")
    else:
        delta_checkpoints = rss_final - rss_post_model
        print(f"  • Delta de RAM general: {delta_checkpoints:+.2f} MB")

    # 9. Verificación en SQLite
    async with get_db() as db:
        async with db.execute("SELECT count(*) FROM posts;") as cursor:
            row = await cursor.fetchone()
            posts_in_db = row[0] if row else 0

        async with db.execute("SELECT status, processed_items, avg_latency_ms FROM batch_checkpoints WHERE batch_id = ?;", (batch_id,)) as cursor:
            cp_row = await cursor.fetchone()

    print(f"\n[6] INTEGRIDAD Y PERSISTENCIA EN SQLITE:")
    print(f"  • Publicaciones en tabla `posts`: {posts_in_db}")
    print(f"  • Registro de checkpoint: {dict(cp_row) if cp_row else 'None'}")

    # Criterio de Aceptación (delta entre checkpoints < 150MB y RAM total < 4.5 GB)
    is_memory_safe = abs(delta_checkpoints) < 150.0 and rss_final < 4500.0
    is_success = (final_status == "COMPLETED") and (posts_in_db >= num_posts) and is_memory_safe

    print("\n" + "=" * 78)
    if is_success:
        print("✅ LOTE PILOTO COMPLETADO EXITOSAMENTE SIN FUGAS DE MEMORIA.")
        print("   El sistema está listo y certificado para la ingesta masiva (1,683 posts).")
    else:
        print("❌ ALERTA: Criterios de aceptación no alcanzados.")
        if not is_memory_safe:
            print("   - Fuga o sobreconsumo de memoria detectado.")
        if posts_in_db != num_posts:
            print(f"   - Discrepancia en posts persistidos: {posts_in_db} != {num_posts}")
    print("=" * 78)
    return is_success


if __name__ == "__main__":
    success = asyncio.run(run_pilot_profile(num_posts=50))
    sys.exit(0 if success else 1)
