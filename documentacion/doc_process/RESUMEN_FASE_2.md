# Resumen de Implementación: Fase 2 (Motor de Inferencia System 1 y Taxonomía v2.1.0)

**Proyecto:** `twitter_post_classifier_master`  
**Fecha:** 2026-10-13  
**Estado:** ✅ COMPLETADO Y VERIFICADO AL 100%

---

## 1. Componentes Construidos

1. **Compilador Taxonómico y Registro Maestro (`backend/app/registry.py`):**
   - Carga dinámica y versionada de `categories.json` v2.1.0 (47 categorías, 8 familias raíz).
   - Generación del árbol de preguntas tipadas compatibles con `Laya Agent`:
     * Pregunta Choice principal (`category`) con las 47 categorías ordenadas por jerarquía y enriquecidas con ejemplos y exclusiones.
     * Preguntas suplementarias tipadas (`content_format`, `technical_depth`, `is_tool_or_code_release`, `reproducible_asset_type`, `sentiment_or_tone`, `is_uncensored_or_nsfw`, `is_local_first`).
     * 8 Preguntas booleanas (Noul) por familia raíz para **Family Gating** anti-alucinación (`is_family_ia`, `is_family_blender`, `is_family_modelado_3d`, `is_family_juegos`, `is_family_dev_tools`, `is_family_mangas`, `is_family_negocios_saas`, `is_family_otros`).
   - Matcher determinista por expresiones regulares para enlaces de Hugging Face (`hf.co`), GitHub (`github.com`), Civitai (`civitai.com`), ComfyUI (`openart.ai/workflows`) y tutoriales.
   - Algoritmo de herencia de umbrales: `categoría -> padre -> abuelo -> default_threshold (0.75)`.

2. **Motor de Inferencia System 1 (`backend/app/engine.py`):**
   - Envoltorio de `laya.Router` optimizado para CPU Intel Core i5-10210U:
     * Límite estricto de hilos PyTorch: `torch.set_num_threads(4)` e inter-op threads: `2`.
   - **Soporte Multilingüe Nativo (ADR-008):** Normalización Unicode NFKC (`normalize_multilingual_text`) para transformar caracteres japoneses y chinos *zenkaku* a *hankaku* sin necesidad de APIs externas de traducción.
   - **Algoritmo de Family Gating:**
     * Penaliza con factor `0.15` a candidatos cuya familia raíz obtuvo Noul negativo (< 0.30) sin activos deterministas.
     * Bonifica con `+0.15` a candidatos en familias activadas (>= 0.50).
   - **Boosters Ponderados:** Bonificación por activos reproducibles (`+0.20`), especificidad de subcategoría (`+0.05`) y coincidencias de palabras clave (`+0.08`).
   - **Flujo de Abstención Preventiva (ADR-007):** Si la confianza máxima es < `MIN_CONFIDENCE_ABSTAIN` (0.55) o < `MIN_THRESHOLD_FOR_PRIMARY` (0.70) sin activos descargables, el post entra en `PENDING` con categoría primaria `otros`.
   - **Detección de Outliers (ADR-004):** Identificación de anomalías algorítmicas (tweets virales de bajo contenido técnico o lanzamientos de código de afinidad extrema).
   - **Telemetría de Hardware:** Endpoint de salud con CPU, memoria total, memoria libre y RAM consumida por el proceso en vivo.

---

## 2. Pruebas y Validación Automatizada (`tests/test_engine.py`)

Se ejecutó la suite completa de pruebas sobre Python 3.14 con inferencia real sobre los checkpoints de Laya:

| Prueba | Caso Evaluado | Resultado |
| :--- | :--- | :---: |
| `test_multilingual_normalization_nfkc` | Conversión de caracteres Zenkaku japoneses a Hankaku | ✅ PASS |
| `test_asset_domain_matcher` | Detección determinista de GitHub y Hugging Face | ✅ PASS |
| `test_system_health` | Telemetría de CPU y memoria RAM del host | ✅ PASS |
| `test_inference_english_blender_tool` | Clasificación de post técnico en inglés con repo de Blender | ✅ PASS (`blender` / `CLASSIFIED`) |
| `test_inference_japanese_post` | Clasificación de post de manga en japonés sin traducción | ✅ PASS (`mangas` / `CLASSIFIED`) |
| `test_inference_ambiguous_post_abstains_to_pending` | Abstención preventiva de tweet cotidiano/ambiguo | ✅ PASS (`PENDING` / `otros`) |

**Resultado global:** `6/6 tests PASSED en 68.62s (100% OK)`.

---

## 3. Próximo Paso: Fase 3

Con la capa de datos (Fase 1) y el motor de inferencia System 1 (Fase 2) plenamente verificados, el siguiente paso es la **Fase 3: Servicios de Negocio**:
- `ingest_service.py`: Deduplicación estricta (0 ms Laya en existentes) y streaming con `ijson`.
- `batch_service.py`: Batch Runner asíncrono en hilo de fondo con commits cada 25 posts y generador SSE.
- `stats_service.py`: Agregaciones para Waffle Grid y Cuadrante Scatter Canvas 2D.
