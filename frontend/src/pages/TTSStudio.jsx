import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SpeakerHigh, Play, Download } from "@phosphor-icons/react";

export default function TTSStudio() {
  const [text, setText] = useState("Welcome to ArcVox, where studio-grade voice meets cinematic video.");
  const [voice, setVoice] = useState("studio");
  const [speed, setSpeed] = useState(1.0);
  const [voices, setVoices] = useState([]);
  const [engine, setEngine] = useState("");
  const [audio, setAudio] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/voice/library").then((r) => {
      const cloned = (r.data.cloned || [])
        .filter((c) => c.status === "ready")
        .map((c) => ({ id: c.id, name: c.name, gender: "cloned", tags: ["your clone"] }));
      const system = r.data.system || [];
      setVoices([...system, ...cloned]);
      setEngine(r.data.engine || "");
      if (system.length && !system.some((v) => v.id === "studio")) setVoice(system[0].id);
    }).catch(() => {});
  }, []);

  const generate = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setAudio(null);
    try {
      const { data } = await api.post("/voice/tts", { text, voice, speed });
      setAudio(`data:audio/wav;base64,${data.audio_base64}`);
      toast.success("Voice generated");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="tts-studio">
      <div className="mono-label mb-3">// MODULE_01 — VOICE / TTS</div>
      <h1 className="h-display text-5xl mb-2">Voice Generator</h1>
      <p className="text-studio-dim mb-10">Up to 4,000 chars. Synthesized on your own hardware — text never leaves this server.</p>

      <div className="grid grid-cols-12 gap-0 border border-white/10">
        {/* LEFT: input */}
        <div className="col-span-12 lg:col-span-8 p-8 border-r border-white/10">
          <div className="mono-label mb-3">SCRIPT</div>
          <textarea
            data-testid="tts-text-input"
            className="w-full h-64 bg-black border border-white/10 p-4 text-white font-mono text-sm focus:outline-none focus:border-white"
            value={text}
            maxLength={4000}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your script here..."
          />
          <div className="mono-label text-right text-studio-dim mt-2">{text.length} / 4000</div>

          <div className="grid grid-cols-3 gap-6 mt-8">
            <div>
              <div className="mono-label mb-2">ENGINE</div>
              <div className="input-box pointer-events-none uppercase" data-testid="tts-engine-display">{engine || "local"}</div>
            </div>
            <div>
              <div className="mono-label mb-2">SPEED</div>
              <input type="number" step="0.1" min="0.25" max="4" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="input-box" data-testid="tts-speed-input" />
            </div>
            <div>
              <div className="mono-label mb-2">CHARACTERS</div>
              <div className="input-box pointer-events-none">{text.length}</div>
            </div>
          </div>

          <button onClick={generate} disabled={loading || !text.trim()} className="btn-accent mt-8 disabled:opacity-50" data-testid="tts-generate-btn">
            <SpeakerHigh size={18} /> {loading ? "Generating…" : "Generate Voice"}
          </button>

          {audio && (
            <div className="mt-8 p-6 border border-white/10 bg-black" data-testid="tts-audio-result">
              <div className="mono-label mb-3 text-studio-red">▶ OUTPUT_{Date.now().toString(36)}</div>
              <audio src={audio} controls className="w-full" data-testid="tts-audio-player" />
              <a href={audio} download="arcvox_voice.wav" className="btn-outline mt-4 text-xs" data-testid="tts-download-link">
                <Download size={14} /> DOWNLOAD WAV
              </a>
            </div>
          )}
        </div>

        {/* RIGHT: voice picker */}
        <div className="col-span-12 lg:col-span-4 p-6">
          <div className="mono-label mb-4">SELECT VOICE</div>
          <div className="flex flex-col">
            {voices.map((v) => (
              <button
                key={v.id}
                onClick={() => setVoice(v.id)}
                data-testid={`tts-voice-${v.id}`}
                className={`text-left border-b border-white/10 py-3 px-2 flex justify-between items-center transition-colors ${voice === v.id ? "bg-white/[0.05]" : "hover:bg-white/[0.02]"}`}
              >
                <div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    {v.name}
                    {voice === v.id && <span className="text-studio-red">●</span>}
                  </div>
                  <div className="mono-label text-studio-dim">{v.tags.join(" · ")}</div>
                </div>
                <span className="mono-label text-studio-dim">{v.gender.slice(0, 1).toUpperCase()}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
