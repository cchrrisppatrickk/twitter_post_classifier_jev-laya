# Resumen de Ejecución: Subfase 5.12.2 - Detección de Duplicados y Modos de Ingesta Masiva / Batch

**Versión del Sistema:** v2.1.0  
**Fecha:** 15 de Octubre, 2026  
**Estado:** COMPLETADO CON ÉXITO (100% de Pruebas Unitarias y E2E Aprobadas)  

---

## 1. Objetivos Cumplidos

En esta subfase se implementó y validó la arquitectura integral de **Deduplicación Inteligente y Modos de Ingesta Masiva (Batch Streaming)** descrita en el ADR-005 y los requerimientos de la Fase 5.12:

1. **Selector Interactivo en Modal de Ingesta (`frontend/modals/ingest_modal.html`):**
   - Incorporación de selector tipo radio card interactivo con dos estrategias operativas:
     - **Opción A (`skip` - Recomendado / 0 ms CPU):** Si el tweet ya está registrado en SQLite WAL, solo se actualizan sus métricas de engagement (`favorite_count`, `retweet_count`, `reply_count`, `bookmark_count`) omitiendo el forward pass de Laya Router.
     - **Opción B (`reclassify`):** Si el tweet ya existe, se re-evalúa con la taxonomía v2.1.0 activa de Laya, se archiva de manera inmutable la versión anterior en `post_classification_history` (`trigger_type="bulk_reclassify"`), y se incrementa el contador de versionado `reclassification_count`.

2. **Soporte en Streaming NDJSON (`POST /api/posts/analyze-batch-stream`):**
   - Manejo de `payload.duplicate_strategy`:
     - Modo `skip`: Detección en 0ms; se construye la respuesta a partir de los datos almacenados en SQLite y se emite el evento SSE con `telemetry: { "latency_ms": 0.0, "engine": "cache_skip", "skipped": true }`.
     - Modo `reclassify`: Ejecuta la inferencia, archiva el estado previo en `post_classification_history`, persiste la nueva clasificación con `reclassification_count = count + 1`, y emite `telemetry: { "reclassified": true }`.

3. **Pipeline de Ingesta por Archivo (`POST /api/ingest` & `IngestService`):**
   - Inclusión del parámetro `duplicate_strategy: str = Query("skip", pattern="^(skip|reclassify)$")`.
   - `IngestService.process_ingest_payload()` discrimina si el post existe:
     - `skip`: actualiza métricas (`existing_posts_updated`), no encola para System 1.
     - `reclassify`: actualiza métricas, encola en `new_clean_posts` y computa `reclassified_posts_queued`.

4. **Archivado Atómico en Checkpoints de Lote (`BatchService._commit_buffer`):**
   - Antes de escribir o reemplazar un post preexistente en SQLite WAL, `_commit_buffer` invoca automáticamente `archive_classification_history()` y preserva `raw_json` original si el nuevo ítem no lo suministra.

5. **Deduplicación Reactiva en Frontend (`frontend/js/modals/ingest_modal.js`):**
   - Al recibir eventos de post clasificados durante el streaming de lote, el controlador busca si el post ya reside en memoria (`window.currentScrapedPosts`):
     - Si existe: actualiza el elemento en el índice exacto y refresca la vista (`renderMatrix()`).
     - Si es nuevo: inserta al inicio con `unshift()` y llama a `appendPostToMatrixRow()`.
   - Retroalimentación visual en la micro-barra con badges `[OMITIDO/0ms]` y `[RECLASIFICADO]`.

---

## 2. Archivos Modificados y Creados

| Componente | Archivo | Modificación |
|---|---|---|
| **Pydantic Schema** | `backend/app/schema.py` | Agregado `reclassified_posts_queued` a `IngestResponse`. |
| **Ingest Service** | `backend/app/services/ingest_service.py` | Soporte para `duplicate_strategy="reclassify"` y conteo dual en lotes. |
| **Ingest Endpoint** | `backend/app/api/endpoints_ingest.py` | Query param `duplicate_strategy` validado con regex. |
| **Database Core** | `backend/app/database.py` | `archive_classification_history` adaptado para aceptar `existing_post` directo y `notes`. |
| **Batch Worker** | `backend/app/services/batch_service.py` | Archivador automático de versiones anteriores en `_commit_buffer`. |
| **Stream Endpoint** | `backend/app/api/endpoints_posts.py` | Flujo de bifurcación `skip` (0ms cache) vs `reclassify` (Laya + historial snapshot). |
| **Frontend Modal HTML** | `frontend/modals/ingest_modal.html` | Selector visual de estrategia para duplicados con estilo Tailwind y badge SQLite WAL. |
| **Frontend Modal JS** | `frontend/js/modals/ingest_modal.js` | Extracción de estrategia seleccionada, payload streaming y actualización in-place en memoria. |
| **Frontend Data Model** | `frontend/js/data.js` | Inclusión de `raw_json`, `classification_json`, `taxonomy_version` y `reclassification_count` en `formatAppPost`. |
| **Pruebas Unitarias** | `tests/test_batch_duplicates.py` | 5 pruebas unitarias exhaustivas con 100% de éxito en 38.5s. |
| **Pruebas E2E UI** | `scratch/test_subfase_5_12_2_ingest_modal.py` | Verificación de interactividad Playwright y captura de pantalla. |

---

## 3. Resultados de Pruebas y Validación

### 3.1 Suite de Deduplicación y Reclasificación en Lote (`tests/test_batch_duplicates.py`)
```
test_01_ingest_service_skip_strategy .................................... OK
test_02_ingest_service_reclassify_strategy .............................. OK
test_03_analyze_batch_stream_skip ....................................... OK
test_04_analyze_batch_stream_reclassify ................................. OK
test_05_batch_service_commit_buffer_archives_history .................... OK
----------------------------------------------------------------------
Ran 5 tests in 38.565s - OK
```

### 3.2 Suites de Regresión
- **Persistencia Dual e Historial (`tests/test_history_and_persistence.py`):** 5/5 OK.
- **CRUD de Taxonomía y Preguntas Suplementarias (`tests/test_categories_crud.py`):** 6/6 OK.
- **Total:** 16/16 pruebas pasando al 100% sin regresiones.

### 3.3 Verificación Visual Playwright E2E
- **Captura generada:** `subfase_5_12_01_ingest_modal_duplicates.png`.
- Visualización validada: Selector de doble tarjeta, selección por defecto en "Omitir Inferencia (0 ms CPU)", activación fluida de "Re-evaluar con Laya actual" y persistencia en SQLite WAL.

---

## 4. Estado de la Fase 5.12 y Próximos Pasos

- [x] **Subfase 5.12.1:** Esquema de Base de Datos y Persistencia Dual JSON (Backend Core)
- [x] **Subfase 5.12.2:** Detección de Duplicados y Modos de Ingesta Masiva / Batch
- [ ] **Subfase 5.12.3:** Reclasificación Individual Interactiva y Endpoints de Historial & Rollback
- [ ] **Subfase 5.12.4:** Comparativa Visual A/B, Historial y Selector de Conservación en Frontend
