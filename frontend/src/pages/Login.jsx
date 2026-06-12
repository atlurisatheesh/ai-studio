import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { ArrowRight } from "@phosphor-icons/react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      toast.success("Welcome back to ArcVox");
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
          src="https://static.prod-images.emergentagent.com/jobs/97450337-22c5-4ae8-a658-1a62539f373c/images/845696ab3772260af857de8809b585f61d363131669372b7ffc1366f8e11d5af.png"
          alt="ArcVox Studio"
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-studio-void/60 to-transparent" />
        <div className="relative h-full p-12 flex flex-col justify-between">
          <Link to="/" className="font-display text-2xl tracking-tight">
            ARC<span className="text-studio-red">▮</span>VOX
          </Link>
          <div>
            <div className="mono-label mb-4 text-studio-red">// RETURNING CREATOR</div>
            <div className="h-display text-5xl">The studio remembers you.</div>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="mono-label mb-4">// AUTHENTICATE</div>
          <h1 className="h-display text-4xl mb-10">Welcome back.</h1>
          <label className="block mb-6">
            <div className="mono-label mb-2">EMAIL</div>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-bare"
              data-testid="login-email-input"
              autoComplete="email"
            />
          </label>
          <label className="block mb-8">
            <div className="mono-label mb-2">PASSWORD</div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-bare"
              data-testid="login-password-input"
              autoComplete="current-password"
            />
          </label>
          {error && <div className="text-studio-red text-sm mb-4" data-testid="login-error">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="btn-accent w-full disabled:opacity-50"
            data-testid="login-submit-btn"
          >
            {loading ? "Authenticating…" : "Enter Studio"} <ArrowRight size={16} weight="bold" />
          </button>
          <div className="mt-8 mono-label text-studio-dim">
            NO ACCOUNT? <Link to="/signup" className="text-white hover:text-studio-red" data-testid="login-to-signup-link">CREATE ONE →</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
