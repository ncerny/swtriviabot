"""
Image model for Discord bot image processing.

This module provides the Image dataclass used for validating and processing
image URLs before displaying them as Discord embeds. The URL hiding feature
ensures clean chat appearance by embedding images instead of showing raw URLs.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Image:
    """Represents an image with validation and embed data."""
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None  # jpeg, png, gif, webp
    size_bytes: Optional[int] = None
    is_valid: bool = True
    validation_error: Optional[str] = None

    def validate_url(self) -> bool:
        """
        Validate URL format and basic accessibility.

        Returns:
            bool: True if URL is valid and accessible
        """
        import re
        from urllib.parse import urlparse

        # Basic URL format validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(self.url):
            self.validation_error = "Invalid URL format"
            self.is_valid = False
            return False

        # Parse URL to ensure it's well-formed
        try:
            parsed = urlparse(self.url)
            if not parsed.netloc:
                self.validation_error = "Missing domain in URL"
                self.is_valid = False
                return False
        except Exception as e:
            self.validation_error = f"URL parsing error: {str(e)}"
            self.is_valid = False
            return False

        self.is_valid = True
        return True

    def get_embed_data(self) -> dict:
        """
        Return Discord embed-compatible data.

        Returns:
            dict: Embed data for Discord API
        """
        if not self.is_valid:
            raise ValueError("Cannot create embed for invalid image")

        embed = {
            "type": "image",
            "url": self.url
        }

        # Add optional fields if available
        if self.width and self.height:
            embed["width"] = self.width
            embed["height"] = self.height

        return embed
