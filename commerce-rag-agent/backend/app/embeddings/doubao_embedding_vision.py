import base64
import hashlib
import math
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


class DoubaoEmbeddingVision:
    """Doubao multimodal embedding adapter with deterministic fallback."""

    def __init__(self, dimension: int | None = None) -> None:
        load_dotenv()
        self.dimension = dimension or int(os.getenv("DOUBAO_EMBEDDING_DIMENSION", "2048"))
        self.api_key = os.getenv("DOUBAO_EMBEDDING_API_KEY") or os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY", "")
        self.model = os.getenv("DOUBAO_EMBEDDING_MODEL", "doubao-embedding-vision-250615")
        self.base_url = os.getenv(
            "DOUBAO_EMBEDDING_BASE_URL",
            "https://api-vikingdb.vikingdb.cn-beijing.volces.com/api/vikingdb/embedding",
        )
        self.timeout = float(os.getenv("DOUBAO_EMBEDDING_TIMEOUT", "30"))
        self.enable_real = os.getenv("DOUBAO_EMBEDDING_ENABLE_REAL", "false").lower() == "true"
        self.image_mode = os.getenv("DOUBAO_EMBEDDING_IMAGE_MODE", "url").lower()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.enable_real and self.api_key:
            return self._embed_real([self._text_input(text) for text in texts])
        return [self._embed_fallback(text.encode("utf-8")) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        if self.enable_real and self.api_key:
            return self._embed_real([self._text_input(text)])[0]
        return self._embed_fallback(text.encode("utf-8"))

    def embed_image(self, path_or_url: str) -> list[float]:
        if self.enable_real and self.api_key:
            return self._embed_real([self._image_input(path_or_url)])[0]
        path = Path(path_or_url)
        payload = path.read_bytes() if path.exists() else path_or_url.encode("utf-8")
        return self._embed_fallback(payload)

    def _embed_real(self, inputs: list[dict[str, Any]]) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": inputs,
            "encoding_format": "float",
            "embedding_dimension": self.dimension,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.base_url, headers=self._headers(), json=payload)
            response.raise_for_status()
        data = response.json()
        items = data.get("data") or data.get("result", {}).get("data") or []
        vectors = [item.get("embedding") for item in items]
        if not vectors or any(vector is None for vector in vectors):
            raise RuntimeError("Doubao embedding response did not contain embeddings")
        return [list(map(float, vector)) for vector in vectors]

    def _text_input(self, text: str) -> dict[str, str]:
        return {"type": "text", "text": text}

    def _image_input(self, path_or_url: str) -> dict[str, str]:
        if path_or_url.startswith(("http://", "https://", "tos://")):
            return {"type": "image_url", "image_url": path_or_url}
        if self.image_mode == "base64":
            payload = base64.b64encode(Path(path_or_url).read_bytes()).decode("ascii")
            return {"type": "image_url", "image_url": f"data:image/png;base64,{payload}"}
        return {"type": "image_url", "image_url": path_or_url}

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("DOUBAO_EMBEDDING_API_KEY, DOUBAO_API_KEY or ARK_API_KEY is required")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _embed_fallback(self, payload: bytes) -> list[float]:
        vector = [0.0] * self.dimension
        for offset in range(0, max(len(payload), 1), 8):
            block = payload[offset : offset + 8] or b"empty"
            digest = hashlib.sha256(block).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector
