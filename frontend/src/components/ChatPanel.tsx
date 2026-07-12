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

  // Check LLM availability on mount
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

  // Auto-scroll to bottom
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
    <div
      style={{
        position: "absolute",
        top: 10,
        right: 10,
        width: 360,
        maxHeight: "70vh",
        background: "rgba(20, 20, 30, 0.95)",
        borderRadius: 10,
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        color: "#e0e0e0",
        fontFamily: "sans-serif",
        fontSize: 13,
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "10px 14px",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontWeight: 600,
        }}
      >
        <span>
          🤖 AI Coach
          {llmAvailable === false && (
            <span style={{ fontSize: 11, color: "#ff9800", marginLeft: 8 }}>
              (offline)
            </span>
          )}
        </span>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#aaa",
            cursor: "pointer",
            fontSize: 16,
          }}
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          minHeight: 200,
          maxHeight: 400,
        }}
      >
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
                  ? "#2196F3"
                  : msg.role === "system"
                  ? "rgba(255,255,255,0.05)"
                  : "rgba(255,255,255,0.1)",
              color: msg.role === "user" ? "#fff" : "#ddd",
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
          <div style={{ color: "#888", fontSize: 12, fontStyle: "italic" }}>
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "8px 14px",
          borderTop: "1px solid rgba(255,255,255,0.1)",
          display: "flex",
          gap: 8,
        }}
      >
        <button
          onClick={explainCurrentMoment}
          disabled={loading}
          style={{
            padding: "6px 10px",
            background: "#4CAF50",
            border: "none",
            borderRadius: 4,
            color: "#fff",
            cursor: "pointer",
            fontSize: 11,
            whiteSpace: "nowrap",
            opacity: loading ? 0.5 : 1,
          }}
        >
          Explain Now
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the match..."
          disabled={loading}
          style={{
            flex: 1,
            padding: "6px 10px",
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.2)",
            borderRadius: 4,
            color: "#fff",
            fontSize: 12,
            outline: "none",
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            padding: "6px 12px",
            background: "#2196F3",
            border: "none",
            borderRadius: 4,
            color: "#fff",
            cursor: "pointer",
            fontSize: 12,
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
