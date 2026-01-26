#!/bin/bash
# Script para activar el venv y lanzar el monitor/dashboard/clean plug-and-play (solo python)
cd "$(dirname "$0")"
source .venv/bin/activate
if [ -z "$1" ]; then
  echo "Uso: ./run_monitor.sh [monitor|dashboard|clean]"
  exit 1
fi
python -m src.main "$@"
