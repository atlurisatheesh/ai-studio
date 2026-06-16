import { useEffect, useRef, useState } from "react";
import { api, formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { FilmSlate, Info, UploadSimple } from "@phosphor-icons/react";

export default function DubbingStudio() {
  const [file, setFile] = useState(null);
  const [languages, setLanguages] = useState([]);
  const [targetCode, setTargetCode] = useState("hi");
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("studio");
  const [dubStatus, setDubStatus] = useState(null);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    api.get("/dub/languages").then((r) => setLanguages(r.data || [])).catch(() => {});
    api.get("/voice/library").then((r) => {
      const cloned = (r.data.cloned || [])
        .filter((c) => c.status === "ready")
        .map((c) => ({ id: c.id, name: `${c.name} (clone)` }));
      setVoices([...(r.data.system || []), ...cloned]);
    }).catch(() => {});
    api.get("/engines/status").then((r) => setDubStatus(r.data.dub)).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const poll = (jobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/dub/jobs/${jobId}`);
        setJob(data);
        if (!["queued", "processing"].includes(data.status)) {
          clearInterval(pollRef.current);
          setLoading(false);
          if (data.status === "failed") toast.error(data.error || "Dubbing job failed");
          else toast.success("Dub ready");
        }
      } catch (e) {
        clearInterval(pollRef.current);
        setLoading(false);
        toast.error(formatApiError(e));
      }
    }, 2000);
  };

  const generate = async () => {
    if (!file) return toast.error("Upload an audio or video clip first");
    setLoading(true);
    setJob(null);
    try {
      const target = languages.find((l) => l.code === targetCode);
      const fd = new FormData();
      fd.append("source", file);
      fd.append("target_language", target?.name || targetCode);
      fd.append("target_language_code", targetCode);
      fd.append("voice", voice);
      const { data } = await api.post("/dub/generate", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJob(data);
      poll(data.id);
    } catch (err) {
      setLoading(false);
      toast.error(formatApiError(err));
    }
  };

  const assetUrl = (apiPath) => `${API}${apiPath.replace(/^\/api/, "")}`;
  const running = job && ["queued", "processing"].includes(job.status);
  const isVideoFile = file && /\.(mp4|mov|mkv|webm|avi)$/i.test(file.name);

  return (
    <div data-testid="dubbing-studio">
      <div className="mono-label mb-3">// MODULE_09 — DUBBING</div>
      <h1 className="h-display text-5xl mb-2">Dubbing Studio</h1>
      <p className="text-studio-dim mb-10">
        Upload a clip — it's transcribed, translated, and re-voiced in the target language on this server.
      </p>

      <div className="mb-6 border border-white/10 bg-white/[0.02] p-4 flex gap-3 text-sm">
        <Info size={18} className="text-studio-red shrink-0 mt-0.5" />
        <div className="text-studio-dim">
          {dubStatus?.lipsync_resync_available ? (
            <><strong className="text-white">Lip-resync engine online:</strong> video dubs get the mouth re-synced to the new language.</>
          ) : (
            <><strong className="text-white">Audio-mux mode:</strong> for video, the new-language track replaces the original audio (classic dub — lips won't re-match). Audio-only files always work. Full lip-resync activates with <code>AVATAR_ENGINE=musetalk</code> on a GPU host.</>
          )}
          {!dubStatus?.ffmpeg_installed && <div className="mt-1 text-amber-400">ffmpeg not detected on this server — video dubbing needs it; audio-only dubbing works regardless.</div>}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-0 border border-white/10">
        <div className="col-span-12 lg:col-span-7 p-8 border-r border-white/10">
          <div className="mono-label mb-3">SOURCE CLIP</div>
          <label
            className="block border border-dashed border-white/20 hover:border-white/50 p-6 cursor-pointer text-center mb-6"
            data-testid="dub-file-drop"
          >
            <input type="file" accept="audio/*,video/*" className="hidden" onChange={onFile} data-testid="dub-file-input" />
            <UploadSimple size={22} className="mx-auto mb-2 text-studio-dim" />
            <div className="text-sm">{file ? file.name : "Click to upload audio or video"}</div>
          </label>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="mono-label mb-2">TARGET LANGUAGE</div>
              <select className="input-box" value={targetCode} onChange={(e) => setTargetCode(e.target.value)} data-testid="dub-language-select">
                {languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <div className="mono-label mb-2">VOICE</div>
              <select className="input-box" value={voice} onChange={(e) => setVoice(e.target.value)} data-testid="dub-voice-select">
                {voices.length === 0 && <option value="studio">studio</option>}
                {voices.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </div>
          </div>

          <button onClick={generate} disabled={loading || !file} className="btn-accent mt-8 disabled:opacity-50" data-testid="dub-generate-btn">
            <FilmSlate size={18} /> {running ? `Dubbing… (${job.status})` : loading ? "Starting…" : "Generate Dub"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-5 p-6 bg-black/40">
          <div className="mono-label mb-3">OUTPUT</div>
          <div className="aspect-video bg-black border border-white/10 flex items-center justify-center mb-4 overflow-hidden" data-testid="dub-preview">
            {job?.status === "completed" && job.url && job.mode !== "audio" ? (
              <video src={assetUrl(job.url)} controls className="w-full h-full object-cover" data-testid="dub-video-player" />
            ) : (
              <FilmSlate size={48} className="text-studio-muted" />
            )}
          </div>
          {job?.status === "completed" && job.url && job.mode === "audio" && (
            <audio src={assetUrl(job.url)} controls className="w-full mb-4" data-testid="dub-audio-player" />
          )}
          {running && (
            <div className="mono-label text-studio-red animate-pulse mb-3" data-testid="dub-job-status">
              ● {job.status.toUpperCase()} — TRANSCRIBE → TRANSLATE → RE-VOICE
            </div>
          )}
          {job?.status === "failed" && (
            <div className="text-xs text-studio-red font-mono mb-3" data-testid="dub-job-error">{job.error}</div>
          )}
          {job?.transcript && (
            <div className="mb-3">
              <div className="mono-label mb-1">ORIGINAL ({job.source_language})</div>
              <div className="text-xs text-studio-dim whitespace-pre-wrap">{job.transcript}</div>
            </div>
          )}
          {job?.translated_text && (
            <div>
              <div className="mono-label mb-1">TRANSLATED</div>
              <div className="text-xs text-white whitespace-pre-wrap">{job.translated_text}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
