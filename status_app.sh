#!/usr/bin/env bash
# ==============================================================================
# status_app.sh - Verifica el estado del servicio y salud del sistema
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/server.pid"
PORT=8000
HOST="127.0.0.1"

echo "=== Estado de Twitter Post Classifier Master ==="

RUNNING=false
PID=""

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        RUNNING=true
    fi
fi

if ! $RUNNING; then
    PORT_PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [[ -n "$PORT_PID" ]]; then
        RUNNING=true
        PID="$PORT_PID"
    fi
fi

if $RUNNING; then
    echo "🟢 Estado:  EN EJECUCIÓN (PID: $PID)"
    echo "   URL:     http://$HOST:$PORT/"
    echo "   API:     http://$HOST:$PORT/docs"
    
    # Probar endpoint de salud
    HEALTH=$(curl -s --max-time 3 "http://$HOST:$PORT/api/system/health" 2>/dev/null || true)
    if [[ -n "$HEALTH" ]]; then
        echo "   Salud:   $HEALTH"
    fi
else
    echo "🔴 Estado:  DETENIDO"
    echo "   Para iniciar: ./start_app.sh"
fi
