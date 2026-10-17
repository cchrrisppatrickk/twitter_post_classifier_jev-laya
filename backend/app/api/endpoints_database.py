"""
endpoints_database.py - Endpoints API REST para Gestión, Mantenimiento,
Exportación, Importación y Reinicio de la Base de Datos SQLite WAL.
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..database import (
    get_db_session,
    get_database_stats,
    reset_database_data,
    export_database_data,
    import_database_data,
    optimize_database
)
from ..schema import (
    DatabaseStatsResponse,
    DatabaseResetRequest,
    DatabaseResetResponse,
    DatabaseImportRequest,
    DatabaseImportResponse,
    DatabaseOptimizeResponse
)

logger = logging.getLogger("api_database")
router = APIRouter(prefix="/api/database", tags=["database"])


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_stats(db: aiosqlite.Connection = Depends(get_db_session)):
    """
    Retorna métricas y telemetría de almacenamiento en tiempo real:
    - Conteo de posts clasificados, snapshots de historial, checkpoints y feedback.
    - Tamaño del archivo SQLite y archivo WAL en disco.
    - Versión del motor SQLite y modo de diario activo.
    """
    return await get_database_stats(db)


@router.post("/reset", response_model=DatabaseResetResponse)
async def reset_data(
    payload: Optional[DatabaseResetRequest] = None,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Limpia selectivamente los registros de posts, historial y checkpoints de prueba.
    Preserva estrictamente categories.json (la taxonomía nunca es eliminada).
    """
    req = payload or DatabaseResetRequest()
    logger.warning(
        f"Iniciando reinicio selectivo de base de datos: "
        f"posts={req.clear_posts}, history={req.clear_history}, checkpoints={req.clear_checkpoints}"
    )
    result = await reset_database_data(
        db,
        clear_posts=req.clear_posts,
        clear_history=req.clear_history,
        clear_checkpoints=req.clear_checkpoints,
        clear_feedback=req.clear_feedback,
        vacuum=req.vacuum
    )
    logger.info(f"Reinicio de base de datos finalizado: {result['message']}")
    return result


@router.get("/export")
async def export_backup(
    include_history: bool = True,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Descarga una copia de seguridad completa estructurada en formato JSON
    con todos los posts, clasificaciones duales (raw_json + classification_json)
    e historial cronológico de auditoría.
    """
    backup_dict = await export_database_data(db, include_history=include_history)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_twitter_posts_{timestamp}.json"

    json_str = json.dumps(backup_dict, ensure_ascii=False, indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/import", response_model=DatabaseImportResponse)
async def import_backup(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db_session)
):
    """
    Restaura una copia de seguridad JSON previamente exportada.
    Soporta carga por body JSON estructurado o mediante archivo multipart (.json).
    Modos: 'merge' (sobrescribe o añade nuevos) o 'replace' (limpia antes de restaurar).
    """
    content_type = request.headers.get("content-type", "")
    backup_content: Optional[Dict[str, Any]] = None
    mode = "merge"

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró ningún archivo en el campo 'file' del formulario."
            )
        try:
            content_bytes = await uploaded_file.read()
            backup_content = json.loads(content_bytes.decode("utf-8"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo cargado no es un JSON válido: {e}"
            )
        mode = str(form.get("mode") or "merge")
    else:
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuerpo JSON inválido o malformado: {e}"
            )

        if isinstance(body, dict):
            if "backup" in body and isinstance(body["backup"], dict):
                backup_content = body["backup"]
                mode = body.get("mode", "merge")
            else:
                backup_content = body
                mode = body.get("mode", "merge")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se esperaba un objeto JSON en el cuerpo de la petición."
            )

    if not isinstance(backup_content, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La estructura del backup debe ser un objeto JSON con claves 'posts' o 'history'."
        )

    result = await import_database_data(db, backup_content, mode=mode)
    return result


@router.post("/optimize", response_model=DatabaseOptimizeResponse)
async def optimize_db(db: aiosqlite.Connection = Depends(get_db_session)):
    """
    Ejecuta mantenimiento proactivo del motor SQLite:
    - Trunca el diario WAL a 0 bytes.
    - Ejecuta PRAGMA optimize para actualizar estadísticas del planificador de queries.
    - Ejecuta VACUUM para compactar páginas libres y reducir el tamaño del archivo en disco.
    """
    return await optimize_database(db)
