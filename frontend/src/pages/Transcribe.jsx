import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Waveform, UploadSimple } from "@phosphor-icons/react";

export default function Transcribe() {
  const [file, setFile] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [language, setLanguage] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setTranscript("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/voice/transcribe", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setTranscript(data.text || "");
      setLanguage(data.language || "");
      toast.success("Transcribed");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="transcribe-studio">
      <div className="mono-label mb-3">// MODULE — TRANSCRIBE</div>
      <h1 className="h-display text-5xl mb-2">Speech to Text</h1>
      <p className="text-studio-dim mb-10">Whisper-grade transcription. MP3, WAV, M4A, WEBM up to 25MB.</p>

      <div className="grid grid-cols-12 border border-white/10">
        <div className="col-span-12 lg:col-span-5 p-8 border-r border-white/10">
          <label className="block">
            <div className="mono-label mb-3">UPLOAD AUDIO FILE</div>
            <div className="border border-dashed border-white/15 p-10 text-center hover:border-white/40 transition-colors cursor-pointer" data-testid="transcribe-upload-zone">
              <UploadSimple size={32} className="mx-auto mb-3 text-studio-dim" />
              <div className="text-sm">{file ? file.name : "Click to select audio"}</div>
              <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                data-testid="transcribe-file-input"
              />
            </div>
          </label>
          <button onClick={submit} disabled={!file || loading} className="btn-accent mt-6 w-full disabled:opacity-50" data-testid="transcribe-submit-btn">
            <Waveform size={18} /> {loading ? "Transcribing…" : "Transcribe"}
          </button>
        </div>

        <div className="col-span-12 lg:col-span-7 p-8">
          <div className="mono-label mb-3">TRANSCRIPT {language && <span className="text-studio-red">· {language}</span>}</div>
          <div
            className="w-full min-h-[300px] bg-black border border-white/10 p-4 text-white text-sm whitespace-pre-wrap font-mono"
            data-testid="transcribe-result"
          >
            {transcript || <span className="text-studio-muted">Output will appear here…</span>}
          </div>
          {transcript && (
            <button
              onClick={() => { navigator.clipboard.writeText(transcript); toast.success("Copied"); }}
              className="btn-outline mt-4 text-xs"
              data-testid="transcribe-copy-btn"
            >
              COPY TEXT
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
