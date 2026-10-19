"""
registry.py - Registro Taxonómico Maestro v2.1.0 y Compilador de Preguntas Tipadas (System 1).
Carga dinámicamente categories.json, gestiona herencia de umbrales, detección determinista
de dominios y compila el esquema tipado para Laya Router.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import settings

logger = logging.getLogger("registry")
logging.basicConfig(level=logging.INFO)

# Caché en memoria del registro
_REGISTRY_CACHE: Optional[Dict[str, Any]] = None
_CATEGORIES_DICT: Optional[Dict[str, Dict[str, Any]]] = None
_FAMILIES_DICT: Optional[Dict[str, Dict[str, Any]]] = None


def load_registry_data(reload: bool = False) -> Dict[str, Any]:
    """Carga y almacena en caché el archivo maestro categories.json."""
    global _REGISTRY_CACHE, _CATEGORIES_DICT, _FAMILIES_DICT
    if _REGISTRY_CACHE is not None and not reload:
        return _REGISTRY_CACHE

    cat_path = settings.CATEGORIES_PATH
    if not cat_path.exists():
        logger.error(f"Archivo de taxonomía no encontrado en: {cat_path}")
        return {}

    with open(cat_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _REGISTRY_CACHE = data
    _CATEGORIES_DICT = {c["id"]: c for c in data.get("topic_categories", [])}
    _FAMILIES_DICT = {c["id"]: c for c in data.get("topic_categories", []) if c.get("is_family", False)}

    logger.info(
        f"Taxonomía cargada exitosamente: versión {data.get('registry_version', 'unknown')}, "
        f"{len(_CATEGORIES_DICT)} categorías, {len(_FAMILIES_DICT)} familias raíz."
    )
    return _REGISTRY_CACHE


def get_categories_dict() -> Dict[str, Dict[str, Any]]:
    """Retorna diccionario de categorías indexadas por ID."""
    global _CATEGORIES_DICT
    if _CATEGORIES_DICT is None:
        load_registry_data()
    return _CATEGORIES_DICT or {}


def get_category_metadata(category_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene los metadatos completos de una categoría dada."""
    return get_categories_dict().get(category_id)


def get_root_family(category_id: str) -> str:
    """
    Recorre hacia arriba el árbol de parent_id hasta hallar la familia raíz.
    Si no tiene parent_id o es una familia, retorna su propio ID.
    """
    cats = get_categories_dict()
    curr = category_id
    visited: Set[str] = set()

    while curr and curr in cats and curr not in visited:
        visited.add(curr)
        parent = cats[curr].get("parent_id")
        if not parent:
            return curr
        curr = parent
    return curr or "otros"


def get_effective_threshold(category_id: str) -> float:
    """
    Calcula el umbral efectivo aplicando herencia:
    categoría -> padre -> abuelo -> default_threshold (0.75).
    """
    cats = get_categories_dict()
    curr = category_id
    visited: Set[str] = set()

    while curr and curr in cats and curr not in visited:
        visited.add(curr)
        c_info = cats[curr]
        if "threshold" in c_info and c_info["threshold"] is not None:
            return float(c_info["threshold"])
        curr = c_info.get("parent_id")

    return float(settings.DEFAULT_THRESHOLD)


def detect_asset_domains(text: str) -> Tuple[List[str], List[str]]:
    """
    Detección determinista por expresiones regulares de dominios reproducibles
    (GitHub, Hugging Face, Civitai, ComfyUI, etc.).
    Retorna: (tipos_de_assets_detectados, urls_encontradas)
    """
    data = load_registry_data()
    scoring_cfg = data.get("scoring", {})
    domain_matchers: Dict[str, List[str]] = scoring_cfg.get("asset_domain_matchers", {
        "github_repo": ["github.com/", "gitlab.com/"],
        "huggingface_model": ["huggingface.co/", "hf.co/"],
        "civitai_lora": ["civitai.com/"],
        "comfyui_workflow": ["openart.ai/workflows", "comfyworkflows.com", "flowt.ai"],
        "tutorial_link": ["youtube.com/", "youtu.be/", "medium.com/", "substack.com/"]
    })

    # Extraer URLs presentes en el texto
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
    found_urls = url_pattern.findall(text)

    detected_assets: Set[str] = set()
    text_lower = text.lower()

    for asset_type, domains in domain_matchers.items():
        for dom in domains:
            if dom.lower() in text_lower:
                detected_assets.add(asset_type)
                break

    return list(detected_assets), found_urls


def detect_deterministic_override(text: str, found_urls: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Evalúa reglas deterministas duras de OVERRIDE basadas en dominios de activos.
    Si se detecta un activo inequívoco (Civitai, ComfyUI, Hugging Face Diffusers, etc.),
    retorna (modalidad_forzada, tipo_de_activo) para neutralizar el sesgo del modelo.
    """
    data = load_registry_data()
    scoring = data.get("scoring", {})
    overrides_map = scoring.get("deterministic_overrides", {})

    text_lower = text.lower()
    
    # 1. Comprobar dominios de URLs encontradas
    for url in found_urls:
        u_lower = url.lower()
        if "civitai.com" in u_lower:
            return "mod_image", "civitai_lora"
        if any(w in u_lower for w in ["openart.ai/workflows", "comfyworkflows.com", "flowt.ai", "comfy.icu"]):
            return "mod_image", "comfyui_workflow"
        if "huggingface.co" in u_lower or "hf.co" in u_lower:
            # Si menciona video o diffusers de video
            if any(v in u_lower or v in text_lower for v in ["wan", "ltxv", "ltx-video", "hunyuanvideo", "cogvideox", "minimax"]):
                return "mod_video", "huggingface_model"
            # Si menciona 3D
            if any(t in u_lower or t in text_lower for t in ["trellis", "pixal3d", "hunyuan3d", "triposr"]):
                return "mod_3d", "huggingface_model"
            # Por defecto en HF si menciona checkpoint/lora/diffusers/flux/anima/sd
            if any(img in u_lower or img in text_lower for img in ["flux", "anima", "illustrious", "lora", "sdxl", "diffusers", "safetensors", "checkpoint"]):
                return "mod_image", "huggingface_model"

    # 2. Comprobar menciones en el texto si hay dominios mapeados
    for domain, forced_modality in overrides_map.items():
        if domain.lower() in text_lower:
            return forced_modality, None

    return None, None


PASS1_QUESTION_IDS = [
    "gen_modality",
    "content_format",
    "technical_depth",
    "is_local_first",
    "is_uncensored_or_nsfw"
]


def build_pass1_schema() -> Dict[str, Any]:
    """Compila el esquema ultra-ligero para Pasada 1 (5 preguntas base)."""
    data = load_registry_data()
    supp = data.get("supplementary_questions", {})
    schema: Dict[str, Any] = {}
    for qid in PASS1_QUESTION_IDS:
        if qid in supp and supp[qid].get("active", True):
            schema[qid] = supp[qid]
    return schema


def build_pass2_schema(modality: str) -> Dict[str, Any]:
    """Compila el esquema condicional para Pasada 2 (1 pregunta de familia específica)."""
    data = load_registry_data()
    supp = data.get("supplementary_questions", {})
    mapping = {
        "mod_image": "model_family_image",
        "mod_video": "model_family_video",
        "mod_3d": "model_family_3d",
        "mod_audio": "model_family_audio",
    }
    target_qid = mapping.get(modality)
    if target_qid and target_qid in supp and supp[target_qid].get("active", True):
        return {target_qid: supp[target_qid]}
    return {}


def build_decision_schema(active_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compila el esquema fuertemente tipado para el enrutador de Laya System 1:
      1. 'category': Elección discreta (Choice) entre las categorías activas.
      2. Preguntas suplementarias: content_format, technical_depth, etc. (filtradas según active_questions o su flag active).
      3. Preguntas booleanas (Noul) por cada familia raíz para Family Gating anti-colapso léxico.
    """
    data = load_registry_data()
    categories = data.get("topic_categories", [])

    include_all = active_questions is None
    active_set = set(active_questions) if active_questions is not None else set()

    schema: Dict[str, Any] = {}

    # 1. Criterios de la pregunta Choice principal
    if include_all or "category" in active_set:
        choice_criteria: Dict[str, str] = {}
        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.get("priority", 50))
            for cat in sorted_cats:
                if not cat.get("active", True):
                    continue
                desc = cat.get("description", "")
                examples = cat.get("examples", [])
                exclusions = cat.get("exclusions", [])
                parts = [desc]
                if examples:
                    parts.append(f"(Ejemplos: {'; '.join(examples[:2])})")
                if exclusions:
                    parts.append(f"(Exclusiones: {'; '.join(exclusions[:2])})")
                choice_criteria[cat["id"]] = " ".join(parts)
        else:
            choice_criteria = {
                "ia": "Inteligencia artificial, LLMs, modelos generativos.",
                "blender": "Herramienta Blender 3D, geometry nodes, cycles, renders.",
                "modelado_3d": "Gráficos 3D por computadora, WebGL, shaders.",
                "juegos": "Desarrollo de videojuegos, motores Unity, Unreal, Godot.",
                "dev_tools": "Desarrollo de software, código abierto, herramientas web.",
                "mangas": "Manga, anime, ilustración digital, webcomics.",
                "negocios_saas": "SaaS, métricas MRR, tracción y startups.",
                "otros": "Publicaciones personales, memes y discusiones generales."
            }

        schema["category"] = {
            "type": "choice",
            "instructions": "¿Cuál es la categoría temática principal de este post?",
            "criteria": choice_criteria
        }

    # 2. Agregar preguntas suplementarias estándar (respetando active_questions o q_cfg['active'])
    supp = data.get("supplementary_questions", {})
    for q_id, q_cfg in supp.items():
        if isinstance(q_cfg, dict) and "type" in q_cfg and "instructions" in q_cfg:
            is_active = q_cfg.get("active", True)
            if include_all:
                if is_active:
                    schema[q_id] = q_cfg
            else:
                if q_id in active_set:
                    schema[q_id] = q_cfg

    # 3. Preguntas Noul de Familias Raíz (Family Gating - PROMPT.md)
    # Se incluyen si se incluye "category" o si include_all es True o si se solicitó explícitamente alguna familia
    if include_all or "category" in active_set or any(q.startswith("is_family_") for q in active_set):
        root_families = {
            "is_family_ia": "¿El post trata temáticamente sobre Inteligencia Artificial, Machine Learning o modelos de IA?",
            "is_family_blender": "¿El post trata específicamente sobre Blender, geometry nodes, addons o renders 3D en Blender?",
            "is_family_modelado_3d": "¿El post trata sobre gráficos 3D, WebGL, Three.js, shaders, VFX o modelado 3D general?",
            "is_family_juegos": "¿El post trata temáticamente sobre desarrollo de videojuegos, game engines (Unity, Unreal, Godot) o gameplay?",
            "is_family_dev_tools": "¿El post trata sobre desarrollo de software, programación, terminal, repositorios de código o arquitectura?",
            "is_family_mangas": "¿El post trata sobre manga, anime, ilustración digital, dibujo tradicional o webcomics?",
            "is_family_negocios_saas": "¿El post trata sobre métricas de negocio, SaaS, tracción de ingresos (MRR), facturación o startups?",
            "is_family_otros": "¿El post es un comentario informal, broma, tweet de vida cotidiana o no encaja en temas técnicos?"
        }

        for fam_key, fam_instr in root_families.items():
            if include_all or "category" in active_set or fam_key in active_set:
                schema[fam_key] = {
                    "type": "noul",
                    "instructions": fam_instr
                }

    return schema
