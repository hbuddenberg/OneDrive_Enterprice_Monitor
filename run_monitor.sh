#!/bin/bash
# Script multiplataforma para ejecutar el monitor, dashboard o limpieza
# Uso: ./run_monitor.sh [monitor|dashboard|clean]

cd "$(dirname "$0")"
source .venv/bin/activate

if [ -z "$1" ]; then
  echo "Uso: $0 [monitor|dashboard|clean]"
  exit 1
fi

# Detectar si uv está disponible en el venv y usarlo si existe
UV_PATH=".venv/bin/uv"
if [ -x "$UV_PATH" ]; then
  "$UV_PATH" run python -m src.main "$@"
  exit $?
fi

# Si no, usar python normal
python -m src.main "$@"
