"""
Unit tests for image_service.py
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord import Embed
import aiohttp

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

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_success(self):
        """Test successful Tenor GIF search."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
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

        async with aiohttp.ClientSession() as session:
            service.session = session
            with patch.object(session, 'get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_response_data)
                mock_response_cm = AsyncMock()
                mock_response_cm.__aenter__ = AsyncMock(return_value=mock_response)
                mock_response_cm.__aexit__ = AsyncMock(return_value=None)
                mock_get.return_value = mock_response_cm

                results = await service._search_tenor_gifs("dancing cat")

                assert len(results) == 2
                assert results[0]['url'] == "https://media.tenor.com/gif1.gif"
                assert results[0]['preview_url'] == "https://media.tenor.com/tiny1.gif"
                assert results[1]['url'] == "https://media.tenor.com/gif2.gif"

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_no_api_key(self):
        """Test Tenor search without API key."""
        service = ImageService()
        service.tenor_api_key = None
        
        async with aiohttp.ClientSession() as session:
            service.session = session
            results = await service._search_tenor_gifs("test")
            assert results is None

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_no_session(self):
        """Test Tenor search without session."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        service.session = None
        
        results = await service._search_tenor_gifs("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_api_error(self):
        """Test Tenor search with API error."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        async with aiohttp.ClientSession() as session:
            service.session = session
            with patch.object(session, 'get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 500
                mock_response_cm = AsyncMock()
                mock_response_cm.__aenter__ = AsyncMock(return_value=mock_response)
                mock_response_cm.__aexit__ = AsyncMock(return_value=None)
                mock_get.return_value = mock_response_cm

                results = await service._search_tenor_gifs("test")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_no_results(self):
        """Test Tenor search with no results."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        async with aiohttp.ClientSession() as session:
            service.session = session
            with patch.object(session, 'get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"results": []})
                mock_response_cm = AsyncMock()
                mock_response_cm.__aenter__ = AsyncMock(return_value=mock_response)
                mock_response_cm.__aexit__ = AsyncMock(return_value=None)
                mock_get.return_value = mock_response_cm

                results = await service._search_tenor_gifs("nonexistent")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_timeout(self):
        """Test Tenor search with timeout."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        async with aiohttp.ClientSession() as session:
            service.session = session
            with patch.object(session, 'get') as mock_get:
                mock_get.side_effect = asyncio.TimeoutError()
                
                results = await service._search_tenor_gifs("test")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_tenor_gifs_network_error(self):
        """Test Tenor search with network error."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        async with aiohttp.ClientSession() as session:
            service.session = session
            with patch.object(session, 'get') as mock_get:
                mock_get.side_effect = aiohttp.ClientError("Network error")
                
                results = await service._search_tenor_gifs("test")
                assert results == []

    @pytest.mark.asyncio
    async def test_process_search_term_success(self):
        """Test successful search term processing."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        mock_gifs = [
            {'url': 'https://media.tenor.com/gif1.gif', 'preview_url': 'https://media.tenor.com/tiny1.gif'}
        ]
        
        with patch.object(service, '_search_tenor_gifs', return_value=mock_gifs):
            success, result = await service._process_search_term("test")
            
            assert success is True
            assert result == mock_gifs

    @pytest.mark.asyncio
    async def test_process_search_term_no_results(self):
        """Test search term processing with no results."""
        service = ImageService()
        service.tenor_api_key = "test-key"
        
        with patch.object(service, '_search_tenor_gifs', return_value=[]):
            success, result = await service._process_search_term("test")
            
            assert success is False
            assert "No GIFs found for 'test'" in result

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test ImageService as async context manager."""
        async with ImageService(timeout=5.0) as service:
            assert service.session is not None
            assert isinstance(service.session, aiohttp.ClientSession)
        
        # Session should be closed after exiting context
        assert service.session.closed

    @pytest.mark.asyncio
    async def test_format_user_friendly_error_general_timeout(self):
        """Test general error formatting for timeout."""
        service = ImageService()
        error = service._format_user_friendly_error("general", "Request timeout")
        assert "timed out" in error.lower()

    @pytest.mark.asyncio
    async def test_format_user_friendly_error_general_network(self):
        """Test general error formatting for network error."""
        service = ImageService()
        error = service._format_user_friendly_error("general", "Network connection failed")
        assert "network error" in error.lower()

    @pytest.mark.asyncio
    async def test_format_user_friendly_error_validation_403(self):
        """Test validation error formatting for 403."""
        service = ImageService()
        error = service._format_user_friendly_error("validation", "HTTP 403: Forbidden")
        assert "403" in error
        assert "denied" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_with_session_client_error(self):
        """Test validation with client error."""
        service = ImageService()
        image = Image(url="https://example.com/image.jpg")
        
        mock_session = AsyncMock()
        mock_head_cm = AsyncMock()
        mock_head_cm.__aenter__.side_effect = aiohttp.ClientError("Network error")
        mock_session.head = MagicMock(return_value=mock_head_cm)
        
        success, error = await service._validate_with_session(image, mock_session)
        assert success is False
        assert "Network error" in error

    @pytest.mark.asyncio
    async def test_validate_with_session_general_exception(self):
        """Test validation with general exception."""
        service = ImageService()
        image = Image(url="https://example.com/image.jpg")
        
        mock_session = AsyncMock()
        mock_head_cm = AsyncMock()
        mock_head_cm.__aenter__.side_effect = Exception("Unexpected error")
        mock_session.head = MagicMock(return_value=mock_head_cm)
        
        success, error = await service._validate_with_session(image, mock_session)
        assert success is False
        assert "Unexpected error" in error
