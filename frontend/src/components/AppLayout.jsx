import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import {
  House,
  Microphone,
  UserCircle,
  Waveform,
  TextT,
  ChatTeardropDots,
  Translate as TranslateIcon,
  FolderSimple,
  SignOut,
  Copy,
  ShieldCheck,
  CloudWarning,
  FilmSlate,
} from "@phosphor-icons/react";

const NAV = [
  { to: "/studio", label: "Overview", Icon: House, end: true, testid: "nav-overview" },
  { to: "/studio/voice", label: "Voice / TTS", Icon: Microphone, testid: "nav-voice" },
  { to: "/studio/clone", label: "Voice Clone", Icon: Copy, testid: "nav-clone" },
  { to: "/studio/transcribe", label: "Transcribe", Icon: Waveform, testid: "nav-transcribe" },
  { to: "/studio/avatar", label: "AI Avatar", Icon: UserCircle, testid: "nav-avatar" },
  { to: "/studio/dub", label: "Dubbing", Icon: FilmSlate, testid: "nav-dub" },
  { to: "/studio/agent", label: "Voice Agent", Icon: ChatTeardropDots, testid: "nav-agent" },
  { to: "/studio/script", label: "Script Writer", Icon: TextT, testid: "nav-script" },
  { to: "/studio/translate", label: "Translate", Icon: TranslateIcon, testid: "nav-translate" },
  { to: "/studio/projects", label: "Library", Icon: FolderSimple, testid: "nav-library" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [cloudLLM, setCloudLLM] = useState(false);

  useEffect(() => {
    api.get("/engines/status")
      .then((r) => setCloudLLM(Boolean(r.data?.cloud_llm_active)))
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen flex bg-studio-void text-white">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 flex flex-col" data-testid="sidebar">
        <Link to="/" className="px-6 py-5 border-b border-white/10 block">
          <div className="font-display text-2xl tracking-tight">
            ARC<span className="text-studio-red">▮</span>VOX
          </div>
          <div className="mono-label mt-1">PRIVATE STUDIO V2</div>
        </Link>

        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV.map(({ to, label, Icon, end, testid }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              data-testid={testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-2.5 text-sm font-medium border-l-2 ${
                  isActive
                    ? "border-studio-red text-white bg-white/[0.03]"
                    : "border-transparent text-studio-dim hover:text-white hover:border-white/30"
                }`
              }
            >
              <Icon size={18} weight={"regular"} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="mono-label mb-2">SIGNED IN</div>
          <div className="text-sm truncate" data-testid="sidebar-user-email">{user?.email}</div>
          {cloudLLM ? (
            <div className="mono-label text-amber-400 mt-1 flex items-center gap-1" data-testid="sidebar-privacy-badge">
              <CloudWarning size={12} /> CLOUD LLM ACTIVE
            </div>
          ) : (
            <div className="mono-label text-studio-red mt-1 flex items-center gap-1" data-testid="sidebar-privacy-badge">
              <ShieldCheck size={12} /> SELF-HOSTED · PRIVATE
            </div>
          )}
          <button
            onClick={async () => { await logout(); navigate("/"); }}
            className="mt-3 w-full flex items-center justify-center gap-2 border border-white/15 hover:border-white px-3 py-2 text-xs font-mono uppercase tracking-widest"
            data-testid="sidebar-logout-btn"
          >
            <SignOut size={14} /> Log Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="h-12 border-b border-white/10 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            {cloudLLM ? (
              <>
                <span className="w-2 h-2 bg-amber-400 animate-pulse-red" />
                <span className="mono-label text-amber-400 flex items-center gap-1.5">
                  <CloudWarning size={13} /> CLOUD LLM ACTIVE · LLM TEXT LEAVES THIS SERVER
                </span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 bg-studio-red animate-pulse-red" />
                <span className="mono-label">LOCAL ENGINES · NO CLOUD APIS</span>
              </>
            )}
          </div>
          <div className="mono-label">{new Date().toUTCString().slice(17, 25)} UTC</div>
        </div>
        <div className="p-6 md:p-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
