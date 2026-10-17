#!/usr/bin/env bash
# ==============================================================================
# stop_app.sh - Detiene Twitter Post Classifier Master de forma limpia
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/server.pid"
PORT=8000

STOPPED=false

# 1. Intentar detener mediante PID_FILE
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        echo "🛑 Deteniendo Twitter Post Classifier Master (PID: $PID)..."
        kill -15 "$PID" 2>/dev/null || true
        
        # Esperar hasta 8 segundos para cierre ordenado de SQLite WAL
        for i in {1..8}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                STOPPED=true
                break
            fi
            sleep 1
        done

        if ! $STOPPED; then
            echo "⚠️  El proceso no respondió a SIGTERM. Forzando detención (SIGKILL)..."
            kill -9 "$PID" 2>/dev/null || true
            sleep 1
            STOPPED=true
        fi
    fi
    rm -f "$PID_FILE"
fi

# 2. Verificar si aún queda algún proceso escuchando en el puerto 8000
PORT_PID=$(lsof -ti :$PORT 2>/dev/null || fuser $PORT/tcp 2>/dev/null || true)
if [[ -n "$PORT_PID" ]]; then
    echo "⚠️  Limpiando procesos en puerto $PORT..."
    echo "$PORT_PID" | xargs -r kill -15 2>/dev/null || true
    sleep 1
    echo "$PORT_PID" | xargs -r kill -9 2>/dev/null || true
    STOPPED=true
fi

if $STOPPED; then
    echo "✅ Servidor detenido correctamente."
else
    echo "ℹ️  La aplicación ya se encontraba detenida (ningún proceso activo en puerto $PORT)."
fi
