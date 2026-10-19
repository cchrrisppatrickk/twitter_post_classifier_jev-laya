# Registro Histórico del Proceso de Desarrollo (doc_process)

Este directorio conserva la memoria técnica completa, planes de implementación y resúmenes ejecutivos generados a lo largo de las distintas fases evolutivas de **Twitter Post Classifier Master**.

---

## 🗂️ Contenido y Fases de Desarrollo

### 1. Fases Fundacionales y Arquitectura Base
- [`ANALISIS_FORENSE_SISTEMA.md`](ANALISIS_FORENSE_SISTEMA.md) — Diagnóstico inicial y mapeo de contratos del sistema.
- [`PLAN_DE_IMPLEMENTACION_MASTER.md`](PLAN_DE_IMPLEMENTACION_MASTER.md) — Plan maestro arquitectónico del proyecto.
- [`RESUMEN_FASE_1.md`](RESUMEN_FASE_1.md) — Inicialización del backend FastAPI y conexión SQLite WAL.
- [`RESUMEN_FASE_2.md`](RESUMEN_FASE_2.md) — Integración del motor de inferencia local Laya / Jev.
- [`RESUMEN_FASE_3.md`](RESUMEN_FASE_3.md) — Servicio de ingesta y deduplicación en 0ms con streaming ijson.
- [`RESUMEN_FASE_4.md`](RESUMEN_FASE_4.md) — Worker de lotes en segundo plano con checkpoints periódicos.

### 2. Fase 5: Dashboard Matricial y Experiencia de Usuario Avanzada
- [`RESUMEN_SUBFASE_5_1.md`](RESUMEN_SUBFASE_5_1.md) — Plantilla base y Gestor de Taxonomía.
- [`RESUMEN_SUBFASE_5_2.md`](RESUMEN_SUBFASE_5_2.md) — Renderizado Dinámico del Waffle Grid.
- [`RESUMEN_SUBFASE_5_3.md`](RESUMEN_SUBFASE_5_3.md) — Cuadrante Scatter Canvas 2D y Vista Tabular Ejecutiva.
- [`RESUMEN_SUBFASE_5_4.md`](RESUMEN_SUBFASE_5_4.md) — Filtros multidimensionales y ordenamiento reactivo.
- [`RESUMEN_SUBFASE_5_5.md`](RESUMEN_SUBFASE_5_5.md) — Modales analíticos: Co-ocurrencias, Pipeline y Visor Enriquecido.
- [`RESUMEN_SUBFASE_5_6.md`](RESUMEN_SUBFASE_5_6.md) — Reporte estratégico ejecutivo y métricas de ROI.
- [`RESUMEN_SUBFASE_5_7.md`](RESUMEN_SUBFASE_5_7.md) — Telemetría en tiempo real de hardware (CPU/RAM).
- [`PLAN_SUBFASE_5_8.md`](PLAN_SUBFASE_5_8.md) & [`RESUMEN_SUBFASE_5_8.md`](RESUMEN_SUBFASE_5_8.md) — Drawer lateral interactivo y resolución de estados `PENDING`.
- [`PLAN_SUBFASE_5_9.md`](PLAN_SUBFASE_5_9.md) & [`RESUMEN_SUBFASE_5_9.md`](RESUMEN_SUBFASE_5_9.md) — Modal de taxonomía y recarga en caliente de categorías.
- [`PLAN_SUBFASE_5_10.md`](PLAN_SUBFASE_5_10.md) & [`RESUMEN_SUBFASE_5_10.md`](RESUMEN_SUBFASE_5_10.md) — Visualización Split/Pie 60/40 en celdas de la matriz Waffle.
- [`PLAN_SUBFASE_5_11.md`](PLAN_SUBFASE_5_11.md) & [`RESUMEN_SUBFASE_5_11.md`](RESUMEN_SUBFASE_5_11.md) — Conmutador de densidades de visualización (S, M, L).
- [`PLAN_SUBFASE_5_12.md`](PLAN_SUBFASE_5_12.md) & Subfases 5.12.1 a 5.12.4:
  - [`RESUMEN_SUBFASE_5_12_1.md`](RESUMEN_SUBFASE_5_12_1.md) — Persistencia dual JSON (`raw_json` y `classification_json`).
  - [`RESUMEN_SUBFASE_5_12_2.md`](RESUMEN_SUBFASE_5_12_2.md) — Tabla de historial y versionado taxonómico.
  - [`RESUMEN_SUBFASE_5_12_3.md`](RESUMEN_SUBFASE_5_12_3.md) — Endpoint de reclasificación A/B con modo `dry_run`.
  - [`RESUMEN_SUBFASE_5_12_4.md`](RESUMEN_SUBFASE_5_12_4.md) — Comparativa A/B visual y rollback atómico en Drawer.
- [`RESUMEN_SUBFASE_5_13.md`](RESUMEN_SUBFASE_5_13.md) — Gestión integral de base de datos SQLite WAL (Stats, Optimize, Reset, Backup).
- [`PLAN_SUBFASE_5_14.md`](PLAN_SUBFASE_5_14.md) & [`RESUMEN_SUBFASE_5_14.md`](RESUMEN_SUBFASE_5_14.md) — JEV Registry Studio v2.1.0 (`config.html`).
- [`PLAN_SUBFASE_5_15.md`](PLAN_SUBFASE_5_15.md) & [`RESUMEN_SUBFASE_5_15.md`](RESUMEN_SUBFASE_5_15.md) — Modularización desacoplada del frontend (11 módulos JS y 6 componentes HTML).
- [`RESUMEN_SUBFASE_5_16.md`](RESUMEN_SUBFASE_5_16.md) — Soporte de aceleración por GPU CUDA / MPS y telemetría de hardware en vivo.

### 3. Fase 6: Ingesta Masiva y Operación a Gran Escala
- [`PLAN_FASE_6_INGESTA_MASIVA.md`](PLAN_FASE_6_INGESTA_MASIVA.md) — Arquitectura de ingesta de 1,600+ publicaciones con streaming reactivo SSE.
- [`RESUMEN_FASE_6.md`](RESUMEN_FASE_6.md) — Verificación en vivo de streaming SSE, telemetría de TPS y reporte estratégico.
- [`FUTURE_UPDATES.md`](FUTURE_UPDATES.md) — Bitácora de mejoras potenciales y extensiones futuras del sistema.

---

## 🖼️ Capturas y Evidencias Visuales
Todas las evidencias visuales y capturas de pantalla de estas fases se encuentran centralizadas en [`../imagenes/`](../imagenes/README.md).
