"""Unit tests for ImageTracker service."""

import pytest
import time
from unittest.mock import patch
from src.services.image_tracker import ImageTracker, PendingImageUpload, get_image_tracker


class TestPendingImageUpload:
    """Tests for PendingImageUpload dataclass."""

    def test_pending_image_upload_creation(self):
        """Test creating a PendingImageUpload instance."""
        upload = PendingImageUpload(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999,
            timestamp=time.time()
        )
        assert upload.user_id == 123
        assert upload.channel_id == 456
        assert upload.message_id == 789
        assert upload.guild_id == 999
        assert isinstance(upload.timestamp, float)

    def test_is_expired_not_expired(self):
        """Test that a recent upload is not expired."""
        upload = PendingImageUpload(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999,
            timestamp=time.time()
        )
        assert not upload.is_expired(timeout_seconds=180)

    def test_is_expired_is_expired(self):
        """Test that an old upload is expired."""
        upload = PendingImageUpload(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999,
            timestamp=time.time() - 200  # 200 seconds ago
        )
        assert upload.is_expired(timeout_seconds=180)

    def test_is_expired_custom_timeout(self):
        """Test custom timeout values."""
        upload = PendingImageUpload(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999,
            timestamp=time.time() - 50  # 50 seconds ago
        )
        assert not upload.is_expired(timeout_seconds=60)
        assert upload.is_expired(timeout_seconds=30)


class TestImageTracker:
    """Tests for ImageTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh ImageTracker instance for each test."""
        return ImageTracker()

    def test_add_pending(self, tracker):
        """Test adding a pending upload."""
        tracker.add_pending(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999
        )
        
        pending = tracker.get_pending(guild_id=999, user_id=123)
        assert pending is not None
        assert pending.user_id == 123
        assert pending.channel_id == 456
        assert pending.message_id == 789
        assert pending.guild_id == 999

    def test_get_pending_nonexistent(self, tracker):
        """Test getting a pending upload that doesn't exist."""
        pending = tracker.get_pending(guild_id=999, user_id=123)
        assert pending is None

    def test_remove_pending(self, tracker):
        """Test removing a pending upload."""
        tracker.add_pending(
            user_id=123,
            channel_id=456,
            message_id=789,
            guild_id=999
        )
        
        # Verify it exists
        assert tracker.get_pending(guild_id=999, user_id=123) is not None
        
        # Remove it
        tracker.remove_pending(guild_id=999, user_id=123)
        
        # Verify it's gone
        assert tracker.get_pending(guild_id=999, user_id=123) is None

    def test_remove_pending_nonexistent(self, tracker):
        """Test removing a pending upload that doesn't exist (should not error)."""
        # Should not raise an error
        tracker.remove_pending(guild_id=999, user_id=123)

    def test_multiple_guilds(self, tracker):
        """Test tracking uploads for multiple guilds."""
        tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=111)
        tracker.add_pending(user_id=123, channel_id=456, message_id=790, guild_id=222)
        
        # Should be able to get each one independently
        pending1 = tracker.get_pending(guild_id=111, user_id=123)
        pending2 = tracker.get_pending(guild_id=222, user_id=123)
        
        assert pending1 is not None
        assert pending2 is not None
        assert pending1.message_id == 789
        assert pending2.message_id == 790

    def test_multiple_users_same_guild(self, tracker):
        """Test tracking uploads for multiple users in same guild."""
        tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
        tracker.add_pending(user_id=124, channel_id=456, message_id=790, guild_id=999)
        
        # Should be able to get each one independently
        pending1 = tracker.get_pending(guild_id=999, user_id=123)
        pending2 = tracker.get_pending(guild_id=999, user_id=124)
        
        assert pending1 is not None
        assert pending2 is not None
        assert pending1.user_id == 123
        assert pending2.user_id == 124

    def test_cleanup_expired_none_expired(self, tracker):
        """Test cleanup when no uploads are expired."""
        tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
        tracker.add_pending(user_id=124, channel_id=456, message_id=790, guild_id=999)
        
        removed_count = tracker.cleanup_expired()
        
        assert removed_count == 0
        assert tracker.get_pending(guild_id=999, user_id=123) is not None
        assert tracker.get_pending(guild_id=999, user_id=124) is not None

    def test_cleanup_expired_some_expired(self, tracker):
        """Test cleanup when some uploads are expired."""
        current_time = time.time()
        
        # Add a recent upload
        with patch('time.time', return_value=current_time):
            tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
        
        # Add an expired upload (more than 180 seconds old)
        with patch('time.time', return_value=current_time - 200):
            tracker.add_pending(user_id=124, channel_id=456, message_id=790, guild_id=999)
        
        # Now run cleanup with current time
        with patch('time.time', return_value=current_time):
            removed_count = tracker.cleanup_expired()
        
        assert removed_count == 1
        assert tracker.get_pending(guild_id=999, user_id=123) is not None
        assert tracker.get_pending(guild_id=999, user_id=124) is None

    def test_cleanup_expired_all_expired(self, tracker):
        """Test cleanup when all uploads are expired."""
        current_time = time.time()
        
        # Add expired uploads (more than 180 seconds old)
        with patch('time.time', return_value=current_time - 200):
            tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
            tracker.add_pending(user_id=124, channel_id=456, message_id=790, guild_id=999)
        
        # Now run cleanup with current time
        with patch('time.time', return_value=current_time):
            removed_count = tracker.cleanup_expired()
        
        assert removed_count == 2
        assert tracker.get_pending(guild_id=999, user_id=123) is None
        assert tracker.get_pending(guild_id=999, user_id=124) is None

    def test_overwrite_existing_pending(self, tracker):
        """Test that adding a pending upload for same user/guild overwrites the old one."""
        tracker.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
        tracker.add_pending(user_id=123, channel_id=789, message_id=999, guild_id=999)
        
        pending = tracker.get_pending(guild_id=999, user_id=123)
        assert pending is not None
        assert pending.message_id == 999  # Should be the new one
        assert pending.channel_id == 789  # Should be the new one


class TestGetImageTracker:
    """Tests for the singleton get_image_tracker function."""

    def test_get_image_tracker_singleton(self):
        """Test that get_image_tracker returns the same instance."""
        tracker1 = get_image_tracker()
        tracker2 = get_image_tracker()
        
        assert tracker1 is tracker2

    def test_get_image_tracker_persistence(self):
        """Test that data persists across get_image_tracker calls."""
        tracker1 = get_image_tracker()
        tracker1.add_pending(user_id=123, channel_id=456, message_id=789, guild_id=999)
        
        tracker2 = get_image_tracker()
        pending = tracker2.get_pending(guild_id=999, user_id=123)
        
        assert pending is not None
        assert pending.user_id == 123
