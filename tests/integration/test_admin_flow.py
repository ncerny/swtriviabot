"""Integration tests for admin commands workflow."""

import pytest
from unittest.mock import AsyncMock

from src.commands.list_answers import list_answers_command
from src.commands.reset_answers import reset_answers_command
from src.services import answer_service, storage_service


@pytest.mark.asyncio
async def test_list_answers_empty(mock_interaction, tmp_path):
    """Test listing answers when none exist."""
    storage_service.DATA_DIR = tmp_path
    
    await list_answers_command.callback(mock_interaction)
    
    # Verify empty message
    call_args = mock_interaction.followup.send.call_args
    assert "No answers submitted yet" in call_args[0][0]


@pytest.mark.asyncio
async def test_list_answers_with_submissions(mock_interaction, tmp_path):
    """Test listing answers after users submit."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)
    
    # Create answers
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


@pytest.mark.asyncio
async def test_reset_answers(mock_interaction, tmp_path):
    """Test resetting answers."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)
    
    # Create answers
    answer_service.submit_answer(guild_id, "user1", "User1", "Answer 1")
    
    # Save to disk
    session = answer_service.get_session(guild_id)
    storage_service.save_session_to_disk(guild_id, session)
    
    # Verify file exists
    file_path = tmp_path / f"{guild_id}.json"
    assert file_path.exists()
    
    # Reset
    await reset_answers_command.callback(mock_interaction)
    
    # Verify session cleared
    session_after = answer_service.get_session(guild_id)
    assert session_after is None
    
    # Verify file deleted
    assert not file_path.exists()
    
    # Verify confirmation message
    call_args = mock_interaction.followup.send.call_args
    assert "All answers have been reset" in call_args[0][0]


@pytest.mark.asyncio
async def test_list_answers_permission_error(mock_interaction, tmp_path):
    """Test that non-admins cannot list answers."""
    storage_service.DATA_DIR = tmp_path
    
    # Remove admin permission
    import discord
    mock_interaction.user.guild_permissions = discord.Permissions(administrator=False)
    
    # The decorator will catch this before the command runs
    # We need to test the error handler
    from discord import app_commands
    
    error = app_commands.MissingPermissions(["administrator"])
    
    from src.commands.list_answers import list_answers_error
    await list_answers_error(mock_interaction, error)
    
    # Verify permission error message
    call_args = mock_interaction.response.send_message.call_args
    assert "don't have permission" in call_args[0][0]


@pytest.mark.asyncio
async def test_full_workflow(mock_interaction, tmp_path):
    """Test complete workflow: submit -> list -> reset -> list."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)
    
    # Submit answers
    answer_service.submit_answer(guild_id, "user1", "User1", "Answer 1")
    answer_service.submit_answer(guild_id, "user2", "User2", "Answer 2")
    
    # List answers
    await list_answers_command.callback(mock_interaction)
    message1 = mock_interaction.followup.send.call_args[0][0]
    assert "User1" in message1
    assert "User2" in message1
    
    # Reset mock
    mock_interaction.reset_mock()
    mock_interaction.response = AsyncMock()
    mock_interaction.followup = AsyncMock()
    
    # Reset session
    session = answer_service.get_session(guild_id)
    storage_service.save_session_to_disk(guild_id, session)
    await reset_answers_command.callback(mock_interaction)
    
    # Reset mock again
    mock_interaction.reset_mock()
    mock_interaction.response = AsyncMock()
    mock_interaction.followup = AsyncMock()
    
    # List answers again (should be empty)
    await list_answers_command.callback(mock_interaction)
    message2 = mock_interaction.followup.send.call_args[0][0]
    assert "No answers submitted yet" in message2
