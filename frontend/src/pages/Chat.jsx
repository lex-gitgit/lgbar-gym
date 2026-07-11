import { useState, useEffect, useRef, useCallback, useLayoutEffect } from "react";
import { api } from "../api";

const POLL_INTERVAL = 5000;
const NEAR_BOTTOM_THRESHOLD = 100;

function formatTime(isoStr) {
  return new Date(isoStr).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export default function Chat({ user, showFlash }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const lastIdRef = useRef(0);
  const listRef = useRef(null);
  const didInitialScrollRef = useRef(false);

  const isNearBottom = useCallback(() => {
    const el = listRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_THRESHOLD;
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  const appendMessages = useCallback((incoming) => {
    if (!incoming.length) return;
    setMessages((prev) => {
      const seen = new Set(prev.map((m) => m.id));
      const fresh = incoming.filter((m) => !seen.has(m.id));
      if (!fresh.length) return prev;
      return [...prev, ...fresh];
    });
    lastIdRef.current = Math.max(lastIdRef.current, ...incoming.map((m) => m.id));
  }, []);

  useEffect(() => {
    let cancelled = false;

    api.get("/chat/").then((data) => {
      if (cancelled) return;
      setMessages(data);
      if (data.length) lastIdRef.current = data[data.length - 1].id;
      setLoading(false);
    }).catch(() => setLoading(false));

    const poll = () => {
      api.get(`/chat/?after=${lastIdRef.current}`).then((data) => {
        if (cancelled || !data.length) return;
        const wasNearBottom = isNearBottom();
        appendMessages(data);
        if (wasNearBottom) requestAnimationFrame(scrollToBottom);
      }).catch(() => {});
    };

    const interval = setInterval(poll, POLL_INTERVAL);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [appendMessages, isNearBottom, scrollToBottom]);

  // Jump to the latest message before the first paint, so chat never flashes open at the top.
  useLayoutEffect(() => {
    if (!loading && !didInitialScrollRef.current) {
      scrollToBottom();
      didInitialScrollRef.current = true;
    }
  }, [loading, scrollToBottom]);

  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      const msg = await api.post("/chat/", { text: trimmed });
      appendMessages([msg]);
      setText("");
      requestAnimationFrame(scrollToBottom);
    } catch (err) {
      showFlash?.(err.message || "Failed to send message", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div className="chat-page-header">
        <h1>Chat</h1>
      </div>

      <div className="chat-messages" ref={listRef}>
        {loading ? (
          <div className="skeleton skeleton-card" />
        ) : messages.length === 0 ? (
          <div className="empty-state">
            <p>No messages yet. Say hello!</p>
          </div>
        ) : (
          messages.map((m) => {
            const own = m.username === user;
            return (
              <div key={m.id} className={`chat-message ${own ? "chat-message--own" : ""}`}>
                <div className="chat-message-meta">
                  <strong>{m.username}</strong>
                  <span className="text-muted">{formatTime(m.created_at)}</span>
                </div>
                <div className="chat-message-bubble">{m.text}</div>
              </div>
            );
          })
        )}
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Type a message..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          disabled={sending}
        />
        <button type="submit" className="btn btn-primary" disabled={sending || !text.trim()}>
          Send
        </button>
      </form>
    </>
  );
}
