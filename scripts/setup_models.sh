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

echo "── ffmpeg (required for video dubbing — audio dubbing works without it) ──"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "   already installed"
else
  echo "   Not found. Install it: apt install ffmpeg  (or: brew install ffmpeg)"
  echo "   Audio-file dubbing works without ffmpeg; video dubbing needs it to"
  echo "   extract/replace the audio track."
fi

echo "── 3/4 Ollama LLM (scripts / translate / agent) ─────────────────────"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "${OLLAMA_MODEL:-llama3.1:8b}"
else
  echo "   Ollama not found. Install: https://ollama.com  then:"
  echo "   ollama pull ${OLLAMA_MODEL:-llama3.1:8b}"
fi

echo "── 4/4 GPU engines (optional, for HD voice + avatars) ───────────────"
cat <<'EOF'
   Chatterbox (HD TTS + zero-shot voice cloning, 23 langs incl Hindi, MIT):
       pip install chatterbox-tts
       # then set TTS_ENGINE=chatterbox in .env

   Indic Parler-TTS (21 Indian languages — Tamil/Telugu/Bengali/…, Apache-2.0):
       pip install git+https://github.com/huggingface/parler-tts.git
       # gated model: accept terms at https://hf.co/ai4bharat/indic-parler-tts
       # then set TTS_ENGINE=indic_parler and HF_TOKEN=<your token> in .env

   SadTalker (talking-head lipsync from one photo, ~8GB VRAM):
       git clone https://github.com/OpenTalker/SadTalker
       cd SadTalker && pip install -r requirements.txt && bash scripts/download_models.sh
       # then set AVATAR_ENGINE=sadtalker and SADTALKER_DIR=/path/to/SadTalker in .env

   MuseTalk (higher-fidelity lipsync, ~12GB VRAM):
       https://github.com/TMElyralab/MuseTalk
       # then set AVATAR_ENGINE=musetalk and MUSETALK_DIR=/path/to/MuseTalk in .env

   EchoMimic (near-photorealistic audio-driven lipsync, ~16GB VRAM) [RECOMMENDED on high-end GPU]:
       git clone https://github.com/BadToBest/EchoMimic
       cd EchoMimic && pip install -r requirements.txt
       # download checkpoints per its README
       # then set AVATAR_ENGINE=echomimic and ECHOMIMIC_DIR=/path/to/EchoMimic in .env

   LivePortrait (high-fidelity face reenactment with audio, ~8GB VRAM):
       # Use the fork that adds --driving_audio support:
       git clone https://github.com/FurkanGozukara/LivePortrait
       cd LivePortrait && pip install -r requirements.txt
       # download checkpoints per its README
       # then set AVATAR_ENGINE=liveportrait and LIVEPORTRAIT_DIR=/path/to/LivePortrait in .env
EOF

echo "Done."
