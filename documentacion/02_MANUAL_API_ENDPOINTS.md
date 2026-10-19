# 02 · Manual de API REST y Referencia de Endpoints

> **Servidor Base:** FastAPI v0.115+  
> **Host Predeterminado:** `http://127.0.0.1:8000` (o `0.0.0.0:8000`)  
> **Documentación Interactiva Swagger UI:** `http://127.0.0.1:8000/docs`  
> **Especificación OpenAPI:** `http://127.0.0.1:8000/openapi.json`  
> **Protocolos Soportados:** HTTP/1.1 REST (JSON) y Server-Sent Events (SSE Streaming)

---

## 📑 Índice de Enrutadores

1. [Enrutador de Publicaciones (`/api/posts`)](#1-enrutador-de-publicaciones-apiposts)
2. [Enrutador de Ingesta Masiva (`/api/ingest`)](#2-enrutador-de-ingesta-masiva-apiingest)
3. [Enrutador de Lotes y Telemetría SSE (`/api/batch`)](#3-enrutador-de-lotes-y-telemetría-sse-apibatch)
4. [Enrutador de Categorías y Preguntas (`/api/categories`)](#4-enrutador-de-categorías-y-preguntas-apicategories)
5. [Enrutador de Base de Datos SQLite (`/api/database`)](#5-enrutador-de-base-de-datos-sqlite-apidatabase)
6. [Enrutador del Sistema y Diagnóstico (`/api/system`)](#6-enrutador-del-sistema-y-diagnóstico-apisystem)

---

## 1. Enrutador de Publicaciones (`/api/posts`)

Este enrutador gestiona el análisis interactivo de tweets, streaming de lotes en vivo, filtros del dashboard, sobrescrituras humanas, comparativas A/B y auditoría de versiones históricas.

### 1.1 `POST /api/posts/analyze`
Ejecuta la inferencia de System 1 sobre un post individual. Permite evaluar en memoria o persistir atómicamente en SQLite WAL.

- **Request Body (`AnalyzePostRequest`):**
```json
{
  "text": "Released our new open-source 3D WebGL renderer built with Three.js and WebGPU! Check out the repo: https://github.com/dev/webgpu-engine",
  "id": "1846500123456789012",
  "author": "graphics_dev",
  "likes": 340,
  "retweets": 85,
  "media_urls": ["https://pbs.twimg.com/media/sample_preview.jpg"],
  "media_type": "photo",
  "date": "2026-10-15T14:30:00Z",
  "post_url": "https://x.com/graphics_dev/status/1846500123456789012",
  "persist": true,
  "active_questions": null
}
```

- **Response (`200 OK` · `AnalyzePostResponse`):**
```json
{
  "tweet_id": "1846500123456789012",
  "content": "Released our new open-source 3D WebGL renderer built with Three.js and WebGPU!...",
  "author_name": "graphics_dev",
  "primary_category": "threejs_webgl",
  "category_label": "Three.js & WebGL",
  "family_id": "modelado_3d",
  "color_hex": "#0284c7",
  "code": "3D-WGL",
  "affinity_score": 0.945,
  "secondary_categories": [
    { "id": "herramientas_codigo", "score": 0.58 }
  ],
  "format": "code_release",
  "format_confidence": 0.89,
  "technical_depth": 3.0,
  "is_tool_or_code_release": true,
  "is_local_first": false,
  "is_nsfw": false,
  "is_outlier": false,
  "assets": ["github_repo"],
  "status": "CLASSIFIED",
  "engine_used": "convaiinnovations/laya",
  "inference_latency_ms": 18.4,
  "taxonomy_version": "2.1.0",
  "reclassification_count": 0,
  "persisted": true
}
```

---

### 1.2 `POST /api/posts/analyze-batch-stream`
Transmite en tiempo real el progreso de inferencia de un lote de publicaciones mediante Server-Sent Events (SSE).

- **Request Body (`AnalyzeBatchRequest`):**
```json
{
  "posts": [
    { "text": "Nuevo addon de Blender para simular fuego con geometry nodes https://github.com/user/blender-fire", "id": "1001", "persist": true },
    { "text": "Discutiendo modelos de suscripción y MRR para startups SaaS bootstrapped", "id": "1002", "persist": true }
  ],
  "persist": true,
  "duplicate_strategy": "skip",
  "max_new_posts": null,
  "active_questions": null
}
```

- **Response Header:** `Content-Type: text/event-stream; charset=utf-8`
- **Mensajes SSE emitidos:**
```
data: {"event": "item_completed", "index": 1, "total": 2, "post": { ...AnalyzePostResponse... }, "telemetry": {"speed_tps": 32.5, "cpu_percent": 24.1, "ram_mb": 1420.5, "eta_seconds": 0.03}}

data: {"event": "item_completed", "index": 2, "total": 2, "post": { ...AnalyzePostResponse... }, "telemetry": {"speed_tps": 35.1, "cpu_percent": 23.8, "ram_mb": 1422.0, "eta_seconds": 0.0}}

data: {"event": "batch_completed", "index": 2, "total": 2, "telemetry": {"total_processed": 2, "elapsed_seconds": 0.06}}
```

---

### 1.3 `GET /api/posts/ids`
Retorna la totalidad de `tweet_ids` indexados en la base de datos para comprobación de presencia y deduplicación local en cliente sin necesidad de transferir registros completos.

- **Response (`200 OK` · `PostIdsResponse`):**
```json
{
  "total": 1683,
  "tweet_ids": ["1846500123456789012", "1846500987654321098", "1846501112233445566"]
}
```

---

### 1.4 `GET /api/posts/stats`
Compila y entrega todas las métricas agregadas necesarias para renderizar la Matriz Waffle, el Canvas Scatter 2D y las tarjetas de resumen.

- **Response (`200 OK` · `DashboardStatsResponse`):**
```json
{
  "total_posts": 1683,
  "classified_count": 1612,
  "pending_count": 52,
  "outliers_count": 19,
  "avg_affinity_score": 0.812,
  "avg_likes": 128.4,
  "categories_distribution": [
    {
      "id": "llms_modelos",
      "name": "Modelos LLM & Arquitectura",
      "family_id": "ia",
      "color_hex": "#8b5cf6",
      "count": 210,
      "avg_score": 0.884,
      "avg_likes": 345
    }
  ],
  "families_distribution": [
    { "id": "ia", "name": "Inteligencia Artificial", "color_hex": "#8b5cf6", "count": 485 },
    { "id": "blender", "name": "Blender 3D", "color_hex": "#ea580c", "count": 312 }
  ],
  "scatter_points": [
    {
      "id": "1846500123456789012",
      "x": 94.5,
      "y": 340,
      "primary": "threejs_webgl",
      "secondary": "herramientas_codigo",
      "outlier": false,
      "author": "graphics_dev",
      "date": "2026-10-15T14:30:00Z"
    }
  ]
}
```

---

### 1.5 `GET /api/posts`
Consulta paginada del listado de publicaciones con soporte para filtrado multidimensional, búsqueda full-text y ordenamiento configurable.

- **Query Parameters:**
  - `page` *(int, default: 1)*: Número de página.
  - `limit` *(int, default: 50, máx: 1000)*: Tamaño de página.
  - `family` *(string, opcional)*: Filtrar por ID de familia (`ia`, `blender`, etc.).
  - `category` *(string, opcional)*: Filtrar por ID exacto de categoría.
  - `status` *(string, opcional)*: `CLASSIFIED`, `PENDING`, `DISCARDED`.
  - `is_outlier` *(bool, opcional)*: Filtrar publicaciones anómalas.
  - `lang` *(string, opcional)*: Filtrar por código de idioma (`en`, `es`, `ja`).
  - `search` *(string, opcional)*: Búsqueda de texto en autor o contenido.
  - `sort_by` *(enum, default: `date_desc`)*: `date_desc`, `score_desc`, `likes_desc`.

- **Response (`200 OK` · `PostListResponse`):**
```json
{
  "total": 1683,
  "page": 1,
  "limit": 50,
  "posts": [
    {
      "tweet_id": "1846500123456789012",
      "post_url": "https://x.com/graphics_dev/status/1846500123456789012",
      "author_name": "graphics_dev",
      "content": "Released our new open-source 3D WebGL renderer...",
      "preview_text": "Released our new open-source 3D WebGL...",
      "date": "2026-10-15T14:30:00Z",
      "metrics": { "favorite_count": 340, "retweet_count": 85, "reply_count": 12, "bookmark_count": 45 },
      "primary_category": "threejs_webgl",
      "affinity_score": 0.945,
      "status": "CLASSIFIED"
    }
  ]
}
```

---

### 1.6 `GET /api/posts/{tweet_id}`
Recupera todos los campos y metadatos de un post específico, incluyendo sus JSONs persistidos duales (`raw_json` y `classification_json`).

- **Response (`200 OK` · `PostResponse`):**
Retorna la estructura tipada completa de la publicación. Si no existe, retorna `404 Not Found`.

---

### 1.7 `POST /api/posts/{tweet_id}/override`
Permite a un operador humano reclasificar manualmente una publicación o resolver publicaciones en estado `PENDING`.

- **Request Body (`PendingOverrideRequest`):**
```json
{
  "primary_category": "blender_geometry_nodes",
  "secondary_categories": ["shaders_procedurales"],
  "status": "CLASSIFIED_MANUAL"
}
```

- **Response (`200 OK`):**
```json
{
  "status": "SUCCESS",
  "tweet_id": "1846500123456789012",
  "primary_category": "blender_geometry_nodes",
  "affinity_score": 1.0,
  "previous_category": "otros",
  "updated_at": "2026-10-17T15:20:00Z"
}
```

---

### 1.8 `POST /api/posts/{tweet_id}/reclassify`
Ejecuta una re-evaluación del post con el motor System 1. Soporta el modo de simulación A/B (`dry_run=true`) para previsualizar deltas de afinidad antes de escribir en disco.

- **Request Body (`ReclassifyRequest`):**
```json
{
  "dry_run": true,
  "confirm": false,
  "reason": "Auditoría tras actualizar umbrales de la familia IA"
}
```

- **Response (`200 OK` · `PostComparisonResponse`):**
```json
{
  "tweet_id": "1846500123456789012",
  "has_changed": true,
  "delta_affinity": 0.12,
  "previous": {
    "primary_category": "ia_general",
    "affinity_score": 0.72,
    "taxonomy_version": "2.0.0"
  },
  "current": {
    "primary_category": "llms_modelos",
    "affinity_score": 0.84,
    "taxonomy_version": "2.1.0"
  }
}
```

---

### 1.9 `GET /api/posts/{tweet_id}/history`
Consulta el historial cronológico completo de versiones de clasificación registradas para una publicación.

- **Response (`200 OK` · `PostHistoryResponse`):**
```json
{
  "tweet_id": "1846500123456789012",
  "total_versions": 2,
  "history": [
    {
      "id": 1,
      "tweet_id": "1846500123456789012",
      "version_number": 1,
      "taxonomy_version": "2.0.0",
      "primary_category": "ia_general",
      "affinity_score": 0.72,
      "trigger_type": "initial_ingest",
      "created_at": "2026-10-10T12:00:00Z"
    }
  ]
}
```

---

### 1.10 `POST /api/posts/{tweet_id}/history/{history_id}/rollback`
Revierte atómicamente la clasificación de una publicación al estado exacto que tenía en una versión previa guardada en el historial.

- **Response (`200 OK` · `RollbackClassificationResponse`):**
```json
{
  "status": "SUCCESS",
  "tweet_id": "1846500123456789012",
  "restored_history_id": 1,
  "restored_version": 1,
  "primary_category": "ia_general",
  "post": { ...PostResponse actualizado... }
}
```

---

## 2. Enrutador de Ingesta Masiva (`/api/ingest`)

### 2.1 `POST /api/ingest`
Carga un archivo JSON/NDJSON a través de `multipart/form-data`. El backend utiliza `ijson` para iterar elemento por elemento sin cargar el archivo completo en memoria RAM, deduplicando instantáneamente tweets existentes.

- **Form Parameters:**
  - `file`: Archivo subido (`.json`, `.ndjson` o `.jsonl`).
  - `duplicate_strategy` *(string, default: `skip`)*: `skip` (solo actualiza métricas sociales) o `reclassify` (archiva versión previa y reclasifica).
  - `max_new_posts` *(int, opcional)*: Límite superior de posts nuevos a procesar antes de detener el lote.

- **Response (`200 OK` · `IngestResponse`):**
```json
{
  "batch_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "total_posts_in_file": 1683,
  "new_posts_queued": 142,
  "reclassified_posts_queued": 0,
  "existing_posts_updated": 1541,
  "unchanged_posts_skipped": 0,
  "estimated_time_seconds": 2.84
}
```

---

## 3. Enrutador de Lotes y Telemetría SSE (`/api/batch`)

### 3.1 `POST /api/batch/start/{batch_id}`
Reanuda o inicia explícitamente el procesamiento en segundo plano de un lote encolado previamente.

### 3.2 `POST /api/batch/pause/{batch_id}`
Pausa la ejecución de un lote activo de forma segura respetando el checkpoint actual en disco.

### 3.3 `GET /api/batch/status/{batch_id}`
Consulta el estado de avance, ítems procesados y métricas de latencia de un lote específico.

### 3.4 `GET /api/batch/stream/{batch_id}`
Canal Server-Sent Events (SSE) dedicado para suscribirse al flujo de telemetría de un lote específico.

- **Evento SSE de Muestra:**
```json
{
  "batch_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "RUNNING",
  "processed": 85,
  "total": 142,
  "percentage": 59.86,
  "speed_tps": 34.2,
  "avg_latency_ms": 29.2,
  "cpu_percent": 18.5,
  "ram_mb": 1435.0,
  "eta_seconds": 1.66
}
```

---

## 4. Enrutador de Categorías y Preguntas (`/api/categories`)

Este enrutador otorga control total a **JEV Registry Studio** para manipular la taxonomía y el esquema de preguntas sin reiniciar el servidor.

### 4.1 Parámetros Globales
- `GET /api/categories/settings/globals`: Consulta pesos de scoring, umbrales y dominios de activos.
- `PUT /api/categories/settings/globals`: Modifica parámetros globales en `categories.json`.

### 4.2 Banco de Preguntas Tipadas (System 1)
- `GET /api/categories/questions/supplementary`: Lista todas las preguntas suplementarias (`Choice`, `Score`, `Noul`).
- `POST /api/categories/questions/supplementary`: Añade una nueva pregunta estructurada.
- `PUT /api/categories/questions/supplementary/{q_id}`: Edita instrucciones y criterios de una pregunta existente.
- `PATCH /api/categories/questions/supplementary/{q_id}/toggle`: Activa o desactiva una pregunta tipada en tiempo real.
- `DELETE /api/categories/questions/supplementary/{q_id}`: Elimina una pregunta del registro.

### 4.3 Gestión de Taxonomía y Categorías
- `GET /api/categories`: Retorna las 47 categorías del registro activo con sus metadatos.
- `POST /api/categories`: Da de alta una nueva categoría en la taxonomía.
- `GET /api/categories/{category_id}`: Consulta metadatos individuales de una categoría.
- `PUT /api/categories/{category_id}`: Modifica umbral, boosters, palabras clave o familia de la categoría.
- `DELETE /api/categories/{category_id}`: Desactiva o remueve la categoría.

---

## 5. Enrutador de Base de Datos SQLite (`/api/database`)

### 5.1 `GET /api/database/stats`
Obtiene estadísticas físicas y operativas del archivo SQLite y del diario WAL.

- **Response (`200 OK` · `DatabaseStatsResponse`):**
```json
{
  "status": "HEALTHY",
  "posts_count": 1683,
  "history_count": 254,
  "checkpoints_count": 12,
  "feedback_count": 8,
  "db_size_bytes": 18432000,
  "db_size_formatted": "17.58 MB",
  "wal_size_bytes": 32768,
  "wal_size_formatted": "32.00 KB",
  "sqlite_version": "3.45.1",
  "journal_mode": "wal",
  "taxonomy_version": "2.1.0",
  "database_file": "database.sqlite"
}
```

### 5.2 `POST /api/database/optimize`
Ejecuta la sentencia `VACUUM;` y fuerza un checkpoint truncado del diario WAL (`PRAGMA wal_checkpoint(TRUNCATE)`), liberando espacio en disco sin reiniciar la aplicación.

### 5.3 `GET /api/database/export`
Descarga un archivo JSON autocontenido con el volcado completo de las tablas `posts`, `post_classification_history` y `taxonomy_feedback`.

### 5.4 `POST /api/database/import`
Restaura o combina datos a partir de un respaldo JSON exportado previamente.
- Modos: `merge` (combina registros respetando existentes) o `replace` (sustituye por completo).

### 5.5 `POST /api/database/reset`
Vaciado controlado de la base de datos para entornos de pruebas o reinicio de ciclo de vida. Permite preservar selectivamente la tabla de feedback humano.

---

## 6. Enrutador del Sistema y Diagnóstico (`/api/system`)

### 6.1 `GET /api/system/health`
Retorna el estado de operatividad del motor Laya, dispositivo de hardware en uso y consumo de recursos.

- **Response (`200 OK` · `SystemHealthResponse`):**
```json
{
  "status": "healthy",
  "device": "cuda",
  "cpu_model": "Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz",
  "gpu_model": "NVIDIA GeForce RTX 4090",
  "vram_total_gb": 23.99,
  "vram_used_mb": 1120.4,
  "cuda_available": true,
  "device_display": "GPU (NVIDIA GeForce RTX 4090)",
  "estimated_latency": "~33ms/post",
  "ram_total_gb": 15.48,
  "ram_available_gb": 11.20,
  "ram_used_process_mb": 1420.5,
  "models_loaded": ["convaiinnovations/laya"],
  "active_batches": 0,
  "version": "2.1.0"
}
```

### 6.2 `GET /api/system/categories`
Entrega un resumen ágil de categorías y colores mapeados para el renderizado inicial del DOM.

### 6.3 `GET /api/system/checkpoints`
Lista los últimos checkpoints de lotes guardados en la base de datos para auditoría.
