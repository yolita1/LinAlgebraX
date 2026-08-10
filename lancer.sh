#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"

if [ ! -x ".venv/bin/python" ]; then
    if ! python3 -m venv .venv; then
        echo "Impossible de créer l'environnement virtuel."
        echo "Sous Ubuntu ou Debian : sudo apt install python3-venv python3-tk"
        exit 1
    fi
fi

if ! .venv/bin/python -c "import matplotlib" 2>/dev/null; then
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python project.py
