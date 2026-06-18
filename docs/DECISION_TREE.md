# What to do next — decided in advance

You feel stuck because you're trying to choose a path while standing on a fact
you don't have yet: **you have never heard your own product's voice.** Don't
decide blind. Run one cheap experiment, then the right move picks itself.

This page pre-decides your next step for **every** outcome, so the moment you
have a number you act instead of agonising.

---

## Step 0 — the only experiment that matters (10 minutes, free)

1. Open `notebooks/arcvox_quicklisten.ipynb` in **Google Colab** or **Kaggle**
   (both give a free GPU — no purchase, no Kaggle token needed).
2. Runtime → GPU → Run all.
3. Listen to the English clip and the Hindi clip.
4. **Score the voice 1–10 against ElevenLabs** (be honest — pretend you're a
   paying customer comparing tabs).

Write the number down. Everything below branches on it.

---

## The decision tree

### Voice scores 8–10  →  the thesis is PROVEN. Stop building, start selling.

The hard part (does the tech sound good?) is answered: yes. More features will
not help you now — **customers** will. Do this, in order:

1. Pick the one wedge customer from `docs/GO_TO_MARKET.md` (privacy-bound
   Indian-language dubbing).
2. Dub **one real 2-minute clip** they'd actually care about. Make it perfect.
3. Show it to **5 real people** in that segment. Ask one question: *"Would you
   pay for this, and what's the one thing that would stop you?"*
4. Build only the thing they say stops them. Nothing else.
5. Repeat until someone pays.

> Do **not** add text-to-video, more avatar engines, or more languages here.
> Quality is proven; the risk is now "will anyone buy," and only customers
> answer that.

### Voice scores 5–7  →  close but not sellable. One targeted upgrade, then re-test.

Good open models, not yet ElevenLabs. Two levers, cheapest first:

1. **Try the other engines before spending a rupee.** Run
   `notebooks/arcvox_gpu_verify.ipynb` and compare Chatterbox vs Indic
   Parler-TTS on your target language. Often one is clearly better for a given
   language — switching `TTS_ENGINE` is free.
2. **If still short, fine-tune** — see `docs/FINETUNING.md`. This is the
   realistic version of "build our own": take a good open model and specialise
   it on your language/voice for a few hundred dollars of GPU time. Re-score
   after.

Re-test after each lever. Stop the moment you hit 8.

### Voice scores 1–4  →  the base model is wrong, not your code.

Your code is fine — the model underneath isn't good enough for this use. Do
**not** try to fix it with product work. Instead:

1. Swap base models. The open TTS field moves monthly — try F5-TTS, XTTS-v2,
   Fish-Speech, Kokoro, or a newer release. `engines/tts.py` is already an
   abstraction layer; adding an engine is a contained change.
2. Re-run Step 0 with the new engine.
3. Only if **nothing** open clears the bar for your language does fine-tuning
   from `docs/FINETUNING.md` become mandatory rather than optional.

---

## The trap to avoid

Every outcome above has a **single** next action. The failure mode is doing a
little of all of them — polishing captions, adding a language, tweaking the UI
— which feels productive and proves nothing. Pick the branch your score lands
in and do only that branch.

You are one 10-minute notebook run away from knowing which world you live in.
Run it.
