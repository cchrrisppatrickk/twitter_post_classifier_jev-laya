#!/usr/bin/env bash
# ==============================================================================
# start_app.sh - Inicia Twitter Post Classifier Master v2.1.0 en segundo plano
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/server.pid"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/app.log"
PORT=8000
HOST="127.0.0.1"

mkdir -p "$LOG_DIR"

# 1. Detectar entorno virtual de Python
PYTHON_BIN=""
if [[ -x "$SCRIPT_DIR/../laya_tester_app/.venv/bin/python3" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/../laya_tester_app/.venv/bin/python3"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python3" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Error: No se encontró un intérprete de Python 3 funcional." >&2
    exit 1
fi

# 2. Verificar si ya se encuentra en ejecución
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️  La aplicación ya está ejecutándose con PID: $OLD_PID en http://$HOST:$PORT"
        echo "   Para detenerla use: ./stop_app.sh"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Verificar si el puerto 8000 está ocupado por otro proceso
PORT_PID=$(lsof -ti :$PORT 2>/dev/null || fuser $PORT/tcp 2>/dev/null || true)
if [[ -n "$PORT_PID" ]]; then
    echo "⚠️  El puerto $PORT ya está ocupado. Limpiando procesos previos..."
    echo "$PORT_PID" | xargs -r kill -15 2>/dev/null || true
    sleep 1
    echo "$PORT_PID" | xargs -r kill -9 2>/dev/null || true
    sleep 1
fi

export PYTHONUNBUFFERED=1

echo "🚀 Iniciando Twitter Post Classifier Master..."
echo "   Python: $PYTHON_BIN"
echo "   Host:   http://$HOST:$PORT"
echo "   Logs:   $LOG_FILE"

setsid "$PYTHON_BIN" -m uvicorn app.main:app \
    --app-dir backend \
    --host "$HOST" \
    --port "$PORT" \
    --lifespan on \
    >> "$LOG_FILE" 2>&1 &

APP_PID=$!
echo "$APP_PID" > "$PID_FILE"

# 3. Esperar 2 segundos para validar arranque
sleep 2

if kill -0 "$APP_PID" 2>/dev/null; then
    echo "✅ Aplicación iniciada exitosamente [PID: $APP_PID]"
    echo "   Dashboard:   http://$HOST:$PORT/"
    echo "   API Docs:    http://$HOST:$PORT/docs"
    echo "   Para logs:   tail -f $LOG_FILE"
    echo "   Para parar:  ./stop_app.sh"
else
    echo "❌ Error al iniciar la aplicación. Revise los registros en $LOG_FILE:"
    tail -n 20 "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
