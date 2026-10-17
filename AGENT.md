# AGENT.md · Protocolo de Ingeniería y Directivas de Operación

> **PROYECTO:** `twitter-post-classifier-master`  
> **ÁMBITO:** Raíz del proyecto (`/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS/twitter_post_classifier_master`)  
> **ESTRUCTURA DE WORKSPACE:** El directorio general (`/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS`) es un contenedor multi-proyecto destinado a almacenar múltiples aplicaciones independientes de JEV o Laya. Este proyecto es una aplicación autónoma con su propio repositorio Git, configuración y ciclo de vida aislado.  
> **APLICACIÓN:** Todo agente de IA, modelo o asistente que inspeccione, planifique o modifique este repositorio o desarrolle aplicaciones basadas en **JEV / TypeSafe System One**.

---

## 🧭 1. Directiva Suprema: "Graph-First Engineering" (Regla de Oro Prioritaria)

Antes de realizar **CUALQUIER MODIFICACIÓN, EDICIÓN O REFACTORIZACIÓN** de código en cualquier archivo del proyecto:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  EL AGENTE TIENE LA OBLIGACIÓN ESTRICTA Y PRIORITARIA DE CONSULTAR EL GRAFO DE        │
│  CONOCIMIENTO (GRAPHIFY) ANTES DE TOCAR CUALQUIER LÍNEA DE CÓDIGO.                    │
│                                                                                        │
│  Está terminantemente prohibido asumir flujos, alterar firmas o modificar archivos    │
│  a ciegas sin haber realizado previamente el análisis de impacto mediante Graphify.    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 ¿Qué debe identificar la consulta con Graphify?
1. **Radio de Impacto Real (*Blast Radius*):**
   - Identificar todos los nodos, clases, funciones y componentes que dependen directa o indirectamente del archivo o símbolo a modificar (dependencias *upstream* y *downstream*).
2. **Flujo de Ejecución Correcto (*Call Flow* & Contratos):**
   - Identificar la dirección legítima de las llamadas (`caller` → `callee`), interfaces de esquemas compartidos (`Pydantic`, `SQLite`, `DOM IDs`) y relaciones funcionales (`calls`, `implements`, `references`, `shares_data_with`).
3. **Alcance Quirúrgico del Cambio:**
   - Aislar con precisión qué debe cambiarse y **qué NO debe romperse**. Prevenir efectos secundarios invisibles en endpoints, workers asíncronos o eventos del DOM del frontend.

---

## 🛠️ 2. Mecanismos de Consulta a Graphify

El proyecto cuenta con el grafo de conocimiento activo y actualizado en `graphify-out/`. Para consultar el grafo antes de planificar o ejecutar cambios, utiliza cualquiera de los siguientes métodos:

### Método A: Comando CLI directo (`graphify query`)
```bash
# Consulta semántica de flujo con Graphify
graphify query "¿Cómo se relaciona endpoints_posts.py con LayaEngine y SQLite?"

# Trazado de ruta más corta entre dos componentes
graphify path "backend_app_api_endpoints_posts" "backend_app_engine_layaengine_classify_post"

# Explicación de un nodo o módulo clave
graphify explain "backend_app_services_batch_service_batchservice"
```

### Método B: Script Python con NetworkX (Inspección de Dependencias y Vecinos)
Utiliza el intérprete de Graphify guardado en el proyecto:
```bash
$(cat graphify-out/.graphify_python) -c "
import json, networkx as nx
from pathlib import Path

# Cargar grafo
graph_data = json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8'))
G = nx.node_link_graph(graph_data)

# Nodo a investigar
target = 'backend_app_api_endpoints_posts_override_post'

print(f'=== INSPECCIÓN DE NODO: {target} ===')
if target in G:
    print('Vecinos / Dependencias directas:')
    for neighbor in G.neighbors(target):
        edge_data = G.get_edge_data(target, neighbor)
        print(f'  -> {neighbor} | Relación: {edge_data}')
else:
    print(f'Nodo no encontrado directamente. Buscando coincidencias...')
    matches = [n for n in G.nodes if 'override_post' in n]
    print('Coincidencias encontradas:', matches)
"
```

### Método C: Revisión de Artefactos de Graphify
- `graphify-out/GRAPH_REPORT.md`: Para consultar *God Nodes*, grados de conexión y comunidades arquitectónicas.
- `graphify-out/graph.json`: Estructura pura de nodos y aristas.

---

## 🧠 3. Ingeniería de Preguntas para Jev / TypeSafe System One (Skill Obligatoria: `jev-questions`)

En cualquier desarrollo, subfase o aplicación basada en **JEV / TypeSafe System One (Noul, Choice, Score)**, el agente **DEBE APLICAR OBLIGATORIAMENTE** los principios y herramientas de la skill instalada en `~/.agents/skills/jev-questions/`.

> **Principio Clave:** System One retorna juicios tipados (probabilidades, distribuciones y niveles), no texto libre. Una pregunta mal calibrada colapsa a una constante, introduce sesgos o destruye la capacidad discriminativa del pipeline.

### 3.1 Las 9 Reglas de Oro de Estructuración de Preguntas Jev

1. **Los criterios describen situaciones del mundo real, NUNCA listas de palabras (*Surface Forms*):**
   - ❌ *Incorrecto:* `true="Empieza por 'y entonces', 'pero luego', 'exactamente'"` (el modelo lee significado, no patrones léxicos ciegos).
   - ✅ *Correcto:* `true="El inicio depende de contexto que el lector no tiene: completa una idea previa o responde a algo no visible"`.
   - *Regla de frontera:* Si una pregunta se activa por error ante situaciones vecinas (ej. discusión entre panelistas vs interacción con público), explicitar la distinción en la propia pregunta.
2. **Comprobar la capacidad de discriminación (*The Spread Test*):**
   - Una pregunta cuya respuesta honesta sea "más o menos sí" para todo caso no discrimina nada.
   - Medir la dispersión poblacional (*spread*, desviación estándar) con `spread.py`. Si el spread es menor a ~0.15, la pregunta es casi constante y actúa como ruido.
   - ⚠️ **Nunca relajar un umbral para forzar que pase una pregunta plana:** Si el spread es bajo, se debe rediseñar la pregunta o descartarla.
3. **Elegir la primitiva adecuada para la forma del juicio:**
   - **Noul:** Juicio binario absoluto e independiente sobre el estado (sí/no con probabilidad 0.0-1.0).
   - **Choice:** Selección de una entre N opciones enumeradas. **OBLIGATORIO: siempre incluir una opción de escape (`none_of_these` / `other`)**, de lo contrario el modelo forzará la opción "menos mala" de una lista donde ninguna aplica.
   - **Score:** Niveles cualitativos ordenados donde cada nivel describe una situación observable concreta (nunca números abstractos).
4. **Estado: colocar al modelo exactamente donde se sienta el juez:**
   - Si se evalúa si un lector comprenderá el post por sí solo, proporcionar **únicamente lo que el lector ve**. Si se añade contexto adicional, el modelo lo resolverá internamente y concluirá falsamente que todo está claro.
   - Referenciar elementos por identificador limpio (`L042| texto`). El modelo nunca debe calcular, contar o comparar números aritméticos.
   - No marcar un elemento del estado como ancla autoritativa infalible en la instrucción si el llamador no puede garantizar que siempre sea exacto.
5. **Muchas preguntas, un solo estado, una sola petición:**
   - Definir múltiples preguntas sobre el mismo objeto en una sola llamada a System One. El costo marginal es mínimo y garantiza coherencia interna entre juicios.
6. **No pedir al modelo un número que el código va a calcular (*Composite vs Verdict*):**
   - Si el sistema combina dimensiones en código mediante pesos, **no** preguntar además al modelo "¿es bueno en general?".
   - En poblaciones ya prefiltradas, una pregunta genérica ("¿vale la pena clasificarlo?") responderá uniformemente "sí". Preguntar siempre por dimensiones específicas y localizables en el texto.
7. **Separar Juicio de Política (*Judgment vs Policy*):**
   - El modelo emite el juicio puro (`verify(...) -> Judgment`: probabilidades, distribuciones, niveles).
   - El código de la aplicación aplica los umbrales y las acciones (`verdict(j) -> Verdict`).
   - Calibrar umbrales contra los casos difíciles o parciales reales (`threshold.py`), no contra ejemplos ideales.
   - Ordenar la política de evaluación por **reparabilidad** (descartar primero lo irreparable).
8. **Identificar dónde el modelo realmente supera al código:**
   - Gastar inferencia del modelo solo donde no exista un proxy computable. Si un regex, un split o un cálculo constante resuelven el caso, el código es la línea base obligatoria.
9. **Patrones de falla que parecen errores del modelo pero son de diseño:**
   - Si la opción correcta nunca es elegida: comprobar la cobertura de candidatos con `coverage.py`. **El modelo no puede elegir una opción que no fue incluida en la lista**.

### 3.2 Scripts de Verificación de Preguntas (Ejecución Obligatoria)

Ubicación de herramientas: `~/.agents/skills/jev-questions/scripts/`

| Herramienta | Regla | Uso en el Proyecto |
| :--- | :--- | :--- |
| `lint_questions.py <PATH>` | 1, 3, 4, 6 | **Auditoría estática obligatoria.** Escanea Python, JS/TS y JSON (`categories.json`) buscando listas de palabras prohibidas, Choice sin opción de escape, o negaciones confusas. |
| `spread.py RESPONSES.jsonl` | 2 | Valida si las preguntas discriminan o son constantes analizando medianas, rangos y spread. |
| `coverage.py CASES.jsonl` | 9 | Determina si los errores provienen de la pregunta o de que el generador de candidatos omitió la opción correcta. |
| `chance.py picks\|spans` | 2 | Evalúa el puntaje frente a elecciones aleatorias a la misma densidad con p-value exacto. |
| `threshold.py SCORES.jsonl` | 7 | Calibra umbrales óptimos entre contenido genuino y casos límite difíciles. |

---

## 📋 4. Ciclo de Trabajo Obligatorio en 5 Pasos

Todo requerimiento o tarea en este proyecto debe ejecutarse estrictamente bajo las siguientes 5 fases consecutivas:

```
[ Paso 1: Auditoría Graphify + Linter Jev (si aplica) ] 
                            ↓
[ Paso 2: Redacción del Plan Detallado (PLAN_SUBFASE_X_Y.md) ]
                            ↓
[ Paso 3: Ejecución Quirúrgica de Cambios ]
                            ↓
[ Paso 4: Batería de Pruebas Aisladas (run_all_tests.py + E2E + lint_questions) ]
                            ↓
[ Paso 5: Resumen Ejecutivo, Grafo y Commit Atómico del Proyecto ]
```

### 4.1 Protocolo de Ejecución de Pruebas y Prevención de OOM (Process Isolation Obligatorio)

> **REGLA DE ORO DE EJECUCIÓN:** Está **terminantemente desaconsejado** ejecutar toda la suite global en un único proceso monolítico (`python3 -m unittest discover tests`).  
> PyTorch y las arenas de asignación de memoria de `glibc` en inferencia de CPU acumulan tensores y buffers en el heap del proceso. Al descubrir y ejecutar 15+ suites consecutivamente en un solo proceso, la memoria residente (RSS) escala rápidamente superando los 4 GB hasta provocar que el kernel de Linux aborte la tarea por **OOM (Out Of Memory / Killed)**.

Para garantizar una ejecución limpia, libre de contaminación de estado y con memoria RAM constante (~1.5 GB - 1.8 GB máx):

1. **Test Runner Oficial con Aislamiento por Subprocesos:**
   Toda ejecución global de pruebas debe realizarse usando el script de aislamiento de procesos:
   ```bash
   python3 scripts/run_all_tests.py
   ```
   *Mecanismo:* Este script ejecuta cada suite (`tests/test_*.py`) de manera secuencial en su propio subproceso independiente. Al terminar cada archivo de prueba, el sistema operativo Linux reclama de inmediato el 100% de la memoria y buffers del proceso, manteniendo la ejecución completamente limpia y sin acumulación de memoria.

2. **Ejecución Individual de Suites:**
   Si se requiere probar un módulo específico durante el desarrollo interactivo:
   ```bash
   python3 -m unittest tests/test_nombre_modulo.py
   ```

3. **Restauración Obligatoria de Base de Datos en Tests:**
   Ningún test debe modificar de forma persistente `settings.DATABASE_PATH` sin un bloque `addCleanup` o `tearDownClass` / `asyncTearDown` que restaure incondicionalmente la ruta original de producción (`_original_db_path`).

---

## 📐 5. Estándar de Planes Detallados (`PLAN_SUBFASE_X_Y.md`)

Los planes **NUNCA** deben ser genéricos ni redactarse antes de la consulta con Graphify y la auditoría Jev. Todo plan debe residir en `documentacion/PLAN_SUBFASE_X_Y.md` (o `PLAN_DE_IMPLEMENTACION_...md`) y contener la siguiente anatomía obligatoria:

1. **Visión General del Objetivo:**
   - Contexto del problema actual y lista numerada de capacidades que se entregarán.
2. **Hallazgos del Análisis con Graphify:**
   - Nodos auditados en el grafo (`God Nodes`, dependientes directos, aristas INFERRED/EXTRACTED).
   - Identificación de contratos críticos que deben preservarse intactos.
3. **Diseño de Preguntas y Criterios Jev / System One (si aplica):**
   - Justificación de primitivas (Noul, Choice con escape, Score con situaciones).
   - Verificación previa con `lint_questions.py`.
4. **Decisiones de Diseño Clave:**
   - Justificación técnica y trade-offs (manejo de concurrencia, CORS, fallback en frontend, sincronización bidireccional).
5. **Diagrama de Arquitectura / Flujo (Mermaid):**
   - Diagrama claro de cómo interactúan frontend, backend, SQLite WAL y el motor Laya / Jev.
6. **Cambios Propuestos por Componente (Desglose Exhaustivo):**
   - **Backend:** Archivos exactos, endpoints, firmas de funciones y cambios DDL/esquema.
   - **Frontend:** Estructura HTML (`index.html`), estilos CSS (`styles.css`), controladores modulares (`data.js`, `matrix.js`, `views.js`, `drawer.js`, `modals.js`, `app.js`).
7. **Plan de Pruebas y Verificación:**
   - Pruebas unitarias backend con el runner aislado (`python3 scripts/run_all_tests.py` o módulo específico).
   - Pruebas de integración de API con `FastAPI TestClient`.
   - Pruebas End-to-End visuales o de interacción con `Playwright`.
   - Auditoría de preguntas con `python3 ~/.agents/skills/jev-questions/scripts/lint_questions.py`.

---

## 📝 6. Estándar de Resúmenes Ejecutivos (`RESUMEN_SUBFASE_X_Y.md`)

Al finalizar la implementación y superar las pruebas, se debe crear el documento de cierre en `documentacion/RESUMEN_SUBFASE_X_Y.md`:

1. **Objetivos Alcanzados:**
   - Lista punto por punto de las funcionalidades implementadas con su detalle técnico específico.
2. **Pruebas Realizadas y Resultados Verificables:**
   - Comprobaciones numéricas y logs de ejecución (`Ran N tests in Xs - OK`).
   - Resultados de auditoría con `lint_questions.py` en archivos modificados.
   - Descripción de casos de prueba E2E (flujo paso a paso, interacción con el usuario y verificación de respuestas).
   - Referencia a capturas visuales si se ejecutaron tests en navegador.
3. **Sincronización del Grafo y Control de Versiones:**
   - Correr actualización de Graphify para registrar nuevos nodos y dependencias:
     ```bash
     graphify --update
     ```
   - Realizar el commit correspondiente siguiendo estrictamente el protocolo de Git por proyecto (Sección 8).

---

## 🛡️ 7. Reglas de Preservación e Integridad de Código

1. **Preservación de Comentarios y Docstrings:**
   - No eliminar documentación preexistente, docstrings explicativos ni comentarios técnicos de diseño.
2. **Evitar Código Muerto o Mocks Temporales:**
   - No introducir barras ficticias, contadores simulados ni timeouts artificiales sin documentar su propósito.
3. **Compatibilidad Hacia Atrás:**
   - Si se expande un modelo Pydantic o una respuesta JSON, mantener los campos antiguos para no romper la suite de pruebas existente (`tests/test_api.py`, `tests/test_services.py`, etc.).
4. **Estilo Modular en Frontend:**
   - Respetar la separación de responsabilidades:
     - `data.js`: Almacenamiento reactivo y constantes taxonómicas.
     - `matrix.js`: Renderizado de celdas Waffle Grid y dinámicas split/pie.
     - `views.js`: Cuadrante Scatter Canvas 2D y Tabla Ejecutiva.
     - `drawer.js`: Drawer de inspección lateral y modal enriquecido de publicación.
     - `modals.js`: Modales de ingesta, taxonomía, co-ocurrencia y reportes.
     - `app.js`: Punto de entrada, listeners globales y orquestación.

---

## 🐙 8. Control de Versiones Git & GitHub: Aislamiento Estricto por Proyecto

> **PRINCIPIO FUNDAMENTAL DEL WORKSPACE:**  
> La carpeta superior `/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS` está diseñada para albergar **múltiples proyectos independientes** de JEV y Laya.  
> Cada subcarpeta dentro de este directorio (como `twitter_post_classifier_master`) representa un proyecto autónomo con su propio repositorio Git, su propio control de versiones y su propio repositorio remoto en GitHub.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  REGLA DE AISLAMIENTO GIT:                                                             │
│  La inicialización, configuración remota, commits y pushes a GitHub son ESTRICTAMENTE  │
│  POR CARPETA DE PROYECTO INDIVIDUAL, NUNCA DE MANERA GLOBAL O GENERALIZADA.            │
│                                                                                        │
│  Queda TERMINANTEMENTE PROHIBIDO crear repositorios Git en la carpeta contenedora      │
│  general o commitear cambios que mezclen archivos de diferentes proyectos vecinos.      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Protocolo de Verificación Previa Obligatoria (Pre-Flight Git Check)

Antes de ejecutar **CUALQUIER COMANDO GIT** (`git init`, `git add`, `git commit`, `git push`, `git remote`, `git checkout`, etc.), el agente **TIENE LA OBLIGACIÓN ESTRICTA** de realizar las siguientes verificaciones:

1. **Verificación de Directorio de Trabajo Actual (`pwd` / `Cwd`):**
   - Asegurarse incondicionalmente de que el comando se ejecute **DENTRO** de la carpeta raíz del proyecto activo:
     ```bash
     pwd
     # Debe retornar exactamente:
     # /home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS/twitter_post_classifier_master
     ```

2. **Verificación del Toplevel de Git (`git rev-parse --show-toplevel`):**
   - Validar que la raíz del repositorio Git coincida exactamente con la carpeta de este proyecto y no con un directorio padre:
     ```bash
     git rev-parse --show-toplevel
     # SALIDA ESPERADA:
     # /home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/JEV_APPS/twitter_post_classifier_master
     ```
   - ⚠️ **Alerta de Seguridad:** Si `git rev-parse --show-toplevel` apunta a una carpeta padre (como `.../JEV_APPS` o `.../Dev`), el agente debe **DETENERSE INMEDIATAMENTE**. No debe ejecutar `git add .` ni `git commit` bajo ninguna circunstancia hasta asegurar que el repositorio esté inicializado localmente en la subcarpeta del proyecto (`git init -b main`).

3. **Verificación del Repositorio Remoto Exclusivo:**
   - Comprobar que el remoto `origin` apunte única y exclusivamente al repositorio de GitHub correspondiente a este proyecto específico:
     ```bash
     git remote -v
     # Para twitter_post_classifier_master:
     # origin  https://github.com/cchrrisppatrickk/twitter_post_classifier_jev-laya.git (fetch)
     # origin  https://github.com/cchrrisppatrickk/twitter_post_classifier_jev-laya.git (push)
     ```

### 8.2 Flujo Operativo de Commits y Pushes por Proyecto

1. **Aislamiento de Cambios (Commits Atómicos):**
   - Los commits deben incluir exclusivamente los cambios realizados para las subfases o requerimientos de este proyecto.
   - Jamás utilizar rutas relativas hacia arriba (`../`) para agregar archivos en un commit.
2. **Respeto Estricto de `.gitignore` Local:**
   - Cada proyecto cuenta con su propio `.gitignore` en su raíz.
   - Verificar siempre que no se estén incluyendo archivos de base de datos SQLite locales (`backend/data/*.sqlite`), logs temporales (`logs/`), PIDs (`server.pid`), entornos virtuales ni carpetas de pruebas como `.playwright-cli/` o `scratch/`.
3. **Formato de Mensajes de Commit:**
   - Seguir convenciones descriptivas y estructuradas:
     - `feat(nombre-subfase): descripción del cambio funcional`
     - `fix(modulo): resolución de bug o regresión`
     - `docs(subfase): adición o actualización de PLAN o RESUMEN`
     - `test(modulo): nuevas pruebas aisladas o scripts de validación`
4. **Push Individual y Seguro:**
   - El push se realiza únicamente hacia la rama activa del repositorio específico de este proyecto:
     ```bash
     git push origin main
     ```
