import { API_BASE_URL } from "./config";

export async function submitFeedback(messageId: string, rating: 1 | -1) {
  const response = await fetch(`${API_BASE_URL}/api/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId, rating }),
  });
  if (!response.ok) {
    throw new Error(`feedback failed: ${response.status}`);
  }
  return response.json();
}
