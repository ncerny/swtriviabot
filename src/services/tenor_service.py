"""Service for interacting with Tenor GIF API."""

import os
import re
import aiohttp
from typing import Optional


class TenorService:
    """Service for fetching GIF data from Tenor API."""
    
    def __init__(self):
        """Initialize Tenor service with API key from environment."""
        self.api_key = os.getenv("TENOR_API_KEY")
        self.base_url = "https://tenor.googleapis.com/v2"
    
    def is_configured(self) -> bool:
        """Check if Tenor API key is configured."""
        return bool(self.api_key)
    
    async def get_gif_url_from_view_url(self, view_url: str) -> Optional[str]:
        """Extract direct GIF URL from a Tenor view URL.
        
        Args:
            view_url: Tenor view URL (e.g., https://tenor.com/view/something-gif-123456)
            
        Returns:
            Direct GIF URL if successful, None otherwise
        """
        if not self.is_configured():
            print("Warning: TENOR_API_KEY not configured, cannot convert Tenor URLs")
            return None
        
        # Extract GIF ID from URL
        # Format: https://tenor.com/view/name-name-gif-123456789...
        # or: https://tenor.com/view/name-name-name-gif-123456789...
        gif_id = self._extract_gif_id(view_url)
        if not gif_id:
            print(f"Could not extract GIF ID from URL: {view_url}")
            return None
        
        # Call Tenor API to get GIF details
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "key": self.api_key,
                    "ids": gif_id,
                    "media_filter": "gif",  # We want GIF format
                }
                
                async with session.get(
                    f"{self.base_url}/posts",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"Tenor API error: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Extract the GIF URL from response
                    if data and "results" in data and len(data["results"]) > 0:
                        result = data["results"][0]
                        # Get the GIF format from media
                        if "media_formats" in result and "gif" in result["media_formats"]:
                            gif_url = result["media_formats"]["gif"]["url"]
                            print(f"Successfully converted Tenor URL to: {gif_url}")
                            return gif_url
                    
                    print("No GIF found in Tenor API response")
                    return None
                    
        except aiohttp.ClientError as e:
            print(f"Error fetching from Tenor API: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in Tenor service: {e}")
            return None
    
    def _extract_gif_id(self, url: str) -> Optional[str]:
        """Extract GIF ID from Tenor view URL.
        
        Args:
            url: Tenor view URL
            
        Returns:
            GIF ID string if found, None otherwise
        """
        # Match the long numeric ID at the end
        # Format: https://tenor.com/view/something-gif-10510967267960640794
        match = re.search(r'-gif-(\d+)$', url.rstrip('/'))
        if match:
            return match.group(1)
        
        # Also try the older format with shorter IDs
        # Format: https://tenor.com/view/something-12345678
        match = re.search(r'-(\d+)$', url.rstrip('/'))
        if match:
            return match.group(1)
        
        return None


# Global instance
_tenor_service = None


def get_tenor_service() -> TenorService:
    """Get the global Tenor service instance."""
    global _tenor_service
    if _tenor_service is None:
        _tenor_service = TenorService()
    return _tenor_service
