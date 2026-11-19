#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
  echo "Se requiere Python 3.10 o superior (usa PYTHON=/ruta/python3.12 ./setup.sh)." >&2
  exit 1
fi

"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if ! command -v magick >/dev/null 2>&1; then
  echo "AVISO: ImageMagick 7 (magick) no está en PATH; los PSD no podrán procesarse."
  echo "macOS: brew install imagemagick | Arch Linux: sudo pacman -S imagemagick"
fi

echo
echo "Entorno preparado. Para activarlo: source .venv/bin/activate"
echo "Prueba: .venv/bin/python src/extract_illustrations.py --help"
