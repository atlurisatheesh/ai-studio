import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { ArrowRight } from "@phosphor-icons/react";

export default function Signup() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(email, password, name);
      toast.success("Welcome to ArcVox");
      navigate("/studio");
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-studio-void grid grid-cols-1 md:grid-cols-2">
      <div className="hidden md:block relative border-r border-white/10 grain">
        <img
          src="https://static.prod-images.emergentagent.com/jobs/97450337-22c5-4ae8-a658-1a62539f373c/images/dd146a69318ad148248c8d4ee29bf17024a265dd1ff2eb6695857f65d83d85fc.png"
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-studio-void/60 to-transparent" />
        <div className="relative h-full p-12 flex flex-col justify-between">
          <Link to="/" className="font-display text-2xl tracking-tight">
            ARC<span className="text-studio-red">▮</span>VOX
          </Link>
          <div>
            <div className="mono-label mb-4 text-studio-red">// JOIN THE STUDIO</div>
            <div className="h-display text-5xl">Skip 14 vendors.<br />Use one.</div>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="signup-form">
          <div className="mono-label mb-4">// CREATE ACCOUNT</div>
          <h1 className="h-display text-4xl mb-10">Start creating.</h1>
          <label className="block mb-6">
            <div className="mono-label mb-2">NAME</div>
            <input value={name} required onChange={(e) => setName(e.target.value)} className="input-bare" data-testid="signup-name-input" />
          </label>
          <label className="block mb-6">
            <div className="mono-label mb-2">EMAIL</div>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-bare" data-testid="signup-email-input" autoComplete="email" />
          </label>
          <label className="block mb-8">
            <div className="mono-label mb-2">PASSWORD (MIN 6)</div>
            <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className="input-bare" data-testid="signup-password-input" autoComplete="new-password" />
          </label>
          {error && <div className="text-studio-red text-sm mb-4" data-testid="signup-error">{error}</div>}
          <button type="submit" disabled={loading} className="btn-accent w-full disabled:opacity-50" data-testid="signup-submit-btn">
            {loading ? "Creating…" : "Create Account"} <ArrowRight size={16} weight="bold" />
          </button>
          <div className="mt-8 mono-label text-studio-dim">
            HAVE AN ACCOUNT? <Link to="/login" className="text-white hover:text-studio-red" data-testid="signup-to-login-link">LOG IN →</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
