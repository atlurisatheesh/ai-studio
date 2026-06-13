import { useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Waveform, UploadSimple } from "@phosphor-icons/react";

function fmt(secs) {
  const m = Math.floor(secs / 60);
  const s = (secs % 60).toFixed(1).padStart(4, "0");
  return `${m}:${s}`;
}

export default function Transcribe() {
  const [file, setFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [segments, setSegments] = useState([]);
  const [language, setLanguage] = useState("");
  const [duration, setDuration] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef(null);

  // Keep audio URL in sync with selected file
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setTranscript("");
    setSegments([]);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/voice/transcribe", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTranscript(data.text || "");
      setSegments(data.segments || []);
      setLanguage(data.language || "");
      setDuration(data.duration || null);
      toast.success("Transcribed");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const seekTo = (start) => {
    if (audioRef.current) {
      audioRef.current.currentTime = start;
      audioRef.current.play().catch(() => {});
    }
  };

  const activeIdx = segments.findIndex(
    (s) => currentTime >= s.start && currentTime < s.end
  );

  return (
    <div data-testid="transcribe-studio">
      <div className="mono-label mb-3">// MODULE — TRANSCRIBE</div>
      <h1 className="h-display text-5xl mb-2">Speech to Text</h1>
      <p className="text-studio-dim mb-10">
        Whisper large-v3 accuracy — on your machine. MP3, WAV, M4A, WEBM.
        {duration && <span className="text-studio-red ml-2">· {fmt(duration)} audio</span>}
      </p>

      <div className="grid grid-cols-12 border border-white/10">
        {/* LEFT: upload + player */}
        <div className="col-span-12 lg:col-span-5 p-8 border-r border-white/10 flex flex-col gap-6">
          <label className="block">
            <div className="mono-label mb-3">UPLOAD AUDIO FILE</div>
            <div
              className="border border-dashed border-white/15 p-10 text-center hover:border-white/40 transition-colors cursor-pointer"
              data-testid="transcribe-upload-zone"
            >
              <UploadSimple size={32} className="mx-auto mb-3 text-studio-dim" />
              <div className="text-sm">{file ? file.name : "Click to select audio"}</div>
              <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setTranscript("");
                  setSegments([]);
                }}
                data-testid="transcribe-file-input"
              />
            </div>
          </label>

          {audioUrl && (
            <div>
              <div className="mono-label mb-2">AUDIO PLAYER</div>
              <audio
                ref={audioRef}
                src={audioUrl}
                controls
                className="w-full"
                onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
                data-testid="transcribe-audio-player"
              />
              {segments.length > 0 && (
                <div className="text-xs text-studio-dim mt-2">
                  Click a segment below to jump to that point in the audio.
                </div>
              )}
            </div>
          )}

          <button
            onClick={submit}
            disabled={!file || loading}
            className="btn-accent w-full disabled:opacity-50"
            data-testid="transcribe-submit-btn"
          >
            <Waveform size={18} /> {loading ? "Transcribing…" : "Transcribe"}
          </button>
        </div>

        {/* RIGHT: transcript + segments */}
        <div className="col-span-12 lg:col-span-7 p-8 flex flex-col gap-4">
          {segments.length > 0 ? (
            <>
              <div className="mono-label">
                SEGMENTS
                {language && <span className="text-studio-red ml-2">· {language.toUpperCase()}</span>}
              </div>
              <div
                className="flex-1 overflow-y-auto space-y-1 max-h-[60vh] pr-1"
                data-testid="transcribe-segments"
              >
                {segments.map((seg, i) => (
                  <button
                    key={i}
                    onClick={() => seekTo(seg.start)}
                    className={`w-full text-left px-3 py-2 border transition-colors ${
                      i === activeIdx
                        ? "border-studio-red bg-studio-red/10 text-white"
                        : "border-white/10 bg-black hover:border-white/30 text-studio-dim hover:text-white"
                    }`}
                    data-testid={`segment-${i}`}
                  >
                    <span className="font-mono text-xs mr-3 opacity-60">
                      {fmt(seg.start)}
                    </span>
                    <span className="text-sm">{seg.text}</span>
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { navigator.clipboard.writeText(transcript); toast.success("Copied"); }}
                  className="btn-outline text-xs"
                  data-testid="transcribe-copy-btn"
                >
                  COPY TEXT
                </button>
                <button
                  onClick={() => {
                    const srt = segments.map((s, i) => {
                      const toSRT = (t) => {
                        const h = Math.floor(t / 3600);
                        const m = Math.floor((t % 3600) / 60);
                        const sec = (t % 60).toFixed(3).replace(".", ",").padStart(6, "0");
                        return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${sec}`;
                      };
                      return `${i + 1}\n${toSRT(s.start)} --> ${toSRT(s.end)}\n${s.text}\n`;
                    }).join("\n");
                    navigator.clipboard.writeText(srt);
                    toast.success("SRT copied");
                  }}
                  className="btn-outline text-xs"
                  data-testid="transcribe-srt-btn"
                >
                  COPY SRT
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="mono-label">
                TRANSCRIPT
                {language && <span className="text-studio-red ml-2">· {language.toUpperCase()}</span>}
              </div>
              <div
                className="w-full min-h-[300px] bg-black border border-white/10 p-4 text-white text-sm whitespace-pre-wrap font-mono"
                data-testid="transcribe-result"
              >
                {transcript || <span className="text-studio-muted">Output will appear here…</span>}
              </div>
              {transcript && (
                <button
                  onClick={() => { navigator.clipboard.writeText(transcript); toast.success("Copied"); }}
                  className="btn-outline text-xs self-start"
                  data-testid="transcribe-copy-btn"
                >
                  COPY TEXT
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
