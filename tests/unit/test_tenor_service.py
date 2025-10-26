"""Unit tests for Tenor service."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientError

from src.services.tenor_service import TenorService, get_tenor_service


@pytest.fixture
def tenor_service():
    """Create a Tenor service instance with a test API key."""
    with patch.dict(os.environ, {"TENOR_API_KEY": "test_api_key_12345"}):
        service = TenorService()
        yield service


@pytest.fixture
def tenor_service_no_key():
    """Create a Tenor service instance without API key."""
    with patch.dict(os.environ, {}, clear=True):
        if "TENOR_API_KEY" in os.environ:
            del os.environ["TENOR_API_KEY"]
        service = TenorService()
        yield service


def test_tenor_service_initialization_with_key():
    """Test that TenorService initializes correctly with API key."""
    with patch.dict(os.environ, {"TENOR_API_KEY": "test_key"}):
        service = TenorService()
        assert service.api_key == "test_key"
        assert service.base_url == "https://tenor.googleapis.com/v2"
        assert service.is_configured() is True


def test_tenor_service_initialization_without_key():
    """Test that TenorService initializes correctly without API key."""
    with patch.dict(os.environ, {}, clear=True):
        if "TENOR_API_KEY" in os.environ:
            del os.environ["TENOR_API_KEY"]
        service = TenorService()
        assert service.api_key is None
        assert service.is_configured() is False


def test_extract_gif_id_new_format(tenor_service):
    """Test extracting GIF ID from new Tenor URL format."""
    url = "https://tenor.com/view/star-trek-enterprise-enterprise-d-star-trek-the-next-generation-tng-gif-10510967267960640794"
    gif_id = tenor_service._extract_gif_id(url)
    assert gif_id == "10510967267960640794"


def test_extract_gif_id_old_format(tenor_service):
    """Test extracting GIF ID from old Tenor URL format."""
    url = "https://tenor.com/view/funny-cat-12345678"
    gif_id = tenor_service._extract_gif_id(url)
    assert gif_id == "12345678"


def test_extract_gif_id_with_trailing_slash(tenor_service):
    """Test extracting GIF ID from URL with trailing slash."""
    url = "https://tenor.com/view/test-gif-12345678/"
    gif_id = tenor_service._extract_gif_id(url)
    assert gif_id == "12345678"


def test_extract_gif_id_invalid_url(tenor_service):
    """Test extracting GIF ID from invalid URL."""
    url = "https://tenor.com/something-else"
    gif_id = tenor_service._extract_gif_id(url)
    assert gif_id is None


@pytest.mark.asyncio
async def test_get_gif_url_not_configured(tenor_service_no_key):
    """Test that get_gif_url returns None when API key not configured."""
    url = "https://tenor.com/view/test-gif-12345678"
    result = await tenor_service_no_key.get_gif_url_from_view_url(url)
    assert result is None


@pytest.mark.asyncio
async def test_get_gif_url_invalid_url(tenor_service):
    """Test that get_gif_url returns None for invalid URL."""
    url = "https://tenor.com/invalid"
    result = await tenor_service.get_gif_url_from_view_url(url)
    assert result is None


@pytest.mark.asyncio
async def test_get_gif_url_success(tenor_service):
    """Test successful GIF URL retrieval from Tenor API."""
    mock_response = {
        "results": [
            {
                "media_formats": {
                    "gif": {
                        "url": "https://media.tenor.com/test.gif"
                    }
                }
            }
        ]
    }
    
    # Create a mock for ClientSession and response
    with patch("aiohttp.ClientSession") as MockSession:
        # Mock the response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        
        # Mock the session.get context manager
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        
        # Mock the session context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        
        MockSession.return_value = mock_session_cm
        
        url = "https://tenor.com/view/test-gif-12345678"
        result = await tenor_service.get_gif_url_from_view_url(url)
        
        assert result == "https://media.tenor.com/test.gif"
        mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_gif_url_api_error(tenor_service):
    """Test handling of Tenor API error response."""
    with patch("aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 404
        
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        
        MockSession.return_value = mock_session_cm
        
        url = "https://tenor.com/view/test-gif-12345678"
        result = await tenor_service.get_gif_url_from_view_url(url)
        
        assert result is None


@pytest.mark.asyncio
async def test_get_gif_url_network_error(tenor_service):
    """Test handling of network error during API call."""
    mock_session = AsyncMock()
    mock_session.get.side_effect = ClientError("Network error")
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = "https://tenor.com/view/test-gif-12345678"
        result = await tenor_service.get_gif_url_from_view_url(url)
        
        assert result is None


@pytest.mark.asyncio
async def test_get_gif_url_empty_response(tenor_service):
    """Test handling of empty response from Tenor API."""
    mock_response = {"results": []}
    
    with patch("aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        
        MockSession.return_value = mock_session_cm
        
        url = "https://tenor.com/view/test-gif-12345678"
        result = await tenor_service.get_gif_url_from_view_url(url)
        
        assert result is None


@pytest.mark.asyncio
async def test_get_gif_url_missing_gif_format(tenor_service):
    """Test handling when GIF format is missing from response."""
    mock_response = {
        "results": [
            {
                "media_formats": {
                    "mp4": {
                        "url": "https://media.tenor.com/test.mp4"
                    }
                }
            }
        ]
    }
    
    with patch("aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        
        MockSession.return_value = mock_session_cm
        
        url = "https://tenor.com/view/test-gif-12345678"
        result = await tenor_service.get_gif_url_from_view_url(url)
        
        assert result is None


def test_get_tenor_service_singleton():
    """Test that get_tenor_service returns a singleton instance."""
    service1 = get_tenor_service()
    service2 = get_tenor_service()
    assert service1 is service2
