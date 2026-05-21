import { API_BASE_URL } from "./config";
import type { UploadResult } from "./types";

export async function uploadImage(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/upload/image`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`image upload failed: ${response.status}`);
  }
  return response.json();
}
