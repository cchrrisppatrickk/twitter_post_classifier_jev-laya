"""
endpoints_ingest.py - Carga de archivos JSON y reporte de deduplicación en tiempo real (ADR-005).
"""

from __future__ import annotations
import logging
from pathlib import Path
import tempfile
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from ..schema import IngestResponse
from ..services.batch_service import BatchService
from ..services.ingest_service import IngestService

logger = logging.getLogger("api_ingest")
router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def upload_json_dump(
    file: UploadFile = File(...),
    auto_start: bool = True,
    duplicate_strategy: str = Query(default="skip", pattern="^(skip|reclassify)$")
):
    """
    Recibe un archivo JSON exportado por meridian_twitter_scraper_v2 o similar:
    - Aplica deduplicación inteligente con ijson streaming.
    - Si el tweet ya existe: refresca solo métricas si duplicate_strategy='skip' (0 ms Laya)
      o encola para reclasificar archivando historial si duplicate_strategy='reclassify'.
    - Si el tweet es nuevo: lo encola en el Batch Runner para inferencia en segundo plano.
    """
    if not file.filename.endswith((".json", ".jsonl")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Se requiere un archivo .json o .jsonl."
        )

    # Guardar en archivo temporal para permitir streaming ijson
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        response, new_clean_posts = await IngestService.process_ingest_payload(
            tmp_path,
            duplicate_strategy=duplicate_strategy
        )

        # Encolar posts en el BatchService
        batch_svc = BatchService.get_instance()
        await batch_svc.enqueue_batch(
            batch_id=response.batch_id,
            file_name=file.filename,
            posts=new_clean_posts,
            auto_start=auto_start
        )

        return response
    except Exception as e:
        logger.error(f"Error procesando ingesta de archivo {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo durante la ingesta: {str(e)}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)
