# Informe de Análisis Forense Exhaustivo del Sistema
## Twitter Post Classifier Master (v2.1.1 - Laya Decision Engine & JEV Registry Studio)

**Fecha de la Auditoría:** 15 de Octubre, 2026  
**Auditor:** Agente de Ingeniería Antigravity  
**Metodología:** Graph-First Engineering (`graphify`), Ejecución Integral de Pruebas Unitarias y de Integración (59 tests en PyTorch CPU), Auditoría de Esquemas SQLite WAL, Inspección E2E con Playwright en Navegador Brave, y Análisis Estático de Código.

---

## Executive Summary (Resumen Ejecutivo)

Se realizó una auditoría forense profunda y multidimensional del repositorio `twitter_post_classifier_master`, abarcando la capa de datos SQLite WAL, el motor de inferencia local **Laya System 1**, los servicios asíncronos de ingesta y procesamiento por lotes, la capa de endpoints REST/SSE en FastAPI, la arquitectura modular del frontend y la suite completa de pruebas automatizadas.

El sistema demuestra una base arquitectónica sólida y de alto rendimiento:
- **Grafo de Conocimiento:** 979 nodos, 1,705 aristas, 74 comunidades, 0 ciclos de importación cíclica detectados.
- **Suite de Pruebas:** 57 de 59 pruebas pasan exitosamente en condiciones de inferencia real en CPU.
- **Integridad Jev System 1:** El linter `lint_questions.py` arroja 0 errores y 0 advertencias sobre `categories.json`.

Sin embargo, el análisis forense identificó **discrepancias críticas, desalineaciones de especificación, deuda técnica y oportunidades inmediatas de mejora** clasificadas en 6 vectores estructurales:

---

## 1. Vector de Pruebas Automatizadas y Fiabilidad (Test Suite)

### 1.1 Resultados Empíricos de la Suite Completa
Se ejecutó la suite de tests unitarios y de integración mediante el runner oficial:
```bash
../laya_tester_app/.venv/bin/python3 -m unittest discover tests
```
- **Total ejecutados:** 59 pruebas.
- **Tiempo de ejecución:** 471.815 s (~7.8 minutos en CPU con inferencia PyTorch).
- **Resultados:** 57 pasadas (`.`), 2 falladas (`FAIL`).

### 1.2 Análisis Detallado de Pruebas Falladas

#### Falla 1: Incompatibilidad de Especificación en Validación de Entrada (`test_analyze.py`)
```text
FAIL: test_analyze_invalid_input (test_analyze.TestAnalyzeEndpoint.test_analyze_invalid_input)
Valida que textos vacíos o de menos de 2 caracteres sean rechazados con 422.
AssertionError: 200 != 422
```
* **Causa Raíz:** En la Subfase 5.13.1 se añadió el validador `@field_validator("text", mode="before")` en `AnalyzePostRequest` (`backend/app/schema.py`) para evitar caídas en el scraper ante publicaciones que contenían solo emojis únicos (como `🫧`, `🌆`) o espacios vacíos. El sanitizador reemplaza textos vacíos por `"[Sin contenido textual]"`. En consecuencia, una petición con `text="x"` o `text=""` ya nunca devuelve HTTP 422, sino HTTP 200 clasificado como post de baja afinidad.
* **Diagnóstico Forense:** `test_analyze.py` fue escrito bajo la especificación anterior (`min_length=2` estricto) y no fue actualizado tras la Subfase 5.13.1.
* **Acción Requerida:** Alinear `test_analyze.py` con la política de sanitización de 5.13.1 o definir qué condiciones sí deben retornar 422 (p. ej., payload sin campo text o campos de tipo incompatible).

#### Falla 2: Desincronización de Versión en Endpoint de Categorías (`test_api.py`)
```text
FAIL: test_system_categories_endpoint (test_api.TestApiEndpoints.test_system_categories_endpoint)
Verifica GET /api/system/categories.
AssertionError: '2.1.1' != '2.1.0'
```
* **Causa Raíz:** En la Subfase 5.14 se actualizó la taxonomía en `categories.json` a la versión `"2.1.1"`. Sin embargo, `test_api.py:L99` tenía una aserción estricta codificada como literal quemado (`self.assertEqual(data["registry_version"], "2.1.0")`).
* **Diagnóstico Forense:** Fragilidad por codificación literal de versión en la suite de pruebas.
* **Acción Requerida:** Actualizar la aserción en `test_api.py` a `"2.1.1"` o parametrizarla dinámicamente con `settings.APP_VERSION`.

### 1.3 Prueba Huérfana Omitida por el Runner
* **Archivo:** `tests/test_meridian_format.py`
* **Diagnóstico Forense:** Este archivo contiene funciones sueltas tipo pytest (`def test_normalize_meridian_items()`) en vez de heredar de `unittest.TestCase`. Como resultado, `python3 -m unittest discover tests` lo omite por completo de la suite continua.
* **Acción Requerida:** Refactorizar `test_meridian_format.py` para heredar de `unittest.TestCase` e incluirlo en la batería formal.

### 1.4 Contaminación de Estado Global entre Tests (*State Pollution*)
* **Diagnóstico Forense:** Múltiples suites de pruebas (`test_api.py`, `test_override_pending.py`, `test_batch_stream.py`, `test_database_management.py`, `test_subfase_5_13_1.py`) modifican en caliente la propiedad global:
  ```python
  settings.DATABASE_PATH = cls.test_db_path
  ```
  Ninguna de ellas guarda la ruta original para restaurarla en `tearDownClass`. Si `test_database_management.py` borra su base temporal `test_db_mgmt.sqlite` al terminar, las pruebas subsiguientes ejecutan queries sobre un archivo eliminado o recrean bases en ubicaciones erróneas.
* **Acción Requerida:** Implementar un patrón de preservación y restauración en `setUpClass` / `tearDownClass`:
  ```python
  cls._original_db_path = settings.DATABASE_PATH
  # en tearDownClass:
  settings.DATABASE_PATH = cls._original_db_path
  ```

### 1.5 División de Espacio de Nombres en Importaciones (*Split-Brain Imports*)
* **Diagnóstico Forense:** Algunos tests importan módulos como `from app.config import settings` (agregando `backend` al path), mientras otros hacen `from backend.app.config import settings`. En el runtime de Python, esto provoca que `sys.modules` mantenga dos copias independientes de `settings`, provocando que mutaciones de configuración en una prueba no sean visibles en otra.
* **Acción Requerida:** Estandarizar todas las importaciones del backend a la convención `from app....` o `from backend.app....`.

---

## 2. Vector de Memoria RAM, CPU y Telemetría de Hardware

### 2.1 Pico de Consumo de RAM en Inferencia Sostenida
* **Observación Empírica:** Durante el procesamiento continuo de la suite en CPU, el proceso Python escaló hasta **3,990 MB (~4.0 GB)** de consumo RSS.
* **Advertencia Registrada:**
  ```text
  WARNING:engine:Consumo de RAM elevado (3990.1 MB). Ejecutando gc.collect()...
  ```
* **Causa Raíz:** PyTorch CPU mantiene buffers de tensores cacheados tras inferencias sucesivas con Transformers/ModernBERT. Aunque `check_memory_safety()` en `engine.py` ejecuta `gc.collect()`, el umbral de disparo (`> 2048 MB`) se alcanza rápidamente cuando se ejecutan lotes continuos o múltiples workers.
* **Riesgo:** En equipos con 8 GB de RAM física, un consumo de 4 GB compitiendo con el navegador y el sistema operativo puede provocar swapping en disco o terminación por OOM Killer.
* **Acción Requerida:**
  1. Reducir `MAX_LOADED_MODELS` a 1 por defecto en entornos de CPU (`config.py`).
  2. Forzar `gc.collect()` periódicamente en el worker de `BatchService` cada 50 publicaciones procesadas.

### 2.2 Telemetría de CPU Hardcodeada
* **Archivo:** `backend/app/engine.py:L96`
* **Código Actual:**
  ```python
  cpu_info = "Intel Core i5-10210U CPU @ 1.60GHz (4C/8T)"
  ```
* **Diagnóstico Forense:** Aunque la máquina de desarrollo actual cuenta exactamente con ese procesador, el modelo está codificado en texto rígido. Si la aplicación se despliega en un servidor o contenedor Docker con AMD EPYC o Xeon, el endpoint `/api/system/health` mentirá en la telemetría reportada.
* **Acción Requerida:** Detectar dinámicamente el procesador leyendo `/proc/cpuinfo` en Linux o mediante `platform.processor()`.

---

## 3. Vector de Taxonomía y Coherencia de Datos (JEV System 1)

### 3.1 Desalineación entre `categories.json` y `frontend/js/data.js`
* **Diagnóstico Forense:**
  - En `backend/data/categories.json` existen **8 familias maestras oficiales**:
    1. `ia`
    2. `ia_generativa`
    3. `modelos_ia`
    4. `agentes_ia`
    5. `modelado_3d`
    6. `juegos`
    7. `dev_tools`
    8. `mangas`
  - En `frontend/js/data.js:L12`, la constante estática `ROOT_FAMILIES` define únicamente 7 familias:
    `dev_tools`, `ia`, `modelado_3d`, `juegos`, `mangas`, `negocios_saas`, `otros`.
  - Las familias `ia_generativa`, `modelos_ia` y `agentes_ia` **no existen** en `ROOT_FAMILIES` de `data.js`.
  - Además, `negocios_saas` aparece como familia en `data.js`, pero en `categories.json` es una categoría raíz independiente con `parent_id: null` y sin bandera `is_family: true`.
* **Impacto:** Si la API devuelve publicaciones con categorías pertenecientes a `ia_generativa` o `modelos_ia`, el frontend no encuentra su familia en `ROOT_FAMILIES` y puede fallar el coloreado o agrupamiento en el Waffle Grid si no hay fallback dinámico.
* **Acción Requerida:** Sincronizar `ROOT_FAMILIES` en `data.js` para reflejar las 8 familias maestras canónicas de `categories.json`.

### 3.2 Persistencia de Valores por Defecto Obsoletos (`general_discussion`)
* **Diagnóstico Forense:**
  - En la Subfase 5.14 se eliminó la opción `general_discussion` del esquema Choice `content_format`, reemplazándola por `other`.
  - Sin embargo, persisten referencias residuales a `general_discussion` como fallback por defecto:
    - `backend/app/database.py:L153`: `"format": "general_discussion"` en `DEFAULT_POST_VALUES`.
    - `frontend/js/data.js:L309`: `p.format || p.hook_type || 'general_discussion'`.
    - `frontend/js/data.js:L344`: `format: p.format || 'general_discussion'`.
* **Acción Requerida:** Sustituir todos los fallbacks por defecto residuales de `general_discussion` por `"other"`.

### 3.3 Asimetría en el Tratamiento de Publicaciones Vacías
* **Diagnóstico Forense:**
  - En `backend/app/services/ingest_service.py:L36` (ingesta masiva desde archivo JSON), si un post carece de contenido de texto (`if not content:`), el post es descartado silenciosamente (`return None`).
  - En `backend/app/schema.py:L107` (`AnalyzePostRequest` para la API REST interactiva), un post sin texto es rellenado con `"[Sin contenido textual]"` y enviado al modelo Laya para su inferencia.
* **Acción Requerida:** Homogeneizar la política de ingesta: los tweets sin texto deben recibir un tratamiento uniforme en todas las vías de entrada.

---

## 4. Vector de Frontend y Experiencia de Usuario (UI/UX)

### 4.1 Métricas Sintéticas en el Modal de Reporte Ejecutivo (`exec_report_modal.js`)
* **Diagnóstico Forense:** Al inspeccionar `frontend/js/modals/exec_report_modal.js`:
  ```javascript
  const topCategory = [...categories].sort((a, b) => (b.avgLikesTarget || 0) - (a.avgLikesTarget || 0))[0];
  const volumeCategory = [...categories].sort((a, b) => (b.targetCount || 0) - (a.targetCount || 0))[0];
  const totalPosts = posts.length || 796;
  const volPercent = Math.round(((volumeCategory.targetCount || 0) / totalPosts) * 100);
  ```
  El reporte estratégico no calcula las métricas reales a partir de las publicaciones cargadas en base de datos. En su lugar, lee las propiedades sintéticas `avgLikesTarget` y `targetCount` definidas en el array estático de `data.js`.
* **Impacto:** Aunque el usuario ingeste 1,500 publicaciones reales de sus bookmarks de X, el modal de informe ejecutivo sigue presentando diagnósticos estáticos y porcentajes basados en datos ficticios.
* **Acción Requerida:** Conectar `exec_report_modal.js` con las métricas reales agregadas desde `AppState.getPosts()` o desde el endpoint `/api/posts/stats`.

### 4.2 Ruido de Consola por Recurso 404 (`/favicon.ico`)
* **Diagnóstico Forense:** En la verificación con Playwright en Brave, tanto en `http://127.0.0.1:8000/` como en `http://127.0.0.1:8000/config`, el navegador solicita automáticamente `/favicon.ico`, recibiendo un `404 Not Found` en consola.
* **Acción Requerida:** Agregar un favicon SVG o PNG embebido en `frontend/` y mapear la ruta en `main.py` o servir un `FileResponse` / `Response(status_code=204)`.

### 4.3 Desfase en Versiones de Cache-Busting
* **Diagnóstico Forense:**
  - `frontend/config.html`: utiliza `?v=2.1.3`.
  - `frontend/index.html`: utiliza `?v=2.1.2`.
  - `backend/app/config.py`: `APP_VERSION = "2.1.0"`.
  - `backend/data/categories.json`: `registry_version = "2.1.1"`.
* **Acción Requerida:** Unificar la versión del sistema en v2.1.3 o v2.2.0 de forma transversal en el backend, los esquemas de base de datos y los scripts del frontend.

---

## 5. Vector de Documentación y Hoja de Ruta (Roadmap Gaps)

### 5.1 Subfases 5.13.1 y 5.13.2 Indocumentadas
* **Diagnóstico Forense:** En el directorio `tests/` existen los archivos `test_subfase_5_13_1.py` (corrección de emojis Unicode y textos vacíos) y `test_database_management.py` (Subfase 5.13.2: backup, reset, optimización WAL y telemetría de almacenamiento).
  Sin embargo, en `documentacion/` **no existen** los archivos correspondientes:
  - Falta `documentacion/PLAN_SUBFASE_5_13.md`
  - Falta `documentacion/RESUMEN_SUBFASE_5_13.md`
* **Impacto:** Rompe el ciclo documental de 5 pasos exigido por `AGENT.md`.
* **Acción Requerida:** Redactar el resumen documental consolidado de la Subfase 5.13 para mantener la trazabilidad histórica del proyecto.

### 5.2 Fase 6 Pendiente (Validación con Datasets Reales)
* **Diagnóstico Forense:** El `PLAN_DE_IMPLEMENTACION_MASTER.md` proyectó la Fase 6 ("Pruebas End-to-End con Datasets Reales de Bookmarks"). Actualmente, la base de datos `database.sqlite` cuenta con 0 publicaciones tras la ejecución de las pruebas de reset. No se ha ejecutado una prueba de carga masiva de los 1,653 bookmarks en condiciones de producción.
* **Acción Requerida:** Planificar formalmente la Fase 6 / Subfase 5.15 con la ingesta y clasificación masiva del dataset completo de bookmarks.

---

## 6. Matriz de Prioridades de Corrección y Mejora

| ID | Área | Hallazgo Forense | Severidad | Esfuerzo Estimado |
|---|---|---|:---:|:---:|
| **CORR-01** | **Tests** | Corregir fallo en `test_analyze.py` (alinear aserción 200 vs 422 con política 5.13.1). | **Alta** | 10 min |
| **CORR-02** | **Tests** | Corregir fallo en `test_api.py` (actualizar aserción de `registry_version` a `"2.1.1"`). | **Alta** | 5 min |
| **CORR-03** | **Tests** | Implementar aislamiento de `settings.DATABASE_PATH` en `tearDownClass` en todos los tests. | **Alta** | 25 min |
| **CORR-04** | **Tests** | Convertir `test_meridian_format.py` a clase `unittest.TestCase`. | **Media** | 10 min |
| **CORR-05** | **Taxonomía** | Sincronizar las 8 familias de `categories.json` con `ROOT_FAMILIES` en `data.js`. | **Alta** | 15 min |
| **CORR-06** | **Taxonomía** | Purgar fallbacks residuales de `general_discussion` hacia `other` en backend y frontend. | **Media** | 10 min |
| **CORR-07** | **Frontend** | Conectar `exec_report_modal.js` a métricas reales de publicaciones en lugar de mocks. | **Alta** | 30 min |
| **CORR-08** | **Hardware** | Detección dinámica de modelo de CPU en `engine.py` en vez de texto quemado. | **Baja** | 15 min |
| **CORR-09** | **Frontend** | Endpoint `/favicon.ico` para eliminar errores 404 en la consola del navegador. | **Baja** | 5 min |
| **CORR-10** | **Doc** | Generar `documentacion/RESUMEN_SUBFASE_5_13.md` consolidando 5.13.1 y 5.13.2. | **Media** | 20 min |
| **FEAT-01** | **Roadmap** | Ejecutar Fase 6: Ingesta masiva y validación E2E del dataset real de bookmarks (1,653 posts). | **Estratégica** | Subfase completa |

---

## 7. Conclusión Forense

El núcleo de clasificación y persistencia del proyecto es altamente competente, robusto y conforme con los estándares de **JEV / TypeSafe System One**. Los fallos observados en las pruebas no corresponden a errores algorítmicos ni a corrupción de datos, sino a **desfases de especificación fruto de la rápida evolución de las subfases** (versión de taxonomía actualizada a 2.1.1 y sanitización tolerante de emojis en 5.13.1 sin sincronizar las aserciones heredadas).

Abordar las correcciones inmediatas (**CORR-01** a **CORR-07**) dejará la suite de pruebas al **100% de éxito (59/59)**, garantizará el aislamiento de la base de datos de producción y habilitará el terreno para la ejecución de la **Fase 6** con datos reales.
