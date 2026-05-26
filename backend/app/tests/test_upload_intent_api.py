from fastapi.testclient import TestClient

from app.main import app
from app.services import image_service
from app.services.vlm_service import VisualAttributes, VisionAnalysisResult


class FakeVisionLanguageService:
    def analyze_image(self, image_path: str, *, query: str = "") -> VisionAnalysisResult:
        return VisionAnalysisResult(
            enabled=True,
            attributes=VisualAttributes(
                category="咖啡",
                colors=["绿色"],
                search_terms=["速溶咖啡"],
            ),
        )


def test_upload_image_intent_returns_user_confirmation_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(image_service, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr("app.api.upload.VisionLanguageService", FakeVisionLanguageService)
    client = TestClient(app)

    upload_response = client.post(
        "/api/upload/image",
        files={"file": ("coffee.png", b"fake-image-bytes", "image/png")},
    )
    upload_id = upload_response.json()["upload_id"]

    intent_response = client.post(f"/api/upload/image/{upload_id}/intent")

    assert intent_response.status_code == 200
    payload = intent_response.json()
    assert payload["upload_id"] == upload_id
    assert payload["prompt"] == "请帮我找类似咖啡、绿色、速溶咖啡的商品"
    assert payload["vlm_enabled"] is True
