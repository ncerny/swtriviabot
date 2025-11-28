"""Integration tests for list_answers command."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.commands.list_answers import list_answers_command, list_answers_error
from src.services import answer_service
from src.models.session import TriviaSession
from discord import app_commands


@pytest.mark.asyncio
async def test_list_answers_empty(mock_interaction):
    """Test listing answers when no submissions exist."""
    with patch('src.services.answer_service.storage_service') as mock_storage:
        mock_storage.load_session.return_value = None
        
        await list_answers_command.callback(mock_interaction)
        
        # Verify response was deferred
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        
        # Verify empty message
        call_args = mock_interaction.followup.send.call_args
        assert "No answers submitted yet" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_answers_with_submissions(mock_interaction):
    """Test listing answers after users submit."""
    guild_id = str(mock_interaction.guild_id)
    
    with patch('src.services.answer_service.storage_service') as mock_storage:
        # Create session
        session = TriviaSession(guild_id=guild_id)
        
        # Mock storage to return the session when loading
        mock_storage.load_session.return_value = session
        
        # Now submit answers (which will use the mocked session)
        answer_service.submit_answer(guild_id, "user1", "User1", "Answer 1")
        answer_service.submit_answer(guild_id, "user2", "User2", "Answer 2")
        
        await list_answers_command.callback(mock_interaction)
        
        # Verify answer list
        call_args = mock_interaction.followup.send.call_args
        message = call_args[0][0]
        assert "Current Session Answers" in message
        assert "User1" in message
        assert "User2" in message
        assert "Answer 1" in message
        assert "Answer 2" in message
        assert "Total answers: 2" in message
        assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_answers_truncates_long_content(mock_interaction):
    """Test that very long answer lists are truncated."""
    guild_id = str(mock_interaction.guild_id)
    
    with patch('src.services.answer_service.storage_service') as mock_storage:
        # Create session
        session = TriviaSession(guild_id=guild_id)
        
        # Mock storage to return the session when loading
        mock_storage.load_session.return_value = session
        
        # Now submit many long answers (which will use the mocked session)
        for i in range(20):
            long_answer = "A" * 100  # 100 char answer
            answer_service.submit_answer(guild_id, f"user{i}", f"User{i}", long_answer)
        
        await list_answers_command.callback(mock_interaction)
        
        # Verify truncation
        call_args = mock_interaction.followup.send.call_args
        message = call_args[0][0]
        assert "truncated due to length" in message
        assert len(message) <= 2000  # Discord limit


@pytest.mark.asyncio
async def test_list_answers_dm_rejected(mock_interaction):
    """Test that list-answers cannot be used in DMs."""
    mock_interaction.guild_id = None
    
    await list_answers_command.callback(mock_interaction)
    
    # Verify DM rejection
    call_args = mock_interaction.followup.send.call_args
    assert "can only be used in a server" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_answers_permission_error(mock_interaction):
    """Test permission error handler."""
    # Mock is_done to return False so send_message is used
    mock_interaction.response.is_done = MagicMock(return_value=False)
    
    error = app_commands.MissingPermissions(["administrator"])
    
    await list_answers_error(mock_interaction, error)
    
    # Verify permission error message
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    # Check keyword arguments instead of positional
    assert call_args.kwargs["ephemeral"] is True
    # Message is first positional arg
    assert "don't have permission" in call_args.args[0]


@pytest.mark.asyncio
async def test_list_answers_handles_unexpected_errors(mock_interaction, monkeypatch):
    """Test that unexpected errors are handled gracefully."""
    # Force an error by making answer_service.get_session raise an exception
    def mock_get_session(guild_id):
        raise RuntimeError("Simulated error")
    
    monkeypatch.setattr(answer_service, "get_session", mock_get_session)
    
    await list_answers_command.callback(mock_interaction)
    
    # Verify error message
    call_args = mock_interaction.followup.send.call_args
    assert "Something went wrong" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True
