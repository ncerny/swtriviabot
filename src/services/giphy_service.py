"""Service for searching GIFs using Giphy API."""

import os
import aiohttp
from typing import Optional, List, Dict


class GiphyService:
    """Service for searching GIFs via Giphy API."""
    
    def __init__(self):
        """Initialize Giphy service with API key from environment."""
        self.api_key = os.getenv("GIPHY_API_KEY")
        self.base_url = "https://api.giphy.com/v1/gifs"
    
    def is_configured(self) -> bool:
        """Check if Giphy API key is configured."""
        return bool(self.api_key)
    
    async def search_gifs(self, query: str, limit: int = 25) -> List[Dict[str, str]]:
        """Search for GIFs on Giphy.
        
        Args:
            query: Search term
            limit: Maximum number of results (default 25)
            
        Returns:
            List of dicts with 'title' and 'url' keys
        """
        if not self.is_configured():
            print("⚠️  Giphy API not configured. Set GIPHY_API_KEY in .env")
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "api_key": self.api_key,
                    "q": query,
                    "limit": limit,
                    "rating": "pg-13",  # Keep it appropriate
                    "lang": "en",
                }
                
                async with session.get(
                    f"{self.base_url}/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"Giphy API error: {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # Extract GIF info
                    results = []
                    for gif in data.get("data", []):
                        results.append({
                            "title": gif.get("title", "Untitled"),
                            "url": gif["images"]["original"]["url"],
                            "id": gif["id"],
                        })
                    
                    return results
                    
        except aiohttp.ClientError as e:
            print(f"Error fetching from Giphy API: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Giphy service: {e}")
            return []


# Global instance
_giphy_service = None


def get_giphy_service() -> GiphyService:
    """Get the global Giphy service instance."""
    global _giphy_service
    if _giphy_service is None:
        _giphy_service = GiphyService()
    return _giphy_service
