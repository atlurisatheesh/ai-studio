import { useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { ChatTeardropDots, PaperPlaneRight } from "@phosphor-icons/react";

export default function VoiceAgent() {
  const [sessionId] = useState(() => "sess_" + Math.random().toString(36).slice(2, 10));
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hey, I'm the ArcVox agent. Ask me anything — I'll reply with text and optionally voice." },
  ]);
  const [input, setInput] = useState("");
  const [voice, setVoice] = useState("studio");
  const [voices, setVoices] = useState([{ id: "studio", name: "Studio" }]);
  const [withVoice, setWithVoice] = useState(true);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get("/voice/library").then((r) => {
      const cloned = (r.data.cloned || [])
        .filter((c) => c.status === "ready")
        .map((c) => ({ id: c.id, name: `${c.name} (clone)` }));
      const sys = r.data.system || [];
      if (sys.length) {
        setVoices([...sys, ...cloned]);
        setVoice(sys[0].id);
      }
    }).catch(() => {});
  }, []);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setMessages((m) => [...m, { role: "user", text: userMsg }]);
    setInput("");
    setLoading(true);
    try {
      const { data } = await api.post("/agent/chat", {
        session_id: sessionId,
        message: userMsg,
        voice: withVoice ? voice : null,
      });
      setMessages((m) => [...m, { role: "assistant", text: data.reply, audio: data.audio_base64 }]);
      if (data.audio_base64) {
        const a = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
        a.play().catch(() => {});
      }
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 100);
    }
  };

  return (
    <div data-testid="voice-agent-studio" className="h-[calc(100vh-180px)] flex flex-col">
      <div>
        <div className="mono-label mb-3">// MODULE — VOICE AGENT</div>
        <h1 className="h-display text-5xl mb-2">Voice Agent</h1>
        <p className="text-studio-dim mb-6">Conversational AI with voice — running on your own local LLM. No conversation ever leaves this server.</p>
      </div>

      <div className="flex-1 grid grid-cols-12 border border-white/10 min-h-0">
        <div className="col-span-12 lg:col-span-9 flex flex-col border-r border-white/10 min-h-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="agent-messages">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] p-4 border ${m.role === "user" ? "bg-studio-red/10 border-studio-red/40" : "bg-black border-white/10"}`} data-testid={`agent-msg-${i}`}>
                  <div className="mono-label mb-1 text-studio-dim">{m.role === "user" ? "YOU" : "AGENT"}</div>
                  <div className="text-sm leading-relaxed">{m.text}</div>
                  {m.audio && (
                    <audio src={`data:audio/wav;base64,${m.audio}`} controls className="mt-3 w-full" />
                  )}
                </div>
              </div>
            ))}
            {loading && <div className="mono-label text-studio-dim animate-pulse-red">AGENT IS THINKING…</div>}
          </div>
          <div className="border-t border-white/10 p-4 flex gap-3">
            <input
              className="flex-1 bg-black border border-white/10 px-4 py-3 focus:outline-none focus:border-white"
              placeholder="Type a message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
              data-testid="agent-input"
            />
            <button onClick={send} disabled={loading || !input.trim()} className="btn-accent disabled:opacity-50" data-testid="agent-send-btn">
              <PaperPlaneRight size={18} />
            </button>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-3 p-6 bg-black/40">
          <div className="mono-label mb-3">SETTINGS</div>
          <label className="flex items-center gap-2 mb-4 text-sm">
            <input type="checkbox" checked={withVoice} onChange={(e) => setWithVoice(e.target.checked)} data-testid="agent-voice-toggle" />
            Speak replies aloud
          </label>
          <div className="mono-label mb-2">VOICE</div>
          <select value={voice} onChange={(e) => setVoice(e.target.value)} className="input-box mb-4" data-testid="agent-voice-select">
            {voices.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          <div className="mono-label mt-6 mb-2">SESSION</div>
          <div className="font-mono text-xs text-studio-dim break-all">{sessionId}</div>
        </div>
      </div>
    </div>
  );
}
