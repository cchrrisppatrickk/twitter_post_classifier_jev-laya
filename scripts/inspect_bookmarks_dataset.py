#!/usr/bin/env python3
"""
inspect_bookmarks_dataset.py - Auditoría Forense y Normalización del Dataset de Bookmarks
Fase 6.1: Validación estructural previa a la ingesta masiva y perfilado de hardware.
"""

from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.schema import CleanPost, RawPost
from app.services.ingest_service import IngestService, convert_raw_to_clean, normalize_raw_item

DEFAULT_DATASET_PATH = Path(
    "/home/patricklinux/Dev/GEMINI-ANTIGRAVITY APPS/automations/output_files/twitter/extracted_links/"
    "extracted_data_https___x_com_i_bookmarks_bookmarks_20261013_101533.json"
)


def inspect_dataset(file_path: Path):
    print("=" * 76)
    print("🔍 INSPECCIÓN FORENSE Y VALIDACIÓN ESTRUCTURAL DE DATASET (Fase 6.1)")
    print(f"📂 Archivo objetivo: {file_path}")
    print(f"📦 Tamaño en disco: {file_path.stat().st_size / (1024*1024):.2f} MB")
    print("=" * 76)

    t0 = time.perf_counter()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        raw_posts = data.get("posts", [])
        metadata = data.get("metadata", {})
    elif isinstance(data, list):
        raw_posts = data
        metadata = {}
    else:
        print("❌ Error: Estructura JSON desconocida (ni dict ni list).")
        return

    total_records = len(raw_posts)
    print(f"\n[1] METADATOS Y TOTALES:")
    print(f"  • Total de publicaciones en array: {total_records:,}")
    print(f"  • Metadatos extraídos: {metadata}")

    # 1. Unicidad de Tweet IDs
    tweet_ids = [str(p.get("tweet_id", "")) for p in raw_posts if p.get("tweet_id")]
    unique_ids = set(tweet_ids)
    duplicates_count = total_records - len(unique_ids)

    print(f"\n[2] UNICIDAD DE IDENTIFICADORES (tweet_id):")
    print(f"  • Tweet IDs únicos: {len(unique_ids):,}")
    print(f"  • Duplicados internos en JSON: {duplicates_count:,}")
    if duplicates_count > 0:
        dupe_counter = Counter(tweet_ids)
        top_dupes = [k for k, v in dupe_counter.items() if v > 1][:5]
        print(f"  • Muestra de IDs duplicados: {top_dupes}")

    # 2. Análisis de Atributos y Métricas
    languages = Counter()
    media_types = Counter()
    has_video = 0
    has_github = 0
    has_huggingface = 0
    has_civitai = 0
    has_comfy = 0
    text_lengths = []
    likes_list = []
    bookmarks_list = []
    empty_or_whitespace_texts = 0
    authors = Counter()

    for p in raw_posts:
        content = p.get("content") or p.get("text") or ""
        clean_stripped = content.strip()
        if not clean_stripped:
            empty_or_whitespace_texts += 1
        text_lengths.append(len(content))

        # Idioma
        lang = p.get("lang") or "unknown"
        languages[lang] += 1

        # Autor
        author_data = p.get("author", {})
        author_name = (
            author_data.get("name")
            if isinstance(author_data, dict)
            else str(author_data)
        ) or "anon"
        authors[author_name] += 1

        # Métricas
        metrics = p.get("metrics", {})
        if isinstance(metrics, dict):
            likes = metrics.get("favorite_count", 0) or 0
            bmarks = metrics.get("bookmark_count", 0) or 0
        else:
            likes = p.get("likes", 0) or 0
            bmarks = p.get("bookmarks", 0) or 0
        likes_list.append(int(likes))
        bookmarks_list.append(int(bmarks))

        # Media
        m_urls = p.get("media_urls", []) or []
        m_type = p.get("category") or ("video" if any(".mp4" in u for u in m_urls) else ("image" if m_urls else "none"))
        media_types[m_type] += 1
        if any(".mp4" in u for u in m_urls):
            has_video += 1

        # Detección preliminar de activos en texto
        lower_c = content.lower()
        if "github.com/" in lower_c:
            has_github += 1
        if "huggingface.co/" in lower_c or "hf.co/" in lower_c:
            has_huggingface += 1
        if "civitai.com/" in lower_c:
            has_civitai += 1
        if "comfy" in lower_c or "workflow" in lower_c:
            has_comfy += 1

    print(f"\n[3] DISTRIBUCIÓN LINGÜÍSTICA Y AUTORÍA:")
    print(f"  • Top idiomas: {languages.most_common(5)}")
    print(f"  • Autores únicos: {len(authors):,}")
    print(f"  • Top 5 creadores más guardados: {authors.most_common(5)}")

    print(f"\n[4] MÉTRICAS DE ENGAGEMENT Y CONTENIDO:")
    avg_likes = sum(likes_list) / max(len(likes_list), 1)
    max_likes = max(likes_list) if likes_list else 0
    avg_bmarks = sum(bookmarks_list) / max(len(bookmarks_list), 1)
    max_bmarks = max(bookmarks_list) if bookmarks_list else 0
    avg_len = sum(text_lengths) / max(len(text_lengths), 1)
    max_len = max(text_lengths) if text_lengths else 0
    min_len = min(text_lengths) if text_lengths else 0

    print(f"  • Likes promedio: {avg_likes:.1f} (Máximo: {max_likes:,})")
    print(f"  • Bookmarks promedio: {avg_bmarks:.1f} (Máximo: {max_bmarks:,})")
    print(f"  • Longitud media de texto: {avg_len:.1f} caracteres (Rango: {min_len} a {max_len})")
    print(f"  • Textos vacíos / solo espacios: {empty_or_whitespace_texts}")

    print(f"\n[5] MULTIMEDIA Y ACTIVOS REPRODUCIBLES:")
    print(f"  • Tipos de medios: {dict(media_types)}")
    print(f"  • Publicaciones con Video MP4: {has_video:,}")
    print(f"  • Enlaces GitHub detectados: {has_github:,}")
    print(f"  • Enlaces HuggingFace detectados: {has_huggingface:,}")
    print(f"  • Enlaces CivitAI detectados: {has_civitai:,}")
    print(f"  • Menciones ComfyUI / Workflows: {has_comfy:,}")

    # 3. Test de Paso por IngestService y Validación Pydantic
    print(f"\n[6] PRUEBA DE NORMALIZACIÓN Y VALIDACIÓN PYDANTIC (IngestService):")
    conv_success = 0
    conv_errors = []

    for idx, raw_item in enumerate(raw_posts):
        try:
            raw_post: RawPost = normalize_raw_item(raw_item)
            if raw_post is None:
                raise ValueError("normalize_raw_item returned None (faltaba tweet_id u otro dato crítico)")
            clean_post: CleanPost = convert_raw_to_clean(raw_post)
            # Asegurar que los campos clave están poblados
            assert clean_post.tweet_id, "Falta tweet_id"
            assert clean_post.clean_text is not None, "clean_text es None"
            conv_success += 1
        except Exception as e:
            conv_errors.append((idx, raw_item.get("tweet_id", f"idx_{idx}"), str(e)))

    if not conv_errors:
        print(f"  ✓ 100% de éxito: {conv_success:,} / {total_records:,} publicaciones normalizadas a CleanPost sin errores.")
    else:
        print(f"  ❌ Errores de normalización ({len(conv_errors)}):")
        for err_idx, tid, msg in conv_errors[:5]:
            print(f"    - Post #{err_idx} (ID: {tid}): {msg}")

    elapsed = time.perf_counter() - t0
    print(f"\n⏱️ Auditoría forense completada en {elapsed:.2f} segundos.")
    print("=" * 76)


if __name__ == "__main__":
    target = DEFAULT_DATASET_PATH
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    if not target.exists():
        print(f"❌ Error: El archivo {target} no existe.")
        sys.exit(1)
    inspect_dataset(target)
