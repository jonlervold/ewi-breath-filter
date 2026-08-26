#!/bin/bash
set -euo pipefail

python3 -m PyInstaller \
  --clean \
  --noconfirm \
  --windowed \
  --name "EWI Breath Filter" \
  --hidden-import=rtmidi \
  --hidden-import=PySimpleGUI \
  --collect-all rtmidi \
  main.py
