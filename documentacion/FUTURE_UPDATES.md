# 🚀 Hoja de Ruta y Próximas Actualizaciones (Future Updates)

Este documento detalla las funcionalidades estratégicas planificadas para las siguientes versiones de **Twitter Post Classifier Master**, diseñadas para escalar la herramienta hacia una plataforma de inteligencia de contenido automatizada de grado empresarial.

---

## 1. Exportación Avanzada de Datos (Data Export & Portability)

### 📌 Objetivo
Permitir a los usuarios exportar el conjunto completo o filtrado de publicaciones analizadas hacia formatos estándar para análisis en hojas de cálculo (Excel/Google Sheets), bases de datos externas o herramientas No-Code (Airtable, Notion).

### 🛠️ Especificaciones Técnicas
* **Formatos Soportados:**
  * **CSV (`.csv`):** Formato plano estructurado con codificación UTF-8 BOM para apertura directa en Microsoft Excel. Incluye columnas: `tweet_id`, `author`, `created_at`, `text`, `primary_category`, `family`, `confidence`, `waffle_score`, `content_format`, `technical_depth`, `reproducible_asset`, `is_uncensored`, `is_local_first`, `likes`, `retweets`, `url`.
  * **JSON Enriquecido (`.json`):** Volcado completo del payload con semántica estructurada, taxonomía jerárquica y respuestas de preguntas suplementarias.
  * **Excel (`.xlsx`):** Con formato de tabla automática, estilos en encabezados y columnas de color según la familia taxonómica.
* **Filtros de Exportación:**
  * Exportar todo el repositorio indexado en SQLite.
  * Exportar vista filtrada actual (según categoría activa, umbral de confianza o rango de fechas).
* **Integración UI:**
  * Botón desplegable **"Exportar Datos"** en la barra de filtros del Dashboard principal con opciones `CSV`, `JSON`, `Excel`.
* **Endpoints Backend:**
  * `GET /api/posts/export?format=csv&category=...&min_score=...`

---

## 2. Búsqueda Rápida de Texto Completo (Full-Text Search - FTS5)

### 📌 Objetivo
Permitir la localización instantánea de publicaciones mediante palabras clave, operadores booleanos, menciones (`@usuario`) o hashtags dentro de colecciones masivas de miles de tweets.

### 🛠️ Especificaciones Técnicas
* **Motor de Búsqueda:**
  * Implementación de tabla virtual `FTS5` en SQLite (`posts_fts`) sincronizada mediante triggers con la tabla `classified_posts`.
  * Tokenización multilingüe (`unicode61`) para soporte de acentos, caracteres japoneses (kanji/kana), emojis y términos técnicos en inglés.
* **Capacidades de Consulta:**
  * Búsqueda por coincidencia exacta: `"Qwen 2.5-Coder"`.
  * Búsqueda booleana: `comfyui AND lora NOT anime`.
  * Búsqueda por prefijo: `diffus*`.
* **Integración UI:**
  * Barra de búsqueda interactiva en la cabecera del Dashboard con debounce de 300ms y resaltado de coincidencias (*search highlighting*) en el Drawer y tabla.
* **Endpoints Backend:**
  * `GET /api/posts/search?q={query}&limit=50&offset=0`

---

## 3. Automatización de Ingesta Continua (n8n, Webhooks & Cron)

### 📌 Objetivo
Eliminar la necesidad de exportar y subir manualmente archivos JSON de marcadores, permitiendo la ingesta desatendida y periódica desde agentes y flujos de automatización.

### 🛠️ Especificaciones Técnicas
* **Webhook de Ingesta Segura:**
  * Endpoint `POST /api/webhooks/ingest` protegido mediante clave API de cabecera (`X-API-Key`).
  * Acepta payloads unitarios o por lotes directamente desde scrapers externos o extensiones de navegador.
* **Integración con n8n:**
  * Flujo programado en n8n que extrae bookmarks de X/Twitter cada N horas.
  * Envío del JSON crudo al webhook de la aplicación.
  * Disparo automático de la clasificación con el perfil configurado (`fast` o `full`).
* **Notificaciones de Alerta:**
  * Configuración opcional de webhook saliente (Discord, Telegram o Slack) cuando se detecte una publicación con afinidad excepcional (`waffle_score > 85`) o lanzamientos de código abierto (`content_format == launch`).

---

## 4. Contenerización y Despliegue Cloud (Docker & NVIDIA Container Toolkit)

### 📌 Objetivo
Facilitar el despliegue inmediato en entornos productivos locales, servidores VPS o instancias GPU bajo demanda (RunPod, Lambda Labs, AWS EC2, GCP).

### 🛠️ Especificaciones Técnicas
* **`Dockerfile` Multi-Stage Optimizado:**
  * Base `nvidia/cuda:12.2.0-runtime-ubuntu22.04` para aceleración GPU automática.
  * Fallback transparente a imagen ligera basada en Debian para entornos exclusivos de CPU.
  * Cacheo de capas de Python con pre-descarga de pesos del modelo Laya en `/root/.cache/huggingface`.
* **`docker-compose.yml`:**
  * Configuración con reserva de GPU NVIDIA (`deploy.resources.reservations.devices`).
  * Mapeo de volumen persistente para `backend/data/` (SQLite y backups).
  * Variables de entorno unificadas en `.env.production`.
* **Healthcheck de Contenedor:**
  * Monitoreo integrado contra `GET /api/system/health`.

---

## 5. Resumen de Estado del Sistema y Próximos Hitos

| Versión | Estado | Características Principales |
| :--- | :--- | :--- |
| **v2.1.0 (Actual)** | ✅ Completado | Taxonomía 48 clases, Streaming SSE, Checkpoints cada 25 posts, Skip duplicados por `tweet_id`, Gestión BD, Perfiles de Inferencia, Aislamiento de Tests Anti-OOM, Autodetección CPU/GPU. |
| **v2.2.0** | 📋 Planificado | Exportación a CSV/Excel/JSON y Búsqueda de Texto Completo FTS5. |
| **v2.3.0** | 📋 Planificado | Webhook de Ingesta Desatendida e Integración con n8n. |
| **v2.4.0** | 📋 Planificado | Docker Compose con soporte NVIDIA Container Toolkit y Despliegue en Cloud. |
