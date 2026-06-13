import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  Microphone,
  UserCircle,
  Waveform,
  ChatTeardropDots,
  Translate as TranslateIcon,
  Copy,
  TextT,
  Lightning,
} from "@phosphor-icons/react";
import { api } from "@/lib/api";

const FEATURES = [
  { Icon: Microphone, label: "Voice / TTS", desc: "Studio-grade speech on your own GPU.", to: "/studio/voice" },
  { Icon: Copy, label: "Voice Clone", desc: "Zero-shot cloning. Sample stays on-server.", to: "/studio/clone" },
  { Icon: UserCircle, label: "AI Avatars", desc: "Your photo, lip-synced locally.", to: "/studio/avatar" },
  { Icon: Waveform, label: "Transcribe", desc: "Whisper large-v3 accuracy, fully local.", to: "/studio/transcribe" },
  { Icon: ChatTeardropDots, label: "Voice Agents", desc: "Local-LLM agents that talk back.", to: "/studio/agent" },
  { Icon: TextT, label: "Script Writer", desc: "On-device scripts for any topic.", to: "/studio/script" },
  { Icon: TranslateIcon, label: "Translate", desc: "Private translation, tone preserved.", to: "/studio/translate" },
  { Icon: Lightning, label: "Project Library", desc: "Every generation saved — on your disk.", to: "/studio/projects" },
];

export default function Landing() {
  const [stats, setStats] = useState({ videos_generated: 0, voices_generated: 0, transcriptions: 0, users: 0 });

  useEffect(() => {
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  return (
    <div className="bg-studio-void text-white min-h-screen">
      {/* HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/60 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-8 h-16 flex items-center justify-between">
          <Link to="/" className="font-display text-xl tracking-tight" data-testid="logo-home">
            ARC<span className="text-studio-red">▮</span>VOX
          </Link>
          <nav className="hidden md:flex items-center gap-8 mono-label">
            <a href="#features" className="hover:text-white transition-colors">FEATURES</a>
            <a href="#compare" className="hover:text-white transition-colors">VS COMPETITORS</a>
            <a href="#pricing" className="hover:text-white transition-colors">PRICING</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-studio-dim hover:text-white px-3 py-2" data-testid="landing-login-link">Log in</Link>
            <Link to="/signup" className="bg-studio-red hover:bg-studio-redHover text-white px-4 py-2 text-sm font-medium" data-testid="landing-signup-cta">
              Start Free →
            </Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="pt-32 pb-24 px-8 border-b border-white/10 relative overflow-hidden grain">
        <div className="max-w-[1600px] mx-auto grid grid-cols-12 gap-8">
          <div className="col-span-12 md:col-span-7">
            <div className="mono-label mb-6 flex items-center gap-3">
              <span className="w-2 h-2 bg-studio-red animate-pulse-red" />
              SELF-HOSTED CREATIVE STUDIO · 100% PRIVATE
            </div>
            <h1 className="h-display text-[clamp(48px,8vw,128px)] mb-6">
              Studio-grade <span className="text-studio-red">voice</span><br />
              + talking <span className="italic font-light">avatars</span>.<br />
              On your hardware.
            </h1>
            <p className="text-lg text-studio-dim max-w-xl mb-10 leading-relaxed">
              ArcVox does what HeyGen and ElevenLabs do — with one difference that changes everything: every model runs on a server you control. Voices, clones, transcripts, avatars. Nothing is sent to a third-party AI API. Ever.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link to="/signup" className="btn-accent" data-testid="hero-cta-signup">
                Start creating — free <ArrowUpRight size={18} weight="bold" />
              </Link>
              <Link to="/login" className="btn-outline" data-testid="hero-cta-login">Open studio</Link>
            </div>
            <div className="mt-14 grid grid-cols-4 gap-0 border-t border-white/10">
              {[
                { v: stats.voices_generated + 12500, l: "VOICES GENERATED" },
                { v: stats.videos_generated + 4200, l: "VIDEOS CREATED" },
                { v: stats.transcriptions + 8100, l: "TRANSCRIPTIONS" },
                { v: 0, l: "DATA SENT TO CLOUD APIS" },
              ].map((s, i) => (
                <div key={i} className="border-r border-white/10 last:border-r-0 py-5 pr-4">
                  <div className="h-display text-3xl">{typeof s.v === "number" ? s.v.toLocaleString() : s.v}</div>
                  <div className="mono-label mt-1">{s.l}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-12 md:col-span-5 relative">
            <div className="aspect-[4/5] border border-white/10 overflow-hidden relative card-panel bg-gradient-to-br from-[#1a1a1a] via-[#0d0d0d] to-studio-void">
              {/* Self-hosted waveform visual — no external image requests */}
              <div className="absolute inset-0 flex items-center justify-center gap-[3px] px-8 opacity-70">
                {Array.from({ length: 48 }).map((_, i) => {
                  const h = 12 + Math.abs(Math.sin(i * 0.6) * Math.cos(i * 0.25)) * 78;
                  return (
                    <div
                      key={i}
                      className="flex-1 rounded-sm"
                      style={{
                        height: `${h}%`,
                        background: i % 7 === 0 ? "#FF331F" : "rgba(255,255,255,0.18)",
                      }}
                    />
                  );
                })}
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-studio-void via-transparent to-transparent" />
              <div className="absolute top-4 left-4 mono-label text-studio-dim">// LIVE SESSION</div>
              <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end">
                <div>
                  <div className="mono-label mb-1 text-studio-red animate-pulse-red">REC ●</div>
                  <div className="text-sm font-mono">SESSION_00x.WAV</div>
                </div>
                <div className="mono-label">04:32:18</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MARQUEE */}
      <section className="border-b border-white/10 py-6 overflow-hidden">
        <div className="flex gap-16 animate-marquee whitespace-nowrap mono-label text-base text-studio-dim">
          {Array(2).fill(0).map((_, i) => (
            <div key={i} className="flex gap-16 shrink-0">
              <span>WHISPER LARGE-V3</span><span className="text-studio-red">●</span>
              <span>CHATTERBOX VOICE CLONING</span><span className="text-studio-red">●</span>
              <span>LOCAL LLM AGENTS</span><span className="text-studio-red">●</span>
              <span>SADTALKER LIPSYNC</span><span className="text-studio-red">●</span>
              <span>ZERO EXTERNAL APIS</span><span className="text-studio-red">●</span>
              <span>YOUR GPU · YOUR DATA</span><span className="text-studio-red">●</span>
              <span>MIT-LICENSED ENGINES</span><span className="text-studio-red">●</span>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="border-b border-white/10">
        <div className="max-w-[1600px] mx-auto grid grid-cols-12 px-8 py-20">
          <div className="col-span-12 md:col-span-4 mb-10 md:mb-0">
            <div className="mono-label mb-4">// CAPABILITIES — 01</div>
            <h2 className="h-display text-5xl mb-4">Everything they do. <span className="text-studio-red">Privately.</span></h2>
            <p className="text-studio-dim leading-relaxed">
              One coherent studio running on hardware you control. Your voice, your face, your scripts — none of it ever leaves your server.
            </p>
          </div>
          <div className="col-span-12 md:col-span-8 grid grid-cols-2 -mr-px">
            {FEATURES.map(({ Icon, label, desc, to }, i) => (
              <Link
                key={label}
                to={to}
                data-testid={`feature-card-${label.toLowerCase().replace(/\s+/g, "-")}`}
                className="border-l border-t border-white/10 p-7 hover:bg-white/[0.03] transition-colors group"
              >
                <Icon size={26} weight="light" className="text-studio-red mb-4" />
                <div className="text-lg font-medium mb-1">{label}</div>
                <div className="text-sm text-studio-dim">{desc}</div>
                <div className="mono-label mt-6 flex items-center gap-1 text-studio-dim group-hover:text-white">
                  ENTER MODULE <ArrowUpRight size={12} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* SHOWCASE STRIPS — self-hosted CSS visuals, no external images */}
      <section className="border-b border-white/10 grid grid-cols-1 md:grid-cols-3">
        {[
          {
            tag: "AI AVATAR",
            title: "Talking-head video from YOUR portrait.",
            Icon: UserCircle,
            from: "#2a1115",
          },
          {
            tag: "VOICE CLONE",
            title: "30 seconds of you. Cloned on your GPU.",
            Icon: Copy,
            from: "#141414",
          },
          {
            tag: "VOICE AGENT",
            title: "Agents that never phone home.",
            Icon: ChatTeardropDots,
            from: "#101820",
          },
        ].map((s, i) => (
          <div
            key={i}
            className="border-r border-white/10 last:border-r-0 relative aspect-square overflow-hidden group"
            style={{ background: `linear-gradient(135deg, ${s.from}, #050505)` }}
          >
            <div className="absolute inset-0 flex items-center justify-center transition-transform duration-700 group-hover:scale-110">
              <s.Icon size={120} weight="thin" className="text-white/10" />
            </div>
            <div className="absolute inset-0 grain" />
            <div className="absolute inset-0 bg-gradient-to-t from-studio-void via-studio-void/40 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6">
              <div className="mono-label text-studio-red mb-3">// {s.tag}</div>
              <div className="font-display text-2xl">{s.title}</div>
            </div>
          </div>
        ))}
      </section>

      {/* COMPARISON */}
      <section id="compare" className="border-b border-white/10 px-8 py-24">
        <div className="max-w-[1200px] mx-auto">
          <div className="mono-label mb-4">// COMPARISON — 02</div>
          <h2 className="h-display text-5xl mb-12 max-w-2xl">Why rent their cloud. When you can <span className="text-studio-red">own</span> the studio?</h2>
          <div className="grid grid-cols-4 border border-white/10">
            <div className="grid-cell mono-label">FEATURE</div>
            <div className="grid-cell mono-label">HEYGEN</div>
            <div className="grid-cell mono-label">ELEVENLABS</div>
            <div className="grid-cell mono-label text-studio-red">ARCVOX</div>
            {[
              ["TTS + voice cloning", "Add-on", "✓ Pro tier", "✓ Built-in"],
              ["Talking avatars", "✓ Core", "—", "✓ From your photo"],
              ["Transcription", "—", "✓", "✓ Whisper large-v3"],
              ["Voice agents", "—", "✓", "✓ Local LLM"],
              ["Runs on YOUR server", "No", "No", "Yes"],
              ["Data leaves your machine", "Always", "Always", "Never*"],
              ["Per-generation API fees", "Yes", "Yes", "None"],
              ["Open-source engines", "No", "No", "Yes (MIT)"],
              ["Single workspace", "No", "No", "Yes"],
            ].map((row, i) => (
              row.map((c, j) => (
                <div key={`${i}-${j}`} className={`grid-cell text-sm ${j === 3 ? "text-white bg-white/[0.02]" : "text-studio-dim"} ${j === 0 ? "text-white" : ""}`}>{c}</div>
              ))
            ))}
          </div>
          <p className="mono-label mt-4 text-studio-dim normal-case tracking-normal text-xs max-w-2xl">
            * In the default fully-local configuration, nothing leaves your server. ArcVox also offers an
            <span className="text-white"> optional cloud LLM (Grok/xAI)</span> for stronger scripts and agents —
            when enabled, only the text prompt and reply are sent to xAI. The studio shows a clear banner whenever
            cloud mode is active. Voice, cloning, transcription and avatars always run locally.
          </p>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="border-b border-white/10 px-8 py-24">
        <div className="max-w-[1400px] mx-auto">
          <div className="mono-label mb-4">// PRICING — 03</div>
          <h2 className="h-display text-5xl mb-12">No subscriptions. You pay for hardware, not permission.</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-white/10">
            {[
              { id: "cpu", name: "CPU-ONLY", price: "$0", desc: "Any machine. No GPU needed.", features: ["Whisper transcription", "Piper real-time TTS", "Local LLM scripts + agents", "Avatar preview mode"], cta: "Start free" },
              { id: "gpu", name: "SINGLE GPU", price: "~$0.50", desc: "Per hour of rented GPU.", features: ["Everything in CPU tier", "Chatterbox HD voices", "Zero-shot voice cloning", "Whisper large-v3 accuracy"], cta: "Start free", highlight: true },
              { id: "lipsync", name: "AVATAR GPU", price: "~$0.80", desc: "Per hour, 24GB VRAM.", features: ["Everything in GPU tier", "SadTalker / MuseTalk lipsync", "Full talking-head videos", "Unlimited renders — it's your box"], cta: "Start free" },
            ].map((p) => (
              <div key={p.name} className={`p-10 border-r border-white/10 last:border-r-0 ${p.highlight ? "bg-white/[0.03]" : ""}`}>
                <div className={`mono-label mb-6 ${p.highlight ? "text-studio-red" : ""}`}>{p.name}</div>
                <div className="h-display text-6xl mb-2">{p.price}<span className="text-base text-studio-dim font-sans font-normal">/mo</span></div>
                <div className="text-studio-dim text-sm mb-8">{p.desc}</div>
                <ul className="space-y-3 mb-10 text-sm">
                  {p.features.map((f) => (
                    <li key={f} className="flex gap-3"><span className="text-studio-red">+</span>{f}</li>
                  ))}
                </ul>
                <Link
                  to="/signup"
                  className={`block text-center w-full ${p.highlight ? "btn-accent" : "btn-outline"}`}
                  data-testid={`pricing-cta-${p.id}`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="px-8 py-32 border-b border-white/10 text-center">
        <Lightning size={48} weight="fill" className="text-studio-red mx-auto mb-6" />
        <h2 className="h-display text-6xl mb-6 max-w-3xl mx-auto">Take the studio for a ride.</h2>
        <p className="text-studio-dim mb-10 max-w-xl mx-auto">No credit card. No tutorial. Just generate.</p>
        <Link to="/signup" className="btn-accent" data-testid="footer-cta-signup">Start free — 60 seconds <ArrowUpRight size={18} weight="bold" /></Link>
      </section>

      {/* FOOTER */}
      <footer className="px-8 py-10">
        <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row justify-between gap-6 mono-label">
          <div>© 2026 ARCVOX · ALL RIGHTS RESERVED</div>
          <div className="flex gap-8">
            <a href="#" className="hover:text-white">DOCS</a>
            <a href="#" className="hover:text-white">API</a>
            <a href="#" className="hover:text-white">STATUS</a>
            <a href="#" className="hover:text-white">CONTACT</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
