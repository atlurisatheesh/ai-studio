import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { TextT } from "@phosphor-icons/react";

export default function ScriptStudio() {
  const [topic, setTopic] = useState("How AI is reshaping cinematic storytelling");
  const [style, setStyle] = useState("professional");
  const [length, setLength] = useState("short");
  const [script, setScript] = useState("");
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setScript("");
    try {
      const { data } = await api.post("/ai/script", { topic, style, length });
      setScript(data.script || "");
      toast.success("Script ready");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="script-studio">
      <div className="mono-label mb-3">// MODULE — SCRIPT WRITER</div>
      <h1 className="h-display text-5xl mb-2">AI Script Writer</h1>
      <p className="text-studio-dim mb-10">Get a clean, spoken-word script ready for voice generation.</p>

      <div className="grid grid-cols-12 border border-white/10">
        <div className="col-span-12 lg:col-span-5 p-8 border-r border-white/10">
          <div className="mono-label mb-2">TOPIC</div>
          <input className="input-box mb-6" value={topic} onChange={(e) => setTopic(e.target.value)} data-testid="script-topic-input" />
          <div className="mono-label mb-2">STYLE</div>
          <select className="input-box mb-6" value={style} onChange={(e) => setStyle(e.target.value)} data-testid="script-style-select">
            <option value="professional">Professional</option>
            <option value="casual">Casual / Conversational</option>
            <option value="dramatic">Dramatic / Trailer</option>
            <option value="educational">Educational</option>
            <option value="comedic">Comedic</option>
            <option value="inspirational">Inspirational</option>
          </select>
          <div className="mono-label mb-2">LENGTH</div>
          <select className="input-box" value={length} onChange={(e) => setLength(e.target.value)} data-testid="script-length-select">
            <option value="short">Short (30–60s)</option>
            <option value="medium">Medium (1–2min)</option>
            <option value="long">Long (3–5min)</option>
          </select>
          <button onClick={generate} disabled={loading} className="btn-accent mt-8 disabled:opacity-50" data-testid="script-generate-btn">
            <TextT size={18} /> {loading ? "Writing…" : "Generate Script"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-7 p-8 bg-black/40">
          <div className="mono-label mb-3">SCRIPT</div>
          <div className="w-full min-h-[400px] bg-black border border-white/10 p-4 text-white text-sm whitespace-pre-wrap" data-testid="script-result">
            {script || <span className="text-studio-muted">Generated script appears here…</span>}
          </div>
          {script && (
            <button
              onClick={() => { navigator.clipboard.writeText(script); toast.success("Copied"); }}
              className="btn-outline mt-4 text-xs"
              data-testid="script-copy-btn"
            >
              COPY SCRIPT
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
