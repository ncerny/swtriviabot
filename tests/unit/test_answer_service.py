"""Unit tests for answer_service module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.services import answer_service
from src.models.answer import Answer
from src.models.session import TriviaSession


@patch('src.services.answer_service.storage_service')
def test_submit_answer_creates_new_session(mock_storage):
    """Test that submitting an answer creates a new session if none exists."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    text = "Test answer"
    
    # Mock storage to return None (no existing session)
    mock_storage.load_session.return_value = None
    
    answer, is_update = answer_service.submit_answer(guild_id, user_id, username, text)
    
    assert answer.user_id == user_id
    assert answer.username == username
    assert answer.text == text
    assert not is_update
    
    # Verify session was saved
    mock_storage.save_session.assert_called_once()


@patch('src.services.answer_service.storage_service')
def test_submit_answer_updates_existing_answer(mock_storage):
    """Test that submitting a second answer updates the first."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    
    # Create existing session with an answer
    existing_session = TriviaSession(guild_id=guild_id)
    existing_session.add_or_update_answer(Answer(
        user_id=user_id,
        username=username,
        text="First answer",
        timestamp=datetime.now(timezone.utc),
    ))
    
    mock_storage.load_session.return_value = existing_session
    
    # Submit updated answer
    answer, is_update = answer_service.submit_answer(guild_id, user_id, username, "Second answer")
    
    assert is_update
    assert answer.text == "Second answer"
    assert answer.is_updated


@patch('src.services.answer_service.storage_service')
def test_submit_answer_validates_text(mock_storage):
    """Test that empty text raises ValueError."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    
    with pytest.raises(ValueError, match="Answer text cannot be empty"):
        answer_service.submit_answer(guild_id, user_id, username, "   ")


@patch('src.services.answer_service.storage_service')
def test_get_session_returns_none_for_nonexistent(mock_storage):
    """Test that get_session returns None for non-existent guild."""
    mock_storage.load_session.return_value = None
    
    session = answer_service.get_session("nonexistent_guild")
    assert session is None


@patch('src.services.answer_service.storage_service')
def test_get_session_returns_existing_session(mock_storage):
    """Test that get_session returns an existing session."""
    guild_id = "test_guild_123"
    
    existing_session = TriviaSession(guild_id=guild_id)
    mock_storage.load_session.return_value = existing_session
    
    session = answer_service.get_session(guild_id)
    assert session is not None
    assert session.guild_id == guild_id


@patch('src.services.answer_service.storage_service')
def test_reset_session_deletes_from_storage(mock_storage):
    """Test that reset_session deletes the session from storage."""
    guild_id = "test_guild_123"
    
    answer_service.reset_session(guild_id)
    
    mock_storage.delete_session.assert_called_once_with(guild_id)


@patch('src.services.answer_service.storage_service')
def test_create_session(mock_storage):
    """Test that create_session creates an empty session."""
    guild_id = "test_guild_123"
    
    session = answer_service.create_session(guild_id)
    
    assert session.guild_id == guild_id
    assert len(session.answers) == 0


@patch('src.services.answer_service.storage_service')
def test_multiple_users_same_guild(mock_storage):
    """Test that multiple users can submit answers to the same guild."""
    guild_id = "test_guild_123"
    
    # Start with empty session
    session = TriviaSession(guild_id=guild_id)
    
    def load_session_side_effect(gid):
        return session if gid == guild_id else None
    
    mock_storage.load_session.side_effect = load_session_side_effect
    
    # Submit answers from different users
    answer_service.submit_answer(guild_id, "user_1", "User1", "Answer1")
    answer_service.submit_answer(guild_id, "user_2", "User2", "Answer2")
    answer_service.submit_answer(guild_id, "user_3", "User3", "Answer3")
    
    # Verify all answers were added to session
    assert len(session.answers) == 3
    assert "user_1" in session.answers
    assert "user_2" in session.answers
    assert "user_3" in session.answers


@patch('src.services.answer_service.storage_service')
def test_submit_answer_with_long_text(mock_storage):
    """Test submitting answer with very long text."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    long_text = "A" * 3000  # Long but under 4000 char limit
    
    mock_storage.load_session.return_value = None
    
    answer, is_update = answer_service.submit_answer(guild_id, user_id, username, long_text)
    
    assert answer.text == long_text
    assert not is_update


@patch('src.services.answer_service.storage_service')
def test_submit_answer_saves_to_storage(mock_storage):
    """Test that submitting an answer saves the session to storage."""
    guild_id = "test_guild_123"
    mock_storage.load_session.return_value = None
    
    answer_service.submit_answer(guild_id, "user_123", "TestUser", "Test answer")
    
    # Verify save was called
    assert mock_storage.save_session.called
    call_args = mock_storage.save_session.call_args
    assert call_args[0][0] == guild_id
    assert isinstance(call_args[0][1], TriviaSession)
