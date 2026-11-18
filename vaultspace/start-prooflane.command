#!/bin/zsh
cd -- "${0:A:h}" || exit 1
printf 'Vaultspace connected dashboard: http://localhost:8080\nRequires the Prooflane API at 127.0.0.1:8001. Keep this terminal open.\n'
python3 prooflane_dashboard.py
