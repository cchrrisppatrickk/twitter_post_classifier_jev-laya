#!/usr/bin/env python3
"""
build_frontend.py - Compilador Offline de Plantillas Frontend (Subfase 5.11)
Compila la arquitectura modular Jinja2 de:
1. `frontend/index.html` (Dashboard Waffle)
2. `frontend/config.html` (JEV Registry Studio v2.1.0)
Genera artefactos autónomos optimizados en `frontend/dist/` y sincroniza recursivamente
todos los submódulos JavaScript (`config/`, `modals/`, `core/`) y hojas de estilo CSS.
"""

import sys
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def build():
    root_dir = Path(__file__).resolve().parent.parent
    frontend_dir = root_dir / "frontend"
    dist_dir = frontend_dir / "dist"
    
    print(f"[*] Compilando frontend modular desde: {frontend_dir}")
    
    if not (frontend_dir / "index.html").exists():
        print(f"[!] Error: No se encontró {frontend_dir / 'index.html'}")
        sys.exit(1)
        
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Configurar entorno Jinja2
    env = Environment(
        loader=FileSystemLoader(str(frontend_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # 1. Compilar index.html
    template_index = env.get_template("index.html")
    rendered_index = template_index.render(request=None)
    output_index = dist_dir / "index.html"
    with open(output_index, "w", encoding="utf-8") as f:
        f.write(rendered_index)
    print(f"[+] Artefacto Dashboard generado: {output_index} ({output_index.stat().st_size:,} bytes)")
    
    # 2. Compilar config.html (Registry Studio) si existe
    config_src = frontend_dir / "config.html"
    if config_src.exists():
        template_config = env.get_template("config.html")
        rendered_config = template_config.render(request=None)
        output_config = dist_dir / "config.html"
        with open(output_config, "w", encoding="utf-8") as f:
            f.write(rendered_config)
        print(f"[+] Artefacto Registry Studio generado: {output_config} ({output_config.stat().st_size:,} bytes)")
    
    # 3. Sincronizar recursivamente directorios estáticos css y js a dist/
    for folder in ["css", "js"]:
        src = frontend_dir / folder
        dst = dist_dir / folder
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            # Contar archivos copiados
            file_count = sum(1 for p in dst.rglob('*') if p.is_file())
            print(f"[+] Sincronizado recursivo: {folder}/ -> dist/{folder}/ ({file_count} archivos)")

    print("[✓] Compilación frontend y sincronización modular completada con éxito.")

if __name__ == "__main__":
    build()
