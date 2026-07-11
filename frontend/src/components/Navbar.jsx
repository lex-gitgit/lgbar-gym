import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute("data-theme") === "light" ? "dark" : "light";
  html.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}

export default function Navbar({ user, onLogout }) {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    setTheme(localStorage.getItem("theme") || "light");
  }, []);

  return (
    <nav style={{
      background: "var(--nav-bg)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--border)",
      position: "sticky",
      top: 0,
      zIndex: 100,
      transition: "background 0.3s",
    }}>
      <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px" }}>
        <Link to="/dashboard" style={{
          fontSize: "1.2rem",
          fontWeight: 700,
          background: "linear-gradient(135deg, var(--gradient-1), var(--gradient-2))",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
          textDecoration: "none",
        }}>
          Gym Logger
        </Link>
        <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
          <Link to="/dashboard" style={{ color: "var(--text)", textDecoration: "none", fontSize: "0.95rem", fontWeight: 500, padding: "8px 14px", borderRadius: "10px" }}>Dashboard</Link>
          <Link to="/exercises" style={{ color: "var(--text)", textDecoration: "none", fontSize: "0.95rem", fontWeight: 500, padding: "8px 14px", borderRadius: "10px" }}>Exercises</Link>
          <Link to="/presets" style={{ color: "var(--text)", textDecoration: "none", fontSize: "0.95rem", fontWeight: 500, padding: "8px 14px", borderRadius: "10px" }}>Presets</Link>
          <Link to="/day/new" style={{ color: "var(--text)", textDecoration: "none", fontSize: "0.95rem", fontWeight: 500, padding: "8px 14px", borderRadius: "10px" }}>Log Day</Link>
          <form onSubmit={(e) => { e.preventDefault(); onLogout(); }} style={{ display: "inline" }}>
            <button type="submit" style={{
              color: "var(--text)", fontSize: "0.95rem", fontWeight: 500,
              padding: "8px 14px", borderRadius: "10px", background: "none",
              border: "none", cursor: "pointer", fontFamily: "inherit",
            }}>Logout</button>
          </form>
          <button
            onClick={toggleTheme}
            style={{
              background: "var(--bg-card)", border: "1px solid var(--border)",
              borderRadius: "50%", width: "38px", height: "38px",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", fontSize: "1.1rem", color: "var(--text)",
            }}
            title="Toggle theme"
          >
            {theme === "dark" ? "🌙" : "☀️"}
          </button>
        </div>
      </div>
    </nav>
  );
}
