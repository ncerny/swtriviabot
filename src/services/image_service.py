"""
Image service for Discord bot image processing and validation.

This service handles the validation and embedding of image URLs for the Discord trivia bot.
It ensures images are accessible, properly formatted, and within size limits before creating
Discord embeds that hide the URLs from chat, maintaining a clean user interface.

Supports both direct image URLs and Tenor GIF search terms.
"""
import asyncio
import logging
import os
import re
from typing import Tuple, Union, Optional

import aiohttp
from discord import Embed

from ..models.image import Image

logger = logging.getLogger(__name__)


class ImageService:
    """
    Service for validating and processing images for Discord embeds.
    Supports direct image URLs and Tenor GIF search.
    """

    def __init__(self, timeout: float = 10.0):
        """
        Initialize the image service.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session: aiohttp.ClientSession = None
        self.tenor_api_key = os.getenv('TENOR_API_KEY')

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def validate_and_create_embed(self, input_str: str) -> Tuple[bool, Union[Embed, str, list]]:
        """
        Validate an image URL or search for GIF and create a Discord embed.

        Args:
            input_str: Either an image URL or Tenor search term

        Returns:
            Tuple of (success: bool, result: Embed | error_message: str | gif_list: list)
            - For URLs: (True, Embed) or (False, error_str)
            - For search terms: (True, gif_list) or (False, error_str)
        """
        try:
            input_str = input_str.strip()

            # Determine if this is a URL or search term
            if self._is_url(input_str):
                # Handle as direct URL
                return await self._process_direct_url(input_str)
            else:
                # Handle as Tenor search term
                return await self._process_search_term(input_str)

        except Exception as e:
            logger.error(f"Error processing input {input_str}: {str(e)}")
            return False, self._format_user_friendly_error("general", str(e))

    async def _process_direct_url(self, url: str) -> Tuple[bool, Union[Embed, str]]:
        """
        Process a direct image URL.

        Args:
            url: Direct image URL

        Returns:
            Tuple of (success: bool, embed: Embed | error_message: str)
        """
        # Create Image model instance
        image = Image(url=url)

        # Validate URL format first
        if not image.validate_url():
            return False, self._format_user_friendly_error("url_format", image.validation_error)

        # Validate image accessibility and get metadata
        success, error = await self._validate_image_accessibility(image)
        if not success:
            return False, self._format_user_friendly_error("validation", error)

        # Create Discord embed
        embed = Embed()
        embed.set_image(url=image.url)

        # Add metadata if available
        if image.width and image.height:
            embed.add_field(
                name="Dimensions",
                value=f"{image.width} × {image.height}",
                inline=True
            )

        if image.size_bytes:
            size_mb = image.size_bytes / (1024 * 1024)
            embed.add_field(
                name="Size",
                value=f"{size_mb:.1f} MB",
                inline=True
            )

        logger.info(f"Successfully created embed for direct URL: {url}")
        return True, embed

    async def _process_search_term(self, query: str) -> Tuple[bool, Union[list, str]]:
        """
        Process a search term by querying Tenor API.

        Args:
            query: Search term for GIF

        Returns:
            Tuple of (success: bool, gif_list: list | error_message: str)
        """
        if not self.tenor_api_key:
            return False, "❌ **GIF Search Error**: Tenor API key not configured. Please contact the bot administrator."

        logger.info(f"Processing search term: {query}")

        # Search Tenor for GIFs
        gifs = await self._search_tenor_gifs(query)

        if not gifs:
            return False, f"❌ **GIF Search Error**: No GIFs found for '{query}'. Try different search terms or use a direct image URL."

        logger.info(f"Found {len(gifs)} GIFs for search term: {query}")
        return True, gifs

    def _is_url(self, input_str: str) -> bool:
        """
        Determine if input string looks like a URL.

        Args:
            input_str: Input string to check

        Returns:
            True if input looks like a URL, False if it looks like a search term
        """
        # Basic URL pattern check
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(input_str.strip()))

    async def _search_tenor_gifs(self, query: str) -> list[dict]:
        """
        Search Tenor for GIFs and return multiple results.

        Args:
            query: Search query for GIF

        Returns:
            List of dicts with 'url' and 'preview_url' for each result
        """
        if not self.tenor_api_key:
            logger.warning("Tenor API key not configured")
            return None

        if not self.session:
            logger.error("HTTP session not initialized")
            return []

        try:
            # Tenor API search endpoint
            url = "https://tenor.googleapis.com/v2/search"
            params = {
                'q': query.strip(),
                'key': self.tenor_api_key,
                'limit': 5,  # Get top 5 results for selection
                'media_filter': 'gif',  # Only GIFs
                'contentfilter': 'medium'  # Moderate content filter
            }

            logger.info(f"Searching Tenor for: {query}")
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Tenor API error: {response.status}")
                    return []

                data = await response.json()

                results = data.get('results', [])
                if not results:
                    logger.info(f"No Tenor results for: {query}")
                    return []

                # Extract GIF URLs and preview URLs
                gifs = []
                for result in results[:5]:  # Limit to 5
                    media_formats = result.get('media_formats', {})
                    gif_info = media_formats.get('gif')
                    tinygif_info = media_formats.get('tinygif')  # Smaller preview

                    if gif_info and gif_info.get('url'):
                        gif_data = {
                            'url': gif_info['url'],
                            'preview_url': tinygif_info.get('url') if tinygif_info else gif_info['url']
                        }
                        gifs.append(gif_data)

                logger.info(f"Found {len(gifs)} Tenor GIFs for: {query}")
                return gifs

        except asyncio.TimeoutError:
            logger.error(f"Tenor API timeout for query: {query}")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Tenor API network error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Tenor API error: {str(e)}")
            return []

    def _format_user_friendly_error(self, error_type: str, technical_details: str) -> str:
        """
        Convert technical error messages into user-friendly guidance.

        Args:
            error_type: Type of error (url_format, validation, general)
            technical_details: Technical error message

        Returns:
            User-friendly error message with guidance
        """
        base_message = "❌ **Image Error**: "

        if error_type == "url_format":
            return f"{base_message}Please provide a valid image URL (must start with http:// or https://)"

        elif error_type == "validation":
            # Handle specific validation errors
            if "Invalid content type" in technical_details:
                if "text/html" in technical_details:
                    return f"{base_message}This appears to be a webpage link, not a direct image. Right-click on the image and select 'Copy image address' or 'Copy image URL' to get the direct link."
                else:
                    return f"{base_message}The URL doesn't point to a valid image format. Supported formats: JPEG, PNG, GIF, WebP."

            elif "HTTP" in technical_details and "404" in technical_details:
                return f"{base_message}Image not found (404). Please check that the URL is correct and the image still exists."

            elif "HTTP" in technical_details and "403" in technical_details:
                return f"{base_message}Access denied (403). The image may be private or require special permissions."

            elif "Image too large" in technical_details:
                return f"{base_message}Image is too large (Discord limit: 8MB). Please use a smaller image or resize it."

            elif "Unsupported image format" in technical_details:
                return f"{base_message}Unsupported image format. Please use JPEG, PNG, GIF, or WebP."

            elif "timeout" in technical_details.lower():
                return f"{base_message}Image took too long to load. Please try a different URL or check your internet connection."

            else:
                return f"{base_message}Image validation failed: {technical_details}"

        else:  # general errors
            if "timeout" in technical_details.lower():
                return f"{base_message}Request timed out. Please try again or use a different image URL."
            elif "network" in technical_details.lower():
                return f"{base_message}Network error. Please check your internet connection and try again."
            else:
                return f"{base_message}Unable to process image. Please try a different URL or contact support if the issue persists."

    async def _validate_image_accessibility(self, image: Image) -> Tuple[bool, str]:
        """
        Validate that the image URL is accessible and get metadata.

        Args:
            image: Image model instance

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not self.session:
            # Create temporary session if not in context manager
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as temp_session:
                return await self._validate_with_session(image, temp_session)

        return await self._validate_with_session(image, self.session)

    async def _validate_with_session(self, image: Image, session: aiohttp.ClientSession) -> Tuple[bool, str]:
        """
        Validate image with the given session.

        Args:
            image: Image model instance
            session: HTTP session to use

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            async with session.head(image.url) as response:
                if response.status != 200:
                    return False, f"HTTP {response.status}: {response.reason}"

                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if not content_type.startswith('image/'):
                    return False, f"Invalid content type: {content_type}"

                # Extract format from content type
                if 'jpeg' in content_type or 'jpg' in content_type:
                    image.format = 'jpeg'
                elif 'png' in content_type:
                    image.format = 'png'
                elif 'gif' in content_type:
                    image.format = 'gif'
                elif 'webp' in content_type:
                    image.format = 'webp'
                else:
                    return False, f"Unsupported image format: {content_type}"

                # Check content length (size)
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    # Discord limit is 8MB
                    if size_bytes > 8 * 1024 * 1024:
                        return False, "Image too large (max 8MB)"
                    image.size_bytes = size_bytes

                # For more detailed metadata, we could do a GET request
                # But HEAD is sufficient for validation
                image.is_valid = True
                return True, ""

        except asyncio.TimeoutError:
            return False, "Image validation timeout"
        except aiohttp.ClientError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Network or validation error: {str(e)}"


# Convenience function for one-off validation
async def validate_image_url(input_str: str, timeout: float = 10.0) -> Tuple[bool, Union[Embed, str, list]]:
    """
    Convenience function to validate an image URL or search for GIF and create embed.

    Args:
        input_str: Either an image URL or Tenor search term
        timeout: Request timeout

    Returns:
        Tuple of (success: bool, result: Embed | error_message: str | gif_list: list)
    """
    async with ImageService(timeout=timeout) as service:
        return await service.validate_and_create_embed(input_str)
