import { useState, useEffect, useRef, useCallback, useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api";

const STORAGE_KEY = "coach_chat";
const MAX_HISTORY = 20;
const GREETING = "What do you want? You should be mid-set right now. Ask your question or get back to it.";

function greetingMessage() {
  return { role: "assistant", content: GREETING, local: true };
}

function loadStoredMessages() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length ? parsed : null;
  } catch {
    return null;
  }
}

export default function CoachWidget({ user }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState(() => loadStoredMessages() || [greetingMessage()]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  useLayoutEffect(() => {
    if (open) scrollToBottom();
  }, [messages, open, sending, scrollToBottom]);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_HISTORY)));
  }, [messages]);

  const handleReset = () => {
    if (sending) return;
    setMessages([greetingMessage()]);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    const userMsg = { role: "user", content: trimmed };
    const history = [...messages.filter((m) => !m.local), userMsg].slice(-MAX_HISTORY);
    setMessages((prev) => [...prev, userMsg]);
    setText("");
    setSending(true);
    try {
      const data = await api.post("/coach/", {
        messages: history.map(({ role, content }) => ({ role, content })),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err.message || "Coach couldn't be reached. Try again in a bit.",
          local: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  // The full-screen Chat page's input row spans the same bottom edge the
  // launcher would sit on — hide there rather than overlap it. State stays
  // alive since this component isn't unmounted, just not rendered.
  if (location.pathname === "/chat") return null;

  return (
    <>
      <button
        type="button"
        className="coach-launcher"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close Coach" : "Open Coach"}
        aria-expanded={open}
      >
        {open ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <line x1="6" y1="6" x2="18" y2="18" />
            <line x1="6" y1="18" x2="18" y2="6" />
          </svg>
        ) : (
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
        )}
      </button>

      {open && (
        <div className="coach-panel" role="dialog" aria-label="Coach chat">
          <div className="coach-panel-header">
            <span className="coach-panel-title">Coach</span>
            <div className="flex gap-sm">
              <button
                type="button"
                className="coach-panel-btn"
                onClick={handleReset}
                disabled={sending}
                aria-label="Start a new conversation"
                title="New conversation"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="1 4 1 10 7 10" />
                  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                </svg>
              </button>
              <button type="button" className="coach-panel-btn" onClick={() => setOpen(false)} aria-label="Close Coach">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="6" y1="18" x2="18" y2="6" />
                </svg>
              </button>
            </div>
          </div>

          <div className="coach-panel-messages" ref={listRef}>
            {messages.map((m, i) => {
              const own = m.role === "user";
              return (
                <div key={i} className={`chat-message ${own ? "chat-message--own" : ""}`}>
                  <div className="chat-message-meta">
                    <strong>{own ? user : "Coach"}</strong>
                  </div>
                  <div className="chat-message-bubble">{m.content}</div>
                </div>
              );
            })}
            {sending && (
              <div className="chat-message">
                <div className="chat-message-meta">
                  <strong>Coach</strong>
                </div>
                <div className="chat-message-bubble coach-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
          </div>

          <form className="chat-input-row coach-panel-input" onSubmit={handleSend}>
            <input
              type="text"
              placeholder="Ask Coach something…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
              disabled={sending}
            />
            <button type="submit" className="btn btn-primary" disabled={sending || !text.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
