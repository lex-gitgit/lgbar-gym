import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { api } from "./api";
import Sidebar from "./components/Sidebar";

import MobileTopBar from "./components/MobileTopBar";
import FlashMessages from "./components/FlashMessages";

api.initCsrf();

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Exercises = lazy(() => import("./pages/Exercises"));
const DayCreate = lazy(() => import("./pages/DayCreate"));
const DayDetail = lazy(() => import("./pages/DayDetail"));
const PresetForm = lazy(() => import("./pages/PresetForm"));
const PresetDetail = lazy(() => import("./pages/PresetDetail"));
const Leaderboard = lazy(() => import("./pages/Leaderboard"));
const Chat = lazy(() => import("./pages/Chat"));

function PageLoading() {
  return (
    <div className="main-content-inner">
      <div className="skeleton skeleton-text" style={{ height: 32, width: 200, marginBottom: 24 }} />
      <div className="skeleton skeleton-card" />
      <div className="skeleton skeleton-card" />
      <div className="skeleton skeleton-card" style={{ width: '70%' }} />
    </div>
  );
}

function ProtectedRoute({ user, children }) {
  if (!user) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [flash, setFlash] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    document.documentElement.setAttribute("data-theme", saved || "dark");
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const data = await api.get("/me/");
      setUser(data.username);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const showFlash = useCallback((message, type = "success") => {
    setFlash({ message, type });
    setTimeout(() => setFlash(null), 3000);
  }, []);

  const handleLogin = useCallback(async (username, password) => {
    await api.post("/login/", { username, password });
    setUser(username);
    showFlash("Logged in!");
  }, [showFlash]);

  const handleLogout = useCallback(async () => {
    try { await api.post("/logout/"); } catch {}
    setUser(null);
  }, []);

  if (loading) return null;

  if (!user) {
    return (
      <>
        <div className="gradient-bg" />
        <Suspense fallback={null}>
          <Login onLogin={handleLogin} showFlash={showFlash} />
        </Suspense>
        {flash && <FlashMessages message={flash.message} type={flash.type} />}
      </>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        onLogout={handleLogout}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <MobileTopBar onMenuClick={() => setSidebarOpen(true)} onLogout={handleLogout} />
      <main className="main-content">
        <Suspense fallback={<PageLoading />}>
          <div className={location.pathname === "/chat" ? "main-content-full" : "main-content-inner"}>
            <Routes>
              <Route path="/dashboard" element={<Dashboard showFlash={showFlash} />} />
              <Route path="/exercises" element={<Exercises showFlash={showFlash} />} />
              <Route path="/day/new" element={<DayCreate showFlash={showFlash} />} />
              <Route path="/day/:id" element={<DayDetail showFlash={showFlash} />} />
              <Route path="/presets/new" element={<PresetForm showFlash={showFlash} />} />
              <Route path="/presets/:id" element={<PresetDetail showFlash={showFlash} />} />
              <Route path="/presets/:id/edit" element={<PresetForm showFlash={showFlash} />} />
              <Route path="/leaderboard" element={<Leaderboard user={user} />} />
              <Route path="/chat" element={<Chat user={user} showFlash={showFlash} />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </Suspense>
      </main>
      {flash && <FlashMessages message={flash.message} type={flash.type} />}
    </div>
  );
}
