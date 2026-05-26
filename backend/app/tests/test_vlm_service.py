from pathlib import Path

from PIL import Image

from app.services.vlm_service import VisionLanguageService


class FakeVisionClient:
    def __init__(self) -> None:
        self.messages = []

    def chat_sync(self, messages, *, temperature: float = 0.2) -> str:
        self.messages = messages
        return """
        ```json
        {
          "category": "跑鞋",
          "colors": ["黑色", "白色"],
          "materials": ["网布"],
          "style": ["运动", "缓震"],
          "use_cases": ["跑步", "通勤"],
          "visible_text": ["AIR"],
          "search_terms": ["黑白跑鞋", "网布缓震跑鞋"],
          "confidence": 0.86
        }
        ```
        """


def test_vlm_service_extracts_structured_visual_attributes(tmp_path: Path) -> None:
    image_path = tmp_path / "shoe.jpg"
    Image.new("RGB", (8, 8), color="black").save(image_path)
    client = FakeVisionClient()

    result = VisionLanguageService(client=client).analyze_image(
        str(image_path),
        query="找类似的，预算 500",
    )

    assert result.enabled is True
    assert result.attributes.category == "跑鞋"
    assert result.attributes.colors == ["黑色", "白色"]
    assert "网布缓震跑鞋" in result.attributes.search_terms
    user_content = client.messages[1]["content"]
    assert user_content[0]["type"] == "text"
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_vlm_service_falls_back_when_no_client_or_key(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "item.jpg"
    Image.new("RGB", (8, 8), color="white").save(image_path)
    monkeypatch.delenv("DOUBAO_VISION_API_KEY", raising=False)
    monkeypatch.delenv("DOUBAO_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)

    result = VisionLanguageService().analyze_image(str(image_path), query="这是什么")

    assert result.enabled is False
    assert result.error == "missing_api_key"
    assert result.attributes.search_terms == []
