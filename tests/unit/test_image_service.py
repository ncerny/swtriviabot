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

        success, result = await service.validate_and_create_embed(url)

        assert success is False
        assert "Please provide a valid image URL" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_http_error(self, service):
        """Test validation failure for HTTP errors."""
        url = "https://example.com/image.jpg"

        # Mock 404 response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.reason = 'Not Found'

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Properly mock the async context manager for session.head()
            mock_response_cm = AsyncMock()
            mock_response_cm.__aenter__.return_value = mock_response
            mock_session.head.return_value = mock_response_cm

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

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.head.side_effect = asyncio.TimeoutError()

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Image took too long to load" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_large_image(self, service):
        """Test validation failure for images too large."""
        url = "https://example.com/large-image.jpg"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': str(10 * 1024 * 1024)  # 10MB > 8MB limit
        }

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Properly mock the async context manager for session.head()
            mock_response_cm = AsyncMock()
            mock_response_cm.__aenter__.return_value = mock_response
            mock_session.head.return_value = mock_response_cm

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Image is too large" in result

    @pytest.mark.asyncio
    async def test_validate_and_create_embed_unsupported_format(self, service):
        """Test validation failure for unsupported image formats."""
        url = "https://example.com/image.bmp"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'image/bmp'}

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Properly mock the async context manager for session.head()
            mock_response_cm = AsyncMock()
            mock_response_cm.__aenter__.return_value = mock_response
            mock_session.head.return_value = mock_response_cm

            success, result = await service.validate_and_create_embed(url)

            assert success is False
            assert "Unsupported image format" in result

    @pytest.mark.asyncio
    async def test_validate_image_url_convenience_function(self):
        """Test the convenience function validate_image_url."""
        url = "https://example.com/image.png"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': '512000'  # 512KB
        }

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.head.return_value.__aenter__.return_value = mock_response

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

        @pytest.mark.asyncio
        async def test_process_search_term_success(self, service):
        """Test successful Tenor search term processing."""
        # Mock Tenor API response with multiple results
        mock_response_data = {
        "results": [
        {
        "media_formats": {
        "gif": {"url": "https://media.tenor.com/gif1.gif"},
        "tinygif": {"url": "https://media.tenor.com/tiny1.gif"}
        }
        },
        {
        "media_formats": {
        "gif": {"url": "https://media.tenor.com/gif2.gif"}
        }
        }
        ]
        }

        with patch.dict(os.environ, {'TENOR_API_KEY': 'test-key'}), \
        patch('aiohttp.ClientSession') as mock_session_class:

        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Mock the API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response_cm = AsyncMock()
        mock_response_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response_cm

        # Mock successful image validation for the returned GIF URL
        with patch.object(service, '_validate_image_accessibility') as mock_validate:
        mock_validate.return_value = (True, "")

        success, result = await service._process_search_term("dancing cat")

        assert success is True
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['url'] == "https://media.tenor.com/gif1.gif"

        @pytest.mark.asyncio
        async def test_process_search_term_no_api_key(self, service):
        """Test search term processing without API key."""
        with patch.dict(os.environ, {}, clear=True):  # Clear TENOR_API_KEY
        success, result = await service._process_search_term("dancing cat")

        assert success is False
        assert "Tenor API key not configured" in result

        @pytest.mark.asyncio
        async def test_process_search_term_no_results(self, service):
        """Test search term processing with no Tenor results."""
        with patch.dict(os.environ, {'TENOR_API_KEY': 'test-key'}), \
        patch('aiohttp.ClientSession') as mock_session_class:

        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Mock empty results response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"results": []})
        mock_response_cm = AsyncMock()
        mock_response_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response_cm

        success, result = await service._process_search_term("nonexistent search")

        assert success is False
        assert "No GIFs found for 'nonexistent search'" in result
