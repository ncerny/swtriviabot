"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
def mock_firestore():
    """Mock Firestore for all tests."""
    with patch('src.services.storage_service._get_db') as mock_db:
        # Create mock Firestore client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_document = MagicMock()
        
        # Setup chain: db.collection().document()
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_collection.stream.return_value = []
        
        # Mock document operations
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        mock_doc_snapshot.to_dict.return_value = {}
        mock_document.get.return_value = mock_doc_snapshot
        mock_document.set = MagicMock()
        mock_document.delete = MagicMock()
        
        mock_db.return_value = mock_client
        
        yield {
            'db': mock_client,
            'collection': mock_collection,
            'document': mock_document,
            'snapshot': mock_doc_snapshot,
        }


@pytest.fixture(autouse=True)
def reset_storage_service():
    """Reset storage service state between tests."""
    from src.services import storage_service
    
    # Reset the database connection
    storage_service._db = None
    
    yield
    
    # Clean up
    storage_service._db = None
