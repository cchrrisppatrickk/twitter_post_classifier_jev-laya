# Resumen Subfase 5.16: Activación Dinámica de Preguntas y Perfiles de Inferencia Laya

## 1. Contexto y Fundamentación Científica
En la arquitectura **Laya System 1** (`convaiinnovations/laya`), todas las preguntas tipadas (Categorías, Choice, Score, Noul) se compilan en un árbol de decisión y se resuelven en una **única pasada hacia adelante (single forward pass)**. 
- **En CPU**: Cada forward pass toma entre ~18s y ~22s independientemente del número de preguntas.
- **En GPU**: Toma aproximadamente ~33ms.

Sin embargo, el clasificador de Laya cuenta con un presupuesto de tokens finito (`head_max_len`: 192 tokens en inglés, 256 en multilingüe). Al agregar demasiadas preguntas simultáneas con múltiples opciones textuales, se produce **dilución de tokens** y dispersión de atención en la cabeza de inferencia, reduciendo la nitidez de la categorización base.

Para solucionar esto, se implementó un sistema integral de **activación/desactivación de preguntas** y **perfiles de inferencia en tiempo de ingesta**.

---

## 2. Cambios Implementados

### A. Persistencia y Backend Dinámico
1. **`backend/data/categories.json`**:
   - Se añadió la propiedad `"active": true` a todas las preguntas suplementarias (`content_format`, `technical_depth`, `reproducible_asset_type`, `is_uncensored_or_nsfw`, `is_local_first`).
2. **`backend/app/registry.py`**:
   - `build_decision_schema(active_questions: Optional[List[str]] = None)`: Permite compilar selectivamente solo las preguntas activas. Si se especifica una lista `active_questions`, se filtra el árbol preservando siempre las preguntas protegidas (`category`).
3. **`backend/app/engine.py`**:
   - `classify_post(post, active_questions=None)`: Compila el esquema bajo demanda si se recibe un filtro de preguntas por solicitud sin alterar el esquema global del singleton.
4. **Endpoints FastAPI (`backend/app/api/endpoints_categories.py` y `endpoints_posts.py`)**:
   - `PATCH /api/categories/questions/supplementary/{q_id}/toggle`: Endpoint atómico para alternar el estado activo/inactivo de una pregunta con persistencia en disco y recarga en memoria.
   - `POST /api/posts/analyze` y `POST /api/posts/analyze-batch-stream`: Aceptan `active_questions: List[str]` opcional para controlar qué preguntas responder por post o lote.

### B. Registry Studio UI (`frontend/js/config/questions.js`)
- En la pestaña **Preguntas Suplementarias** (`/config`):
  - Cada tarjeta de pregunta muestra un indicador visual **ACTIVA** (verde esmeralda) o **INACTIVA** (gris tenue con opacidad reducida).
  - Botón de switch de activación interactivo (`Desactivar` / `Activar`).
  - Las preguntas inactivas se excluyen automáticamente de los análisis posteriores por defecto.

### C. Ingest Modal: Perfiles de Inferencia (`frontend/js/modals/ingest_modal.js`)
En el modal de Ingesta Masiva / Single Post se integró el selector de **Perfil de Inferencia Laya**:
1. **Completo (Waffle + Todas las preguntas activas)**:
   - Realiza la clasificación completa con todas las preguntas suplementarias activadas en el Registry.
2. **Rápido (Solo Waffle / Categoría Base)**:
   - Ejecuta únicamente la categorización taxonómica de 48 categorías, omitiendo las suplementarias y reduciendo al mínimo la carga de tokens.
3. **Personalizado (Selección granular)**:
   - Despliega un panel interactivo con checkboxes para seleccionar exactamente qué preguntas suplementarias responder para el lote a procesar (ideal para clasificaciones especializadas como modelos específicos, benchmarks, NSFW, o local-first).

---

## 3. Pruebas y Verificación

### A. Pruebas Unitarias e Integración
- Nueva suite: `tests/test_questions_toggle.py`
  - `test_list_supplementary_questions_active_field`: Valida la presencia de `active: true` en la API.
  - `test_toggle_supplementary_question`: Valida el cambio atómico de estado mediante `PATCH /toggle`.
  - `test_build_decision_schema_with_active_filter`: Valida el filtrado del árbol de decisión.
- **Suite completa (17 archivos de pruebas ejecutados con aislamiento de procesos)**:
  - **17/17 suites aprobadas con éxito (100.0%)** en 865.29s sin fugas de memoria ni degradación de CPU.

### B. Verificación de UI en Navegador (Playwright)
- Ejecutado script automatizado interactuando con servidor en vivo:
  - `http://127.0.0.1:8000/config`: 5 botones de toggle detectados y funcionando.
  - `http://127.0.0.1:8000/`: Modal de Ingesta validado con los 3 perfiles de inferencia y checkboxes dinámicos de selección personalizada.
