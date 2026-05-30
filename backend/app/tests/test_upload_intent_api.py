from io import BytesIO

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from PIL import Image
from starlette.datastructures import Headers

from app.main import app
from app.services import image_service
from app.services.image_service import save_upload_image
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
        files={"file": ("coffee.png", _png_bytes(), "image/png")},
    )
    upload_id = upload_response.json()["upload_id"]

    intent_response = client.post(f"/api/upload/image/{upload_id}/intent")

    assert intent_response.status_code == 200
    payload = intent_response.json()
    assert payload["upload_id"] == upload_id
    assert payload["prompt"] == "请帮我找类似咖啡、绿色、速溶咖啡的商品"
    assert payload["vlm_enabled"] is True


def test_upload_rejects_undecodable_image(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(image_service, "UPLOAD_DIR", tmp_path / "uploads")
    file = UploadFile(
        filename="fake.png",
        file=BytesIO(b"not an image"),
        headers=Headers({"content-type": "image/png"}),
    )

    with pytest.raises(ValueError, match="decodable image"):
        save_upload_image(file)


def test_upload_rejects_extension_that_does_not_match_image_format(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(image_service, "UPLOAD_DIR", tmp_path / "uploads")
    file = UploadFile(
        filename="fake.jpg",
        file=BytesIO(_png_bytes()),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with pytest.raises(ValueError, match="extension does not match"):
        save_upload_image(file)


def _png_bytes() -> bytes:
    output = BytesIO()
    image = Image.new("RGB", (2, 2), color=(20, 180, 80))
    image.save(output, format="PNG")
    return output.getvalue()
