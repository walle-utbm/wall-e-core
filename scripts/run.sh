#!/usr/bin/env bash
#
# Assemble le front puis lance le service passerelle (FastAPI/uvicorn).
# Host et port sont lus depuis config.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/build_frontend.sh

# Choisit l'interpréteur : venv du projet en priorité, sinon python3/python.
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

exec "$PY" -m core.server
