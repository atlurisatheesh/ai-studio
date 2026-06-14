# ArcVox notebooks

## `arcvox_gpu_verify.ipynb` — free-GPU engine verification

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
