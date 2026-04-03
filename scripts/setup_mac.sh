#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Vasya AI macOS setup =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
else
  echo "Virtual environment already exists."
fi

echo "Installing Python dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed."
  echo "Install it with: brew install ollama"
else
  echo "Ollama found."
fi

if [ ! -f ".env" ]; then
  echo "Creating .env with default values..."
  cat > .env <<'EOF'
OLLAMA_MODEL=llama3
OLLAMA_FAST_MODEL=llama3
OLLAMA_REASONING_MODEL=llama3
OLLAMA_FAST_THINK=false
OLLAMA_FAST_TEMPERATURE=0.1
OLLAMA_FAST_NUM_PREDICT=256
WHISPER_MODEL=base
WHISPER_PARTIAL_MODEL=base
WHISPER_FINAL_MODEL=large-v3-turbo
STT_PARTIAL_BEAM_SIZE=1
STT_FINAL_BEAM_SIZE=5
RECORD_SECONDS=5
TTS_VOICE=Milena
TTS_RATE=185
GOOGLE_CALENDAR_ENABLED=false
EOF
else
  echo ".env already exists."
fi

mkdir -p storage

echo
echo "Setup complete."
echo "Next steps:"
echo "1. source .venv/bin/activate"
echo "2. ollama run llama3"
echo "3. python scripts/doctor.py"
echo "4. python main.py"
