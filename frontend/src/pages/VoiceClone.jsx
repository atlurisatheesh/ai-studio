import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Copy as CopyIcon, UploadSimple, Info } from "@phosphor-icons/react";

export default function VoiceClone() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [cloned, setCloned] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = () => {
    api.get("/voice/library").then((r) => setCloned(r.data.cloned || [])).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const submit = async () => {
    if (!file || !name) return toast.error("Name and sample required");
    setLoading(true);
    const fd = new FormData();
    fd.append("name", name);
    fd.append("description", description);
    fd.append("sample", file);
    try {
      await api.post("/voice/clone", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Voice sample uploaded");
      setName(""); setDescription(""); setFile(null);
      refresh();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="voice-clone-studio">
      <div className="mono-label mb-3">// MODULE_02 — VOICE CLONE</div>
      <h1 className="h-display text-5xl mb-2">Voice Cloning</h1>
      <p className="text-studio-dim mb-8">Upload a 10–30 second clean sample. Clones are ready instantly — select them in TTS Studio.</p>

      <div className="mb-6 border border-white/10 bg-white/[0.02] p-4 flex gap-3 text-sm">
        <Info size={18} className="text-studio-red shrink-0 mt-0.5" />
        <div className="text-studio-dim">
          <strong className="text-white">Private cloning:</strong> Zero-shot voice cloning runs on this server (Chatterbox engine). Your voice sample is stored locally and never uploaded to any third party.
        </div>
      </div>

      <div className="grid grid-cols-12 border border-white/10">
        <div className="col-span-12 lg:col-span-5 p-8 border-r border-white/10">
          <div className="mono-label mb-2">VOICE NAME</div>
          <input className="input-box mb-6" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Studio Narrator" data-testid="clone-name-input" />
          <div className="mono-label mb-2">DESCRIPTION (OPTIONAL)</div>
          <input className="input-box mb-6" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Warm, mid-range, female" data-testid="clone-description-input" />
          <div className="mono-label mb-2">SAMPLE AUDIO</div>
          <label className="border border-dashed border-white/15 p-8 text-center cursor-pointer block hover:border-white/40">
            <UploadSimple size={28} className="mx-auto mb-2 text-studio-dim" />
            <div className="text-sm">{file ? file.name : "Click to select audio (30s recommended)"}</div>
            <input type="file" accept="audio/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="clone-file-input" />
          </label>
          <button onClick={submit} disabled={loading || !file || !name} className="btn-accent mt-8 w-full disabled:opacity-50" data-testid="clone-submit-btn">
            <CopyIcon size={18} /> {loading ? "Uploading…" : "Create Voice Clone"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-7 p-8">
          <div className="mono-label mb-4">YOUR VOICE LIBRARY ({cloned.length})</div>
          {cloned.length === 0 ? (
            <div className="text-studio-muted text-sm" data-testid="clone-empty">No cloned voices yet.</div>
          ) : (
            <div className="divide-y divide-white/10">
              {cloned.map((v) => (
                <div key={v.id} className="py-4 flex justify-between items-center" data-testid={`clone-row-${v.id}`}>
                  <div>
                    <div className="text-sm font-medium">{v.name}</div>
                    <div className="mono-label text-studio-dim">{v.description || "—"}</div>
                  </div>
                  <div className={`mono-label ${v.status === "ready" ? "text-[#00FF66]" : "text-studio-red"}`}>{v.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
