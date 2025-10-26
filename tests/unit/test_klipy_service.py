"""Unit tests for KlipyService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from src.services.klipy_service import KlipyService


def create_mock_response(status=200, json_data=None, raise_error=None):
    """Helper to create a properly mocked aiohttp response."""
    mock_response = AsyncMock()
    mock_response.status = status
    if json_data is not None:
        mock_response.json = AsyncMock(return_value=json_data)
    if raise_error:
        mock_response.raise_for_status = MagicMock(side_effect=raise_error)
    else:
        mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


def create_mock_session(response):
    """Helper to create a properly mocked aiohttp session."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


@pytest.fixture
def klipy_service():
    """Create a KlipyService instance with a test API key."""
    return KlipyService(api_key="test_api_key")


@pytest.fixture
def mock_klipy_response():
    """Create a mock Klipy API response."""
    return {
        "result": True,
        "data": {
            "gifs": [
                {
                    "id": "gif1",
                    "slug": "excited-minion-gif1",
                    "title": "Excited Minion",
                    "media": {
                        "hd": {
                            "gif": {
                                "url": "https://media.klipy.com/gifs/hd/excited-minion.gif",
                                "size": 2048000,
                            },
                            "mp4": {
                                "url": "https://media.klipy.com/gifs/hd/excited-minion.mp4",
                                "size": 512000,
                            },
                        },
                        "md": {
                            "gif": {
                                "url": "https://media.klipy.com/gifs/md/excited-minion.gif",
                                "size": 1024000,
                            }
                        },
                    },
                },
                {
                    "id": "gif2",
                    "slug": "happy-dance-gif2",
                    "title": "Happy Dance",
                    "media": {
                        "md": {
                            "gif": {
                                "url": "https://media.klipy.com/gifs/md/happy-dance.gif",
                                "size": 1536000,
                            }
                        },
                        "sm": {
                            "gif": {
                                "url": "https://media.klipy.com/gifs/sm/happy-dance.gif",
                                "size": 512000,
                            }
                        },
                    },
                },
            ]
        },
    }


class TestKlipyServiceInit:
    """Tests for KlipyService initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        service = KlipyService(api_key="my_api_key")
        assert service.api_key == "my_api_key"

    @patch.dict("os.environ", {"KLIPY_API_KEY": "env_api_key"})
    def test_init_with_env_var(self):
        """Test initialization with API key from environment variable."""
        service = KlipyService()
        assert service.api_key == "env_api_key"

    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        service = KlipyService()
        assert service.api_key is None


class TestKlipyServiceSearchGifs:
    """Tests for search_gifs method."""

    @pytest.mark.asyncio
    async def test_search_gifs_success(self, klipy_service, mock_klipy_response):
        """Test successful GIF search."""
        mock_response = create_mock_response(200, mock_klipy_response)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="excited", customer_id="user123", limit=10
            )

        assert len(results) == 2
        assert results[0]["title"] == "Excited Minion"
        assert results[0]["url"] == "https://media.klipy.com/gifs/hd/excited-minion.gif"
        assert results[0]["id"] == "excited-minion-gif1"
        
        assert results[1]["title"] == "Happy Dance"
        assert results[1]["url"] == "https://media.klipy.com/gifs/md/happy-dance.gif"
        assert results[1]["id"] == "happy-dance-gif2"

    @pytest.mark.asyncio
    async def test_search_gifs_with_locale(self, klipy_service, mock_klipy_response):
        """Test GIF search with locale parameter."""
        mock_response = create_mock_response(200, mock_klipy_response)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="excited", customer_id="user123", limit=10, locale="us"
            )

        # Verify locale was included in the request
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["locale"] == "us"
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_gifs_with_content_filter(self, klipy_service, mock_klipy_response):
        """Test GIF search with content filter."""
        mock_response = create_mock_response(200, mock_klipy_response)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="excited", customer_id="user123", limit=10, content_filter="high"
            )

        # Verify content filter was included in the request
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["content_filter"] == "high"
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_gifs_no_api_key(self):
        """Test search without API key raises ValueError."""
        # Mock environment variable to be None
        with patch.dict('os.environ', {}, clear=False):
            # Remove KLIPY_API_KEY if it exists
            import os
            if 'KLIPY_API_KEY' in os.environ:
                del os.environ['KLIPY_API_KEY']
            
            service = KlipyService(api_key=None)
            
            with pytest.raises(ValueError, match="Klipy API key not configured"):
                await service.search_gifs(query="test", customer_id="user123")

    @pytest.mark.asyncio
    async def test_search_gifs_no_customer_id(self, klipy_service):
        """Test search without customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id is required"):
            await klipy_service.search_gifs(query="test", customer_id="")

    @pytest.mark.asyncio
    async def test_search_gifs_limit_clamping(self, klipy_service, mock_klipy_response):
        """Test that limit is clamped to Klipy's 8-50 range."""
        mock_response = create_mock_response(200, mock_klipy_response)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Test limit too low (< 8)
            await klipy_service.search_gifs(query="test", customer_id="user123", limit=5)
            call_args = mock_session.get.call_args
            assert call_args[1]["params"]["per_page"] == 8

            # Test limit too high (> 50)
            await klipy_service.search_gifs(query="test", customer_id="user123", limit=100)
            call_args = mock_session.get.call_args
            assert call_args[1]["params"]["per_page"] == 50

            # Test limit within range
            await klipy_service.search_gifs(query="test", customer_id="user123", limit=25)
            call_args = mock_session.get.call_args
            assert call_args[1]["params"]["per_page"] == 25

    @pytest.mark.asyncio
    async def test_search_gifs_empty_results(self, klipy_service):
        """Test handling of empty search results."""
        mock_response = create_mock_response(200, {"result": True, "data": {"gifs": []}})
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="nonexistent", customer_id="user123"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_gifs_result_false(self, klipy_service):
        """Test handling when API returns result=false."""
        mock_response = create_mock_response(200, {"result": False, "data": {}})
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="test", customer_id="user123"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_gifs_204_no_content(self, klipy_service):
        """Test handling of 204 No Content response (empty results)."""
        mock_response = create_mock_response(204, json_data=None)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="nonexistent", customer_id="user123"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_gifs_missing_hd_format(self, klipy_service):
        """Test fallback when HD format is not available."""
        mock_response_data = {
            "result": True,
            "data": {
                "gifs": [
                    {
                        "id": "gif1",
                        "slug": "test-gif",
                        "title": "Test GIF",
                        "media": {
                            "sm": {
                                "gif": {
                                    "url": "https://media.klipy.com/gifs/sm/test.gif"
                                }
                            }
                        },
                    }
                ]
            },
        }

        mock_response = create_mock_response(200, mock_response_data)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="test", customer_id="user123"
            )

        assert len(results) == 1
        assert results[0]["url"] == "https://media.klipy.com/gifs/sm/test.gif"

    @pytest.mark.asyncio
    async def test_search_gifs_no_gif_url(self, klipy_service):
        """Test handling when no GIF URL is available in any format."""
        mock_response_data = {
            "result": True,
            "data": {
                "gifs": [
                    {
                        "id": "gif1",
                        "slug": "test-gif",
                        "title": "Test GIF",
                        "media": {
                            "hd": {
                                "mp4": {  # Only MP4, no GIF
                                    "url": "https://media.klipy.com/gifs/hd/test.mp4"
                                }
                            }
                        },
                    }
                ]
            },
        }

        mock_response = create_mock_response(200, mock_response_data)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await klipy_service.search_gifs(
                query="test", customer_id="user123"
            )

        # Should skip GIFs without a gif URL
        assert results == []

    @pytest.mark.asyncio
    async def test_search_gifs_http_error(self, klipy_service):
        """Test handling of HTTP errors."""
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=403,
            message="Forbidden"
        )
        mock_response = create_mock_response(403, raise_error=error)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(aiohttp.ClientResponseError):
                await klipy_service.search_gifs(
                    query="test", customer_id="user123"
                )

    @pytest.mark.asyncio
    async def test_search_gifs_network_error(self, klipy_service):
        """Test handling of network errors."""
        mock_session = MagicMock()
        error = aiohttp.ClientError("Network error")
        mock_session.get = MagicMock(side_effect=error)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(aiohttp.ClientError):
                await klipy_service.search_gifs(
                    query="test", customer_id="user123"
                )

    @pytest.mark.asyncio
    async def test_search_gifs_correct_url_format(self, klipy_service, mock_klipy_response):
        """Test that correct URL format is used for API calls."""
        mock_response = create_mock_response(200, mock_klipy_response)
        mock_session = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await klipy_service.search_gifs(
                query="excited", customer_id="user123", limit=10
            )

        # Verify the URL includes the API key
        call_args = mock_session.get.call_args
        assert call_args[0][0] == "https://api.klipy.com/gif/v2/test_api_key/search"
        
        # Verify required parameters
        params = call_args[1]["params"]
        assert params["q"] == "excited"
        assert params["customer_id"] == "user123"
        assert params["per_page"] == 10
        assert params["content_filter"] == "medium"
