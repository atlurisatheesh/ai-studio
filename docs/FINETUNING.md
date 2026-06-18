# "Can we build our own?" — the honest, realistic version

This answers the question directly: **what does it actually take to build voice
and avatar tech like ElevenLabs and HeyGen**, what's out of reach, and what you
can genuinely do.

---

## Two meanings, two very different answers

### Meaning 1 — train a foundation model from scratch  →  No.

Building the actual neural network that ElevenLabs trained is not a "hard"
goal; it's the **wrong** goal:

| What it needs | Reality for you |
|---|---|
| Tens of thousands of hours of clean, licensed, transcribed multilingual speech | ElevenLabs licenses/owns this; it's their moat. You don't have it. |
| A cluster of H100/A100 GPUs running for weeks | $1M–$10M+ in compute |
| A team of ML researchers (audio diffusion / flow-matching / autoregressive modelling) | Specialist PhD-level skills, not a solo build |
| 1–2 years before a competitive result | You'd lose the market while training |

ElevenLabs raised **$180M+** to do exactly this. A solo founder with a free
Kaggle GPU cannot, and **should not try.** Chasing it burns months for nothing.
Feel zero guilt about not doing it — nobody in your position does.

### Meaning 2 — build your own *product* on open models  →  Yes. Already done.

ElevenLabs and HeyGen are maybe **10% model and 90% product** — the UI, the
pipeline, the API, the deployment, the customer focus. The model is a
commodity that's free to everyone: Chatterbox, XTTS-v2, F5-TTS, Indic
Parler-TTS, SadTalker, EchoMimic. **You stand on top of them.** Assembling them
into a private, multilingual studio *is* building your own tool. ArcVox is your
own tool.

> The model is not the moat. The product, the privacy guarantee, and the wedge
> customer are. See `docs/GO_TO_MARKET.md`.

---

## The middle path: fine-tuning (the realistic "build our own")

Between "train from scratch" (impossible) and "use it as-is" (free) sits
**fine-tuning**: take a strong open model and specialise it on *your* language
or *your* target voice. This is achievable, and it's where you'd invest **only
if** Step 0 verification (`docs/DECISION_TREE.md`) shows quality is close but
not quite there.

### What fine-tuning can and can't do

- ✅ **Can:** sharpen a specific language (e.g. better Telugu prosody), lock in
  a specific brand/character voice, reduce accent artefacts on your domain.
- ❌ **Can't:** turn a fundamentally weak base model into ElevenLabs. If the
  base is 4/10, fine-tuning gets you to maybe 6, not 9. Swap the base instead.

### Rough cost / effort (rented GPU, e.g. RunPod / Vast.ai)

| Task | Data needed | GPU time | Ballpark cost |
|---|---|---|---|
| Fine-tune TTS on one target voice | 30 min – 2 hr clean audio of that voice | A single 24GB GPU, hours to ~2 days | $20 – $200 |
| Adapt a model to one language's prosody | A few hours of transcribed, clean speech in that language | 1× 24–48GB GPU, 1–3 days | $100 – $600 |
| Avatar/lipsync fine-tune | Video of the target face | High-VRAM GPU, days | $200 – $1000+ |

These are *order-of-magnitude* figures to set expectations, not quotes. The
point: it's **hundreds of dollars and weeks**, not millions and years — but
still real money and time you spend only after verification says it's worth it.

### Where to start when the time comes

- **TTS fine-tuning:** most open TTS repos ship a fine-tuning/training script
  (Parler-TTS, XTTS, F5-TTS all do). Start from their official guide; you
  provide clean audio + transcripts.
- **Data quality beats data quantity.** 30 minutes of clean, well-transcribed
  audio of one voice beats 10 hours of noisy mixed audio. Garbage in, garbage
  voice out.
- **Always keep a pretrained fallback.** Fine-tuning can regress general
  quality while improving the specialised case. Keep the base model selectable
  via `TTS_ENGINE`.

---

## The bottom line

- **Train a foundation model from scratch:** no — wrong battle, you'll lose.
- **Build the product around open models:** yes — you already did.
- **Fine-tune open models for your wedge:** yes, when verification proves it's
  the missing piece — a few hundred dollars, not a research lab.

The winning move is almost never "build a better model than ElevenLabs." It's
"assemble good-enough open models into the one product a specific customer is
not allowed to buy from ElevenLabs." Spend your scarce time there.
