#!/bin/zsh
cd -- "${0:A:h}" || exit 1
printf 'Starting Vaultspace at http://127.0.0.1:8000\nKeep this terminal open. Press Control+C to stop.\n'
python3 server.py
