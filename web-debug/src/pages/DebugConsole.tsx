import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
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

const examples = parseConfiguredExamples(import.meta.env.VITE_DEBUG_EXAMPLES);

function parseConfiguredExamples(raw: unknown) {
  if (typeof raw !== "string" || !raw.trim()) {
    return [
      "帮我推荐 3500 以内适合学生记笔记和网课的平板",
      "帮我推荐 2000 以内适合上网课和通勤的降噪耳机",
      "帮我推荐 300 以内适合通勤的鞋",
      "帮我找 100 元以内控油定妆的粉饼或散粉",
      "50 元以内有什么低糖或无糖饮品？",
      "退货政策是什么？",
      "兰蔻小黑瓶和资生堂红腰子，哪个更适合敏感肌修护维稳？",
    ];
  }

  return raw
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 12);
}

export function DebugConsole() {
  const [message, setMessage] = useState("");
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

  async function submitMessage(nextMessage: string) {
    const trimmed = nextMessage.trim();
    if (!trimmed || isStreaming) return;
    const assistantId = `pending_${Date.now()}`;
    setError("");
    setIsStreaming(true);
    setEvents([]);
    setTrace([]);
    setMessages((current) => [
      ...current,
      { id: `user_${Date.now()}`, role: "user", content: trimmed, cards: [] },
      { id: assistantId, role: "assistant", content: "", cards: [], comparison: null, pending: true },
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
          if (debugEvent.event === "comparison") {
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId || item.pending ? { ...item, comparison: debugEvent.data } : item
              )
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

  async function handleSend(event: FormEvent) {
    event.preventDefault();
    await submitMessage(message);
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    if (!message.trim() || isStreaming) return;
    event.currentTarget.form?.requestSubmit();
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
            <button key={item} disabled={isStreaming} onClick={() => void submitMessage(item)} title="点击直接发送">
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
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={handleComposerKeyDown} />
          <button disabled={isStreaming || !message.trim()}>
            <Play size={18} /> Send
          </button>
        </form>
      </section>

      <aside className="trace-panel">
        <div className="trace-block trace-summary-block">
          <h3>Agentic RAG Summary</h3>
          <TraceSummary trace={trace} memory={memory} />
        </div>
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

function TraceSummary({ trace, memory }: { trace: unknown; memory: Record<string, unknown> }) {
  const items = Array.isArray(trace) ? (trace as Array<Record<string, unknown>>) : [];
  const supervisor = items.find((item) => item.node === "supervisor");
  const shopping = [...items].reverse().find((item) => item.node === "shopping_guide");
  const intent = items.find((item) => item.node === "intent_router");
  const plan = asRecord(supervisor?.agentic_rag_plan);
  const constraints = asRecord(shopping?.effective_constraints);
  const memorySnapshot = asRecord(shopping?.memory_snapshot) || memory;
  const lowConfidence = Boolean(shopping?.low_confidence);

  if (!items.length) {
    return <div className="trace-empty">等待请求后展示意图、专家 Agent、检索策略和约束记忆。</div>;
  }

  return (
    <div className="trace-summary">
      <div className="trace-kpi-grid">
        <TraceKpi label="Intent" value={stringValue(intent?.intent || supervisor?.intent)} />
        <TraceKpi label="Specialist" value={stringValue(supervisor?.specialist)} />
        <TraceKpi label="Retrieval" value={stringValue(plan?.retrieval_strategy || shopping?.retrieval_mode)} />
        <TraceKpi label="Confidence" value={lowConfidence ? "Low" : stringValue(shopping?.confidence, "Normal")} tone={lowConfidence ? "warn" : "ok"} />
      </div>
      <TraceChips title="Constraints" values={compactRecord(constraints)} />
      <TraceChips title="Memory" values={compactRecord(memorySnapshot)} />
      <TraceChips title="Sources" values={compactList(shopping?.cards || shopping?.keyword_hits || shopping?.chroma_hits)} />
      {lowConfidence && <div className="trace-warning">召回置信度偏低，演示时可以说明系统已触发保守推荐提示。</div>}
    </div>
  );
}

function TraceKpi({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "ok" | "warn" }) {
  return (
    <div className={`trace-kpi ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TraceChips({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="trace-chip-section">
      <span className="trace-chip-title">{title}</span>
      <div className="trace-chips">
        {values.length ? values.map((value) => <code key={value}>{value}</code>) : <em>暂无</em>}
      </div>
    </div>
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function compactRecord(record: Record<string, unknown> | null): string[] {
  if (!record) return [];
  return Object.entries(record)
    .filter(([, value]) => value !== undefined && value !== null && value !== "" && !(Array.isArray(value) && value.length === 0))
    .slice(0, 8)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`);
}

function compactList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.slice(0, 6).map((item) => String(item));
}

function stringValue(value: unknown, fallback = "暂无"): string {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}
