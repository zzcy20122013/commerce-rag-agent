import { API_BASE_URL } from "./config";
import type { IngestResult } from "./types";

export async function ingestDocument(file: File, docType: string, category: string): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_type", docType);
  form.append("category", category);
  form.append("version", "v1");
  const response = await fetch(`${API_BASE_URL}/api/docs/ingest`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`document ingest failed: ${response.status}`);
  }
  return response.json();
}
