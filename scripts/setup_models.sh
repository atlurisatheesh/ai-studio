#!/usr/bin/env bash
# ArcVox Private Studio — model setup
# Downloads/installs the local AI engines. Run on the host that will serve them.
set -euo pipefail

DATA_DIR="${DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/backend/data}"
PIPER_DIR="$DATA_DIR/piper_voices"
mkdir -p "$PIPER_DIR"

echo "── 1/4 Piper voice (CPU TTS fallback, MIT license) ──────────────────"
if [ ! -f "$PIPER_DIR/en_US-lessac-medium.onnx" ]; then
  curl -L -o "$PIPER_DIR/en_US-lessac-medium.onnx" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
  curl -L -o "$PIPER_DIR/en_US-lessac-medium.onnx.json" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
  echo "   Browse more voices/languages: https://huggingface.co/rhasspy/piper-voices"
else
  echo "   already present"
fi

echo "── 2/4 Whisper (STT) ────────────────────────────────────────────────"
echo "   Downloads automatically on first transcription."
echo "   Max accuracy on GPU: set WHISPER_MODEL=large-v3 in .env"

echo "── 3/4 Ollama LLM (scripts / translate / agent) ─────────────────────"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "${OLLAMA_MODEL:-llama3.1:8b}"
else
  echo "   Ollama not found. Install: https://ollama.com  then:"
  echo "   ollama pull ${OLLAMA_MODEL:-llama3.1:8b}"
fi

echo "── 4/4 GPU engines (optional, for HD voice + avatars) ───────────────"
cat <<'EOF'
   Chatterbox (HD TTS + zero-shot voice cloning, MIT):
       pip install chatterbox-tts
       # then set TTS_ENGINE=chatterbox in .env

   SadTalker (talking-head lipsync from one photo):
       git clone https://github.com/OpenTalker/SadTalker
       cd SadTalker && pip install -r requirements.txt && bash scripts/download_models.sh
       # then set AVATAR_ENGINE=sadtalker and SADTALKER_DIR=/path/to/SadTalker in .env

   MuseTalk (higher-fidelity lipsync alternative):
       https://github.com/TMElyralab/MuseTalk
       # then set AVATAR_ENGINE=musetalk and MUSETALK_DIR=/path/to/MuseTalk
EOF

echo "Done."
