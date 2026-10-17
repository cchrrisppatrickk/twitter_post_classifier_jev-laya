"""
endpoints_batch.py - Control de procesamiento por lotes y telemetría SSE (ADR-006).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..database import get_db
from ..schema import BatchCheckpointRecord, BatchTelemetry
from ..services.batch_service import BatchService

logger = logging.getLogger("api_batch")
router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/start/{batch_id}", response_model=Dict[str, Any])
async def start_batch(batch_id: str):
    """Inicia o reanuda el procesamiento de un lote en segundo plano."""
    batch_svc = BatchService.get_instance()
    started = await batch_svc.start_batch(batch_id)
    if not started and batch_svc.status.get(batch_id) != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lote {batch_id} no encontrado o sin posts pendientes."
        )
    return {"status": "success", "batch_id": batch_id, "current_status": batch_svc.status.get(batch_id)}


@router.post("/pause/{batch_id}", response_model=Dict[str, Any])
async def pause_batch(batch_id: str):
    """Pausa temporalmente el procesamiento de un lote activo."""
    batch_svc = BatchService.get_instance()
    paused = await batch_svc.pause_batch(batch_id)
    if not paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El lote {batch_id} no está en ejecución."
        )
    return {"status": "paused", "batch_id": batch_id}


@router.get("/status/{batch_id}", response_model=Dict[str, Any])
async def get_batch_status(batch_id: str):
    """Obtiene el estado actual y métricas de progreso de un lote."""
    batch_svc = BatchService.get_instance()
    live_telem = batch_svc.get_batch_status(batch_id)
    if live_telem:
        return live_telem.model_dump()

    # Consultar persistencia en SQLite
    async with get_db() as db:
        query = "SELECT * FROM batch_checkpoints WHERE batch_id = ? LIMIT 1;"
        async with db.execute(query, (batch_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Lote {batch_id} no encontrado."
    )


@router.get("/stream/{batch_id}")
async def stream_batch_telemetry(batch_id: str):
    """
    Canal Server-Sent Events (SSE) para telemetría en tiempo real:
    Transmite velocidad (TPS), progreso %, latencia media, uso de CPU y RAM a la UI.
    """
    batch_svc = BatchService.get_instance()

    async def sse_event_generator():
        async for telem in batch_svc.subscribe_telemetry(batch_id):
            payload = json.dumps(telem.model_dump(), ensure_ascii=False)
            yield f"event: progress\ndata: {payload}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
