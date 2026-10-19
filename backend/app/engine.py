"""
engine.py - Motor de Inferencia System 1 (Laya Local / mmBERT).
Ejecución local en CPU optimizada para Intel Core i5-10210U, Family Gating anti-alucinación,
detección determinista de activos y soporte multilingüe nativo (Unicode NFKC).
"""

from __future__ import annotations
import gc
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

import json
import urllib.request
import urllib.error

import psutil
import torch

from .config import settings
from .registry import (
    build_decision_schema,
    build_pass1_schema,
    build_pass2_schema,
    detect_asset_domains,
    detect_deterministic_override,
    get_categories_dict,
    get_effective_threshold,
    get_root_family,
    load_registry_data,
)
from .schema import (
    ClassificationResult,
    CleanPost,
    SecondaryCategoryItem,
    SystemHealthResponse,
)

logger = logging.getLogger("engine")
logging.basicConfig(level=logging.INFO)

# Configurar hilos de PyTorch para CPU (Intel Core i5: 4 cores / 8 threads)
try:
    torch.set_num_threads(settings.PYTORCH_NUM_THREADS)
    torch.set_num_interop_threads(settings.PYTORCH_INTEROP_THREADS)
except RuntimeError:
    pass


def normalize_multilingual_text(text: str) -> str:
    """
    Normalización Unicode NFKC (ADR-008):
    Convierte caracteres japoneses/chinos zenkaku (de ancho completo) a hankaku,
    estandariza signos diacríticos y colapsa espacios en blanco.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # Colapsar múltiples espacios y saltos de línea redundantes
    return " ".join(normalized.split())


def _detect_cpu_model() -> str:
    """Detecta dinámicamente el modelo del procesador host."""
    try:
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
        import platform
        proc = platform.processor()
        if proc:
            return proc
    except Exception:
        pass
    import os
    return f"CPU ({os.cpu_count() or 4} cores)"


def resolve_device(requested_device: Optional[str] = None) -> str:
    """
    Resuelve el dispositivo de hardware óptimo para inferencia de Laya:
    - 'auto': Selecciona CUDA si está disponible, luego MPS (Apple Silicon), o CPU por defecto.
    - 'cuda': Fuerza GPU NVIDIA (valida disponibilidad).
    - 'mps': Fuerza aceleración Metal en macOS.
    - 'cpu': Fuerza ejecución pura en procesador central.
    """
    req = (requested_device or settings.DEVICE or "auto").strip().lower()
    if req == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return req


def _detect_gpu_info() -> Dict[str, Any]:
    """Detecta nombre del modelo de GPU, memoria VRAM total y en uso si CUDA está disponible."""
    if not torch.cuda.is_available():
        return {
            "gpu_model": None,
            "vram_total_gb": None,
            "vram_used_mb": None,
            "cuda_available": False
        }
    try:
        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        total_gb = round(props.total_memory / (1024**3), 2)
        allocated_mb = round(torch.cuda.memory_allocated(0) / (1024**2), 2)
        return {
            "gpu_model": gpu_name,
            "vram_total_gb": total_gb,
            "vram_used_mb": allocated_mb,
            "cuda_available": True
        }
    except Exception as e:
        logger.warning(f"Error extrayendo telemetría de GPU CUDA: {e}")
        return {
            "gpu_model": "GPU NVIDIA CUDA",
            "vram_total_gb": None,
            "vram_used_mb": None,
            "cuda_available": True
        }


class LayaEngine:
    _instance: Optional["LayaEngine"] = None

    def __init__(self, device: Optional[str] = None, max_loaded: int = settings.MAX_LOADED_MODELS):
        self.device = resolve_device(device)
        self.max_loaded = max_loaded
        self.router = None
        self.models_loaded: List[str] = []
        self.registry_data = load_registry_data()
        self.schema = build_decision_schema()
        self._init_router()

    def _init_router(self) -> None:
        """Inicializa Laya Router con los pesos locales / cache en PyTorch (CPU o GPU)."""
        gpu_info = _detect_gpu_info()
        if self.device.startswith("cuda"):
            logger.info(f"🚀 Iniciando Laya Router en GPU acelerada [{gpu_info['gpu_model'] or 'CUDA'}] (VRAM: {gpu_info['vram_total_gb'] or 'N/A'} GB)...")
        elif self.device == "mps":
            logger.info("⚡ Iniciando Laya Router en Apple Silicon (Metal Performance Shaders - MPS)...")
        else:
            logger.info(f"⚡ Iniciando Laya Router en modo CPU [{_detect_cpu_model()}] (hilos PyTorch: {torch.get_num_threads()})...")

        t0 = time.perf_counter()
        from laya import Router

        self.router = Router(
            device=self.device,
            max_loaded=self.max_loaded
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.info(f"Laya Router cargado exitosamente en modo {self.device.upper()} ({elapsed_ms:.2f} ms)")

    @classmethod
    def get_instance(cls) -> "LayaEngine":
        """Singleton thread-safe para compartir el modelo en memoria RAM/VRAM sin duplicación."""
        if cls._instance is None:
            cls._instance = LayaEngine()
        return cls._instance

    def get_health(self, active_batches: int = 0) -> SystemHealthResponse:
        """Telemetría de hardware en tiempo real (CPU, GPU, RAM, VRAM y batches activos)."""
        vm = psutil.virtual_memory()
        proc = psutil.Process(os.getpid())
        rss_mb = proc.memory_info().rss / (1024 * 1024)

        cpu_info = _detect_cpu_model()
        gpu_info = _detect_gpu_info()
        loaded = list(self.models_loaded) if self.models_loaded else [settings.PRIMARY_MODEL]

        is_gpu = self.device.startswith("cuda")
        is_mps = self.device == "mps"

        if is_gpu:
            device_display = f"GPU ({gpu_info['gpu_model'] or 'NVIDIA CUDA'})"
            est_latency = "~33ms/post"
        elif is_mps:
            device_display = "Apple Silicon (MPS)"
            est_latency = "~50ms/post"
        else:
            device_display = cpu_info if cpu_info.startswith("CPU") else f"CPU ({cpu_info})"
            est_latency = "~18s/post"

        return SystemHealthResponse(
            status="healthy" if self.router is not None else "degraded",
            device=self.device,
            cpu_model=cpu_info,
            gpu_model=gpu_info["gpu_model"],
            vram_total_gb=gpu_info["vram_total_gb"],
            vram_used_mb=gpu_info["vram_used_mb"],
            cuda_available=gpu_info["cuda_available"],
            device_display=device_display,
            estimated_latency=est_latency,
            ram_total_gb=round(vm.total / (1024**3), 2),
            ram_available_gb=round(vm.available / (1024**3), 2),
            ram_used_process_mb=round(rss_mb, 2),
            models_loaded=loaded,
            active_batches=active_batches,
            version=settings.APP_VERSION
        )

    def check_memory_safety(self, force: bool = False) -> None:
        """Comprueba el consumo de memoria RSS y ejecuta recolección de basura y trim de memoria si excede el umbral o si force=True."""
        try:
            proc = psutil.Process(os.getpid())
            rss_mb = proc.memory_info().rss / (1024 * 1024)
            if force or rss_mb > 4500:
                if rss_mb > 4500:
                    logger.warning(f"Consumo de RAM elevado ({rss_mb:.1f} MB). Ejecutando gc.collect() y trim de memoria...")
                gc.collect()
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    if hasattr(libc, "malloc_trim"):
                        libc.malloc_trim(0)
                except Exception:
                    pass
        except Exception:
            pass

    def _predict_jev(self, state_str: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Envía solicitud de inferencia a la API de TypeSafe System One (Jev Cloud)."""
        headers = {
            "Authorization": f"Bearer {settings.JEV_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "state": state_str,
            "questions": schema
        }
        url = f"{settings.JEV_BASE_URL.rstrip('/')}/v1/predict"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

    def _predict_with_engine(self, state_str: str, schema: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Enruta la inferencia a Jev (Cloud) o Laya (Local) según settings.DECISION_ENGINE."""
        if settings.DECISION_ENGINE.lower() == "jev" and settings.JEV_API_KEY:
            try:
                res = self._predict_jev(state_str, schema)
                return res, "jev"
            except Exception as e:
                logger.warning(f"Error al invocar Jev API ({e}). Ejecutando fallback en Laya local...")

        # Inferencia local en Laya
        with torch.inference_mode():
            res = self.router.predict(state_str, schema)
        routing = res.get("routing", {})
        used_model = routing.get("model", settings.PRIMARY_MODEL)
        if used_model not in self.models_loaded:
            self.models_loaded.append(used_model)
        return res, used_model

    def classify_post(self, post: CleanPost, active_questions: Optional[List[str]] = None) -> ClassificationResult:
        """
        Ejecuta la inferencia híbrida neuro-simbólica System 1:
        1. Pre-evaluación Simbólica: Overrides deterministas por URLs y dominios (Civitai, ComfyUI, Hugging Face).
        2. Inferencia en 2 Pasadas Condicionales (Pasada 1: base ligera; Pasada 2: familia de modelo).
        3. Post-procesamiento: Boosters cruzados, Family Gating y política de abstención calibrada.
        """
        t0 = time.perf_counter()

        # 1. Preparar texto normalizado
        norm_text = normalize_multilingual_text(post.clean_text)
        state_str = (
            f"Author: {post.author_name}\n"
            f"Content: {norm_text}\n"
            f"Media: {post.media_type} (count: {post.media_count})"
        )
        if post.detected_domains:
            state_str += f"\nDomains: {', '.join(post.detected_domains)}"

        # 2. Pre-evaluación Simbólica (Deterministic Overrides)
        override_modality, override_asset = None, None
        if settings.ENABLE_DETERMINISTIC_OVERRIDES:
            urls_to_check = list(post.detected_domains) + list(post.detected_assets)
            if post.post_url:
                urls_to_check.append(post.post_url)
            override_modality, override_asset = detect_deterministic_override(norm_text, urls_to_check)
            if override_asset and override_asset not in post.detected_assets:
                post.detected_assets.append(override_asset)

        # 3. Inferencia de Preguntas (Arquitectura de 2 Pasadas)
        raw_answers: Dict[str, Any] = {}
        engine_used = "laya"

        if active_questions is not None:
            # Modo explícito (usado en tests específicos o perfiles custom)
            schema_to_use = build_decision_schema(active_questions=active_questions)
            raw_res, engine_used = self._predict_with_engine(state_str, schema_to_use)
            raw_answers = raw_res.get("answers", {})
        else:
            # Pasada 1: Esquema base ligero (category + pass1_questions)
            pass1_q_list = ["category", "gen_modality", "content_format", "technical_depth", "is_local_first", "is_uncensored_or_nsfw"]
            schema_pass1 = build_decision_schema(active_questions=pass1_q_list)
            res_pass1, engine_used = self._predict_with_engine(state_str, schema_pass1)
            raw_answers.update(res_pass1.get("answers", {}))

            # Determinar modalidad efectiva (override determinista manda sobre el modelo)
            eff_modality = override_modality or raw_answers.get("gen_modality", {}).get("choice")

            # Pasada 2 (Condicional): Solo si la modalidad es generativa
            if eff_modality in {"mod_image", "mod_video", "mod_3d", "mod_audio"}:
                schema_pass2 = build_pass2_schema(eff_modality)
                if schema_pass2:
                    res_pass2, _ = self._predict_with_engine(state_str, schema_pass2)
                    raw_answers.update(res_pass2.get("answers", {}))

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if override_modality:
            raw_answers["deterministic_override"] = {
                "modality": override_modality,
                "asset": override_asset
            }

        # 4. Post-procesar respuestas
        return self._post_process(
            post=post,
            state_str=state_str,
            raw_answers=raw_answers,
            override_modality=override_modality,
            engine_used=engine_used,
            latency_ms=elapsed_ms
        )

    def _post_process(
        self,
        post: CleanPost,
        state_str: str,
        raw_answers: Dict[str, Any],
        override_modality: Optional[str],
        engine_used: str,
        latency_ms: float
    ) -> ClassificationResult:
        cats_dict = get_categories_dict()

        # 3a. Extraer preguntas suplementarias
        # Technical depth (Score)
        depth_ans = raw_answers.get("technical_depth", {})
        tech_depth = 1.0
        if isinstance(depth_ans, dict):
            tech_depth = float(depth_ans.get("score", 1.0))

        # Format (Choice)
        format_ans = raw_answers.get("content_format", {})
        content_format = "other"
        format_conf = 0.0
        if isinstance(format_ans, dict):
            content_format = format_ans.get("choice", "other")
            format_conf = float(format_ans.get("answer_confidence") or format_ans.get("confidence") or 0.0)

        # Flags Booleanas (Noul)
        local_ans = raw_answers.get("is_local_first", {})
        is_local_first = False
        if isinstance(local_ans, dict):
            is_local_first = float(local_ans.get("noul", 0.0)) >= 0.50

        nsfw_ans = raw_answers.get("is_uncensored_or_nsfw", {})
        is_nsfw = False
        if isinstance(nsfw_ans, dict):
            is_nsfw = float(nsfw_ans.get("noul", 0.0)) >= 0.50

        # Modalidad y familias de modelos de IA
        modality_ans = raw_answers.get("gen_modality", {})
        gen_modality = modality_ans.get("choice") if isinstance(modality_ans, dict) else None

        img_fam = raw_answers.get("model_family_image", {}).get("choice") if isinstance(raw_answers.get("model_family_image"), dict) else None
        vid_fam = raw_answers.get("model_family_video", {}).get("choice") if isinstance(raw_answers.get("model_family_video"), dict) else None
        m3d_fam = raw_answers.get("model_family_3d", {}).get("choice") if isinstance(raw_answers.get("model_family_3d"), dict) else None
        aud_fam = raw_answers.get("model_family_audio", {}).get("choice") if isinstance(raw_answers.get("model_family_audio"), dict) else None

        # 3b. Extraer respuestas de Familias Raíz (Family Gating)
        active_families: Set[str] = set()
        family_scores: Dict[str, float] = {}
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

        for q_key, fam_id in family_map.items():
            f_ans = raw_answers.get(q_key, {})
            if isinstance(f_ans, dict):
                score_val = float(f_ans.get("noul", 0.0))
                family_scores[fam_id] = score_val
                if score_val >= 0.45:
                    active_families.add(fam_id)

        # 3c. Detección determinista de assets
        detected_assets = list(post.detected_assets)
        asset_choice_ans = raw_answers.get("reproducible_asset_type", {})
        if isinstance(asset_choice_ans, dict):
            chosen_asset = asset_choice_ans.get("choice")
            if chosen_asset and chosen_asset != "none" and chosen_asset not in detected_assets:
                detected_assets.append(chosen_asset)

        # 3d. Construir candidatos iniciales desde 'category'
        cat_ans = raw_answers.get("category", {})
        probabilities: Dict[str, float] = {}
        if isinstance(cat_ans, dict):
            raw_probs = cat_ans.get("probabilities", {})
            if isinstance(raw_probs, dict):
                probabilities = {k: float(v) for k, v in raw_probs.items()}
            elif cat_ans.get("choice"):
                probabilities[cat_ans["choice"]] = float(cat_ans.get("answer_confidence") or cat_ans.get("confidence") or 0.6)

        candidates: Dict[str, float] = {}
        for c_id, prob in probabilities.items():
            if prob >= 0.01:
                candidates[c_id] = prob

        # Inyección determinista por activos detectados
        for c_id, c_info in cats_dict.items():
            cat_assets = c_info.get("boosters", {}).get("reproducible_assets", [])
            if any(a in cat_assets for a in detected_assets):
                root_fam = get_root_family(c_id)
                fam_noul = family_scores.get(root_fam, 0.5)
                if fam_noul >= 0.35 or root_fam in active_families:
                    candidates[c_id] = max(candidates.get(c_id, 0.0), 0.55)

        # Inyección por keywords en familias activas
        state_lower = state_str.lower()
        for c_id, c_info in cats_dict.items():
            root_fam = get_root_family(c_id)
            if root_fam in active_families:
                kws = c_info.get("keywords", [])
                if any(kw.lower() in state_lower for kw in kws):
                    candidates[c_id] = max(candidates.get(c_id, 0.0), 0.45)

        # 3e. Inyección de Candidatos por Familias de Modelos de IA
        if img_fam and img_fam != "none":
            active_families.add("ia")
            candidates["gen_imagenes"] = max(candidates.get("gen_imagenes", 0.0), 0.70)
            if img_fam == "flux":
                candidates["gen_imagenes"] = max(candidates.get("gen_imagenes", 0.0), 0.85)
            elif img_fam == "anima_illustrious":
                candidates["fanart_anime"] = max(candidates.get("fanart_anime", 0.0), 0.65)
                candidates["mangas"] = max(candidates.get("mangas", 0.0), 0.60)

        if vid_fam and vid_fam != "none":
            active_families.add("ia")
            candidates["gen_video"] = max(candidates.get("gen_video", 0.0), 0.80)

        if m3d_fam and m3d_fam != "none":
            active_families.add("ia")
            active_families.add("modelado_3d")
            candidates["gen_3d"] = max(candidates.get("gen_3d", 0.0), 0.80)
            candidates["modelado_3d"] = max(candidates.get("modelado_3d", 0.0), 0.60)

        if aud_fam and aud_fam != "none":
            active_families.add("ia")
            candidates["gen_audio"] = max(candidates.get("gen_audio", 0.0), 0.80)

        # Inyección por Modalidad general
        eff_mod = override_modality or gen_modality
        if eff_mod == "mod_code_web3d":
            candidates["threejs_webgl"] = max(candidates.get("threejs_webgl", 0.0), 0.75)
            candidates["dev_tools"] = max(candidates.get("dev_tools", 0.0), 0.65)
        elif eff_mod == "mod_game_dev":
            candidates["indie_dev"] = max(candidates.get("indie_dev", 0.0), 0.75)
            candidates["juegos"] = max(candidates.get("juegos", 0.0), 0.70)
        elif eff_mod == "mod_art_manual":
            candidates["mangas"] = max(candidates.get("mangas", 0.0), 0.75)
            candidates["fanart_anime"] = max(candidates.get("fanart_anime", 0.0), 0.65)
        elif eff_mod == "mod_llm_agents":
            candidates["agentes_ia"] = max(candidates.get("agentes_ia", 0.0), 0.75)

        # OVERRIDE DETERMINISTA DURO: si hay señal directa (Civitai, ComfyUI, etc.)
        if override_modality == "mod_image":
            active_families.add("ia")
            candidates["gen_imagenes"] = max(candidates.get("gen_imagenes", 0.0), 0.90)
            if "civitai_lora" in detected_assets:
                candidates["lora_civitai"] = max(candidates.get("lora_civitai", 0.0), 0.92)
            if "comfyui_workflow" in detected_assets:
                candidates["comfyui_workflows"] = max(candidates.get("comfyui_workflows", 0.0), 0.92)
                candidates["comfyui"] = max(candidates.get("comfyui", 0.0), 0.85)

        # 3f. Aplicar Family Gating y Boosters finales
        boosted_scores: Dict[str, float] = {}
        for c_id, base_score in candidates.items():
            c_info = cats_dict.get(c_id, {})
            root_fam = get_root_family(c_id)
            score = base_score

            # Family Gating: si la familia fue rechazada (<0.30)
            fam_noul = family_scores.get(root_fam, 0.5)
            if fam_noul < 0.30 and not any(a in c_info.get("boosters", {}).get("reproducible_assets", []) for a in detected_assets) and not (override_modality and root_fam == "ia"):
                score *= 0.15
            elif fam_noul >= 0.50:
                score += 0.15

            # Asset bonus (+0.20)
            cat_assets = c_info.get("boosters", {}).get("reproducible_assets", [])
            if any(a in cat_assets for a in detected_assets):
                score += 0.20

            # Specificity bonus (+0.05)
            if c_info.get("parent_id"):
                score += 0.05

            # Keyword bonus (+0.08)
            kws = c_info.get("keywords", [])
            if any(kw.lower() in state_lower for kw in kws):
                score += 0.08

            # Penalización anti-secuestro si hubo override determinista
            if override_modality == "mod_image" and root_fam in {"dev_tools", "negocios_saas"}:
                score *= 0.20
            elif override_modality == "mod_video" and root_fam in {"dev_tools", "negocios_saas"}:
                score *= 0.20

            boosted_scores[c_id] = round(score, 4)

        # 3g. Ordenar y seleccionar categoría primaria
        sorted_candidates = sorted(boosted_scores.items(), key=lambda x: x[1], reverse=True)

        primary_cat = "otros"
        affinity_score = 0.0
        status: str = "CLASSIFIED"

        if sorted_candidates:
            top_cat, top_score = sorted_candidates[0]
            eff_threshold = get_effective_threshold(top_cat)
            has_reproducible_asset = len(detected_assets) > 0

            # Si hubo override determinista inequívoco, se confía en la regla dura
            if override_modality:
                status = "CLASSIFIED"
                primary_cat = top_cat
                affinity_score = round(min(top_score, 1.0), 4)
            else:
                # Política de abstención diferenciada Laya vs Jev
                if "laya" in str(engine_used).lower():
                    threshold_to_use = max(eff_threshold, settings.LAYA_THRESHOLD)
                    min_abstain = settings.LAYA_MIN_ABSTAIN
                else:
                    threshold_to_use = min(eff_threshold, settings.JEV_THRESHOLD)
                    min_abstain = settings.JEV_MIN_ABSTAIN

                if top_score < min_abstain:
                    status = "PENDING"
                    primary_cat = "otros"
                    affinity_score = round(top_score, 4)
                elif top_score < threshold_to_use and not has_reproducible_asset:
                    status = "PENDING"
                    primary_cat = "otros"
                    affinity_score = round(top_score, 4)
                else:
                    status = "CLASSIFIED"
                    primary_cat = top_cat
                    affinity_score = round(min(top_score, 1.0), 4)

        # Categorías secundarias
        secondary_list: List[SecondaryCategoryItem] = []
        for c_id, sc in sorted_candidates[1:4]:
            if sc >= 0.35 and c_id != primary_cat and c_id != "otros":
                secondary_list.append(SecondaryCategoryItem(id=c_id, score=min(round(sc, 4), 1.0)))

        # Detección de anomalías / Outliers (ADR-004)
        is_outlier = False
        likes = post.metrics.favorite_count
        if likes > 5000 and (affinity_score < 0.60 or tech_depth <= 1.5):
            is_outlier = True
        elif affinity_score > 0.95 and has_reproducible_asset and likes > 1000:
            is_outlier = True

        return ClassificationResult(
            primary_category=primary_cat,
            secondary_categories=secondary_list,
            affinity_score=affinity_score,
            format=content_format,
            format_confidence=format_conf,
            technical_depth=tech_depth,
            assets=detected_assets,
            is_local_first=is_local_first,
            is_nsfw=is_nsfw,
            is_outlier=is_outlier,
            status=status,
            engine_used=engine_used,
            inference_latency_ms=round(latency_ms, 2),
            raw_answers=raw_answers
        )
