# 05 · Guía de Despliegue, Operación y Mantenimiento

> **Proyecto:** `Twitter Post Classifier Master`  
> **Sistemas Operativos Compatibles:** Linux (Fedora, Ubuntu, Debian, Arch), macOS (Apple Silicon MPS / Intel), Windows (WSL2 recomendado)  
> **Intérprete Mínimo:** Python 3.10 o superior  
> **Entornos de Ejecución:** Servidor Local On-Premise y Google Colab Acelerado por GPU  

---

## 🛠️ 1. Requisitos Previos e Instalación de Dependencias

### 1.1 Requisitos de Hardware

| Componente | Mínimo Recomendado (CPU) | Óptimo Acelerado (GPU) |
| :--- | :--- | :--- |
| **Procesador** | CPU Intel Core i5 / AMD Ryzen 5 (4 núcleos) | Cualquier CPU host (2+ núcleos) |
| **Acelerador** | Ninguno (Inferencia vectorial CPU) | **NVIDIA CUDA** (≥2 GB VRAM) o **Apple Silicon (MPS)** |
| **Memoria RAM** | 4 GB de memoria residente libre | 4 GB de memoria residente libre |
| **Almacenamiento** | 500 MB libres (Espacio para modelos y SQLite WAL) | 500 MB libres |
| **Latencia Esperada** | ~200 a 300 ms por publicación | **~5 a 25 ms por publicación** |

### 1.2 Instalación de Dependencias con Entorno Virtual
Se recomienda la creación de un entorno virtual aislado utilizando `venv` o el gestor de paquetes de alta velocidad `uv`:

```bash
# Navegar a la raíz del proyecto
cd "/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS/twitter_post_classifier_master"

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias oficiales del backend
pip install -r backend/requirements.txt
```

---

## ⚙️ 2. Configuración del Sistema (`.env`)

La aplicación carga su configuración desde variables de entorno o mediante un archivo `.env` en la raíz del proyecto (gobernado por `backend/app/config.py`):

```bash
# --- Metadatos y Entorno ---
APP_NAME="Twitter Post Classifier Master"
APP_VERSION="2.1.0"
ENVIRONMENT="production"
DEBUG=false

# --- Hardware e Inferencia ---
# 'auto' selecciona CUDA si está disponible, luego MPS (Apple Silicon), o CPU por defecto.
DEVICE="auto"
PYTORCH_NUM_THREADS=3
PYTORCH_INTEROP_THREADS=2
PRIMARY_MODEL="convaiinnovations/laya"

# --- Ingesta y Procesamiento en Lote ---
CHECKPOINT_INTERVAL=25
STREAM_CHUNK_SIZE=100
MAX_BATCH_WORKERS=1
YIELD_SLEEP_SECONDS=0.005
BATCH_YIELD_SECONDS=0.015

# --- Servidor y Red ---
API_HOST="0.0.0.0"
API_PORT=8000
CORS_ORIGINS=["*"]

# --- Base de Datos (SQLite WAL) ---
SQLITE_WAL_MODE=true
SQLITE_SYNCHRONOUS="NORMAL"
SQLITE_BUSY_TIMEOUT_MS=5000
SQLITE_CACHE_SIZE=-64000
```

---

## 🚀 3. Puesta en Marcha Local con Scripts de Control

El proyecto incluye scripts Bash robustos en la raíz que gestionan el ciclo de vida del proceso en segundo plano, verifican puertos en conflicto y auditan la inicialización.

### 3.1 Iniciar la Aplicación (`./start_app.sh`)
Inicia el servidor FastAPI con Uvicorn desacoplado de la terminal en segundo plano:
```bash
chmod +x start_app.sh stop_app.sh status_app.sh
./start_app.sh
```
*Capacidades automáticas del script:*
- Detecta el intérprete de Python en entornos virtuales vecinos o en `.venv`.
- Verifica si el puerto `8000` está ocupado por procesos huérfanos y los libera limpiamente.
- Ejecuta `uvicorn` en un grupo de procesos independiente con `setsid` y redirige los registros a `logs/app.log`.
- Guarda el PID activo en `server.pid` y valida la disponibilidad HTTP tras 2 segundos.

### 3.2 Verificar Estado de Salud (`./status_app.sh`)
Inspecciona si el proceso está en ejecución, consulta el uso de memoria RAM y comprueba el endpoint de diagnóstico `/api/system/health`:
```bash
./status_app.sh
```

### 3.3 Detener la Aplicación (`./stop_app.sh`)
Finaliza el proceso de forma segura enviando la señal `SIGTERM` para permitir el cierre limpio de transacciones en SQLite WAL. Si no responde tras 3 segundos, aplica `SIGKILL` y elimina el archivo `server.pid`:
```bash
./stop_app.sh
```

---

## ☁️ 4. Despliegue en la Nube con Google Colab (GPU NVIDIA)

Para clasificar lotes masivos de decenas de miles de posts sin consumir recursos de la máquina local, el repositorio incluye el cuaderno optimizado [`Twitter_Classifier_Colab_GPU.ipynb`](../Twitter_Classifier_Colab_GPU.ipynb).

```
┌────────────────────────────────────────────────────────────────────────┐
│               FLUJO DE OPERACIÓN EN GOOGLE COLAB CON GPU               │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Abrir Twitter_Classifier_Colab_GPU.ipynb en Google Colab            │
│ 2. Seleccionar Entorno de Ejecución > Cambiar tipo > GPU T4            │
│ 3. Ejecutar Celda 1: Clona el repositorio e instala 'uv' y paquetes    │
│ 4. Ejecutar Celda 2: Inicia Uvicorn con aceleración CUDA (~15ms/post)  │
│ 5. Ejecutar Celda 3: Genera URL pública vía Cloudflare Tunnels         │
│ 6. (Opcional) Monta Google Drive para persistir 'database.sqlite'      │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Características Clave del Cuaderno Colab:
- **Inferencia CUDA Acelerada:** Inferencia por GPU NVIDIA T4 (~5 a 20 ms por tweet).
- **Túnel Seguro Cloudflare:** Permite acceder al Dashboard interactivo desde cualquier navegador mediante un dominio HTTPS temporal (`https://xxxx.trycloudflare.com`) sin requerir reenvío de puertos ni exponer IPs públicas.
- **Protocolo Anti-Desconexión:** Incorpora un reproductor de audio silencioso en bucle y pings periódicos que evitan la suspensión automática por inactividad de la sesión de Colab.
- **Sincronización con Google Drive:** Permite respaldar la base de datos `database.sqlite` clasificada directamente en tu unidad personal antes de cerrar la máquina virtual.

---

## 💾 5. Mantenimiento y Operaciones de Base de Datos (SQLite WAL)

El motor de almacenamiento utiliza SQLite en modo **Write-Ahead Logging (WAL)**, lo cual genera tres archivos en `backend/data/`:
1. `database.sqlite`: Archivo de datos principal.
2. `database.sqlite-wal`: Diario de transacciones de escritura anticipada.
3. `database.sqlite-shm`: Memoria compartida para sincronización entre procesos lectores.

### 5.1 Optimización y Compactación (`VACUUM`)
A medida que se realizan miles de inserciones y actualizaciones, el archivo WAL puede acumular páginas pendientes de commit. Para liberar espacio y truncar el diario:
- **Desde la UI:** Ir a **Registry Studio (`/config`)** > Pestaña **Base de Datos** > Clic en **"Optimizar Base de Datos"**.
- **Vía API / cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/database/optimize
```

### 5.2 Copias de Seguridad (Export / Import)
- **Generar Respaldo Completo:**
```bash
curl -O http://127.0.0.1:8000/api/database/export
```
Descarga un archivo JSON estructurado con todos los posts, clasificaciones, historial de versiones y feedback humano.
- **Restaurar Respaldo:**
Se puede cargar a través de la interfaz web en la pestaña Base de Datos o invocando `POST /api/database/import` en modo `merge` o `replace`.

---

## 🧪 6. Aseguramiento de Calidad y Suite de Pruebas

### 6.1 Protocolo de Aislamiento de Procesos (`Process Isolation`)

> ⚠️ **ALERTA CRÍTICA DE ARQUITECTURA (Evitar OOM en CPU):**  
> PyTorch y las arenas de asignación de memoria de `glibc` en inferencia de CPU acumulan tensores y buffers en el heap del proceso. Al descubrir y ejecutar más de 15 suites consecutivas en un solo proceso monolítico (`python3 -m unittest discover tests`), la memoria residente (RSS) escala rápidamente superando los 4 GB hasta que el kernel de Linux aborta la tarea por **Out Of Memory (OOM / Killed)**.

Para mantener una ejecución limpia con memoria constante (~1.5 GB máx.):

```bash
# Runner Oficial de Pruebas con Aislamiento por Subprocesos
python3 scripts/run_all_tests.py
```
*Mecanismo:* Este script ejecuta cada archivo `tests/test_*.py` en un subproceso Linux independiente. Al concluir cada suite, el sistema operativo reclama de inmediato el 100% de la memoria, garantizando estabilidad total.

### 6.2 Ejecución de una Suite Específica
Si se está depurando un módulo puntual:
```bash
python3 -m unittest tests/test_api.py
python3 -m unittest tests/test_engine.py
python3 -m unittest tests/test_services.py
```

### 6.3 Pruebas End-to-End Visuales (Playwright)
Las pruebas visuales y funcionales sobre el navegador se encuentran automatizadas bajo `.playwright-cli/`:
- Verifican la carga del Dashboard, interacción con celdas de la Matriz Waffle, apertura del Drawer lateral, filtros en tiempo real y persistencia de temas.
- Las capturas generadas se almacenan en `documentacion/imagenes/`.
