"""
Klipy API service for searching GIFs, Clips, Stickers, and Memes.

Klipy provides free lifetime access to a comprehensive media library.
Documentation: https://docs.klipy.com/
"""

import os
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class KlipyService:
    """Service for interacting with Klipy API."""

    BASE_URL = "https://api.klipy.com"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Klipy service.

        Args:
            api_key: Klipy API key (app_key). If not provided, reads from KLIPY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("KLIPY_API_KEY")

    async def search_gifs(
        self,
        query: str,
        customer_id: str,
        limit: int = 10,
        content_filter: str = "medium",
        locale: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for GIFs using Klipy API.

        Args:
            query: Search term or phrase
            customer_id: Unique user identifier (required by Klipy for personalization)
            limit: Maximum number of results (8-50, will be capped at 50)
            content_filter: Content safety level - "off", "low", "medium", or "high"
            locale: Country code (ISO 3166-1 alpha-2, e.g., "us", "uk", "ge")

        Returns:
            List of dicts with keys: title, url, id

        Raises:
            ValueError: If API key is not configured or customer_id is not provided
            aiohttp.ClientError: If API request fails
        """
        if not self.api_key:
            raise ValueError(
                "Klipy API key not configured. Set KLIPY_API_KEY environment variable. "
                "Get your API key at: https://partner.klipy.com/api-keys"
            )

        if not customer_id:
            raise ValueError("customer_id is required for Klipy API requests")

        # Klipy requires per_page between 8-50
        per_page = max(8, min(limit, 50))

        # Build API URL
        url = f"{self.BASE_URL}/gif/v2/{self.api_key}/search"

        # Build query parameters
        params = {
            "q": query,
            "per_page": per_page,
            "customer_id": customer_id,
            "content_filter": content_filter,
        }

        if locale:
            params["locale"] = locale

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    # Handle 204 No Content (empty results)
                    if response.status == 204:
                        logger.info(f"✅ Klipy returned no results for query: {query}")
                        return []
                    
                    response.raise_for_status()
                    data = await response.json()

                    # Check if request was successful
                    if not data.get("result"):
                        logger.error(f"❌ Klipy API returned result=false: {data}")
                        return []

                    # Extract GIF data
                    gifs_data = data.get("data", {}).get("gifs", [])

                    # Transform to our standard format
                    gifs = []
                    for gif in gifs_data:
                        # Get the highest quality GIF URL (hd format, gif type)
                        media = gif.get("media", {})
                        hd_media = media.get("hd", {})
                        gif_url = hd_media.get("gif", {}).get("url")

                        # Fallback to md or sm if hd not available
                        if not gif_url:
                            md_media = media.get("md", {})
                            gif_url = md_media.get("gif", {}).get("url")

                        if not gif_url:
                            sm_media = media.get("sm", {})
                            gif_url = sm_media.get("gif", {}).get("url")

                        if gif_url:
                            gifs.append(
                                {
                                    "title": gif.get("title", "Untitled"),
                                    "url": gif_url,
                                    "id": gif.get("slug", gif.get("id", "")),
                                }
                            )

                    logger.info(f"✅ Found {len(gifs)} GIFs from Klipy for query: {query}")
                    return gifs

        except aiohttp.ClientResponseError as e:
            logger.error(f"❌ Klipy API error: {e.status} - {e.message}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"❌ Klipy API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error searching Klipy: {e}")
            raise
