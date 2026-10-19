# 04 · Taxonomía y Preguntas Tipadas System 1

> **Registro:** `categories.json` (Versión 2.1.0)  
> **Motor de Inferencia:** JEV / TypeSafe System One (`convaiinnovations/laya`)  
> **Enfoque Teórico:** Discriminación estructurada, Family Gating y Principios `jev-questions`  

---

## 🧭 1. Fundamentos: ¿Por Qué System 1 y No un LLM Generativo?

La clasificación y extracción de metadatos sobre grandes flujos de datos en tiempo real plantea desafíos que los Modelos de Lenguaje Grandes generativos (LLMs autoregresivos como GPT-4 o Claude) resuelven con ineficiencia:

1. **La Trampa del Formato Libre:** Un LLM generativo produce texto carácter por carácter. A menudo introduce variaciones léxicas imprevistas, markdown innecesario o JSONs mal formados que rompen la serialización en base de datos.
2. **Latencia Inviable:** Generar 100 tokens toma entre 1,000 y 3,000 milisegundos por publicación. Procesar un volcado de 2,000 posts tomaría más de 1.5 horas.
3. **Costo Recurrente y Privacidad:** Cada lote consume tokens de entrada y salida facturables y envía datos de usuarios a servidores externos.
4. **Alucinaciones Forzadas:** Si se le presenta una lista de opciones a un LLM sin una alternativa clara de escape, forzará la opción "menos mala", categorizando un meme de gatos como "Desarrollo de Software" simplemente por tener la palabra "código".

### El Enfoque JEV / TypeSafe System One
**System One** opera bajo el paradigma de **evaluación directa de representaciones contextuales**:
- Utiliza un modelo encoder de embeddings densos multilingües (`mmBERT` optimizado).
- No genera texto libre; en su lugar, proyecta el contenido del post contra un espacio latente estructurado por **preguntas fuertemente tipadas**.
- Retorna **juicios puros** (probabilidades discretas, niveles cualitativos y distribuciones de pertenencia) en un único *forward pass* que toma **~5 a 25 ms**.

---

## 🌳 2. La Taxonomía Maestra v2.1.0

La taxonomía del sistema está organizada en una jerarquía de dos niveles: **8 Familias Raíz** y **47 Categorías Técnicas Especializadas**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      ÁRBOL TAXONÓMICO MAESTRO v2.1.0                   │
├─────────────────────┬──────────────────────────────────────────────────┤
│ 1. IA & ML          │ llms_modelos, agentes_ia, vision_difusion,       │
│    (8 categorías)   │ audio_voz_ia, hardware_ia, local_llm,            │
│                     │ fine_tuning, etica_ia                            │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 2. Blender 3D       │ blender_general, blender_geometry_nodes,         │
│    (7 categorías)   │ blender_addons, shaders_procedurales,            │
│                     │ animacion_3d, rigging, vfx_compositing           │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 3. Modelado & WebGL │ modelado_hard_surface, escultura_digital,        │
│    (6 categorías)   │ texturizado_pbr, threejs_webgl, webgpu,          │
│                     │ renderizado_tiempo_real                          │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 4. Videojuegos      │ desarrollo_videojuegos, unity_engine,            │
│    (6 categorías)   │ unreal_engine, godot_engine, game_design,        │
│                     │ shaders_juegos                                   │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 5. Dev Tools & Web  │ dev_tools_general, herramientas_codigo,          │
│    (7 categorías)   │ terminal_cli, frontend_web, backend_apis,        │
│                     │ arquitectura_software, open_source_showcase      │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 6. Manga & Arte     │ mangas_anime, ilustracion_digital,               │
│    (4 categorías)   │ dibujo_tradicional, tutoriales_arte              │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 7. Negocios & SaaS  │ negocios_general, saas_growth, indie_hacking,    │
│    (5 categorías)   │ monetizacion_creadores, analisis_mercado         │
├─────────────────────┼──────────────────────────────────────────────────┤
│ 8. Otros & Vida     │ otros_general, humor_tech, carrera_profesional,  │
│    (4 categorías)   │ debate_comunidad                                 │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

## 📐 3. Primitivas de Juicio Tipadas (TypeSafe Primitives)

Cada evaluación semántica se realiza a través de una de las tres primitivas fundamentales de System 1:

### 3.1 Primitiva `Choice` (Selección Discreta Ponderada)
Se utiliza para la asignación categórica donde el modelo debe elegir una opción entre un conjunto finito y excluyente:
- **Regla de Oro Obligatoria:** Toda pregunta `Choice` debe incluir una opción de escape explícita (`none_of_these` u `otros`). Sin ella, el modelo se ve forzado a asignar probabilidad a opciones incorrectas.
- **Formato del Juicio:** Retorna una distribución de probabilidades `P(C_i)` normalizada donde `∑ P(C_i) = 1.0`.

```json
{
  "type": "choice",
  "instructions": "¿Cuál es el formato principal de este contenido?",
  "criteria": {
    "code_release": "Publicación o anuncio de un repositorio, biblioteca, framework o paquete de software con enlaces a código fuente.",
    "tutorial_guide": "Explicación educativa paso a paso, guía técnica o material pedagógico que enseña a resolver un problema concreto.",
    "showcase_demo": "Demostración visual, render, video o captura que exhibe un resultado final o trabajo en proceso sin código adjunto.",
    "technical_thread": "Hilo estructurado de análisis técnico, arquitectura o lecciones aprendidas.",
    "opinion_debate": "Comentario editorial, opinión personal, debate o discusión sobre la industria.",
    "none_of_these": "El post no encaja de forma clara en ninguno de los formatos anteriores."
  }
}
```

---

### 3.2 Primitiva `Noul` (Certeza Booleana)
Se utiliza para juicios binarios independientes sobre la presencia o ausencia de un rasgo en el estado observable:
- **Retorno:** Un escalar de probabilidad continuo entre `0.0` (falso absoluto) y `1.0` (verdadero absoluto).
- **Uso en el Proyecto:** 
  - Verificación de familias temáticas para **Family Gating** (`is_family_ia`, `is_family_blender`, etc.).
  - Banderas de seguridad y taxonomía (`is_local_first`, `is_uncensored_or_nsfw`).

```json
{
  "type": "noul",
  "instructions": "¿El post describe software, modelos o flujos que se ejecutan 100% de manera local en la máquina del usuario (Local-First / On-Device) sin depender de servidores en la nube?"
}
```

---

### 3.3 Primitiva `Score` (Niveles Cualitativos Ordenados)
Se utiliza cuando una dimensión posee una escala gradual ordenada.
- **Regla de Oro Obligatoria:** Cada nivel debe describir una **situación observable concreta**, nunca adjetivos ambiguos ("bueno", "regular") ni números abstractos.
- **Uso en el Proyecto:** Profundidad técnica (`technical_depth`) en una escala de 1.0 a 5.0.

```json
{
  "type": "score",
  "instructions": "¿Cuál es la profundidad técnica del contenido expuesto en la publicación?",
  "levels": {
    "1": "Nivel Superficial: Opinión genérica, meme, anuncio publicitario sin detalles técnicos o comentario de usuario final.",
    "2": "Nivel Divulgativo: Resumen de una noticia tecnológica o descripción conceptual accesible sin implementación práctica.",
    "3": "Nivel Práctico Intermedio: Comparte código funcional, configuración de herramientas, comandos de terminal o workflow reproducible.",
    "4": "Nivel Técnico Avanzado: Análisis de arquitectura interna, matemáticas de un modelo, optimización de shaders o benchmark riguroso.",
    "5": "Nivel Experto / Core: Código fuente de bajo nivel (C++, CUDA, Rust), papers científicos con formulación matemática o ingeniería de compiladores."
  }
}
```

---

## 🛡️ 4. Mecanismo de Family Gating (Anti-Colapso Léxico)

El mayor desafío en la clasificación fina con decenas de categorías afines es la **ambigüedad léxica**.  
*Ejemplo clásico:* Un tweet que dice: *"Escribí un script en Python para exportar geometry nodes con shaders personalizados"*.  
- Contiene términos de `dev_tools` (*Python, script*).
- Contiene términos de `blender` (*geometry nodes*).
- Contiene términos de `modelado_3d` (*shaders*).

Sin una arquitectura de contención, los clasificadores léxicos suelen asignar la mayor puntuación a `dev_tools` debido al peso de las palabras de programación.

### Solución en Dos Fases:
1. **Fase 1: Evaluación de Familias Raíz (Gating):**
   El motor evalúa concurrentemente 8 preguntas `Noul` correspondientes a las familias raíz.
   ```python
   family_map = {
       "is_family_ia": "ia",
       "is_family_blender": "blender",
       "is_family_modelado_3d": "modelado_3d",
       "is_family_juegos": "juegos",
       "is_family_dev_tools": "dev_tools",
       "is_family_mangas": "mangas",
       "is_family_negocios_saas": "negocios_saas",
       "is_family_otros": "otros"
   }
   ```
2. **Fase 2: Modulación Dinámica de Puntuaciones:**
   Para cada categoría candidata evaluada en la pregunta `Choice`:
   - Si la familia raíz a la que pertenece obtuvo una certeza `Noul < 0.30`, la categoría candidata es fuertemente penalizada multiplicando su score por `0.15`.
   - Si la familia raíz obtuvo una certeza `Noul ≥ 0.50`, recibe una bonificación de `+0.15`.

```
                    ┌────────────────────────────┐
                    │ Texto Normalizado del Post │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│ Inferencia Choice (Categoría) │         │ Inferencia Noul (8 Familias)  │
│ 47 clases simultáneas         │         │ Certeza booleana por familia  │
└──────────────┬────────────────┘         └──────────────┬────────────────┘
               │                                         │
               └────────────────────┬────────────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │ Ponderación de Family Gating │
                     ├─────────────────────────────┤
                     │ • Fam Score >= 0.50 -> +0.15 │
                     │ • Fam Score <  0.30 -> x0.15 │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │ Boosters Deterministas (URL)│
                     │ • GitHub Repo       -> +0.20│
                     │ • Hugging Face      -> +0.20│
                     │ • Civitai / ComfyUI -> +0.20│
                     │ • Specificity Bonus -> +0.05│
                     │ • Keyword Match     -> +0.08│
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │ Puntuación Final y Umbral   │
                     │ • Top Score >= Umbral       │
                     │   -> STATUS: CLASSIFIED     │
                     │ • Top Score <  Umbral       │
                     │   -> STATUS: PENDING        │
                     └─────────────────────────────┘
```

---

## ⚡ 5. Detección Determinista de Activos y Boosters por URL

La inferencia neural se complementa con **análisis determinista de patrones en URLs**:

```python
asset_domain_matchers = {
    "github_repo": ["github.com/", "gitlab.com/"],
    "huggingface_model": ["huggingface.co/", "hf.co/"],
    "civitai_lora": ["civitai.com/"],
    "comfyui_workflow": ["openart.ai/workflows", "comfyworkflows.com", "flowt.ai"],
    "tutorial_link": ["youtube.com/", "youtu.be/", "medium.com/", "substack.com/"]
}
```

Si el texto del tweet contiene un enlace a `huggingface.co/` o `civitai.com/`, el motor inyecta de forma determinista la categoría correspondiente con una bonificación de certeza de `+0.20`, asegurando que publicaciones con repositorios de código o pesos descargables sean clasificadas con máxima precisión técnica.

---

## 🚦 6. Política de Decisión, Abstención y Anomalías

### 6.1 Política de Abstención (`PENDING`)
La honestidad epistémica es un principio fundacional de **JEV**:
- Si una publicación obtiene una puntuación inferior al umbral mínimo de abstención (`MIN_CONFIDENCE_ABSTAIN = 0.55`) o inferior al umbral efectivo de su categoría sin contar con un activo reproducible confirmado, el sistema **se abstiene**.
- Su estado se marca como `PENDING`, se asigna temporalmente a la categoría comodín `otros` y se destaca visualmente en el Dashboard con un borde amarillo pulsante para revisión o re-evaluación asistida por humanos.

### 6.2 Detección de Anomalías (`Outliers`)
Una publicación se marca automáticamente con `is_outlier = 1` en base a dos criterios analíticos:
1. **Ruido Viral:** Publicaciones con más de 5,000 *likes* pero con afinidad técnica baja (`<0.60`) o profundidad técnica superficial (`≤1.5`).
2. **Gemas de Nicho:** Publicaciones con afinidad técnica extrema (`>0.95`) y enlaces a repositorios confirmados que obtuvieron tracción masiva comunitaria (`>1,000 likes`).
