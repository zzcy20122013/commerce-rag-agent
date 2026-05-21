import { API_BASE_URL } from "./config";
import type { DebugEvent } from "./types";

type StreamChatParams = {
  message: string;
  sessionId?: string;
  memory?: Record<string, unknown>;
  uploadId?: string;
  onEvent: (event: DebugEvent) => void;
};

export async function streamChat({ message, sessionId, memory, uploadId, onEvent }: StreamChatParams) {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
      memory: memory || undefined,
      upload_id: uploadId || undefined,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`chat stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const parsed = parseSseBlock(part);
      if (parsed) onEvent(parsed);
    }
  }

  const parsed = parseSseBlock(buffer);
  if (parsed) onEvent(parsed);
}

function parseSseBlock(block: string): DebugEvent | null {
  const lines = block.split(/\r?\n/).filter(Boolean);
  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!eventLine || !dataLine) return null;
  const event = eventLine.replace("event:", "").trim();
  const rawData = dataLine.replace("data:", "").trim();
  const data = safeJson(rawData);
  if (
    event === "message" ||
    event === "trace" ||
    event === "product_cards" ||
    event === "comparison" ||
    event === "done" ||
    event === "error"
  ) {
    return { event, data, raw: block } as DebugEvent;
  }
  return null;
}

function safeJson(raw: string) {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}
