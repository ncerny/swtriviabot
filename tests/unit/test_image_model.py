"""Unit tests for the Image model."""

from types import SimpleNamespace

import pytest

from src.models.image import Image


def test_image_validate_url_rejects_invalid_format() -> None:
    """Malformed URLs set validation error state."""

    image = Image(url="not-a-url")
    assert image.validate_url() is False
    assert image.is_valid is False
    assert image.validation_error == "Invalid URL format"


def test_image_validate_url_requires_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing domain triggers validation failure."""

    image = Image(url="https://example.com/path")

    def _fake_urlparse(url: str) -> SimpleNamespace:
        return SimpleNamespace(netloc="")

    monkeypatch.setattr("urllib.parse.urlparse", _fake_urlparse)

    assert image.validate_url() is False
    assert image.is_valid is False
    assert image.validation_error == "Missing domain in URL"


def test_get_embed_data_raises_when_invalid() -> None:
    """Cannot build embed for invalid images."""

    image = Image(url="https://example.com/image.png", is_valid=False)

    with pytest.raises(ValueError, match="Cannot create embed"):
        image.get_embed_data()


def test_get_embed_data_includes_dimensions() -> None:
    """Embed includes width and height when provided."""

    image = Image(url="https://example.com/pic.png", width=640, height=480)
    image.is_valid = True

    embed = image.get_embed_data()

    assert embed["type"] == "image"
    assert embed["url"] == "https://example.com/pic.png"
    assert embed["width"] == 640
    assert embed["height"] == 480
