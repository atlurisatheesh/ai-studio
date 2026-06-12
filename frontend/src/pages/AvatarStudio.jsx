import { useEffect, useRef, useState } from "react";
import { api, formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { UserCircle, Info, UploadSimple } from "@phosphor-icons/react";

export default function AvatarStudio() {
  const [script, setScript] = useState("Hi, I'm your presenter. Let me walk you through this quarter's results.");
  const [voice, setVoice] = useState("studio");
  const [voices, setVoices] = useState([]);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lipsyncReady, setLipsyncReady] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    api.get("/voice/library").then((r) => {
      const cloned = (r.data.cloned || [])
        .filter((c) => c.status === "ready")
        .map((c) => ({ id: c.id, name: `${c.name} (clone)` }));
      setVoices([...(r.data.system || []), ...cloned]);
    }).catch(() => {});
    api.get("/engines/status").then((r) => setLipsyncReady(!!r.data.avatar?.engine_ready)).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  const onPhoto = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPhoto(f);
    setPhotoPreview(URL.createObjectURL(f));
  };

  const poll = (jobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/avatar/jobs/${jobId}`);
        setJob(data);
        if (!["queued", "processing"].includes(data.status)) {
          clearInterval(pollRef.current);
          setLoading(false);
          if (data.status === "failed") toast.error(data.error || "Avatar job failed");
          else toast.success(data.status === "completed" ? "Talking-head video ready" : "Preview ready");
        }
      } catch (e) {
        clearInterval(pollRef.current);
        setLoading(false);
        toast.error(formatApiError(e));
      }
    }, 2000);
  };

  const generate = async () => {
    if (!photo) return toast.error("Upload a portrait photo first");
    setLoading(true);
    setJob(null);
    try {
      const fd = new FormData();
      fd.append("script", script);
      fd.append("voice", voice);
      fd.append("portrait", photo);
      const { data } = await api.post("/avatar/generate", fd, {
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

  return (
    <div data-testid="avatar-studio">
      <div className="mono-label mb-3">// MODULE_04 — AI AVATAR</div>
      <h1 className="h-display text-5xl mb-2">AI Avatar Studio</h1>
      <p className="text-studio-dim mb-10">Your photo + your script, lip-synced on your own hardware.</p>

      <div className="mb-6 border border-white/10 bg-white/[0.02] p-4 flex gap-3 text-sm">
        <Info size={18} className="text-studio-red shrink-0 mt-0.5" />
        <div className="text-studio-dim">
          {lipsyncReady ? (
            <><strong className="text-white">Lipsync engine online:</strong> full talking-head video is generated locally. Your face photo never leaves this server.</>
          ) : (
            <><strong className="text-white">Preview mode:</strong> portrait + narrated voice. Full lip-synced motion activates when a local engine (SadTalker / MuseTalk) is installed on the GPU host — no external API involved either way.</>
          )}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-0 border border-white/10">
        <div className="col-span-12 lg:col-span-7 p-8 border-r border-white/10">
          <div className="mono-label mb-3">PORTRAIT PHOTO</div>
          <label
            className="block border border-dashed border-white/20 hover:border-white/50 p-6 cursor-pointer text-center mb-6"
            data-testid="avatar-photo-drop"
          >
            <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onPhoto} data-testid="avatar-photo-input" />
            <UploadSimple size={22} className="mx-auto mb-2 text-studio-dim" />
            <div className="text-sm">{photo ? photo.name : "Click to upload a front-facing portrait (jpg / png / webp)"}</div>
          </label>

          <div className="mono-label mb-3">SCRIPT</div>
          <textarea
            className="w-full h-40 bg-black border border-white/10 p-4 text-white font-mono text-sm focus:outline-none focus:border-white"
            value={script}
            maxLength={2000}
            onChange={(e) => setScript(e.target.value)}
            data-testid="avatar-script-input"
          />
          <div className="mono-label mb-2 mt-6">VOICE</div>
          <select className="input-box" value={voice} onChange={(e) => setVoice(e.target.value)} data-testid="avatar-voice-select">
            {voices.length === 0 && <option value="studio">studio</option>}
            {voices.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          <button onClick={generate} disabled={loading || !script.trim()} className="btn-accent mt-8 disabled:opacity-50" data-testid="avatar-generate-btn">
            <UserCircle size={18} /> {running ? `Rendering… (${job.status})` : loading ? "Starting…" : "Generate Avatar"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-5 p-6 bg-black/40">
          <div className="mono-label mb-3">OUTPUT</div>
          <div className="aspect-[3/4] bg-black border border-white/10 flex items-center justify-center mb-4 overflow-hidden" data-testid="avatar-preview">
            {job?.status === "completed" && job.url ? (
              <video src={assetUrl(job.url)} controls className="w-full h-full object-cover" data-testid="avatar-video-player" />
            ) : photoPreview ? (
              <img src={photoPreview} alt="" className="w-full h-full object-cover opacity-80" />
            ) : (
              <UserCircle size={48} className="text-studio-muted" />
            )}
          </div>
          {job?.status === "completed_preview" && job.url && (
            <audio src={assetUrl(job.url)} controls className="w-full" data-testid="avatar-audio-player" />
          )}
          {running && (
            <div className="mono-label text-studio-red animate-pulse" data-testid="avatar-job-status">
              ● {job.status.toUpperCase()} — RENDERING ON LOCAL GPU
            </div>
          )}
          {job?.status === "failed" && (
            <div className="text-xs text-studio-red font-mono" data-testid="avatar-job-error">{job.error}</div>
          )}
        </div>
      </div>
    </div>
  );
}
