import base64
import json
import mimetypes
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.llm.openai_compatible_client import OpenAICompatibleClient


class VisionChatClient(Protocol):
    def chat_sync(self, messages: list[dict[str, Any]], *, temperature: float = 0.2) -> str:
        ...


@dataclass(frozen=True)
class VisualAttributes:
    category: str = ""
    colors: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    visible_text: list[str] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VisionAnalysisResult:
    enabled: bool
    attributes: VisualAttributes = field(default_factory=VisualAttributes)
    error: str | None = None

    def to_trace(self) -> dict[str, Any]:
        return {
            "vlm_enabled": self.enabled,
            "vlm_error": self.error,
            "vlm_attributes": self.attributes.to_dict(),
        }


class VisionLanguageService:
    def __init__(self, *, client: VisionChatClient | None = None) -> None:
        self.client = client

    def analyze_image(self, image_path: str, *, query: str = "") -> VisionAnalysisResult:
        if self.client is None and not _has_vision_key():
            return VisionAnalysisResult(enabled=False, error="missing_api_key")
        try:
            client = self.client or _build_vision_client()
            content = client.chat_sync(
                build_vlm_messages(image_path=image_path, query=query),
                temperature=0.1,
            )
            return VisionAnalysisResult(enabled=True, attributes=parse_visual_attributes(content))
        except Exception as error:
            return VisionAnalysisResult(enabled=False, error=_short_error(error))


def build_vlm_messages(*, image_path: str, query: str = "") -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "你是电商拍照找货的视觉识别模块。只输出 JSON，不要输出解释。"
                "字段包括 category, colors, materials, style, use_cases, visible_text, "
                "search_terms, confidence。search_terms 使用中文短语，适合商品检索。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "请识别图片里的商品外观属性，并结合用户文字补充检索关键词。"
                        f"用户文字：{query or '无'}"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": _image_data_url(image_path)},
                },
            ],
        },
    ]


def parse_visual_attributes(content: str) -> VisualAttributes:
    payload = _extract_json_object(content)
    return VisualAttributes(
        category=str(payload.get("category") or "").strip(),
        colors=_string_list(payload.get("colors")),
        materials=_string_list(payload.get("materials")),
        style=_string_list(payload.get("style")),
        use_cases=_string_list(payload.get("use_cases")),
        visible_text=_string_list(payload.get("visible_text")),
        search_terms=_string_list(payload.get("search_terms")),
        confidence=_safe_float(payload.get("confidence")),
    )


def visual_terms_from_attributes(attributes: VisualAttributes) -> list[str]:
    terms: list[str] = []
    for value in [
        attributes.category,
        *attributes.colors,
        *attributes.materials,
        *attributes.style,
        *attributes.use_cases,
        *attributes.visible_text,
        *attributes.search_terms,
    ]:
        clean = str(value).strip()
        if clean and clean not in terms:
            terms.append(clean)
    return terms


def _build_vision_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        api_key=os.getenv("DOUBAO_VISION_API_KEY") or os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY", ""),
        base_url=os.getenv("DOUBAO_VISION_BASE_URL") or os.getenv("DOUBAO_BASE_URL"),
        model=os.getenv("DOUBAO_VISION_MODEL") or os.getenv("DOUBAO_MODEL"),
    )


def _has_vision_key() -> bool:
    return bool(os.getenv("DOUBAO_VISION_API_KEY") or os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"))


def _image_data_url(image_path: str) -> str:
    path = Path(image_path)
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("VLM response must be a JSON object")
    return parsed


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[,，、/]\s*", value)
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    result: list[str] = []
    for item in items:
        clean = str(item).strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _short_error(error: Exception) -> str:
    return f"{error.__class__.__name__}: {str(error)[:120]}"
