import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import AppLayout from "@/components/AppLayout";
import Dashboard from "@/pages/Dashboard";
import TTSStudio from "@/pages/TTSStudio";
import AvatarStudio from "@/pages/AvatarStudio";
import Transcribe from "@/pages/Transcribe";
import VoiceClone from "@/pages/VoiceClone";
import VoiceAgent from "@/pages/VoiceAgent";
import Translate from "@/pages/Translate";
import ScriptStudio from "@/pages/ScriptStudio";
import DubbingStudio from "@/pages/DubbingStudio";
import ProjectsPage from "@/pages/ProjectsPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen bg-studio-void flex items-center justify-center" data-testid="auth-loading">
        <div className="font-mono text-xs uppercase tracking-[0.3em] text-studio-dim">Authenticating…</div>
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/studio" replace />;
  return children;
}

function App() {
  useEffect(() => {
    document.title = "ArcVox — Private AI Voice & Avatar Studio";
  }, []);

  return (
    <div className="App bg-studio-void min-h-screen text-white">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
            <Route
              path="/studio"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="voice" element={<TTSStudio />} />
              <Route path="avatar" element={<AvatarStudio />} />
              <Route path="dub" element={<DubbingStudio />} />
              <Route path="clone" element={<VoiceClone />} />
              <Route path="transcribe" element={<Transcribe />} />
              <Route path="agent" element={<VoiceAgent />} />
              <Route path="translate" element={<Translate />} />
              <Route path="script" element={<ScriptStudio />} />
              <Route path="projects" element={<ProjectsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster theme="dark" position="bottom-right" />
      </AuthProvider>
    </div>
  );
}

export default App;
