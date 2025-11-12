"""Unit tests for storage_service module."""

import pytest
import json
from pathlib import Path

from src.services import storage_service
from src.models.session import TriviaSession
from src.models.answer import Answer
from datetime import datetime, timezone


def test_save_and_load_session(tmp_path):
    """Test saving and loading a session."""
    # Override data directory for testing
    storage_service.DATA_DIR = tmp_path
    
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    session.add_or_update_answer(Answer(
        user_id="user_123",
        username="TestUser",
        text="Test answer",
        timestamp=datetime.now(timezone.utc),
    ))
    
    # Save session
    storage_service.save_session_to_disk(guild_id, session)
    
    # Verify file exists
    file_path = tmp_path / f"{guild_id}.json"
    assert file_path.exists()
    
    # Load session
    loaded_session = storage_service.load_session_from_disk(guild_id)
    
    assert loaded_session is not None
    assert loaded_session.guild_id == guild_id
    assert len(loaded_session.answers) == 1
    assert "user_123" in loaded_session.answers


def test_load_nonexistent_session(tmp_path):
    """Test loading a session that doesn't exist."""
    storage_service.DATA_DIR = tmp_path
    
    session = storage_service.load_session_from_disk("nonexistent_guild")
    assert session is None


def test_delete_session_file(tmp_path):
    """Test deleting a session file."""
    storage_service.DATA_DIR = tmp_path
    
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    
    # Save session
    storage_service.save_session_to_disk(guild_id, session)
    file_path = tmp_path / f"{guild_id}.json"
    assert file_path.exists()
    
    # Delete session
    storage_service.delete_session_file(guild_id)
    assert not file_path.exists()


def test_delete_nonexistent_session_file(tmp_path):
    """Test deleting a session file that doesn't exist (should not error)."""
    storage_service.DATA_DIR = tmp_path
    
    # Should not raise an exception
    storage_service.delete_session_file("nonexistent_guild")


def test_load_all_sessions(tmp_path):
    """Test loading all sessions from disk."""
    storage_service.DATA_DIR = tmp_path
    
    # Create multiple sessions
    guilds = ["guild_1", "guild_2", "guild_3"]
    for guild_id in guilds:
        session = TriviaSession(guild_id=guild_id)
        storage_service.save_session_to_disk(guild_id, session)
    
    # Load all sessions
    all_sessions = storage_service.load_all_sessions()
    
    assert len(all_sessions) == 3
    assert all(guild_id in all_sessions for guild_id in guilds)


def test_load_all_sessions_empty_directory(tmp_path):
    """Test loading sessions from an empty directory."""
    storage_service.DATA_DIR = tmp_path
    
    all_sessions = storage_service.load_all_sessions()
    assert len(all_sessions) == 0


def test_save_session_atomic_write(tmp_path):
    """Test that session save uses atomic write (no .tmp files left behind)."""
    storage_service.DATA_DIR = tmp_path
    
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    
    storage_service.save_session_to_disk(guild_id, session)
    
    # Check that no .tmp files exist
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
    
    # Check that the actual file exists
    json_file = tmp_path / f"{guild_id}.json"
    assert json_file.exists()


def test_load_corrupted_session_file(tmp_path):
    """Test loading a corrupted JSON file returns None."""
    storage_service.DATA_DIR = tmp_path
    
    guild_id = "test_guild_123"
    file_path = tmp_path / f"{guild_id}.json"
    
    # Write invalid JSON
    file_path.write_text("{ invalid json }")
    
    # Should return None instead of raising an exception
    session = storage_service.load_session_from_disk(guild_id)
    assert session is None


def test_session_json_format(tmp_path):
    """Test that saved session has correct JSON structure."""
    storage_service.DATA_DIR = tmp_path
    
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    session.add_or_update_answer(Answer(
        user_id="user_123",
        username="TestUser",
        text="Test answer",
        timestamp=datetime.now(timezone.utc),
    ))
    
    storage_service.save_session_to_disk(guild_id, session)
    
    # Read and parse JSON
    file_path = tmp_path / f"{guild_id}.json"
    with open(file_path, "r") as f:
        data = json.load(f)
    
    # Verify structure
    assert "guild_id" in data
    assert "answers" in data
    assert "created_at" in data
    assert "last_activity" in data
    assert data["guild_id"] == guild_id


def test_save_session_cleans_temp_on_failure(tmp_path, monkeypatch):
    """Temp files are removed if the final rename fails."""

    storage_service.DATA_DIR = tmp_path
    guild_id = "guild"
    session = TriviaSession(guild_id=guild_id)

    class _ReplaceError(Exception):
        pass

    original_replace = Path.replace

    def _patched_replace(self, target):
        if self.suffix == ".tmp":
            raise _ReplaceError("rename failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", _patched_replace)

    with pytest.raises(_ReplaceError):
        storage_service.save_session_to_disk(guild_id, session)

    assert not any(tmp_path.glob("*.tmp"))


