"""Unit tests for answer_service module."""

import pytest
from datetime import datetime, timezone

from src.services import answer_service
from src.models.answer import Answer
from src.models.session import TriviaSession


def test_submit_answer_creates_new_session():
    """Test that submitting an answer creates a new session if none exists."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    text = "Test answer"
    
    answer, is_update = answer_service.submit_answer(guild_id, user_id, username, text)
    
    assert answer.user_id == user_id
    assert answer.username == username
    assert answer.text == text
    assert not is_update
    assert guild_id in answer_service._sessions


def test_submit_answer_updates_existing_answer():
    """Test that submitting a second answer updates the first."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    
    # First submission
    answer1, is_update1 = answer_service.submit_answer(guild_id, user_id, username, "First answer")
    assert not is_update1
    
    # Second submission (update)
    answer2, is_update2 = answer_service.submit_answer(guild_id, user_id, username, "Second answer")
    assert is_update2
    assert answer2.text == "Second answer"
    assert answer2.is_updated


def test_submit_answer_validates_text():
    """Test that empty text raises ValueError."""
    guild_id = "test_guild_123"
    user_id = "user_456"
    username = "TestUser"
    
    with pytest.raises(ValueError, match="Answer text cannot be empty"):
        answer_service.submit_answer(guild_id, user_id, username, "   ")


def test_get_session_returns_none_for_nonexistent():
    """Test that get_session returns None for non-existent guild."""
    session = answer_service.get_session("nonexistent_guild")
    assert session is None


def test_get_session_returns_existing_session():
    """Test that get_session returns an existing session."""
    guild_id = "test_guild_123"
    
    # Create session by submitting an answer
    answer_service.submit_answer(guild_id, "user_123", "TestUser", "Test answer")
    
    session = answer_service.get_session(guild_id)
    assert session is not None
    assert session.guild_id == guild_id
    assert len(session.answers) == 1


def test_reset_session_clears_answers():
    """Test that reset_session removes the session."""
    guild_id = "test_guild_123"
    
    # Create session
    answer_service.submit_answer(guild_id, "user_123", "TestUser", "Test answer")
    assert guild_id in answer_service._sessions
    
    # Reset
    answer_service.reset_session(guild_id)
    assert guild_id not in answer_service._sessions


def test_reset_session_handles_nonexistent_guild():
    """Test that resetting a non-existent session doesn't raise an error."""
    answer_service.reset_session("nonexistent_guild")
    # Should not raise any exception


def test_create_session():
    """Test that create_session creates an empty session."""
    guild_id = "test_guild_123"
    
    session = answer_service.create_session(guild_id)
    
    assert session.guild_id == guild_id
    assert len(session.answers) == 0
    assert guild_id in answer_service._sessions


def test_get_all_sessions():
    """Test that get_all_sessions returns all active sessions."""
    # Create multiple sessions
    answer_service.submit_answer("guild_1", "user_1", "User1", "Answer1")
    answer_service.submit_answer("guild_2", "user_2", "User2", "Answer2")
    
    all_sessions = answer_service.get_all_sessions()
    
    assert len(all_sessions) == 2
    assert "guild_1" in all_sessions
    assert "guild_2" in all_sessions


def test_load_sessions():
    """Test that load_sessions replaces current sessions."""
    # Create initial session
    answer_service.submit_answer("guild_1", "user_1", "User1", "Answer1")
    
    # Create new sessions to load
    new_sessions = {
        "guild_2": TriviaSession(guild_id="guild_2"),
        "guild_3": TriviaSession(guild_id="guild_3"),
    }
    
    answer_service.load_sessions(new_sessions)
    
    all_sessions = answer_service.get_all_sessions()
    assert "guild_1" not in all_sessions
    assert "guild_2" in all_sessions
    assert "guild_3" in all_sessions


def test_multiple_users_same_guild():
    """Test that multiple users can submit answers to the same guild."""
    guild_id = "test_guild_123"
    
    answer_service.submit_answer(guild_id, "user_1", "User1", "Answer1")
    answer_service.submit_answer(guild_id, "user_2", "User2", "Answer2")
    answer_service.submit_answer(guild_id, "user_3", "User3", "Answer3")
    
    session = answer_service.get_session(guild_id)
    assert len(session.answers) == 3
    assert "user_1" in session.answers
    assert "user_2" in session.answers
    assert "user_3" in session.answers
