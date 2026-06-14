# ArcVox notebooks

## `arcvox_quicklisten.ipynb` — easiest, zero setup 🔊

**If you just want to hear whether the voices are good, start here.** No uploads,
no API key, no decisions.

1. Open [Google Colab](https://colab.research.google.com/) → **File → Upload notebook** → pick `arcvox_quicklisten.ipynb`.
2. **Runtime → Change runtime type → GPU → Save.**
3. **Runtime → Run all.** Wait ~5–8 minutes.
4. Scroll down and press **▶** on each audio player.

You'll hear an English voice and a Hindi voice from ArcVox's engine, and see the
transcription read them back. That's the core product, proven, for free.

## `arcvox_gpu_verify.ipynb` — the full test

Proves the pretrained engines ArcVox ships with produce real, commercial-grade
output — **without training anything**. Runs on a free Colab or Kaggle T4 (16GB).

### Use it

1. Open [Google Colab](https://colab.research.google.com/) → *Upload notebook* →
   pick `arcvox_gpu_verify.ipynb`. (Or upload to a Kaggle Notebook.)
2. **Runtime → Change runtime type → GPU** (Colab) / enable the GPU accelerator (Kaggle).
3. Run the cells top to bottom. You'll produce:
   - `arcvox_tts.wav` / `arcvox_hindi_cb.wav` — Chatterbox English + Hindi
   - `arcvox_clone.wav` — your uploaded voice, zero-shot cloned
   - `tamil.wav` / `telugu.wav` / `hindi.wav` — **Indian languages** via AI4Bharat
     Indic Parler-TTS (Apache-2.0; gated — paste an HF token when prompted)
   - Whisper `large-v3` transcripts of all of the above (incl. Indian languages)
   - an `.mp4` talking-head of your portrait lip-syncing the audio (SadTalker)

### Why there's no training step

These are pretrained, MIT-licensed weights (Resemble AI, OpenAI/SYSTRAN, avatar
labs). You download and run inference — the same thing the ArcVox backend does.
Training a base model from scratch would take hundreds of GPUs, months, and
millions of dollars, and it's unnecessary: your edge is privacy + self-hosting,
not a novel model.

### Important

Running on Colab/Kaggle uploads your samples to Google/Kaggle infrastructure —
fine for **your own testing**, but **not** the private production deployment.
For real users, run these same engines on hardware you control (see the main
README's hardware guide). The notebook's Appendix shows an optional `cloudflared`
tunnel to drive the live app from the GPU session for end-to-end testing only.
