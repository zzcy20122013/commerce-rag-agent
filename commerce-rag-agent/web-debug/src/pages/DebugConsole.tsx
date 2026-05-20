import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Database,
  FileUp,
  ImagePlus,
  Play,
  RefreshCw,
  Server,
  TerminalSquare,
} from "lucide-react";
import { API_BASE_URL, absoluteUrl } from "../api/config";
import { ingestDocument } from "../api/docs";
import { streamChat } from "../api/chatStream";
import { uploadImage } from "../api/upload";
import type { DebugEvent, UploadResult } from "../api/types";
import { ChatMessage, type UiMessage } from "../components/ChatMessage";

const examples = [
  "帮我推荐 2000 以内适合学生记笔记和网课的平板",
  "退货政策是什么？",
  "找类似这双鞋，但价格 300 以内，适合通勤",
  "有没有更轻一点的？",
];

export function DebugConsole() {
  const [message, setMessage] = useState(examples[0]);
  const [sessionId, setSessionId] = useState("");
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [docStatus, setDocStatus] = useState("未导入文档");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [memory, setMemory] = useState<Record<string, unknown>>({});
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [trace, setTrace] = useState<unknown>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState("");
  const messageListRef = useRef<HTMLDivElement | null>(null);

  const rawEvents = useMemo(() => events.map((event) => event.raw).join("\n\n"), [events]);

  function scrollMessagesToBottom() {
    window.requestAnimationFrame(() => {
      const list = messageListRef.current;
      if (list) {
        list.scrollTop = list.scrollHeight;
      }
    });
  }

  useEffect(() => {
    scrollMessagesToBottom();
  }, [messages]);

  async function handleSend(event: FormEvent) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isStreaming) return;
    const assistantId = `pending_${Date.now()}`;
    setError("");
    setIsStreaming(true);
    setEvents([]);
    setTrace([]);
    setMessages((current) => [
      ...current,
      { id: `user_${Date.now()}`, role: "user", content: trimmed, cards: [] },
      { id: assistantId, role: "assistant", content: "", cards: [], pending: true },
    ]);
    scrollMessagesToBottom();
    setMessage("");

    try {
      await streamChat({
        message: trimmed,
        sessionId,
        memory,
        uploadId: upload?.upload_id,
        onEvent: (debugEvent) => {
          setEvents((current) => [...current, debugEvent]);
          if (debugEvent.event === "message") {
            setSessionId(debugEvent.data.session_id || sessionId);
            if (debugEvent.data.memory) {
              setMemory(debugEvent.data.memory);
            }
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId || item.pending
                  ? {
                      ...item,
                      id: debugEvent.data.message_id || item.id,
                      content: item.content + debugEvent.data.content,
                    }
                  : item
              )
            );
            scrollMessagesToBottom();
          }
          if (debugEvent.event === "product_cards") {
            setMessages((current) =>
              current.map((item) => (item.id === assistantId || item.pending ? { ...item, cards: debugEvent.data } : item))
            );
            scrollMessagesToBottom();
          }
          if (debugEvent.event === "trace") {
            setTrace(debugEvent.data);
          }
          if (debugEvent.event === "error") {
            setError(JSON.stringify(debugEvent.data));
            setMessages((current) => current.map((item) => (item.pending ? { ...item, pending: false } : item)));
            setIsStreaming(false);
            scrollMessagesToBottom();
          }
          if (debugEvent.event === "done") {
            setMessages((current) => current.map((item) => (item.pending ? { ...item, pending: false } : item)));
            setIsStreaming(false);
            setUpload(null);
            scrollMessagesToBottom();
          }
        },
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "请求失败");
      setMessages((current) => current.map((item) => (item.pending ? { ...item, pending: false } : item)));
      setIsStreaming(false);
      scrollMessagesToBottom();
    }
  }

  async function handleImageChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      setUpload(await uploadImage(file));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "图片上传失败");
    } finally {
      event.currentTarget.value = "";
    }
  }

  async function handleDocChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setDocStatus("文档导入中...");
    try {
      const result = await ingestDocument(file, "debug_upload", "debug");
      setDocStatus(`已导入 ${result.chunks} 个 chunk，${result.document_id}`);
    } catch (caught) {
      setDocStatus("导入失败");
      setError(caught instanceof Error ? caught.message : "文档导入失败");
    } finally {
      event.currentTarget.value = "";
    }
  }

  function updateFeedback(messageId: string, rating: 1 | -1) {
    setMessages((current) => current.map((item) => (item.id === messageId ? { ...item, feedback: rating } : item)));
  }

  function resetDebugSession() {
    setSessionId("");
    setMemory({});
    setMessages([]);
    setEvents([]);
    setTrace([]);
    setUpload(null);
    setError("");
  }

  return (
    <main className="debug-shell">
      <aside className="side-panel">
        <div className="brand">
          <div className="brand-mark">
            <TerminalSquare size={22} />
          </div>
          <div>
            <h1>RAG Commerce Debug</h1>
            <p>Agent / RAG / SSE console</p>
          </div>
        </div>

        <section className="panel-section">
          <div className="section-title">
            <Server size={16} /> Backend
          </div>
          <div className="endpoint">{API_BASE_URL}</div>
          <button className="ghost-button" onClick={() => window.open(`${API_BASE_URL}/docs`, "_blank")}>
            <Activity size={15} /> Open Swagger
          </button>
        </section>

        <section className="panel-section">
          <div className="section-title">
            <ImagePlus size={16} /> Image Upload
          </div>
          <label className="file-button">
            选择图片
            <input type="file" accept="image/*" onChange={(event) => void handleImageChange(event)} />
          </label>
          {upload && (
            <div className="upload-preview">
              <img src={absoluteUrl(upload.preview_url)} alt="uploaded" />
              <code>{upload.upload_id}</code>
            </div>
          )}
        </section>

        <section className="panel-section">
          <div className="section-title">
            <FileUp size={16} /> Docs Ingestion
          </div>
          <label className="file-button">
            导入 .md/.txt/.csv
            <input type="file" accept=".md,.txt,.csv" onChange={(event) => void handleDocChange(event)} />
          </label>
          <p className="muted">{docStatus}</p>
        </section>

        <section className="panel-section">
          <div className="section-title">
            <Database size={16} /> Session
          </div>
          <input className="line-input" value={sessionId} onChange={(event) => setSessionId(event.target.value)} placeholder="session_id 自动回填" />
          <button className="ghost-button" onClick={resetDebugSession}>
            <RefreshCw size={15} /> Reset
          </button>
          <button className="ghost-button" onClick={() => setMemory({})}>
            <RefreshCw size={15} /> Clear Memory
          </button>
        </section>
      </aside>

      <section className="chat-panel">
        <div className="chat-header">
          <div>
            <h2>Chat Stream</h2>
            <p>验证 Doubao 回答、商品卡片、图搜和多轮记忆</p>
          </div>
          <div className={`status-pill ${isStreaming ? "live" : ""}`}>{isStreaming ? "Streaming" : "Idle"}</div>
        </div>

        <div className="examples">
          {examples.map((item) => (
            <button key={item} onClick={() => setMessage(item)}>
              {item}
            </button>
          ))}
        </div>

        <div className="message-list" ref={messageListRef}>
          {messages.length === 0 && (
            <div className="empty-state">
              <TerminalSquare size={30} />
              <strong>发送一条请求开始调试</strong>
              <span>右侧会显示 trace 和原始 SSE 事件。</span>
            </div>
          )}
          {messages.map((item) => (
            <ChatMessage key={item.id} message={item} onFeedback={updateFeedback} onError={setError} />
          ))}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form className="composer" onSubmit={(event) => void handleSend(event)}>
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
          <button disabled={isStreaming || !message.trim()}>
            <Play size={18} /> Send
          </button>
        </form>
      </section>

      <aside className="trace-panel">
        <div className="trace-block">
          <h3>Trace</h3>
          <pre>{JSON.stringify(trace, null, 2)}</pre>
        </div>
        <div className="trace-block raw">
          <h3>Raw SSE</h3>
          <pre>{rawEvents || "No events yet."}</pre>
        </div>
      </aside>
    </main>
  );
}
