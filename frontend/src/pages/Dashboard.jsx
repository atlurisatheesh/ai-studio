import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  Microphone,
  UserCircle,
  Waveform,
  ChatTeardropDots,
  Translate as TranslateIcon,
  Copy,
  TextT,
  ArrowUpRight,
  CircleNotch,
} from "@phosphor-icons/react";

const MODULES = [
  { Icon: Microphone, label: "Voice / TTS", desc: "Studio voices on your own GPU.", to: "/studio/voice", testid: "module-voice" },
  { Icon: Copy, label: "Voice Clone", desc: "Zero-shot cloning. Sample never leaves.", to: "/studio/clone", testid: "module-clone" },
  { Icon: Waveform, label: "Transcribe", desc: "Whisper large-v3, fully local.", to: "/studio/transcribe", testid: "module-transcribe" },
  { Icon: UserCircle, label: "AI Avatar", desc: "Your photo, lip-synced locally.", to: "/studio/avatar", testid: "module-avatar" },
  { Icon: ChatTeardropDots, label: "Voice Agent", desc: "Local LLM chat + voice.", to: "/studio/agent", testid: "module-agent" },
  { Icon: TextT, label: "Script Writer", desc: "AI scripts, on-device LLM.", to: "/studio/script", testid: "module-script" },
  { Icon: TranslateIcon, label: "Translate", desc: "Private translation, tone preserved.", to: "/studio/translate", testid: "module-translate" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [engines, setEngines] = useState(null);

  useEffect(() => {
    api.get("/projects?limit=8").then((r) => setProjects(r.data)).catch(() => {});
    api.get("/engines/status").then((r) => setEngines(r.data)).catch(() => {});
  }, []);

  return (
    <div data-testid="dashboard-root">
      <div className="mono-label mb-3">// OVERVIEW</div>
      <h1 className="h-display text-5xl mb-2">Hello, {user?.name?.split(" ")[0] || "creator"}.</h1>
      <p className="text-studio-dim mb-6">Pick a module. Or jump back into a recent project.</p>

      <div className="border border-white/10 mb-10 grid grid-cols-2 lg:grid-cols-4" data-testid="engine-status-strip">
        {engines ? (
          [
            { name: "SPEECH-TO-TEXT", ok: engines.stt?.installed, detail: engines.stt?.model },
            { name: "TEXT-TO-SPEECH", ok: engines.tts?.chatterbox_installed || engines.tts?.piper_installed, detail: engines.tts?.backend },
            { name: "LOCAL LLM", ok: engines.llm?.running, detail: engines.llm?.model },
            { name: "AVATAR LIPSYNC", ok: engines.avatar?.engine_ready, detail: engines.avatar?.mode },
          ].map((e) => (
            <div key={e.name} className="p-4 border-r border-white/10 last:border-r-0">
              <div className="mono-label mb-1">{e.name}</div>
              <div className={`text-xs font-mono ${e.ok ? "text-[#00FF66]" : "text-studio-dim"}`}>
                {e.ok ? "● ONLINE" : "○ OFFLINE"} <span className="text-studio-dim">· {e.detail || "—"}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="p-4 col-span-4 flex items-center gap-2 text-studio-dim text-xs font-mono">
            <CircleNotch size={14} className="animate-spin" /> CHECKING LOCAL ENGINES…
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 border border-white/10 -mb-px">
        {MODULES.map(({ Icon, label, desc, to, testid }) => (
          <Link
            key={label}
            to={to}
            data-testid={testid}
            className="border-r border-b border-white/10 p-6 group hover:bg-white/[0.03] transition-colors"
          >
            <Icon size={26} weight="light" className="text-studio-red mb-4" />
            <div className="text-lg font-medium mb-1">{label}</div>
            <div className="text-sm text-studio-dim mb-6">{desc}</div>
            <div className="mono-label text-studio-dim group-hover:text-white flex items-center gap-1">
              OPEN <ArrowUpRight size={12} />
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="mono-label mb-2">// RECENT PROJECTS</div>
            <h2 className="h-display text-3xl">Library</h2>
          </div>
          <Link to="/studio/projects" className="mono-label hover:text-studio-red" data-testid="dashboard-view-all-projects">
            VIEW ALL →
          </Link>
        </div>
        {projects.length === 0 ? (
          <div className="border border-white/10 p-10 text-studio-dim text-sm" data-testid="dashboard-no-projects">
            No projects yet. Try the <Link to="/studio/voice" className="underline text-studio-red">Voice Generator</Link> first.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border border-white/10">
            {projects.slice(0, 8).map((p) => (
              <div key={p.id} className="border-r border-b border-white/10 p-5">
                <div className="mono-label text-studio-red mb-2">{p.kind.toUpperCase()}</div>
                <div className="text-sm font-medium truncate mb-2">{p.title || "Untitled"}</div>
                <div className="mono-label text-studio-dim">{new Date(p.created_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
