import hashlib
import math
import os
from pathlib import Path

from dotenv import load_dotenv


class BgeM3Embedding:
    """bge-m3 embedding interface with deterministic fallback for local development."""

    def __init__(self, dimension: int = 384) -> None:
        load_dotenv()
        self.dimension = dimension
        self.model_name = os.getenv("BGE_M3_MODEL_NAME", "BAAI/bge-m3")
        self.device = os.getenv("BGE_M3_DEVICE", "cpu")
        self.use_fp16 = os.getenv("BGE_M3_USE_FP16", "false").lower() == "true"
        self.enable_real = os.getenv("BGE_M3_ENABLE_REAL", "false").lower() == "true"
        self._model = None
        configure_huggingface_home()

    def embed_query(self, text: str) -> list[float]:
        if self.enable_real:
            return self._embed_real([text])[0]
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.enable_real:
            return self._embed_real(texts)
        return [self._embed(text) for text in texts]

    def _embed_real(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        output = model.encode(texts, batch_size=int(os.getenv("BGE_M3_BATCH_SIZE", "16")), max_length=8192)
        dense_vectors = output["dense_vecs"] if isinstance(output, dict) else output
        return [list(map(float, vector)) for vector in dense_vectors]

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as error:  # pragma: no cover - depends on optional local model installation
            raise RuntimeError("FlagEmbedding is not installed. Run: python -m pip install -U FlagEmbedding") from error
        self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16, device=self.device)
        return self._model

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._tokens(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _tokens(self, text: str) -> list[str]:
        compact = "".join(ch.lower() for ch in text if not ch.isspace())
        tokens = list(compact)
        tokens.extend(compact[index : index + 2] for index in range(max(len(compact) - 1, 0)))
        return [token for token in tokens if token]


def configure_huggingface_home() -> None:
    hf_home = os.getenv("HF_HOME")
    if not hf_home:
        return
    Path(hf_home).mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = hf_home
