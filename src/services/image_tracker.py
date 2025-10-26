"""
Service to track pending image uploads for trivia questions.

When a user posts a question without an image, we track it and watch
for their next message in case they post an image separately.
"""

import time
from typing import Optional, Dict
from dataclasses import dataclass
import discord


@dataclass
class PendingImageUpload:
    """Tracks a question waiting for an image upload."""
    
    user_id: int
    channel_id: int
    message_id: int  # The question message ID
    guild_id: int
    timestamp: float
    
    def is_expired(self, timeout_seconds: int = 180) -> bool:
        """Check if this pending upload has expired (default 3 minutes)."""
        return time.time() - self.timestamp > timeout_seconds


class ImageTracker:
    """Tracks pending image uploads for trivia questions."""
    
    def __init__(self):
        """Initialize the image tracker."""
        # Key: (guild_id, user_id) -> PendingImageUpload
        self._pending: Dict[tuple[int, int], PendingImageUpload] = {}
    
    def add_pending(
        self,
        user_id: int,
        channel_id: int,
        message_id: int,
        guild_id: int
    ) -> None:
        """
        Track a question that's waiting for an image.
        
        Args:
            user_id: User who posted the question
            channel_id: Channel where question was posted
            message_id: Message ID of the question
            guild_id: Guild ID
        """
        key = (guild_id, user_id)
        self._pending[key] = PendingImageUpload(
            user_id=user_id,
            channel_id=channel_id,
            message_id=message_id,
            guild_id=guild_id,
            timestamp=time.time()
        )
    
    def get_pending(self, guild_id: int, user_id: int) -> Optional[PendingImageUpload]:
        """
        Get pending image upload for a user in a guild.
        
        Args:
            guild_id: Guild ID
            user_id: User ID
            
        Returns:
            PendingImageUpload if found and not expired, None otherwise
        """
        key = (guild_id, user_id)
        pending = self._pending.get(key)
        
        if pending is None:
            return None
        
        # Check if expired
        if pending.is_expired():
            del self._pending[key]
            return None
        
        return pending
    
    def remove_pending(self, guild_id: int, user_id: int) -> None:
        """
        Remove a pending image upload.
        
        Args:
            guild_id: Guild ID
            user_id: User ID
        """
        key = (guild_id, user_id)
        self._pending.pop(key, None)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired pending uploads.
        
        Returns:
            Number of expired entries removed
        """
        expired_keys = [
            key for key, pending in self._pending.items()
            if pending.is_expired()
        ]
        
        for key in expired_keys:
            del self._pending[key]
        
        return len(expired_keys)
    
    def count_pending(self) -> int:
        """Get the number of pending uploads."""
        return len(self._pending)


# Global instance
_image_tracker = ImageTracker()


def get_image_tracker() -> ImageTracker:
    """Get the global image tracker instance."""
    return _image_tracker
