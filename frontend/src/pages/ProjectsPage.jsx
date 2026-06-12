import { useEffect, useState } from "react";
import { api, formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { Trash, Play } from "@phosphor-icons/react";

const KIND_FILTERS = ["all", "tts", "video", "avatar", "transcription", "music", "translation", "script"];

export default function ProjectsPage() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [active, setActive] = useState(null);

  const load = (kind = filter) => {
    const url = kind === "all" ? "/projects" : `/projects?kind=${kind}`;
    api.get(url).then((r) => setItems(r.data)).catch((e) => toast.error(formatApiError(e)));
  };
  useEffect(() => { load(filter); }, [filter]);

  const del = async (id) => {
    if (!window.confirm("Delete this project?")) return;
    try {
      await api.delete(`/projects/${id}`);
      toast.success("Deleted");
      load();
      if (active?.id === id) setActive(null);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  return (
    <div data-testid="projects-page">
      <div className="mono-label mb-3">// LIBRARY</div>
      <h1 className="h-display text-5xl mb-6">Project Library</h1>

      <div className="flex flex-wrap gap-2 mb-6">
        {KIND_FILTERS.map((k) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            data-testid={`filter-${k}`}
            className={`px-4 py-2 mono-label border ${filter === k ? "border-studio-red text-studio-red" : "border-white/15 text-studio-dim hover:text-white"}`}
          >
            {k.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-0 border border-white/10">
        <div className="col-span-12 lg:col-span-7 border-r border-white/10 max-h-[70vh] overflow-y-auto" data-testid="projects-list">
          {items.length === 0 && <div className="p-8 text-studio-muted text-sm">No projects yet.</div>}
          {items.map((p) => (
            <div
              key={p.id}
              onClick={() => setActive(p)}
              data-testid={`project-row-${p.id}`}
              className={`p-5 border-b border-white/10 cursor-pointer transition-colors ${active?.id === p.id ? "bg-white/[0.05]" : "hover:bg-white/[0.02]"}`}
            >
              <div className="flex justify-between items-start">
                <div className="min-w-0">
                  <div className="mono-label text-studio-red mb-1">{p.kind.toUpperCase()}</div>
                  <div className="text-sm font-medium truncate">{p.title || "Untitled"}</div>
                  <div className="mono-label text-studio-dim mt-1">{new Date(p.created_at).toLocaleString()}</div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); del(p.id); }}
                  className="text-studio-dim hover:text-studio-red shrink-0"
                  data-testid={`delete-project-${p.id}`}
                >
                  <Trash size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="col-span-12 lg:col-span-5 p-6" data-testid="project-preview">
          {!active ? (
            <div className="text-studio-muted text-sm text-center py-20">Select a project to preview.</div>
          ) : (
            <div>
              <div className="mono-label mb-2 text-studio-red">{active.kind.toUpperCase()}</div>
              <div className="font-medium mb-1">{active.title}</div>
              <div className="mono-label text-studio-dim mb-4">{new Date(active.created_at).toLocaleString()}</div>

              {active.payload?.audio_base64 && (
                <audio src={`data:audio/mp3;base64,${active.payload.audio_base64}`} controls className="w-full mb-4" />
              )}
              {active.payload?.portrait_base64 && (
                <img src={`data:image/png;base64,${active.payload.portrait_base64}`} alt="" className="w-full mb-4 border border-white/10" />
              )}
              {active.payload?.file && (
                <video src={`${API}/assets/${active.payload.file}`} controls className="w-full mb-4 border border-white/10" />
              )}

              {(active.payload?.text || active.payload?.script || active.payload?.translated || active.payload?.composition_plan) && (
                <pre className="bg-black border border-white/10 p-3 text-xs whitespace-pre-wrap text-studio-dim max-h-64 overflow-y-auto">
                  {active.payload?.text || active.payload?.script || active.payload?.translated || active.payload?.composition_plan}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
