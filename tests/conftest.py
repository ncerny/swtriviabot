"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import discord
from discord import app_commands


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321098765432
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.Member)
    user.id = 123456789012345678
    user.display_name = "TestUser"
    user.name = "TestUser"
    user.discriminator = "1234"
    user.guild_permissions = discord.Permissions(administrator=True)
    return user


@pytest.fixture
def mock_channel(mock_guild):
    """Create a mock Discord text channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 111222333444555666
    channel.name = "trivia-channel"
    channel.guild = mock_guild
    
    # Mock permissions
    permissions = MagicMock(spec=discord.Permissions)
    permissions.send_messages = True
    permissions.embed_links = True
    channel.permissions_for = MagicMock(return_value=permissions)
    
    return channel


@pytest.fixture
def mock_interaction(mock_guild, mock_user, mock_channel):
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.guild_id = mock_guild.id
    interaction.guild = mock_guild
    interaction.user = mock_user
    interaction.channel = mock_channel
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.command = MagicMock()
    interaction.command.name = "test_command"
    interaction.extras = {}
    return interaction


@pytest.fixture
def sample_answer_data():
    """Create sample answer data for testing."""
    return {
        "user_id": "123456789012345678",
        "username": "TestUser",
        "text": "Test answer text",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_updated": False,
    }


@pytest.fixture
def sample_session_data():
    """Create sample session data for testing."""
    return {
        "guild_id": "987654321098765432",
        "answers": {
            "123456789012345678": {
                "user_id": "123456789012345678",
                "username": "TestUser",
                "text": "Test answer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_updated": False,
            }
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(autouse=True)
def reset_answer_service():
    """Reset answer service state between tests."""
    from src.services import answer_service
    
    # Store original state
    original_sessions = answer_service._sessions.copy()
    
    # Clear state for test
    answer_service._sessions.clear()
    
    yield
    
    # Restore original state
    answer_service._sessions = original_sessions


@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """Ensure test data files are cleaned up."""
    import os
    from src.services import storage_service
    
    # Temporarily override data directory for tests
    original_data_dir = storage_service.DATA_DIR
    storage_service.DATA_DIR = tmp_path
    
    yield
    
    # Restore original directory
    storage_service.DATA_DIR = original_data_dir
