import hashlib
import math
import os
from pathlib import Path

from dotenv import load_dotenv

from app.embeddings.doubao_embedding_vision import DoubaoEmbeddingVision


class ChineseClipEmbedding:
    """Chinese-CLIP image/text embedding interface with deterministic fallback."""

    def __init__(self, dimension: int = 512) -> None:
        load_dotenv()
        self.dimension = dimension
        self.model_name = os.getenv("CHINESE_CLIP_MODEL_NAME", "OFA-Sys/chinese-clip-vit-base-patch16")
        self.device = os.getenv("CHINESE_CLIP_DEVICE", "cpu")
        self.enable_real = os.getenv("CHINESE_CLIP_ENABLE_REAL", "false").lower() == "true"
        self.local_files_only = os.getenv("CHINESE_CLIP_LOCAL_FILES_ONLY", "false").lower() == "true"
        self.provider = os.getenv("IMAGE_EMBEDDING_PROVIDER", os.getenv("EMBEDDING_PROVIDER", "doubao")).lower()
        self._doubao = DoubaoEmbeddingVision() if self.provider == "doubao" else None
        self._model = None
        self._image_processor = None
        self._tokenizer = None
        configure_huggingface_home()
        if self.local_files_only:
            configure_offline_mode()

    def embed_image(self, path: str) -> list[float]:
        if self._doubao is not None:
            return self._doubao.embed_image(path)
        if self.enable_real:
            return self._embed_image_real(path)
        image_path = Path(path)
        payload = image_path.as_posix().encode("utf-8") + b"\n" + image_path.read_bytes()
        return self._embed(payload)

    def embed_text(self, text: str) -> list[float]:
        if self._doubao is not None:
            return self._doubao.embed_text(text)
        if self.enable_real:
            return self._embed_text_real(text)
        return self._embed(text.encode("utf-8"))

    def _embed_image_real(self, path: str) -> list[float]:
        model, image_processor, _, torch = self._load_model()
        from PIL import Image

        image = Image.open(path).convert("RGB")
        inputs = image_processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            features = model.get_image_features(**inputs)
        return normalize_tensor(extract_features(features), torch)

    def _embed_text_real(self, text: str) -> list[float]:
        model, _, tokenizer, torch = self._load_model()
        inputs = tokenizer([text], padding=True, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            features = model.get_text_features(**inputs)
        return normalize_tensor(extract_features(features), torch)

    def _load_model(self):
        if self._model is not None and self._image_processor is not None and self._tokenizer is not None:
            import torch

            return self._model, self._image_processor, self._tokenizer, torch
        try:
            import torch
            from transformers import BertTokenizer, ChineseCLIPImageProcessorPil, ChineseCLIPModel
        except ImportError as error:  # pragma: no cover - depends on optional local model installation
            raise RuntimeError("Chinese-CLIP requires torch, transformers and pillow to be installed.") from error

        options = {"local_files_only": self.local_files_only}
        self._image_processor = ChineseCLIPImageProcessorPil.from_pretrained(self.model_name, **options)
        self._tokenizer = BertTokenizer.from_pretrained(self.model_name, **options)
        self._model = ChineseCLIPModel.from_pretrained(self.model_name, use_safetensors=False, **options)
        self._model.to(self.device)
        self._model.eval()
        return self._model, self._image_processor, self._tokenizer, torch

    def _embed(self, payload: bytes) -> list[float]:
        vector = [0.0] * self.dimension
        for offset in range(0, max(len(payload), 1), 8):
            block = payload[offset : offset + 8] or b"empty"
            digest = hashlib.sha256(block).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


def normalize_tensor(features, torch) -> list[float]:
    normalized = torch.nn.functional.normalize(features, p=2, dim=-1)
    return [float(value) for value in normalized[0].detach().cpu().tolist()]


def extract_features(features):
    return getattr(features, "pooler_output", features)


def configure_huggingface_home() -> None:
    hf_home = os.getenv("HF_HOME")
    if not hf_home:
        return
    Path(hf_home).mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = hf_home


def configure_offline_mode() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
