import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Key, Copy, Trash, Info } from "@phosphor-icons/react";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [freshKey, setFreshKey] = useState(null);

  const load = () => api.get("/keys").then((r) => setKeys(r.data || [])).catch(() => {});

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!name.trim()) return toast.error("Name the key, e.g. \"bulk-dub-worker\"");
    setCreating(true);
    try {
      const { data } = await api.post("/keys", { name: name.trim() });
      setFreshKey(data);
      setName("");
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setCreating(false);
    }
  };

  const revoke = async (id) => {
    try {
      await api.delete(`/keys/${id}`);
      toast.success("Key revoked");
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const copy = (text) => {
    navigator.clipboard?.writeText(text);
    toast.success("Copied");
  };

  return (
    <div data-testid="api-keys-root">
      <div className="mono-label mb-3">// SETTINGS — API KEYS</div>
      <h1 className="h-display text-5xl mb-2">API Keys</h1>
      <p className="text-studio-dim mb-10">
        Programmatic access for bulk jobs — script catalog-scale dubbing or TTS without a browser session.
        Send the key as <code className="text-white">Authorization: Bearer ak_live_...</code>; it works on every endpoint a logged-in session can call.
      </p>

      {freshKey && (
        <div className="mb-6 border border-studio-red bg-studio-red/5 p-4" data-testid="api-key-fresh">
          <div className="mono-label text-studio-red mb-2 flex items-center gap-1.5">
            <Info size={14} /> COPY THIS NOW — IT WON'T BE SHOWN AGAIN
          </div>
          <div className="flex items-center gap-2">
            <code className="text-sm break-all flex-1 bg-black/40 px-3 py-2">{freshKey.key}</code>
            <button onClick={() => copy(freshKey.key)} className="border border-white/15 hover:border-white px-3 py-2" data-testid="api-key-copy-btn">
              <Copy size={16} />
            </button>
          </div>
        </div>
      )}

      <div className="border border-white/10 p-6 mb-10">
        <div className="mono-label mb-3">CREATE A NEW KEY</div>
        <div className="flex gap-3">
          <input
            className="input-box flex-1"
            placeholder="e.g. bulk-dub-worker"
            value={name}
            onChange={(e) => setName(e.target.value)}
            data-testid="api-key-name-input"
          />
          <button onClick={create} disabled={creating} className="btn-accent disabled:opacity-50" data-testid="api-key-create-btn">
            <Key size={16} /> {creating ? "Creating…" : "Create Key"}
          </button>
        </div>
      </div>

      <div className="mono-label mb-3">YOUR KEYS</div>
      {keys.length === 0 ? (
        <div className="border border-white/10 p-10 text-studio-dim text-sm" data-testid="api-keys-empty">
          No API keys yet.
        </div>
      ) : (
        <div className="border border-white/10" data-testid="api-keys-list">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between border-b border-white/10 last:border-b-0 px-5 py-4">
              <div>
                <div className="text-sm font-medium">{k.name}</div>
                <div className="mono-label text-studio-dim mt-1">
                  {k.prefix}… · created {new Date(k.created_at).toLocaleDateString()}
                  {k.last_used_at && ` · last used ${new Date(k.last_used_at).toLocaleDateString()}`}
                  {k.revoked_at && <span className="text-studio-red"> · REVOKED</span>}
                </div>
              </div>
              {!k.revoked_at && (
                <button onClick={() => revoke(k.id)} className="border border-white/15 hover:border-studio-red hover:text-studio-red px-3 py-2" data-testid={`api-key-revoke-${k.id}`}>
                  <Trash size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
