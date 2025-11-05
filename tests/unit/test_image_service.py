"""
Unit tests for image_service.py
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord import Embed

from src.services.image_service import ImageService, validate_image_url
from src.models.image import Image


class TestImageService:
    """Test cases for ImageService class."""

    @pytest.fixture
    def service(self):
        """Create ImageService instance."""
        return ImageService(timeout=5.0)

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_success(self, service):
        """Test successful image validation and embed creation."""
        url = "https://example.com/image.jpg"

        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': '1024000'  # 1MB
        }
        mock_response.reason = 'OK'

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Mock the context manager for the session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            # Mock the head request
            mock_session.head.return_value.__aenter__.return_value = mock_response
            mock_session.head.return_value.__aexit__.return_value = None

            success, result = await service.validate_and_create_embed(url)

            assert success is True
            assert isinstance(result, Embed)
            assert result.image.url == url

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_invalid_url(self, service):
        """Test validation failure for invalid URL."""
        url = "not-a-valid-url"

        # This will be treated as a search term (not a URL), so we expect Tenor error
        success, result = await service.validate_and_create_embed(url)

        assert success is False
        assert "Tenor API key not configured" in result or "No GIFs found" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_http_error(self, service):
        """Test validation failure for HTTP errors."""
        url = "https://example.com/image.jpg"

        # Mock the internal validation method to return HTTP error
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
            mock_validate.return_value = (False, "HTTP 404: Not Found")

            success, result = await service.validate_and_create_embed(url)

        assert success is False
        assert "Image not found (404)" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_invalid_content_type(self, service):
        """Test validation failure for non-image content."""
        url = "https://example.com/page.html"

        # Mock the internal validation method to return the error we want to test
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
            mock_validate.return_value = (False, "Invalid content type: text/html; charset=utf-8")

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "webpage link, not a direct image" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_timeout(self, service):
        """Test validation failure due to timeout."""
        url = "https://example.com/image.jpg"

        # Mock the internal validation method to return timeout error
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
            mock_validate.return_value = (False, "Image validation timeout")

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Image took too long to load" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_large_image(self, service):
        """Test validation failure for images too large."""
        url = "https://example.com/large-image.jpg"

        # Mock the internal validation method to return large image error
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
            mock_validate.return_value = (False, "Image too large (max 8MB)")

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Image is too large" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_unsupported_format(self, service):
        """Test validation failure for unsupported image formats."""
        url = "https://example.com/image.bmp"

        # Mock the internal validation method to return unsupported format error
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
            mock_validate.return_value = (False, "Unsupported image format: image/bmp")

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Unsupported image format" in result

    @pytest.mark.asyncio
    async def test_validate_image_url_convenience_function(self):
        """Test the convenience function validate_image_url."""
        url = "https://example.com/image.png"

        # Mock successful validation
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '512000'
        }
        mock_response.reason = 'OK'

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock the context manager for the session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.close = AsyncMock()

            # Mock the head request with proper async context manager
            mock_head_cm = AsyncMock()
            mock_head_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_head_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.head = MagicMock(return_value=mock_head_cm)

            success, result = await validate_image_url(url, timeout=3.0)

            assert success is True
            assert isinstance(result, Embed)


class TestImageModel:
    """Test cases for Image model."""

    def test_image_creation(self):
        """Test Image model creation."""
        image = Image(url="https://example.com/image.jpg")
        assert image.url == "https://example.com/image.jpg"
        assert image.is_valid is True
        assert image.validation_error is None

    def test_validate_url_valid(self):
        """Test URL validation for valid URLs."""
        image = Image(url="https://example.com/image.jpg")
        assert image.validate_url() is True
        assert image.is_valid is True

    def test_validate_url_invalid_format(self):
        """Test URL validation for invalid formats."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com/image.jpg",
            "//example.com/image.jpg",
            "https://",
        ]

        for url in invalid_urls:
            image = Image(url=url)
            assert image.validate_url() is False
            assert image.is_valid is False
            assert image.validation_error is not None

    def test_get_embed_data_valid(self):
        """Test embed data creation for valid images."""
        image = Image(url="https://example.com/image.jpg", width=800, height=600)
        embed_data = image.get_embed_data()

        assert embed_data['type'] == 'image'
        assert embed_data['url'] == image.url
        assert embed_data['width'] == 800
        assert embed_data['height'] == 600

    def test_get_embed_data_invalid(self):
        """Test embed data creation fails for invalid images."""
        image = Image(url="invalid-url")
        image.validate_url()  # This will set is_valid to False

        with pytest.raises(ValueError, match="Cannot create embed for invalid image"):
            image.get_embed_data()

    def test_is_url_detection(self):
        """Test URL vs search term detection."""
        service = ImageService()

        # URLs should be detected
        assert service._is_url("https://example.com/image.jpg") is True
        assert service._is_url("http://example.com/image.png") is True
        assert service._is_url("HTTPS://EXAMPLE.COM/IMAGE.GIF") is True

        # Search terms should not be detected as URLs
        assert service._is_url("dancing cat") is False
        assert service._is_url("funny meme") is False
        assert service._is_url("cat") is False

        # Edge cases
        assert service._is_url("") is False
        assert service._is_url("   ") is False
        assert service._is_url("not-a-url") is False
