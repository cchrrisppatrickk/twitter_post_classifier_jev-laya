# ⚡ Twitter Post Classifier Master
### AI Metadata Scraper, Semantic System 1 Classifier & Interactive Matrix Dashboard

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-EE4C2C.svg?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL_Mode-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Google Colab](https://img.shields.io/badge/Colab-GPU_T4-F9AB00.svg?style=flat&logo=googlecolab&logoColor=white)](Twitter_Classifier_Colab_GPU.ipynb)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🌟 ¿Qué es Twitter Post Classifier Master?

**Twitter Post Classifier Master** es una plataforma moderna e inteligente para analizar, categorizar y visualizar grandes colecciones de publicaciones de la red social **X (Twitter)**.

A diferencia de los métodos tradicionales con modelos generativos (como GPT-4 o Claude), que resultan lentos (2 a 4 segundos por post), costosos y propensos a inventar formatos, este sistema utiliza **JEV / TypeSafe System One (`convaiinnovations/laya` · mmBERT)**. 

El resultado es un sistema que evalúa publicaciones en **milisegundos**, con certeza matemática, costo cero por API, total privacidad local y un **Dashboard visual interactivo** que transforma volcados caóticos de tweets en un mapa de conocimiento claro y accionable.

---

## 📸 Vista Rápida del Sistema

| Matriz Waffle Dinámica (48 Categorías) | Cuadrante Scatter 2D (Afinidad vs Likes) |
| :---: | :---: |
| ![Matriz Waffle](documentacion/imagenes/waffle_grid_dynamic_48.png) | ![Cuadrante Scatter](documentacion/imagenes/scatter_quadrant_canvas.png) |

| Streaming SSE en Vivo | JEV Registry Studio (Editor de Reglas) |
| :---: | :---: |
| ![Streaming SSE](documentacion/imagenes/fase6_live_stream_in_progress.png) | ![Registry Studio](documentacion/imagenes/subfase_5_14_questions_tab.png) |

---

## ✨ Características Principales

### ⚡ 1. Inferencia Semántica Ultrarrápida (System 1)
- **Velocidad Extrema:** Clasifica cada post en **~5 a 20 ms en GPU NVIDIA CUDA** o ~200 ms en CPU común.
- **Multidimensional en un solo pase:** Resuelve simultáneamente categoría primaria, categorías secundarias, formato del contenido (*código, release, tutorial, hilo*), nivel de profundidad técnica (1 a 5 estrellas) y detección de activos (*GitHub, Hugging Face, Civitai, ComfyUI*).
- **Family Gating (Anti-Confusión):** Un sistema inteligente de compuertas lógicas que evita falsos positivos entre dominios afines (por ejemplo, diferencia con precisión si un script de Python pertenece a Blender o a Desarrollo Web).

### 📊 2. Dashboard Matricial y Analítico
- **Matriz Waffle Interactiva:** Mapeo visual de publicaciones agrupadas en **8 grandes familias temáticas**, con celdas proporcionales y visualización diagonal (*Split 60/40*) para publicaciones multidisciplinarias.
- **Cuadrante Scatter Canvas 2D:** Ubica cada tweet en un mapa cartesiano de **Afinidad Semántica vs Engagement (Likes)** para descubrir inmediatamente *Gemas Ocultas* o detectar *Ruido Viral*.
- **Tabla Ejecutiva con Métricas:** Vista densa con ordenamiento instantáneo, cálculo de viralidad y enlaces directos a X.

### 🔄 3. Ingesta Masiva y Deduplicación en 0 ms
- Carga archivos JSON de cualquier tamaño sin saturar la memoria RAM gracias a lectura por streaming con `ijson`.
- **Deduplicación instantánea:** Si un tweet ya existe en la base de datos, el sistema actualiza sus métricas sociales en 0 ms sin gastar recursos de IA.
- **Streaming en Vivo (SSE):** Observa el avance de clasificación post a post en tiempo real con barras de progreso y métricas de velocidad (tweets por segundo).

### 🔬 4. Inspección Profunda y Comparativa A/B (Drawer)
- Panel lateral deslizable que muestra el contenido completo del tweet, autor y visor de fotos y videos.
- **Modo Reclasificar A/B:** Prueba cambios en las reglas y observa en tiempo real cómo cambia la predicción de la IA antes de confirmar.
- **Historial y Rollback:** Guarda cada versión de clasificación previa y permite revertir cualquier cambio con un solo clic.

### 🛠️ 5. JEV Registry Studio (`/config`)
- Panel visual completo para crear nuevas categorías, cambiar colores, ajustar palabras clave y activar o desactivar preguntas sin tocar una sola línea de código.
- Laboratorio de pruebas en vivo y herramientas de mantenimiento para la base de datos SQLite WAL (optimización, copias de seguridad JSON y restauración).

---

## 🎯 Las 8 Familias Temáticas del Sistema

El clasificador viene preconfigurado con una taxonomía de **47 categorías especializadas** organizadas en 8 familias maestras:

1. 🟣 **Inteligencia Artificial & ML:** LLMs, Agentes, Difusión y Visión, Audio/Voz, Fine-Tuning y Hardware.
2. 🟠 **Blender 3D:** Addons, Geometry Nodes, Shaders Procedurales, Animación, Rigging y VFX.
3. 🔵 **Gráficos 3D & WebGL:** Three.js, WebGPU, Shaders, Texturizado PBR y Renderizado en Tiempo Real.
4. 🟢 **Desarrollo de Videojuegos:** Godot, Unreal Engine, Unity, Game Design y Gameplay.
5. 🟡 **Herramientas Dev & Código:** Terminal CLI, Frontend Web, APIs Backend, Arquitectura y Open Source.
6. 🌸 **Manga & Ilustración:** Anime, Ilustración Digital, Dibujo Tradicional y Webcomics.
7. 🌲 **Negocios & SaaS:** Startups, Tracción MRR, Indie Hacking y Monetización.
8. ⚪ **Comunidad & Otros:** Cultura tech, humor, debates y vida cotidiana.

---

## 🚀 Inicio Rápido (Quickstart)

Puedes poner a funcionar el proyecto en tu propia computadora o directamente en la nube:

### Opción A: Ejecución Local en tu Computadora (Linux / macOS / WSL)

1. **Clonar el repositorio y preparar el entorno:**
   ```bash
   git clone https://github.com/cchrrisppatrickk/twitter_post_classifier_jev-laya.git
   cd twitter_post_classifier_jev-laya
   
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. **Iniciar la aplicación con los scripts incluidos:**
   ```bash
   # Iniciar el servidor en segundo plano
   ./start_app.sh
   ```

3. **¡Listo! Abre tu navegador:**
   - 🌐 **Dashboard Principal:** [http://localhost:8000](http://localhost:8000)
   - ⚙️ **JEV Registry Studio:** [http://localhost:8000/config](http://localhost:8000/config)
   - 📖 **Documentación Swagger API:** [http://localhost:8000/docs](http://localhost:8000/docs)

*Para consultar el estado o detener el servidor:*
```bash
./status_app.sh    # Ver estado y consumo
./stop_app.sh      # Detener el servidor de forma segura
```

---

### Opción B: Ejecución en la Nube con Google Colab (GPU Gratis)

Si no cuentas con una GPU dedicada en tu equipo o deseas clasificar decenas de miles de posts a máxima velocidad:

1. Abre el cuaderno [`Twitter_Classifier_Colab_GPU.ipynb`](Twitter_Classifier_Colab_GPU.ipynb) en [Google Colab](https://colab.research.google.com).
2. Ve a **Entorno de ejecución > Cambiar tipo de entorno** y selecciona **GPU T4**.
3. Ejecuta las celdas en orden. El cuaderno:
   - Instalará el sistema con aceleración por hardware CUDA.
   - Generará un enlace público seguro vía **Cloudflare Tunnels** para que abras el Dashboard desde cualquier lugar.
   - Te permitirá conectar tu Google Drive para respaldar tu base de datos clasificada con un solo clic.

---

## 📁 Estructura del Repositorio

```
├── backend/                       # Servidor API FastAPI e Inferencia
│   ├── app/
│   │   ├── api/                   # Rutas REST (posts, ingest, batch, categories, database, system)
│   │   ├── services/              # IngestService (ijson), BatchService (colas/SSE), StatsService
│   │   ├── engine.py              # Motor de inferencia System 1 (Laya Router / mmBERT)
│   │   ├── registry.py            # Compilador de preguntas tipadas y taxonomía
│   │   ├── database.py            # Conexión asíncrona a SQLite WAL y esquemas DDL
│   │   ├── schema.py              # Modelos tipados de datos Pydantic v2
│   │   └── main.py                # Punto de entrada de FastAPI y ciclo de vida
│   ├── data/
│   │   ├── categories.json        # Registro maestro de categorías y scoring
│   │   └── database.sqlite        # Base de datos persistente (creada al inicio)
│   └── requirements.txt           # Dependencias de Python
├── frontend/                      # Interfaz de Usuario Web
│   ├── index.html                 # Dashboard interactivo principal
│   ├── config.html                # JEV Registry Studio
│   ├── components/                # Componentes modulares Jinja2 (Header, Scanner, Drawer...)
│   ├── modals/                    # Modales analíticos e ingesta
│   ├── css/styles.css             # Estilos y animaciones
│   └── js/                        # Controladores modulares ES6+ (API, Waffle, Scatter, Drawer...)
├── documentacion/                 # Documentación Técnica Exhaustiva
│   ├── 01_ARQUITECTURA_Y_DISENO.md
│   ├── 02_MANUAL_API_ENDPOINTS.md
│   ├── 03_INTERFAZ_USUARIO_Y_EXPERIENCIA.md
│   ├── 04_TAXONOMIA_Y_PREGUNTAS_SYSTEM_1.md
│   ├── 05_GUIA_DESPLIEGUE_Y_OPERACION.md
│   ├── imagenes/                  # Galería de capturas de la UI
│   └── doc_process/               # Histórico de desarrollo (Fases 1 a 6)
├── scripts/
│   └── run_all_tests.py           # Test runner oficial con aislamiento de memoria
├── tests/                         # Suite de pruebas unitarias e integración
├── start_app.sh                   # Script para arrancar el servidor
├── status_app.sh                  # Script para comprobar salud del sistema
├── stop_app.sh                    # Script para detener el servidor
└── Twitter_Classifier_Colab_GPU.ipynb # Cuaderno de Google Colab para GPU
```

---

## 📖 Documentación Técnica Detallada

Para profundizar en el diseño y funcionamiento interno del sistema, consulta los manuales en la carpeta [`documentacion/`](documentacion/README.md):

- 🏛️ **[01 · Arquitectura y Diseño](documentacion/01_ARQUITECTURA_Y_DISENO.md):** Principios de persistencia dual JSON, Family Gating y diagramas de flujo.
- 🔌 **[02 · Manual de Endpoints API](documentacion/02_MANUAL_API_ENDPOINTS.md):** Referencia exhaustiva de todas las rutas HTTP y streaming SSE con ejemplos de JSON.
- 🎨 **[03 · Interfaz de Usuario y UX](documentacion/03_INTERFAZ_USUARIO_Y_EXPERIENCIA.md):** Guía detallada del Dashboard, la Matriz Waffle, el Canvas Scatter 2D y Registry Studio.
- 🧠 **[04 · Taxonomía y Preguntas System 1](documentacion/04_TAXONOMIA_Y_PREGUNTAS_SYSTEM_1.md):** Formulación de preguntas tipadas (`Choice`, `Score`, `Noul`) y boosters deterministas.
- 🚢 **[05 · Guía de Despliegue y Operación](documentacion/05_GUIA_DESPLIEGUE_Y_OPERACION.md):** Instalación avanzada, Colab GPU, SQLite WAL y prevención de fugas de memoria.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta el archivo `LICENSE` para más información.
