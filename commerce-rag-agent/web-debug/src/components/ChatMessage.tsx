import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { submitFeedback } from "../api/feedback";
import type { ProductCard } from "../api/types";
import { ProductCards } from "./ProductCards";

export type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  cards: ProductCard[];
  pending?: boolean;
  feedback?: 1 | -1;
};

type ChatMessageProps = {
  message: UiMessage;
  onFeedback: (messageId: string, rating: 1 | -1) => void;
  onError?: (message: string) => void;
};

function renderInlineMarkdown(content: string) {
  return content.split("\n").flatMap((line, lineIndex) => {
    const visibleLine = line.replace(/^\s*-\s+/, "");
    const parts = visibleLine.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={`${lineIndex}-${partIndex}`}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    return lineIndex === 0 ? parts : [<br key={`br-${lineIndex}`} />, ...parts];
  });
}

export function ChatMessage({ message, onFeedback, onError }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  async function handleFeedback(rating: 1 | -1) {
    if (!message.id.startsWith("msg_") || isSubmittingFeedback) return;
    setIsSubmittingFeedback(true);
    try {
      await submitFeedback(message.id, rating);
      onFeedback(message.id, rating);
    } catch (caught) {
      onError?.(caught instanceof Error ? caught.message : "反馈提交失败");
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-card">
        <div className="message-label">{isAssistant ? "Agent" : "User"}</div>
        <div className="message-content">
          {message.content ? renderInlineMarkdown(message.content) : message.pending ? "等待响应..." : ""}
        </div>
        {message.pending && <div className="stream-indicator">streaming</div>}
        <ProductCards cards={message.cards} />
        {isAssistant && !message.pending && message.id.startsWith("msg_") && (
          <div className="feedback-row">
            <button disabled={message.feedback !== undefined || isSubmittingFeedback} onClick={() => void handleFeedback(1)} title="点赞">
              <ThumbsUp size={15} /> {message.feedback === 1 ? "已赞" : "赞"}
            </button>
            <button disabled={message.feedback !== undefined || isSubmittingFeedback} onClick={() => void handleFeedback(-1)} title="点踩">
              <ThumbsDown size={15} /> {message.feedback === -1 ? "已踩" : "踩"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
