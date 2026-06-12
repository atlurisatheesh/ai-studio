import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Translate as TranslateIcon } from "@phosphor-icons/react";

const LANGUAGES = [
  "Spanish", "French", "German", "Italian", "Portuguese", "Dutch", "Russian",
  "Japanese", "Korean", "Chinese (Mandarin)", "Hindi", "Arabic", "Turkish",
  "Polish", "Swedish", "Norwegian", "Greek", "Hebrew", "Vietnamese", "Thai", "Indonesian"
];

export default function Translate() {
  const [text, setText] = useState("");
  const [target, setTarget] = useState("Spanish");
  const [preserveTone, setPreserveTone] = useState(true);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setOutput("");
    try {
      const { data } = await api.post("/ai/translate", { text, target_language: target, preserve_tone: preserveTone });
      setOutput(data.translated || "");
      toast.success("Translated");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="translate-studio">
      <div className="mono-label mb-3">// MODULE — TRANSLATE</div>
      <h1 className="h-display text-5xl mb-2">AI Translator</h1>
      <p className="text-studio-dim mb-10">Tone-preserving translation across 175+ languages.</p>

      <div className="grid grid-cols-12 border border-white/10">
        <div className="col-span-12 lg:col-span-6 p-8 border-r border-white/10">
          <div className="mono-label mb-2">SOURCE TEXT</div>
          <textarea
            className="w-full h-56 bg-black border border-white/10 p-4 font-mono text-sm focus:outline-none focus:border-white"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste any text…"
            data-testid="translate-source-input"
          />
          <div className="grid grid-cols-2 gap-6 mt-6">
            <div>
              <div className="mono-label mb-2">TARGET LANGUAGE</div>
              <select className="input-box" value={target} onChange={(e) => setTarget(e.target.value)} data-testid="translate-target-select">
                {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={preserveTone} onChange={(e) => setPreserveTone(e.target.checked)} data-testid="translate-tone-toggle" />
                Preserve tone & style
              </label>
            </div>
          </div>
          <button onClick={run} disabled={loading || !text.trim()} className="btn-accent mt-8 disabled:opacity-50" data-testid="translate-submit-btn">
            <TranslateIcon size={18} /> {loading ? "Translating…" : "Translate"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-6 p-8 bg-black/40">
          <div className="mono-label mb-2">TRANSLATED — {target.toUpperCase()}</div>
          <div className="w-full min-h-[300px] bg-black border border-white/10 p-4 text-white text-sm whitespace-pre-wrap" data-testid="translate-result">
            {output || <span className="text-studio-muted">Translation appears here…</span>}
          </div>
          {output && (
            <button
              onClick={() => { navigator.clipboard.writeText(output); toast.success("Copied"); }}
              className="btn-outline mt-4 text-xs"
              data-testid="translate-copy-btn"
            >
              COPY
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
