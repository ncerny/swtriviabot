"""Integration tests for answer submission workflow."""

import pytest
from unittest.mock import AsyncMock, patch

from src.commands.answer import answer_command
from src.services import answer_service, storage_service


@pytest.mark.asyncio
async def test_submit_answer_first_time(mock_interaction, tmp_path):
    """Test submitting an answer for the first time."""
    storage_service.DATA_DIR = tmp_path
    
    # Call the callback function directly
    await answer_command.callback(mock_interaction, text="Paris")
    
    # Verify response was deferred
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    
    # Verify success message sent
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "✅ Your answer has been recorded!" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_submit_answer_update_existing(mock_interaction, tmp_path):
    """Test updating an existing answer."""
    storage_service.DATA_DIR = tmp_path
    
    # First submission
    await answer_command.callback(mock_interaction, text="Paris")
    
    # Reset mock
    mock_interaction.reset_mock()
    mock_interaction.response = AsyncMock()
    mock_interaction.followup = AsyncMock()
    
    # Second submission (update)
    await answer_command.callback(mock_interaction, text="France")
    
    # Verify update message
    call_args = mock_interaction.followup.send.call_args
    assert "🔄 You've already answered this question - updating your answer!" in call_args[0][0]


@pytest.mark.asyncio
async def test_submit_empty_answer(mock_interaction, tmp_path):
    """Test that empty answers are rejected."""
    storage_service.DATA_DIR = tmp_path
    
    await answer_command.callback(mock_interaction, text="   ")
    
    # Verify error message
    call_args = mock_interaction.followup.send.call_args
    assert "❌" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_submit_answer_creates_session_file(mock_interaction, tmp_path):
    """Test that submitting an answer creates a session file on disk."""
    storage_service.DATA_DIR = tmp_path
    
    await answer_command.callback(mock_interaction, text="Test answer")
    
    # Verify file was created
    guild_id = str(mock_interaction.guild_id)
    file_path = tmp_path / f"{guild_id}.json"
    assert file_path.exists()


@pytest.mark.asyncio
async def test_multiple_users_submit_answers(mock_interaction, tmp_path):
    """Test multiple users submitting answers to the same guild."""
    storage_service.DATA_DIR = tmp_path
    
    # User 1 submits
    await answer_command.callback(mock_interaction, text="Answer 1")
    
    # User 2 submits
    mock_interaction.user.id = 999888777666
    mock_interaction.user.display_name = "User2"
    await answer_command.callback(mock_interaction, text="Answer 2")
    
    # Verify both answers are stored
    guild_id = str(mock_interaction.guild_id)
    session = answer_service.get_session(guild_id)
    assert len(session.answers) == 2


@pytest.mark.asyncio
async def test_dm_submission_rejected(mock_interaction, tmp_path):
    """Test that answers via DM are rejected."""
    storage_service.DATA_DIR = tmp_path
    mock_interaction.guild_id = None
    
    await answer_command.callback(mock_interaction, text="Test answer")
    
    # Verify error message about DMs
    call_args = mock_interaction.followup.send.call_args
    assert "DMs" in call_args[0][0] or "server" in call_args[0][0]
