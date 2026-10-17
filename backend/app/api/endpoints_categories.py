"""
endpoints_categories.py - Gestión Completa CRUD de Taxonomía, Ajustes Globales
y Banco de Preguntas Tipadas Laya (System 1) para Registry Studio v2.1.0.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import settings
from ..database import get_connection
from ..engine import LayaEngine
from ..registry import (
    build_decision_schema,
    get_categories_dict,
    get_root_family,
    load_registry_data,
)

logger = logging.getLogger("api_categories")
router = APIRouter(prefix="/api/categories", tags=["categories"])

PROTECTED_FAMILIES = {
    "ia", "blender", "modelado_3d", "juegos", "dev_tools",
    "mangas", "negocios_saas", "otros"
}

PROTECTED_SYSTEM_QUESTIONS = {
    "category", "content_format", "technical_depth"
}


class CategoryCreateRequest(BaseModel):
    code: Optional[str] = Field(default=None, max_length=5, description="Código corto (ej. TU, FLX, BLN)")
    name: Optional[str] = Field(default=None, max_length=80, description="Nombre legible de la categoría")
    label: Optional[str] = Field(default=None, max_length=80, description="Etiqueta visible de la categoría")
    id: Optional[str] = Field(default=None, description="Identificador único snake_case (se autogenera si es nulo)")
    parent_id: Optional[str] = Field(default=None, description="Familia raíz o categoría padre")
    description: Optional[str] = Field(default="", description="Criterios y directiva temática para la IA")
    keywords: List[str] = Field(default_factory=list, description="Palabras clave de activación")
    examples: List[str] = Field(default_factory=list, description="Ejemplos representativos de posts")
    exclusions: List[str] = Field(default_factory=list, description="Casos límite excluidos")
    color_hex: Optional[str] = Field(default=None, description="Color hexadecimal para la UI")
    threshold: float = Field(default=0.75, ge=0.50, le=0.99)
    priority: int = Field(default=30, ge=1, le=999)
    is_family: bool = Field(default=False)
    boosters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    active: bool = Field(default=True)


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    label: Optional[str] = Field(default=None, min_length=2, max_length=80)
    code: Optional[str] = Field(default=None, max_length=5)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    color_hex: Optional[str] = None
    threshold: Optional[float] = Field(default=None, ge=0.50, le=0.99)
    priority: Optional[int] = Field(default=None, ge=1, le=999)
    active: Optional[bool] = None


class CategoryItemResponse(BaseModel):
    id: str
    code: str
    name: str
    label: str
    parent_id: Optional[str] = None
    family_id: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    boosters: Dict[str, Any] = Field(default_factory=dict)
    color_hex: str
    threshold: float
    priority: int
    active: bool
    is_family: bool = False


class GlobalSettingsUpdateRequest(BaseModel):
    fallback_category: Optional[str] = None
    fallback_format: Optional[str] = None
    default_threshold: Optional[float] = Field(default=None, ge=0.50, le=0.95)
    min_confidence_abstain: Optional[float] = Field(default=None, ge=0.30, le=0.85)
    min_threshold_for_primary: Optional[float] = Field(default=None, ge=0.50, le=0.95)
    max_labels_per_post: Optional[int] = Field(default=None, ge=1, le=10)
    multi_label: Optional[bool] = None


class SupplementaryQuestionRequest(BaseModel):
    id: Optional[str] = Field(default=None, description="Identificador único (ej. target_audience)")
    type: str = Field(description="Tipo de inferencia: 'choice', 'score' o 'noul'")
    instructions: str = Field(min_length=5, description="Instrucción de inferencia en lenguaje natural")
    active: Optional[bool] = Field(default=True, description="Estado de activación de la pregunta")
    criteria: Optional[Any] = Field(default=None, description="Criterios para tipo choice (dict), score (list) o noul (dict)")


def _derive_code(cat_id: str, label: str) -> str:
    """Genera un código corto de 2 a 4 caracteres para badges de la UI."""
    words = re.findall(r'[A-Za-z0-9]+', label)
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()[:4]
    clean_id = re.sub(r'[^A-Za-z0-9]', '', cat_id)
    return clean_id[:4].upper() if clean_id else "CAT"


def _save_categories_json_atomically(data: Dict[str, Any]) -> None:
    """Persiste atómicamente el archivo categories.json y recarga en caliente Laya Router."""
    cat_path = settings.CATEGORIES_PATH
    temp_path = Path(str(cat_path) + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(cat_path)

    # Recargar taxonomía y actualizar schema en Laya
    load_registry_data(reload=True)
    engine = LayaEngine.get_instance()
    engine.schema = build_decision_schema()
    logger.info("categories.json persistido y Laya Router recargado exitosamente.")


def _build_category_response(c_data: Dict[str, Any]) -> CategoryItemResponse:
    c_id = c_data["id"]
    root_fam = get_root_family(c_id)
    label = c_data.get("label", c_id)
    code = c_data.get("code") or _derive_code(c_id, label)
    color = c_data.get("color_hex") or "#8b5cf6"

    return CategoryItemResponse(
        id=c_id,
        code=code,
        name=label,
        label=label,
        parent_id=c_data.get("parent_id"),
        family_id=root_fam,
        description=c_data.get("description", ""),
        keywords=c_data.get("keywords", []),
        examples=c_data.get("examples", []),
        exclusions=c_data.get("exclusions", []),
        boosters=c_data.get("boosters", {}),
        color_hex=color,
        threshold=float(c_data.get("threshold", 0.75)),
        priority=int(c_data.get("priority", 50)),
        active=bool(c_data.get("active", True)),
        is_family=bool(c_data.get("is_family", False) or c_id in PROTECTED_FAMILIES)
    )


# ============================================================================
# RUTAS DE AJUSTES GLOBALES Y SCORING (Deben preceder a /{id})
# ============================================================================

@router.get("/settings/globals", response_model=Dict[str, Any])
async def get_global_settings():
    """Retorna los ajustes globales del pipeline, boosters y scoring de categories.json."""
    data = load_registry_data()
    return {
        "global_settings": data.get("global_settings", {}),
        "scoring": data.get("scoring", {}),
        "registry_version": data.get("registry_version", "2.1.0"),
        "total_categories": len(data.get("topic_categories", [])),
        "protected_families": list(PROTECTED_FAMILIES)
    }


@router.put("/settings/globals", response_model=Dict[str, Any])
async def update_global_settings(payload: GlobalSettingsUpdateRequest):
    """Actualiza los parámetros globales de inferencia y umbrales en categories.json."""
    data = load_registry_data(reload=True)
    g_settings = data.setdefault("global_settings", {})

    update_dict = payload.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if v is not None:
            g_settings[k] = v

    _save_categories_json_atomically(data)
    logger.info("Ajustes globales actualizados exitosamente en categories.json")
    return {
        "status": "success",
        "global_settings": g_settings,
        "message": "Ajustes globales persistidos y aplicados al motor."
    }


# ============================================================================
# RUTAS DEL BANCO DE PREGUNTAS TIPADAS SYSTEM 1 (Deben preceder a /{id})
# ============================================================================

@router.get("/questions/supplementary", response_model=Dict[str, Any])
async def list_supplementary_questions():
    """Retorna el banco de preguntas suplementarias tipadas de inferencia Laya con su estado active."""
    data = load_registry_data()
    raw_supp = data.get("supplementary_questions", {})
    # Asegurar que cada entrada exponga el campo 'active' (por defecto True)
    formatted_supp = {}
    for q_id, q_cfg in raw_supp.items():
        if isinstance(q_cfg, dict):
            entry = dict(q_cfg)
            entry["active"] = entry.get("active", True)
            formatted_supp[q_id] = entry

    return {
        "supplementary_questions": formatted_supp,
        "protected_questions": list(PROTECTED_SYSTEM_QUESTIONS)
    }


@router.post("/questions/supplementary", status_code=status.HTTP_201_CREATED)
async def create_supplementary_question(payload: SupplementaryQuestionRequest):
    """Añade una nueva pregunta tipada (choice, score o noul) a Laya Router."""
    if not payload.id:
        raise HTTPException(status_code=400, detail="El identificador de la pregunta (id) es obligatorio.")

    q_id = re.sub(r'[^a-z0-9_]', '', payload.id.lower().replace(' ', '_')).strip('_')
    if not q_id:
        raise HTTPException(status_code=400, detail="ID de pregunta inválido.")

    valid_types = {"choice", "score", "noul"}
    if payload.type.lower() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Tipo de pregunta no soportado. Tipos válidos: {valid_types}")

    data = load_registry_data(reload=True)
    supp = data.setdefault("supplementary_questions", {})

    if q_id in supp or q_id in PROTECTED_SYSTEM_QUESTIONS:
        raise HTTPException(status_code=409, detail=f"Ya existe una pregunta tipada con el ID '{q_id}'.")

    question_entry: Dict[str, Any] = {
        "type": payload.type.lower(),
        "instructions": payload.instructions.strip(),
        "active": True if payload.active is None else payload.active
    }
    if payload.criteria is not None:
        question_entry["criteria"] = payload.criteria

    supp[q_id] = question_entry
    data["supplementary_questions"] = supp
    _save_categories_json_atomically(data)

    try:
        engine = LayaEngine.get_instance()
        engine.schema = build_decision_schema()
    except Exception as e:
        logger.warning(f"No se pudo sincronizar LayaEngine tras crear pregunta: {e}")

    logger.info(f"Nueva pregunta tipada añadida a Laya: '{q_id}' [{payload.type}] (activa={question_entry['active']})")
    return {"status": "success", "question_id": q_id, "question": question_entry}


@router.put("/questions/supplementary/{q_id}")
async def update_supplementary_question(q_id: str, payload: SupplementaryQuestionRequest):
    """Actualiza las instrucciones, criterios o estado active de una pregunta tipada existente."""
    data = load_registry_data(reload=True)
    supp = data.setdefault("supplementary_questions", {})

    if q_id not in supp:
        raise HTTPException(status_code=404, detail=f"No se encontró la pregunta con ID '{q_id}'.")

    target = supp[q_id]
    if payload.instructions:
        target["instructions"] = payload.instructions.strip()
    if payload.type:
        target["type"] = payload.type.lower()
    if payload.criteria is not None:
        target["criteria"] = payload.criteria
    if payload.active is not None:
        target["active"] = payload.active

    supp[q_id] = target
    data["supplementary_questions"] = supp
    _save_categories_json_atomically(data)

    try:
        engine = LayaEngine.get_instance()
        engine.schema = build_decision_schema()
    except Exception as e:
        logger.warning(f"No se pudo sincronizar LayaEngine tras actualizar pregunta: {e}")

    logger.info(f"Pregunta tipada '{q_id}' actualizada exitosamente.")
    return {"status": "success", "question_id": q_id, "question": target}


@router.patch("/questions/supplementary/{q_id}/toggle")
async def toggle_supplementary_question(q_id: str):
    """Alterna el estado activo/inactivo (active: true/false) de una pregunta suplementaria."""
    data = load_registry_data(reload=True)
    supp = data.setdefault("supplementary_questions", {})

    if q_id not in supp:
        raise HTTPException(status_code=404, detail=f"No se encontró la pregunta con ID '{q_id}'.")

    target = supp[q_id]
    current_status = target.get("active", True)
    new_status = not current_status
    target["active"] = new_status

    supp[q_id] = target
    data["supplementary_questions"] = supp
    _save_categories_json_atomically(data)

    try:
        engine = LayaEngine.get_instance()
        engine.schema = build_decision_schema()
    except Exception as e:
        logger.warning(f"No se pudo sincronizar LayaEngine tras toggle de pregunta: {e}")

    logger.info(f"Estado de pregunta '{q_id}' alternado a {'ACTIVA' if new_status else 'INACTIVA'}.")
    return {"status": "success", "question_id": q_id, "active": new_status, "question": target}


@router.delete("/questions/supplementary/{q_id}")
async def delete_supplementary_question(q_id: str):
    """Elimina una pregunta tipada suplementaria personalizada (protege las core del sistema)."""
    if q_id in PROTECTED_SYSTEM_QUESTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"La pregunta '{q_id}' es una dimensión núcleo del sistema y está protegida contra eliminación."
        )

    data = load_registry_data(reload=True)
    supp = data.setdefault("supplementary_questions", {})

    if q_id not in supp:
        raise HTTPException(status_code=404, detail=f"No se encontró la pregunta con ID '{q_id}'.")

    del supp[q_id]
    data["supplementary_questions"] = supp
    _save_categories_json_atomically(data)

    try:
        engine = LayaEngine.get_instance()
        engine.schema = build_decision_schema()
    except Exception as e:
        logger.warning(f"No se pudo sincronizar LayaEngine tras eliminar pregunta: {e}")

    logger.info(f"Pregunta tipada '{q_id}' eliminada de categories.json.")
    return {"status": "success", "deleted_id": q_id, "message": "Pregunta eliminada exitosamente."}


# ============================================================================
# RUTAS PRINCIPALES DE CATEGORÍAS (LISTAR, CREAR, OBTENER, EDITAR, ELIMINAR)
# ============================================================================

@router.get("", response_model=List[CategoryItemResponse])
async def list_categories(family: Optional[str] = None):
    """Retorna la lista completa de categorías cargadas desde categories.json v2.1.0."""
    cats = get_categories_dict()
    result: List[CategoryItemResponse] = []

    for c_id, c_data in cats.items():
        root_fam = get_root_family(c_id)
        if family and root_fam != family:
            continue
        result.append(_build_category_response(c_data))

    # Ordenar por prioridad
    return sorted(result, key=lambda c: c.priority)


@router.post("", response_model=CategoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreateRequest):
    """
    Crea una nueva categoría en la taxonomía:
    - Valida que no exista colisión de ID.
    - Persiste atómicamente en categories.json en disco.
    - Recarga la taxonomía en caliente (load_registry_data) y actualiza Laya Router.
    """
    data = load_registry_data(reload=True)
    categories = data.get("topic_categories", [])

    cat_label = (payload.label or payload.name or payload.id or "Nueva Categoría").strip()
    raw_id = payload.id or payload.label or payload.name or "nueva_categoria"
    cat_id = re.sub(r'[^a-z0-9_]', '', raw_id.lower().replace(' ', '_').replace('-', '_')).strip('_')
    if not cat_id:
        raise HTTPException(status_code=400, detail="No se pudo derivar un ID válido para la categoría.")

    existing_ids = {c["id"] for c in categories}
    if cat_id in existing_ids:
        raise HTTPException(status_code=409, detail=f"La categoría con ID '{cat_id}' ya existe.")

    parent_id = payload.parent_id
    if not parent_id or parent_id not in existing_ids:
        parent_id = "otros" if "otros" in existing_ids else None

    palette = ["#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#0284c7", "#ea580c", "#6366f1", "#14b8a6"]
    color = payload.color_hex or palette[len(categories) % len(palette)]
    code = (payload.code or _derive_code(cat_id, cat_label)).upper()[:4]
    desc = payload.description.strip() or f"Publicaciones temáticas sobre {cat_label}."

    new_cat_entry = {
        "id": cat_id,
        "label": cat_label,
        "parent_id": parent_id,
        "priority": payload.priority,
        "threshold": payload.threshold,
        "description": desc,
        "examples": payload.examples or payload.keywords[:3],
        "exclusions": payload.exclusions or [],
        "keywords": [k.strip().lower() for k in payload.keywords if k.strip()],
        "boosters": payload.boosters if payload.boosters else {
            "reproducible_assets": [],
            "keywords": [k.strip().lower() for k in payload.keywords[:5] if k.strip()]
        },
        "color_hex": color,
        "code": code,
        "active": payload.active,
        "is_family": payload.is_family
    }

    categories.append(new_cat_entry)
    data["topic_categories"] = categories
    _save_categories_json_atomically(data)

    logger.info(f"Nueva categoría creada: '{cat_id}' ({payload.name})")
    return _build_category_response(new_cat_entry)


@router.get("/{category_id}", response_model=CategoryItemResponse)
async def get_category(category_id: str):
    """Obtiene el detalle completo de una categoría por su ID."""
    cats = get_categories_dict()
    if category_id not in cats:
        raise HTTPException(status_code=404, detail=f"Categoría '{category_id}' no encontrada.")
    return _build_category_response(cats[category_id])


@router.put("/{category_id}", response_model=CategoryItemResponse)
async def update_category(category_id: str, payload: CategoryUpdateRequest):
    """
    Actualiza completamente una categoría existente en categories.json.
    Permite modificar label, description, keywords, examples, exclusions, threshold, priority, color y active.
    """
    data = load_registry_data(reload=True)
    categories = data.get("topic_categories", [])

    cat_idx = next((i for i, c in enumerate(categories) if c["id"] == category_id), None)
    if cat_idx is None:
        raise HTTPException(status_code=404, detail=f"Categoría '{category_id}' no encontrada.")

    target = categories[cat_idx]

    # Actualizar campos provistos
    if payload.label is not None:
        target["label"] = payload.label.strip()
    elif payload.name is not None:
        target["label"] = payload.name.strip()

    if payload.code is not None:
        target["code"] = payload.code.strip().upper()[:4]
    if payload.description is not None:
        target["description"] = payload.description.strip()
    if payload.keywords is not None:
        target["keywords"] = [k.strip().lower() for k in payload.keywords if k.strip()]
        target.setdefault("boosters", {})["keywords"] = target["keywords"][:5]
    if payload.examples is not None:
        target["examples"] = [e.strip() for e in payload.examples if e.strip()]
    if payload.exclusions is not None:
        target["exclusions"] = [x.strip() for x in payload.exclusions if x.strip()]
    if payload.color_hex is not None:
        target["color_hex"] = payload.color_hex
    if payload.threshold is not None:
        target["threshold"] = payload.threshold
    if payload.priority is not None:
        target["priority"] = payload.priority
    if payload.active is not None:
        target["active"] = payload.active

    # Si se cambia el parent_id, validar que exista
    if payload.parent_id is not None:
        existing_ids = {c["id"] for c in categories}
        if payload.parent_id in existing_ids:
            target["parent_id"] = payload.parent_id
        elif payload.parent_id == "" or payload.parent_id is None:
            # Solo permitir parent_id nulo si es una familia raíz
            if target.get("is_family", False) or category_id in PROTECTED_FAMILIES:
                target["parent_id"] = None

    categories[cat_idx] = target
    data["topic_categories"] = categories
    _save_categories_json_atomically(data)

    logger.info(f"Categoría '{category_id}' actualizada exitosamente.")
    return _build_category_response(target)


@router.delete("/{category_id}")
async def delete_category(category_id: str):
    """
    Elimina una categoría de la taxonomía categories.json.
    - PROTECCIÓN: Bloquea la eliminación si es una de las 8 familias raíz protegidas.
    - REASIGNACIÓN: Reasigna en SQLite WAL todas las publicaciones de esta categoría a 'otros' (PENDING).
    - JERARQUÍA: Reubica las subcategorías huérfanas bajo la categoría padre o 'otros'.
    """
    data = load_registry_data(reload=True)
    categories = data.get("topic_categories", [])

    cat_idx = next((i for i, c in enumerate(categories) if c["id"] == category_id), None)
    if cat_idx is None:
        raise HTTPException(status_code=404, detail=f"Categoría '{category_id}' no encontrada.")

    target = categories[cat_idx]

    # Validar protección de familias raíz
    if category_id in PROTECTED_FAMILIES or target.get("is_family", False):
        raise HTTPException(
            status_code=400,
            detail=f"No es posible eliminar la familia raíz '{category_id}'. Está protegida para salvaguardar el Family Gating de Laya Engine."
        )

    parent_id = target.get("parent_id") or "otros"

    # 1. Reasignar subcategorías hijas
    for c in categories:
        if c.get("parent_id") == category_id:
            c["parent_id"] = parent_id

    # 2. Remover categoría de la lista
    categories.pop(cat_idx)
    data["topic_categories"] = categories
    _save_categories_json_atomically(data)

    # 3. Reasignar publicaciones huérfanas en la base de datos SQLite WAL
    reassigned_count = 0
    try:
        db = await get_connection()
        try:
            cursor = await db.execute(
                "UPDATE posts SET primary_category = 'otros', status = 'PENDING' WHERE primary_category = ?",
                (category_id,)
            )
            reassigned_count = cursor.rowcount
            await db.commit()
        finally:
            await db.close()
    except Exception as e:
        logger.warning(f"Error al reasignar posts tras eliminar categoría '{category_id}': {e}")

    logger.info(f"Categoría '{category_id}' eliminada exitosamente. Posts reasignados: {reassigned_count}")
    return {
        "status": "success",
        "deleted_id": category_id,
        "reassigned_posts": reassigned_count,
        "message": f"Categoría '{category_id}' eliminada. {reassigned_count} posts reasignados a 'otros'."
    }
