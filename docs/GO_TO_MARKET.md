# Go-to-market — turning "beat them" into who / what / how

"Beat ElevenLabs and HeyGen" is unwinnable as stated — they're billion-dollar
companies and you won't out-spend their research. But that's the wrong frame.
You don't beat a big company everywhere. You beat them for **one specific
customer they serve badly.** This page names that customer and the smallest
path to a first "yes."

---

## Why you can win at all (the structural edge)

ElevenLabs and HeyGen are **cloud SaaS**. Their entire business depends on your
audio and video flowing through their servers. That creates three things they
**cannot** copy without breaking their own model:

1. **Privacy / on-prem.** They can't promise "your data never leaves your
   building." You can — it's your whole architecture. For anyone legally barred
   from sending audio to a US cloud, ElevenLabs isn't an option at any price.
2. **Cost at volume.** Per-minute pricing punishes heavy users. Self-hosting
   turns a runaway monthly bill into a fixed GPU cost. The more they use, the
   more you win.
3. **Indian languages + local presence.** AI4Bharat's models + on-prem
   deployment for Indian media and enterprise — a market the incumbents treat
   as an afterthought.

Your moat is **not** voice quality (you'll be at parity-or-behind a research
lab forever). Your moat is **where the data is allowed to live** and **what it
costs at scale.**

---

## The one wedge customer

Don't sell "an AI studio." Sell one outcome to one buyer:

> **Private, multilingual dubbing for an organisation that legally or
> commercially cannot send its audio/video to a foreign cloud — with a strong
> bias toward Indian languages.**

Concrete first-buyer candidates (pick the one you can actually reach):

| Buyer | Why they can't use ElevenLabs/HeyGen | What you sell them |
|---|---|---|
| Regional media / OTT house dubbing into Tamil/Telugu/Hindi | Per-minute cost explodes at catalogue scale | On-prem dubbing at fixed GPU cost, all Indian languages |
| Hospital / clinic chain | Patient audio can't leave the building (privacy law) | Local transcription + voiced summaries, nothing leaves the LAN |
| Bank / NBFC / insurer | Call recordings are regulated data | On-prem transcription + dubbing, audit-friendly |
| Government / PSU comms | Sovereignty + procurement rules forbid foreign cloud | Self-hosted, runs in their own data centre |

Start with whichever one you have a warm contact in. A warm intro beats a
better pitch.

---

## The 5 steps to a first "yes"

1. **Make one perfect demo.** Take a real 2-minute clip your target buyer would
   recognise (a news segment, a training video, a sample call). Dub it into
   their language. Polish until *you'd* pay for it. One clip, not a feature
   tour.
2. **Show 5 real people** in that segment. Don't pitch — ask: *"Would you pay
   for this? What's the one thing that would stop you?"* Write down the
   blockers verbatim.
3. **Fix only the top blocker.** If they say "the second speaker sounds like
   the first," that's diarization (now built — turn it on). If they say "it
   has to run in our data centre," that's the Docker deployment doc. Build the
   thing they named, nothing else.
4. **Get one paid pilot.** Even ₹10,000 for one month. A customer who pays
   tells you more than 100 who say "nice." Price on value (what they'd pay
   ElevenLabs at volume), not on your cost.
5. **Write down why they bought.** That sentence is your marketing, your
   roadmap, and your filter for every future feature request.

---

## What NOT to do right now

- **Don't** build text-to-video, more avatar engines, or a marketplace. Those
  are incumbent features; chasing them is fighting on their ground.
- **Don't** add languages or polish UI before step 2. You don't yet know what
  the customer needs — guessing is how the next three months disappear.
- **Don't** try to be "as good as ElevenLabs at everything." Be unbeatable at
  *private Indian-language dubbing* and ignore the rest.

---

## The honest reframe

You already built the product. The remaining risk was never "can the code
work" — it was "will anyone pay." That risk is retired by **talking to five
people**, not by writing more code. The scariest step (showing it to a real
buyer) is also the only one that moves you forward.
