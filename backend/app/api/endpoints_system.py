"""
endpoints_system.py - Telemetría de hardware, estado del modelo Laya y taxonomía activa.
"""

from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter

from ..database import get_db
from ..engine import LayaEngine
from ..registry import load_registry_data
from ..schema import SystemHealthResponse
from ..services.batch_service import BatchService

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """Retorna estado del hardware local (CPU Intel Core i5, RAM, modelos cargados)."""
    batch_svc = BatchService.get_instance()
    active_cnt = sum(1 for s in batch_svc.status.values() if s == "RUNNING")
    engine = LayaEngine.get_instance()
    return engine.get_health(active_batches=active_cnt)


@router.get("/categories")
async def get_taxonomy_registry():
    """Retorna el árbol taxonómico completo de categories.json v2.1.0."""
    return load_registry_data()


@router.get("/checkpoints")
async def get_recent_checkpoints():
    """Retorna historial reciente de lotes y sesiones de procesamiento."""
    async with get_db() as db:
        query = "SELECT * FROM batch_checkpoints ORDER BY created_at DESC LIMIT 10;"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
