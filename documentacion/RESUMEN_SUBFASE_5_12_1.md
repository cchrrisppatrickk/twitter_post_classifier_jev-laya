# Resumen de Subfase 5.12.1: Esquema de Base de Datos y Persistencia Dual JSON (Backend Core)

## 1. Visión General y Objetivos Alcanzados

La **Subfase 5.12.1** establece los cimientos de datos para la **Fase 5.12 (Persistencia Dual JSON, Historial de Clasificación y Re-categorización A/B)**. Con esta actualización, el sistema garantiza fidelidad absoluta en el almacenamiento: ningún campo original del scraper se pierde y el objeto completo de inferencia de Laya queda resguardado junto con un registro inmutable de auditoría.

### Logros Clave:

1. **Ampliación del Esquema de la Tabla `posts`:**
   - Se agregaron 4 columnas estructurales en SQLite WAL:
     - `raw_json` (`TEXT`): Almacena la estructura JSON íntegra recibida del scraper/archivo de Twitter.
     - `classification_json` (`TEXT`): Almacena el objeto JSON completo de la inferencia System 1/RLCD (incluyendo `raw_answers`, probabilidades de categorías, bonificaciones de dominio y métricas de latencia).
     - `taxonomy_version` (`TEXT` DEFAULT `'2.1.0'`): Fingerprint de la versión taxonómica activa al momento de la inferencia.
     - `reclassification_count` (`INTEGER` DEFAULT `0`): Contador acumulativo de reevaluaciones.

2. **Creación de la Tabla Relacional `post_classification_history`:**
   - Tabla normalizada para versionado histórico con clave foránea a `posts(tweet_id)` y borrado en cascada:
     ```sql
     CREATE TABLE IF NOT EXISTS post_classification_history (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         tweet_id TEXT NOT NULL,
         version_number INTEGER NOT NULL,
         taxonomy_version TEXT NOT NULL,
         primary_category TEXT NOT NULL,
         secondary_categories TEXT,
         affinity_score REAL DEFAULT 0.0,
         format TEXT,
         technical_depth REAL DEFAULT 1.0,
         assets TEXT,
         raw_answers TEXT,
         classification_json TEXT NOT NULL,
         trigger_type TEXT NOT NULL,      -- 'initial_ingest', 'bulk_reclassify', 'manual_reclassify', 'manual_override', 'pre_rollback'
         reason TEXT,
         status TEXT DEFAULT 'ARCHIVED',  -- 'ARCHIVED', 'ACTIVE_SUPERSEDED', 'ROLLED_BACK'
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         FOREIGN KEY(tweet_id) REFERENCES posts(tweet_id) ON DELETE CASCADE
     );
     ```
   - Índices de alto rendimiento creados: `idx_history_tweet` e `idx_history_created`.

3. **Migración Automática e Idempotente en [`database.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/database.py):**
   - La función `init_db()` inspecciona `PRAGMA table_info(posts)` y ejecuta `ALTER TABLE` dinámicamente si las columnas no existen, preservando el 100% de los datos previos sin necesidad de regenerar la base de datos.

4. **Operaciones CRUD de Historial y Rollback:**
   - `archive_classification_history()`: Toma una instantánea inmutable del estado actual del post con número de versión secuencial incremental (`version_number = N + 1`) e incrementa `reclassification_count`.
   - `get_post_history()`: Recupera el árbol genealógico completo de clasificaciones en orden cronológico inverso deserializando automáticamente los campos JSON.
   - `get_history_entry_by_id()`: Consulta individual de instantáneas archivadas.
   - `rollback_post_classification()`: Restaura una versión histórica previa, archivando el estado actual antes de la restauración (`pre_rollback`) y actualizando la fila activa en `posts` a estado `CLASSIFIED_MANUAL`.

5. **Modelos Pydantic V2 en [`schema.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/schema.py):**
   - Actualización de `RawPost` y `CleanPost` con `raw_source_json`.
   - Actualización de `PostResponse` y `AnalyzePostResponse` con `raw_json`, `classification_json`, `taxonomy_version` y `reclassification_count`.
   - Nuevos modelos para auditoría y reclasificación: `ClassificationHistoryItem`, `PostHistoryResponse`, `RollbackClassificationResponse`, `ReclassifyRequest`, `PostComparisonResponse`.

6. **Integración en Servicios de Ingesta y Batch:**
   - [`ingest_service.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/services/ingest_service.py): Mantiene intacto el diccionario original `raw_source_json` durante la normalización y detección de assets.
   - [`batch_service.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/services/batch_service.py): Persiste `raw_json` y `classification_json` en los commits periódicos del worker en segundo plano.
   - [`endpoints_posts.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/api/endpoints_posts.py): Inyecta y devuelve los JSONs completos en `/api/posts/analyze`, `/api/posts/analyze-batch-stream` y `/api/posts/{tweet_id}`.

---

## 2. Pruebas Realizadas y Resultados

### Suite de Pruebas Unitarias de Historial (`tests/test_history_and_persistence.py`):
Se desarrollaron 5 pruebas exhaustivas verificando el ciclo de vida completo:
1. `test_01_schema_columns_and_history_table`: Migración DDL y presencia de columnas en `posts` y `post_classification_history`.
2. `test_02_insert_and_retrieve_dual_json`: Inserción y deserialización íntegra de `raw_json` y `classification_json`.
3. `test_03_archive_history_and_version_increment`: Versionado incremental (v1 → v2), actualización de `reclassification_count` y orden cronológico.
4. `test_04_rollback_classification`: Restauración segura de versiones anteriores, archivado `pre_rollback` y marcado `ROLLED_BACK`.
5. `test_05_api_analyze_with_dual_json`: Inferencia de Laya en tiempo real con persistencia en SQLite y retorno verificado de ambos JSONs vía API REST.

**Resultado:**
```text
Ran 5 tests in 22.723s - OK
```

### Regresión Backend (`tests/test_categories_crud.py`):
```text
Ran 6 tests in 0.203s - OK
```

---

## 3. Archivos Creados y Modificados en la Subfase 5.12.1

| Estado | Archivo | Responsabilidad Arquitectónica |
|---|---|---|
| **Nuevo** | [`tests/test_history_and_persistence.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/tests/test_history_and_persistence.py) | Suite de pruebas unitarias para persistencia dual JSON, historial y rollback |
| **Nuevo** | [`documentacion/RESUMEN_SUBFASE_5_12_1.md`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/documentacion/RESUMEN_SUBFASE_5_12_1.md) | Resumen formal de la Subfase 5.12.1 |
| **Modificado** | [`backend/app/database.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/database.py) | DDL `posts` (nuevas columnas), DDL `post_classification_history`, migraciones automáticas y funciones de historial |
| **Modificado** | [`backend/app/schema.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/schema.py) | Modelos Pydantic para `ClassificationHistoryItem`, `RollbackClassificationResponse`, campos duales JSON |
| **Modificado** | [`backend/app/services/ingest_service.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/services/ingest_service.py) | Preservación de `raw_source_json` en `RawPost` y `CleanPost` |
| **Modificado** | [`backend/app/services/batch_service.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/services/batch_service.py) | Guardado de `raw_json` y `classification_json` en lotes masivos |
| **Modificado** | [`backend/app/api/endpoints_posts.py`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/backend/app/api/endpoints_posts.py) | Inyección y respuesta de JSONs completos en endpoints de análisis e inspección |
| **Modificado** | [`documentacion/PLAN_SUBFASE_5_12.md`](file:///home/patricklinux/Dev/GEMINI-ANTIGRAVITY%20APPS/JEV_APPS/twitter_post_classifier_master/documentacion/PLAN_SUBFASE_5_12.md) | Marcado de Subfase 5.12.1 como completada |
