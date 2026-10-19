# Documentación Oficial · Twitter Post Classifier Master

> **Versión del Sistema:** v2.1.0  
> **Motor de Inferencia:** JEV / TypeSafe System One (`convaiinnovations/laya` · mmBERT)  
> **Almacenamiento:** SQLite en modo WAL con persistencia dual JSON  
> **Interfaz:** Dashboard Reactivo Modular (TailwindCSS + Vanilla JS ES6+)  
> **Repositorio:** [github.com/cchrrisppatrickk/twitter_post_classifier_jev-laya](https://github.com/cchrrisppatrickk/twitter_post_classifier_jev-laya)

---

## 🧭 Visión General de la Documentación

Esta suite de documentación técnica proporciona una referencia completa y exhaustiva sobre la arquitectura interna, los contratos de la API REST y streaming Server-Sent Events (SSE), el diseño de la interfaz de usuario, la formulación de juicios semánticos tipados con System 1 y los protocolos de despliegue y operación en producción o entornos acelerados por GPU.

```
documentacion/
├── README.md                              # <-- Estás aquí (Índice Maestro)
├── 01_ARQUITECTURA_Y_DISENO.md            # Qué es, qué hace, cómo lo hace y diagramas
├── 02_MANUAL_API_ENDPOINTS.md             # Especificación técnica exhaustiva de endpoints REST y SSE
├── 03_INTERFAZ_USUARIO_Y_EXPERIENCIA.md   # Dashboard, Waffle Grid, Scatter Canvas y Registry Studio
├── 04_TAXONOMIA_Y_PREGUNTAS_SYSTEM_1.md   # 47 categorías, 8 familias, preguntas tipadas y gating
├── 05_GUIA_DESPLIEGUE_Y_OPERACION.md      # Instalación local, Colab GPU, SQLite WAL y tests
├── imagenes/                              # Galería y catálogo de capturas E2E del sistema
└── doc_process/                           # Histórico de desarrollo (Fases 1 a 6 y Subfases 5.1 a 5.16)
```

---

## 📚 Mapa de Documentos Técnicos

### 1. [Arquitectura y Diseño del Sistema (`01_ARQUITECTURA_Y_DISENO.md`)](01_ARQUITECTURA_Y_DISENO.md)
- **Objetivo:** Comprender la estructura global del sistema, principios de ingeniería, stack tecnológico y flujo de datos end-to-end.
- **Contenido Clave:**
  - Qué es el clasificador y qué ventajas ofrece frente a LLMs generativos lentos y caros.
  - Arquitectura en capas: FastAPI, Servicios Asíncronos, Singleton `LayaEngine`, Base de Datos SQLite WAL y Frontend Modular.
  - Diagramas Mermaid de Arquitectura C4 y ciclo de vida de un post.
  - Principios de diseño: *Dual JSON Persistence*, *Zero-Downtime Deduplication* y *Process Isolation*.

### 2. [Manual de API y Referencia de Endpoints (`02_MANUAL_API_ENDPOINTS.md`)](02_MANUAL_API_ENDPOINTS.md)
- **Objetivo:** Especificación técnica rigurosa de cada endpoint disponible en el backend para desarrolladores e integradores.
- **Contenido Clave:**
  - Router `/api/posts`: Análisis individual (`/analyze`), streaming en lote (`/analyze-batch-stream`), métricas del dashboard (`/stats`), consulta filtrada (`/`), sobrescritura manual (`/override`), comparativa A/B (`/reclassify`) e historial con rollback.
  - Router `/api/ingest`: Ingesta masiva desde archivos JSON/NDJSON vía streaming ijson con bifurcación en 0ms.
  - Router `/api/batch`: Control de colas y streaming SSE de telemetría de lotes.
  - Router `/api/categories`: Configuración global, CRUD de categorías y gestión de preguntas tipadas (`Choice`, `Score`, `Noul`).
  - Router `/api/database`: Métricas de almacenamiento, compactación (`VACUUM`), respaldo y restauración JSON.
  - Router `/api/system`: Salud y telemetría de hardware en tiempo real (CPU/GPU, VRAM, RAM).

### 3. [Interfaz de Usuario y Experiencia (`03_INTERFAZ_USUARIO_Y_EXPERIENCIA.md`)](03_INTERFAZ_USUARIO_Y_EXPERIENCIA.md)
- **Objetivo:** Describir la composición visual, los componentes interactivos y el flujo de trabajo en el frontend.
- **Contenido Clave:**
  - Sistema de diseño "Editorial Terminal": Paleta cromática, tipografía `JetBrains Mono` + `Inter`, soporte de tema claro/oscuro.
  - Header con Badge dinámico de aceleración por hardware (CPU vs GPU CUDA / MPS).
  - *Live Scanner* con barra de progreso dual y streaming en tiempo real.
  - Las 3 Vistas Principales: **Matriz Waffle Grid** (con visualización diagonal Split/Pie 60/40), **Cuadrante Scatter Canvas 2D** (Afinidad vs Likes) y **Tabla Analítica Ejecutiva**.
  - Drawer lateral para inspección profunda, visualización multimedia, comparativa A/B y rollback.
  - Modales especializados (Ingesta, Taxonomía, Co-ocurrencias, Pipeline y Reporte Ejecutivo).
  - **JEV Registry Studio (`/config.html`)**: Gestión de taxonomía, banco de preguntas tipadas, calibrador de reglas y herramientas de base de datos.

### 4. [Taxonomía y Preguntas System 1 (`04_TAXONOMIA_Y_PREGUNTAS_SYSTEM_1.md`)](04_TAXONOMIA_Y_PREGUNTAS_SYSTEM_1.md)
- **Objetivo:** Explicar el modelo semántico, la jerarquía de categorías y los fundamentos de formulación de preguntas JEV / TypeSafe System One.
- **Contenido Clave:**
  - La Taxonomía v2.1.0: 8 familias raíz (`ia`, `blender`, `modelado_3d`, `juegos`, `dev_tools`, `mangas`, `negocios_saas`, `otros`) y sus 47 categorías especializadas.
  - Primitivas de juicio estructurado: `Choice` (con opción de escape obligatoria), `Noul` (certeza booleana 0.0-1.0) y `Score` (niveles observables 1-5).
  - Mecanismo de *Family Gating*: Ponderación lógica y anti-colapso léxico entre dominios técnicos.
  - Boosters deterministas por dominios de URLs (GitHub, HuggingFace, Civitai, ComfyUI, etc.) y keywords ponderadas.
  - Política de abstención (`PENDING`) y detección de anomalías (`Outlier`).

### 5. [Guía de Despliegue y Operación (`05_GUIA_DESPLIEGUE_Y_OPERACION.md`)](05_GUIA_DESPLIEGUE_Y_OPERACION.md)
- **Objetivo:** Manual operativo para instalar, configurar, monitorear y mantener el sistema en entornos locales o en la nube.
- **Contenido Clave:**
  - Requisitos previos de hardware y software (Python 3.10+, PyTorch, aiosqlite).
  - Puesta en marcha local con scripts Bash (`start_app.sh`, `status_app.sh`, `stop_app.sh`).
  - Despliegue en la nube mediante Google Colab acelerado por GPU NVIDIA (`Twitter_Classifier_Colab_GPU.ipynb`) con túneles Cloudflare.
  - Mantenimiento preventivo de SQLite WAL (compactación `VACUUM`, backups automáticos).
  - Suite de pruebas automatizadas con aislamiento de memoria (`python3 scripts/run_all_tests.py`) y pruebas E2E con Playwright.

---

## 🎯 Rutas de Lectura Recomendadas por Rol

```
┌─────────────────────────┐     ┌─────────────────────────────────────────────────────────┐
│ Rol / Perfil            │     │ Secuencia Recomendada de Lectura                         │
├─────────────────────────┼─────┼─────────────────────────────────────────────────────────┤
│ Arquitecto de Software  │ ──► │ 01_ARQUITECTURA -> 04_TAXONOMIA -> 02_MANUAL_API        │
│ Ingeniero Fullstack     │ ──► │ 01_ARQUITECTURA -> 02_MANUAL_API -> 03_INTERFAZ         │
│ Ingeniero IA / Data Sci │ ──► │ 04_TAXONOMIA -> 01_ARQUITECTURA -> 02_MANUAL_API        │
│ DevOps / Operaciones    │ ──► │ 05_GUIA_DESPLIEGUE -> 01_ARQUITECTURA                   │
│ Diseñador UI / UX       │ ──► │ 03_INTERFAZ -> 01_ARQUITECTURA                          │
└─────────────────────────┘     └─────────────────────────────────────────────────────────┘
```

---

## 🖼️ Recursos Visuales y Memoria Histórica

- **Evidencias Visuales:** [`documentacion/imagenes/`](imagenes/README.md) almacena todas las capturas de pantalla de la interfaz generadas mediante pruebas E2E.
- **Memoria de Desarrollo:** [`documentacion/doc_process/`](doc_process/README.md) resguarda los 35 documentos de planificación y resúmenes ejecutivos que documentan la construcción del sistema desde la Fase 1 hasta la Fase 6.
