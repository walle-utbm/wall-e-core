#!/usr/bin/env bash
#
# Assemble le front-end servi par le pont :
#   build/web = copie de dashboard-wall-e/walle-dashboard + overlays de core/.
# Le sous-module dashboard reste INTACT (on copie, on n'édite jamais dedans).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/dashboard-wall-e/walle-dashboard"
OVERRIDES="$ROOT/core/frontend_overrides"
OUT="$ROOT/build/web"

if [ ! -d "$SRC" ]; then
  echo "[build_frontend] Sous-module dashboard introuvable ($SRC)."
  echo "                 Lance : git submodule update --init --recursive"
  exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT"
cp -r "$SRC"/. "$OUT"/

# Overlays (review.js + tout fichier supplémentaire du parent).
if [ -d "$OVERRIDES" ]; then
  cp -r "$OVERRIDES"/. "$OUT"/
fi

# Injecte review.js dans index.html (après main.js), de façon idempotente.
INDEX="$OUT/index.html"
if ! grep -q 'js/review.js' "$INDEX"; then
  sed -i 's#\(<script src="js/main.js"></script>\)#\1\n<script src="js/review.js"></script>#' "$INDEX"
fi

echo "[build_frontend] Front assemblé dans $OUT"
