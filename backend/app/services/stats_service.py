"""
stats_service.py - Agregador de Estadísticas para la Waffle Grid y Cuadrante Scatter Canvas 2D.
Compila conteos, afinidades, promedios de virality y puntos de dispersión
basados en la taxonomía v2.1.0 (47 categorías en 8 familias).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional
import aiosqlite

from ..registry import get_categories_dict, get_root_family, load_registry_data
from ..schema import (
    CategoryDistributionItem,
    DashboardStatsResponse,
    FamilyDistributionItem,
    ScatterPoint,
)

logger = logging.getLogger("stats_service")
logging.basicConfig(level=logging.INFO)

# Paleta cromática por defecto para las 8 familias raíz
FAMILY_INFO: Dict[str, Dict[str, str]] = {
    "ia": {"name": "Inteligencia Artificial", "color_hex": "#8b5cf6"},
    "blender": {"name": "Blender 3D", "color_hex": "#ea580c"},
    "modelado_3d": {"name": "Gráficos & Modelado 3D", "color_hex": "#0284c7"},
    "juegos": {"name": "Desarrollo de Videojuegos", "color_hex": "#10b981"},
    "dev_tools": {"name": "Herramientas Dev & Código", "color_hex": "#f59e0b"},
    "mangas": {"name": "Manga, Anime & Ilustración", "color_hex": "#ec4899"},
    "negocios_saas": {"name": "Negocios, SaaS & MRR", "color_hex": "#059669"},
    "otros": {"name": "Otros & Vida Cotidiana", "color_hex": "#6b7280"},
}


class StatsService:
    @staticmethod
    async def get_dashboard_stats(db: aiosqlite.Connection) -> DashboardStatsResponse:
        """Calcula todas las métricas agregadas necesarias para el renderizado del dashboard."""
        cats_dict = get_categories_dict()
        reg_data = load_registry_data()

        # 1. Resumen global de métricas
        summary_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('CLASSIFIED', 'CLASSIFIED_MANUAL') THEN 1 ELSE 0 END) as classified,
            SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN is_outlier = 1 THEN 1 ELSE 0 END) as outliers,
            COALESCE(AVG(affinity_score), 0.0) as avg_affinity,
            COALESCE(AVG(favorite_count), 0.0) as avg_likes
        FROM posts;
        """
        async with db.execute(summary_query) as cursor:
            row = await cursor.fetchone()
            total_posts = int(row["total"] or 0)
            classified_count = int(row["classified"] or 0)
            pending_count = int(row["pending"] or 0)
            outliers_count = int(row["outliers"] or 0)
            avg_affinity = round(float(row["avg_affinity"] or 0.0), 3)
            avg_likes = round(float(row["avg_likes"] or 0.0), 1)

        # 2. Distribución de categorías en BD
        cat_stats_query = """
        SELECT
            primary_category,
            COUNT(*) as count,
            COALESCE(AVG(affinity_score), 0.0) as avg_score,
            COALESCE(AVG(favorite_count), 0.0) as avg_likes
        FROM posts
        GROUP BY primary_category;
        """
        cat_counts: Dict[str, Dict[str, Any]] = {}
        async with db.execute(cat_stats_query) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                c_id = r["primary_category"]
                cat_counts[c_id] = {
                    "count": int(r["count"]),
                    "avg_score": round(float(r["avg_score"]), 3),
                    "avg_likes": int(r["avg_likes"])
                }

        # 3. Compilar todas las 47 categorías con su metadata
        categories_dist: List[CategoryDistributionItem] = []
        family_counts: Dict[str, int] = {f_id: 0 for f_id in FAMILY_INFO.keys()}

        for c_id, c_info in cats_dict.items():
            if not c_info.get("active", True):
                continue
            root_fam = get_root_family(c_id)
            stats = cat_counts.get(c_id, {"count": 0, "avg_score": 0.0, "avg_likes": 0})
            cnt = stats["count"]

            if root_fam in family_counts:
                family_counts[root_fam] += cnt
            else:
                family_counts["otros"] += cnt

            color = c_info.get("color_hex") or FAMILY_INFO.get(root_fam, {}).get("color_hex", "#6b7280")
            categories_dist.append(CategoryDistributionItem(
                id=c_id,
                name=c_info.get("label", c_id),
                family_id=root_fam,
                color_hex=color,
                count=cnt,
                avg_score=stats["avg_score"],
                avg_likes=stats["avg_likes"]
            ))

        # 4. Compilar distribución de familias raíz
        families_dist: List[FamilyDistributionItem] = []
        for fam_id, f_data in FAMILY_INFO.items():
            families_dist.append(FamilyDistributionItem(
                id=fam_id,
                name=f_data["name"],
                color_hex=f_data["color_hex"],
                count=family_counts.get(fam_id, 0)
            ))

        # 5. Extraer puntos para el Cuadrante Scatter Canvas 2D
        scatter_query = """
        SELECT
            tweet_id,
            affinity_score,
            favorite_count,
            primary_category,
            secondary_categories,
            is_outlier,
            author_name,
            date
        FROM posts
        ORDER BY date DESC
        LIMIT 1500;
        """
        scatter_points: List[ScatterPoint] = []
        async with db.execute(scatter_query) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                sec_cat = None
                sec_raw = r["secondary_categories"]
                if sec_raw:
                    try:
                        secs = json.loads(sec_raw) if isinstance(sec_raw, str) else sec_raw
                        if secs and isinstance(secs, list) and len(secs) > 0:
                            first_sec = secs[0]
                            sec_cat = first_sec.get("id") if isinstance(first_sec, dict) else str(first_sec)
                    except Exception:
                        pass

                scatter_points.append(ScatterPoint(
                    id=r["tweet_id"],
                    x=round(float(r["affinity_score"] or 0.0) * 100.0, 1),
                    y=int(r["favorite_count"] or 0),
                    primary=r["primary_category"],
                    secondary=sec_cat,
                    outlier=bool(r["is_outlier"]),
                    author=r["author_name"],
                    date=r["date"]
                ))

        return DashboardStatsResponse(
            total_posts=total_posts,
            classified_count=classified_count,
            pending_count=pending_count,
            outliers_count=outliers_count,
            avg_affinity_score=avg_affinity,
            avg_likes=avg_likes,
            categories_distribution=categories_dist,
            families_distribution=families_dist,
            scatter_points=scatter_points
        )
