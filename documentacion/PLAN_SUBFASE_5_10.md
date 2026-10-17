# Plan de Implementación: Subfase 5.10 - Registry Studio: Configuración General de Decisiones & Taxonomía CRUD

## 1. Visión General del Objetivo

El objetivo de esta subfase es evolucionar la administración taxonómica de Twitter Post Classifier Master desde el modal básico hacia un **Estudio de Configuración General de Decisiones (Registry Studio)** accesible en la ruta `/config`, adaptando la plantilla de diseño de alta fidelidad `configuraci_n_de_decisiones_jev (1).html`.

Esta actualización proporciona:
1. **CRUD Completo de Categorías:** Creación, lectura, edición profunda (directiva, keywords, ejemplos, exclusiones, umbral RLCD) y eliminación protegida (con salvaguarda estricta sobre las 8 familias raíz para no alterar el Family Gating).
2. **Ajustes Globales del Pipeline:** Configuración interactiva de umbral por defecto, piso de abstención PENDING, max labels y visualización de boosters deterministas.
3. **Gestión del Banco de Preguntas Tipadas (System 1):** Visualización y afinación interactiva de las preguntas suplementarias (`content_format`, `technical_depth` [Score], `reproducible_asset_type`, y booleanos `noul`), con capacidad de crear nuevas preguntas analíticas personalizadas.
4. **Reglas de Decisión:** Explicación visual del algoritmo de desempate y la herencia jerárquica de umbrales.
5. **Navegación Fluida:** Conexión directa en la misma pestaña entre `/` (Dashboard Waffle) y `/config`, sincronizando los cambios en caliente sin reiniciar el servidor.

---

## 2. Desglose en Subfases Ejecutables

```
Subfase 5.10: Registry Studio (Configuración General & Taxonomía)
├── 5.10.1: Backend CRUD Extendido & Persistencia Atómica (Categories, Globals, Questions)
├── 5.10.2: Cliente API Unificado (api.js) y Montaje de Ruta FastAPI /config
├── 5.10.3: Frontend Tab 1: Taxonomía y Categorías (Grid Reactivo, Modal CRUD Completo)
├── 5.10.4: Frontend Tabs 2, 3 y 4: Ajustes Globales, Banco de Preguntas y Reglas
└── 5.10.5: Verificación E2E con Playwright, Auditoría Graphify y Documentación Oficial
```

---

### Subfase 5.10.1: Backend CRUD Extendido & Persistencia Atómica
- **Objetivo:** Dotar a la API de FastAPI de todas las operaciones de lectura y modificación sobre `categories.json` con persistencia atómica en disco y recarga en caliente de Laya Router.
- **Tareas:**
  - Enriquecer `CategoryItemResponse` con `examples`, `exclusions`, `boosters` e `is_family`.
  - Crear endpoint `PUT /api/categories/{id}` para actualizar metadatos completos de cualquier categoría.
  - Crear endpoint `DELETE /api/categories/{id}` con validación de seguridad (bloquear eliminación si `is_family == True` o si es una de las 8 familias raíz) y reasignar posts existentes en SQLite WAL a `otros`.
  - Crear endpoints `GET /api/categories/settings/globals` y `PUT /api/categories/settings/globals`.
  - Crear endpoints `GET /api/categories/questions/supplementary`, `PUT /api/categories/questions/supplementary/{q_id}`, `POST /api/categories/questions/supplementary` y `DELETE /api/categories/questions/supplementary/{q_id}`.
  - Crear suite de pruebas unitarias `tests/test_categories_crud.py`.

---

### Subfase 5.10.2: Cliente API Unificado y Ruta FastAPI `/config`
- **Objetivo:** Conectar el frontend con los nuevos endpoints y habilitar la página `/config`.
- **Tareas:**
  - Extender `frontend/js/api.js` con métodos tipados: `update`, `delete`, `getGlobalSettings`, `updateGlobalSettings`, `getQuestions`, `updateQuestion`, `createQuestion`, `deleteQuestion`.
  - Registrar ruta `GET /config` en `backend/app/main.py` mediante `templates.TemplateResponse(request=request, name="config.html")`.
  - Crear la estructura base de `frontend/config.html` adaptando estilos (Inter, JetBrains Mono, Tailwind, modo claro/oscuro) y navegación.
  - Actualizar botones en `frontend/components/header.html` y `live_scanner.html` con enlace directo a `/config`.

---

### Subfase 5.10.3: Frontend Tab 1 - Taxonomía y Categorías (CRUD Interactivo)
- **Objetivo:** Implementar la interfaz interactiva para explorar, filtrar, crear, editar y eliminar categorías.
- **Tareas:**
  - Renderizado dinámico de tarjetas de categorías con indicador de color, badges de familia/subcategoría, directiva descriptiva, chips de keywords y umbral RLCD.
  - Buscador en tiempo real y selectores de filtrado por familia y ordenación.
  - Modal flotante de edición y creación con soporte dinámico para añadir/remover chips de keywords, ejemplos positivos y exclusiones estrictas.
  - Botón de eliminación con confirmación y candado de seguridad en familias raíz protegidas.

---

### Subfase 5.10.4: Frontend Tabs 2, 3 y 4 - Ajustes Globales, Banco de Preguntas y Reglas
- **Objetivo:** Operatividad de las pestañas complementarias del Registry Studio.
- **Tareas:**
  - **Tab 2:** Sliders sincronizados para umbral global, piso de abstención PENDING, max labels y visualización de boosters deterministas.
  - **Tab 3:** Visualizador y editor del Banco de Preguntas Tipadas (Choice, Score, Noul), con modal para editar directivas o crear nuevas preguntas analíticas.
  - **Tab 4:** Infografía interactiva del pipeline formal de desempate en 4 pasos y árbol de herencia de umbrales.

---

### Subfase 5.10.5: Verificación Integral E2E, Graphify y Documentación
- **Objetivo:** Validación de extremo a extremo sin regresiones.
- **Tareas:**
  - Script Playwright `scratch/test_config_studio_e2e.py` validando flujo completo: navegación desde `/`, edición de categoría, visualización de preguntas, retorno a `/`.
  - Capturas de pantalla oficiales en el directorio de artefactos.
  - Auditoría de arquitectura con Graphify (`graph_stats`, `god_nodes`).
  - Redacción del resumen oficial `documentacion/RESUMEN_SUBFASE_5_10.md` y actualización del plan maestro.
