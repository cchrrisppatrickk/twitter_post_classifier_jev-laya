# Plan de Implementación Fase 5.12: Persistencia Dual JSON, Historial de Clasificación y Re-categorización A/B

## 1. Diagnóstico Actual: ¿Cómo se guardan hoy los datos en SQLite?

### Entrada vs Almacenamiento Actual:
Actualmente, el sistema recibe dos estructuras de datos:
1. **Entrada (Input):** Un JSON de metadatos del post (proveniente de scrapers de Twitter/X o Meridian con texto, autor, métricas, multimedia, enlaces, etc.).
2. **Salida (Output):** Un objeto de inferencia generado por Laya System 1 (`ClassificationResult` con `primary_category`, `secondary_categories`, `affinity_score`, `format`, `technical_depth`, `assets`, `raw_answers`, etc.).

### ¿Qué se guarda realmente en SQLite hoy?
En la tabla `posts` de SQLite WAL ([`backend/app/database.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/database.py)), se guardan **columnas tabulares planas normalizadas**:
- **Identificación:** `tweet_id` (PRIMARY KEY), `post_url`.
- **Autoría:** `author_name`, `author_id`.
- **Contenido:** `content`, `preview_text`, `date`, `lang`.
- **Métricas:** `favorite_count`, `retweet_count`, `reply_count`, `bookmark_count`.
- **Multimedia:** `media_urls` (JSON string), `media_count`, `media_type`.
- **Inferencia Laya:** `primary_category`, `secondary_categories` (JSON string), `affinity_score`, `format`, `format_confidence`, `technical_depth`, `assets` (JSON string), `is_local_first`, `is_nsfw`, `is_outlier`, `status`, `engine_used`, `inference_latency_ms`.

### Limitaciones Identificadas (Lo que falta):
1. **No se guarda el JSON crudo original (`raw_json`):** Si el scraper envía campos adicionales (followers, entidades, videos con bitrate específico, hashtags, etc.), se pierden al insertarse en SQLite.
2. **No se guarda el JSON completo de inferencia (`classification_json`):** Campos ricos como `raw_answers` con probabilidades detalladas por categoría y bonificaciones por dominio (`domain_boosts`) no quedan almacenados en la fila. En consecuencia, el modal de vista completa (`RichPostModal`) actualmente sintetizaba un JSON simulado para la pestaña "Raw JSON".
3. **No existe historial de clasificaciones:** Si un post se actualiza o reclasifica, SQLite sobrescribe la fila (`ON CONFLICT DO UPDATE`), borrando la categoría y confianza anteriores sin posibilidad de auditar la evolución ni hacer rollback.
4. **Deduplicación estricta pero rígida:** Durante la ingesta por lotes, si el post ya existe, solo se actualizan las métricas sociales y se omite la inferencia (0 ms Laya). Pero si el analista actualizó la taxonomía (nuevas palabras clave, umbrales o preguntas) y desea reclasificar los posts existentes, no existe un selector para decidir entre omitir o reclasificar con historial.

---

## 2. Arquitectura de Solución Propuesta

### 2.1 Esquema de Base de Datos Enriquecido (SQLite WAL)

#### A. Ampliación de la Tabla `posts`:
Se añadirán 4 columnas mediante migración DDL idempotente:
- `raw_json` (`TEXT`): String JSON con la estructura completa original recibida del scraper/archivo.
- `classification_json` (`TEXT`): String JSON con la respuesta completa de inferencia de Laya (`raw_answers`, `probabilities`, `scores`, `latency`, `rules_applied`).
- `taxonomy_version` (`TEXT` DEFAULT `'2.1.0'`): Versión de la taxonomía con la que fue clasificado el post.
- `reclassification_count` (`INTEGER` DEFAULT `0`): Contador de veces que el post ha sido reevaluado.

#### B. Nueva Tabla Relacional: `post_classification_history`
```sql
CREATE TABLE IF NOT EXISTS post_classification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,          -- 1, 2, 3...
    taxonomy_version TEXT NOT NULL,           -- '2.0.0', '2.1.0', etc.
    primary_category TEXT NOT NULL,
    secondary_categories TEXT,                 -- JSON array
    affinity_score REAL DEFAULT 0.0,
    format TEXT,
    technical_depth REAL DEFAULT 1.0,
    assets TEXT,                               -- JSON array
    classification_json TEXT NOT NULL,         -- JSON completo de esa versión
    trigger_type TEXT NOT NULL,                -- 'initial_ingest', 'bulk_reclassify', 'manual_reclassify', 'manual_override'
    reason TEXT,                               -- Nota o justificativo del cambio
    status TEXT DEFAULT 'ARCHIVED',            -- 'ARCHIVED', 'ACTIVE_SUPERSEDED', 'ROLLED_BACK'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tweet_id) REFERENCES posts(tweet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_tweet ON post_classification_history(tweet_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON post_classification_history(created_at DESC);
```

---

### 2.2 Flujo de Deduplicación y Reclasificación en Ingesta Masiva

En el modal de Ingesta Masiva ([`frontend/js/modals/ingest_modal.js`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/frontend/js/modals/ingest_modal.js)), se incorporará un selector interactivo de **Estrategia para Posts Existentes**:

- **Opción 1: Omitir duplicados ya registrados (Recomendado - 0 ms CPU):** Actualiza únicamente likes/retweets y preserva intacta la clasificación.
- **Opción 2: Re-evaluar existentes con taxonomía actual:** Ejecuta Laya sobre los posts repetidos, archiva la clasificación previa en `post_classification_history`, actualiza la base de datos y marca el post con un badge `RECLASIFICADO (DIFF DISPONIBLE)` para que el analista pueda auditar las diferencias.

---

### 2.3 Flujo de Reclasificación Individual Interactiva & Comparativa A/B

1. **Detección:** Si el `tweet_id` ya existe en SQLite al ingresar en modo individual, la UI informa:
   > *"Este post ya fue clasificado anteriormente como [ia_modelos] (Confianza: 78%). ¿Deseas re-evaluarlo con la taxonomía actual v2.1.0 o conservar la versión actual?"*
2. **Modo Simulación / Dry-Run:** Si el usuario elige re-evaluar, Laya calcula el forward pass en ~28 ms sin sobrescribir la base de datos de inmediato.
3. **Modal de Comparativa A/B Diff:** Se despliega una interfaz lado a lado en el modal del post:
   - **Izquierda (Versión Previa / v2.0.0):** Categoría, afinidad, formato, profundidad técnica, fecha.
   - **Derecha (Nueva Versión / v2.1.0):** Nueva categoría sugerida, afinidad calibrada, nuevas directivas aplicadas.
   - **Resaltado de Diferencias:** Si la categoría cambió (ej. de `ia_modelos` a `ia_local`), se resalta con el delta de afinidad.
4. **Decisión del Usuario en 1 Clic:**
   - **[Conservar Clasificación Anterior]:** Descarta la nueva inferencia y mantiene el registro original.
   - **[Aceptar y Aplicar Nueva Clasificación]:** Archiva la versión anterior en `post_classification_history`, actualiza `posts` con la nueva y refresca la Waffle Grid en vivo.
5. **Historial y Rollback:** Pestaña "Historial de Versiones" en `#richPostModal` y en el Drawer con botón `[Rollback]` para restaurar versiones pasadas en cualquier momento.

---

## 3. Desglose en Subfases de Implementación

### Subfase 5.12.1: Esquema de Base de Datos y Persistencia Dual JSON (Backend Core) [COMPLETADA]
- Migración DDL no destructiva: adición de columnas `raw_json`, `classification_json`, `taxonomy_version`, `reclassification_count` en la tabla `posts`.
- Creación de tabla `post_classification_history` e índices.
- Modelos Pydantic en `schema.py` (`ClassificationHistoryItem`, `PostComparisonResponse`, etc.).
- Funciones en `database.py`: `archive_classification_history()`, `get_post_history()`, `rollback_post_classification()`.
- Actualización de `batch_service.py` e `ingest_service.py` para persistir ambos JSONs completos.
- Suite de pruebas unitarias (`tests/test_history_and_persistence.py`): 5/5 tests pasando al 100%.

### Subfase 5.12.2: Detección de Duplicados y Modos de Ingesta Masiva / Batch [COMPLETADA]
- Selector interactivo de estrategia en `frontend/modals/ingest_modal.html` y `frontend/js/modals/ingest_modal.js` (`skip` vs `reclassify`).
- Endpoint `POST /api/posts/analyze-batch-stream` con bifurcación cooperativa: `skip` (0 ms CPU / actualización de métricas) vs `reclassify` (Laya forward pass + archivado snapshot).
- Pipeline `POST /api/ingest` e `IngestService.process_ingest_payload()` con soporte de query param `duplicate_strategy`.
- Archivador automático en `BatchService._commit_buffer()` con preservación de `raw_json` e incremento de versión.
- Deduplicación reactiva in-place en memoria para la Matriz Waffle.
- Suite de pruebas unitarias (`tests/test_batch_duplicates.py`): 5/5 OK. Resumen en `documentacion/RESUMEN_SUBFASE_5_12_2.md`.

### Subfase 5.12.3: Reclasificación Individual Interactiva y Endpoints de Historial & Rollback [COMPLETADA]
- Endpoint `POST /api/posts/{tweet_id}/reclassify`:
  - `dry_run=True`: simula inferencia en caliente, retorna `PostComparisonResponse` con diff de afinidad y categorías sin mutar SQLite.
  - `confirm=True` / `dry_run=False`: archiva versión previa en `post_classification_history`, persiste nueva clasificación e incrementa `reclassification_count`.
- Endpoint `GET /api/posts/{tweet_id}/history`: historial cronológico de versiones retornando `PostHistoryResponse`.
- Endpoint `POST /api/posts/{tweet_id}/history/{history_id}/rollback`: reversión segura de clasificación anterior con snapshot `pre_rollback`.
- Métodos clientes en `frontend/js/api.js`: `API.posts.reclassify()`, `API.posts.getHistory()`, `API.posts.rollback()`.
- Suite de pruebas unitarias y de integración (`tests/test_reclassification_and_history_api.py`): 5/5 OK. Resumen en `documentacion/RESUMEN_SUBFASE_5_12_3.md`.


### Subfase 5.12.4: Comparativa Visual A/B, Historial y Selector de Conservación en Frontend [COMPLETADA]
- Actualización de `frontend/modals/rich_post_modal.html` y `frontend/js/modals/rich_post_modal.js`:
  - Cuarta pestaña interactiva (`#modalTabHistoryBtn`, `#tabContentHistory`) con contador dinámico `#modalHistoryCountBadge`.
  - Conexión real de pestañas Raw JSON con `raw_json` y `classification_json` reales persistidos en SQLite WAL.
  - Widget de comparación A/B Diff lado a lado (`#modalDiffWidget`) con badges de delta de afinidad y diagnóstico del cambio.
  - Botones de acción en 1 clic: `[Conservar Clasificación Anterior]` (`#modalDiffDismissBtn`) y `[Aceptar y Aplicar Nueva Clasificación]` (`#modalDiffApplyBtn`).
  - Lista cronológica de historial (`#modalHistoryListContainer`) con snapshots inmutables y botón `[Rollback]` operativo.
- Actualización de `frontend/js/drawer.js` y `frontend/components/drawer.html` con botón "Re-evaluar con Laya actual (A/B)" y badges de versión (`#drawerTaxonomyVersionBadge`, `#drawerReclassCountBadge`).
- Compilación de plantillas y assets sincronizados con `scripts/build_frontend.py`.
- Suite automatizada Playwright E2E (`scratch/test_subfase_5_12_reclassification_e2e.py`) verificada con capturas de pantalla `subfase_5_12_02_ab_diff_modal.png` y `subfase_5_12_03_history_rollback.png`. Resumen en `documentacion/RESUMEN_SUBFASE_5_12_4.md`.
