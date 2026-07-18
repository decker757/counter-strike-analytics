import { useState, useRef, useEffect } from "react";

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

interface ChatPanelProps {
  currentTick: number;
  visible: boolean;
  onClose: () => void;
}

export default function ChatPanel({ currentTick, visible, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "system",
      content: "AI Coach ready. Ask me about the match, or click 'Explain' to analyze the current moment.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [llmAvailable, setLlmAvailable] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function checkStatus() {
      try {
        const resp = await fetch("http://localhost:8000/api/llm/status");
        const data = await resp.json();
        setLlmAvailable(data.available);
      } catch {
        setLlmAvailable(false);
      }
    }
    if (visible) checkStatus();
  }, [visible]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await fetch("http://localhost:8000/api/llm/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: messages.filter((m) => m.role !== "system"),
        }),
      });
      const data = await resp.json();

      if (data.status === "unavailable") {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ ${data.message || "LLM not available. Install Ollama and pull a model to enable coaching."}`,
          },
        ]);
        setLlmAvailable(false);
      } else if (data.text) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.text },
        ]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Connection error: ${e instanceof Error ? e.message : "Could not reach the server."}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const explainCurrentMoment = async () => {
    if (loading) return;
    setLoading(true);

    try {
      const resp = await fetch(`http://localhost:8000/api/llm/explain/${currentTick}`);
      const data = await resp.json();

      if (data.status === "unavailable") {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ ${data.message || "LLM not available."}`,
          },
        ]);
        setLlmAvailable(false);
      } else if (data.text) {
        setMessages((prev) => [
          ...prev,
          { role: "user", content: `Explain what's happening at tick ${currentTick}` },
          { role: "assistant", content: data.text },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Could not fetch explanation." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (!visible) return null;

  return (
    <div className="overlay-panel animate-in" style={{ maxHeight: "70vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontWeight: 600,
        fontSize: 13,
        color: "var(--text-primary)",
      }}>
        <span>
          🤖 AI Coach
          {llmAvailable === false && (
            <span style={{ fontSize: 11, color: "var(--warning)", marginLeft: 8, fontWeight: 400 }}>
              offline
            </span>
          )}
          {llmAvailable === true && (
            <span style={{ fontSize: 10, color: "var(--success)", marginLeft: 6, fontWeight: 400 }}>
              ● online
            </span>
          )}
        </span>
        <button
          onClick={onClose}
          className="btn btn-icon"
          style={{ padding: "2px 8px", fontSize: 14 }}
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        minHeight: 200,
        maxHeight: 380,
      }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
              padding: "8px 12px",
              borderRadius: 8,
              background:
                msg.role === "user"
                  ? "var(--accent)"
                  : msg.role === "system"
                  ? "rgba(255,255,255,0.04)"
                  : "rgba(255,255,255,0.06)",
              border: msg.role === "user"
                ? "1px solid rgba(77, 166, 255, 0.4)"
                : "1px solid var(--border-subtle)",
              color: msg.role === "user" ? "#fff" : "var(--text-primary)",
              fontSize: 12,
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 0" }}>
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span style={{ color: "var(--text-secondary)", fontSize: 11, fontStyle: "italic", marginLeft: 4 }}>
              Thinking…
            </span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: "8px 14px 12px",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        gap: 8,
      }}>
        <button
          onClick={explainCurrentMoment}
          disabled={loading}
          className="btn btn-success"
          style={{ fontSize: 11, whiteSpace: "nowrap" }}
        >
          ⚡ Explain Now
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the match…"
          disabled={loading}
          style={{
            flex: 1,
            padding: "6px 10px",
            background: "rgba(255,255,255,0.06)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)",
            fontSize: 12,
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className="btn btn-primary"
          style={{ fontSize: 12, padding: "6px 14px" }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
