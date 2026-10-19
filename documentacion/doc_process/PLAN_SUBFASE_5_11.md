# Plan de Implementación: Subfase 5.11 - Refactorización y Modularización Arquitectónica de la Lógica JavaScript

## 1. Visión General del Objetivo

En la **Subfase 5.9** logramos una modularización radical del HTML de `frontend/index.html` (reducción de 1,423 a 87 líneas divididas en 13 componentes y modales). Posteriormente, en la **Subfase 5.10**, creamos el **JEV Registry Studio v2.1.0** para la gestión de taxonomía, preguntas y decisiones.

Sin embargo, el código JavaScript ha crecido sustancialmente acumulando **más de 5,100 líneas** concentradas en grandes archivos monolíticos:
- `frontend/js/config.js` cuenta con **1,397 líneas** en un solo archivo plano para todo el Registry Studio.
- `frontend/js/modals.js` cuenta con **1,229 líneas** agrupando 6 modales dispares y código legado de la taxonomía antigua.
- `frontend/js/drawer.js` cuenta con **836 líneas**, conteniendo una fuerte mezcla de responsabilidades al albergar tanto el Drawer lateral como la lógica completa del `#richPostModal` (reproductor de video HTML5, desglose semántico y visor dual JSON).

El objetivo de la **Subfase 5.11** es refactorizar, optimizar y desacoplar la capa JavaScript, logrando una arquitectura de componentes modulares, con responsabilidades claras, cero código muerto y alta mantenibilidad sin romper ninguna conexión existente con el backend FastAPI ni alterar el comportamiento de la UI.

---

## 2. Desglose en Subfases Ejecutables

```
Subfase 5.11: Refactorización y Modularización Arquitectónica de JS
├── 5.11.1: Modularización del Registry Studio (frontend/js/config/)
│   ├── state.js (Almacén de estado reactivo, HUD, caché de categorías)
│   ├── categories.js (Grid de 48 tarjetas, filtros, modal CRUD de taxonomía)
│   ├── globals.js (Formulario de ajustes globales y boosters)
│   ├── questions.js (Banco de preguntas tipadas y modal CRUD)
│   ├── simulator.js (Simulador determinista Multi-Label RLCD)
│   └── app.js (Orquestador de pestañas, tema claro/oscuro, toasts y confirmaciones)
├── 5.11.2: Desacoplamiento de Modales (frontend/js/modals/)
│   ├── rich_post_modal.js (Extracción de lógica multimedia desde drawer.js)
│   ├── ingest_modal.js (Ingesta JSON masiva, parseo Meridian y SSE batch runner)
│   ├── overlap_modal.js (Matriz de co-ocurrencias multietiqueta)
│   ├── pipeline_modal.js (Consola de telemetría y logs)
│   ├── exec_report_modal.js (Diagnóstico ejecutivo del batch)
│   ├── analysis_result_modal.js (Visualización de inferencia individual Laya)
│   └── Retiro de ~170 líneas de código muerto (modal legado de taxonomía)
├── 5.11.3: Refactorización Core y Limpieza de Drawer
│   ├── frontend/js/core/state.js (Almacén global de estado del dashboard)
│   ├── frontend/js/core/utils.js (Funciones puras de escape y formateo)
│   ├── frontend/js/drawer.js (Reducción de 836 a ~220 líneas enfocadas)
│   └── Optimización de frontend/js/data.js y sincronización reactiva
└── 5.11.4: Compilador Offline, Pruebas E2E y Auditoría Graphify
    ├── Actualización de scripts/build_frontend.py (soporte config.html y subcarpetas)
    ├── Validación de regresión con Playwright en / y /config
    ├── Auditoría topológica con Graphify MCP (graph_stats, god_nodes)
    └── Redacción de RESUMEN_SUBFASE_5_11.md y actualización de PLAN_DE_IMPLEMENTACION_MASTER.md
```

---

## 3. Plan de Verificación

1. **Pruebas Automatizadas Backend:**
   - `tests/test_categories_crud.py` y `tests/test_services.py` con pytest.
2. **Pruebas E2E Playwright:**
   - `scratch/test_config_studio_e2e.py` (8/8 pasos en `/config`).
   - `scratch/test_subfase_5_9_modular_frontend.py` (52 selectores y flujos del dashboard en `/`).
3. **Auditoría Graphify:**
   - Verificación de reducción del tamaño de nodos centrales (`god_nodes`) y estadísticas globales del grafo (`graph_stats`).
