"""Unit tests for example_answers.json loading functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# We'll test the logic directly without complex path mocking


@pytest.fixture
def example_data():
    """Sample example_answers.json data."""
    return {
        "answers": {
            "user1": {
                "is_updated": False,
                "text": "Example answer 1",
                "timestamp": "2025-11-30T18:40:01.803315+00:00",
                "user_id": "user1",
                "username": "TestUser1"
            },
            "user2": {
                "is_updated": False,
                "text": "Example answer 2",
                "timestamp": "2025-11-30T22:27:37.410350+00:00",
                "user_id": "user2",
                "username": "TestUser2"
            }
        },
        "created_at": "2025-11-30T18:14:58.380457+00:00",
        "guild_id": "1305944927099686952",
        "last_activity": "2025-12-01T01:45:22.305596+00:00"
    }


def test_load_example_answers_logic(example_data):
    """Test the core logic of loading example answers with test guild override."""
    # Test the actual parsing logic by mocking file operations
    json_str = json.dumps(example_data)
    test_guild_id = "999888777666"  # Different from the one in example_data

    with patch('src.bot.DEV_MODE', True):
        with patch('src.bot.DISCORD_TEST_GUILD_ID', test_guild_id):
            # Mock Path.exists to return True
            with patch('pathlib.Path.exists', return_value=True):
                # Mock open to return our JSON data
                with patch('builtins.open', mock_open(read_data=json_str)):
                    # Mock storage_service.save_session
                    with patch('src.bot.storage_service') as mock_storage:
                        from src.bot import load_example_answers
                        load_example_answers()

                        # Verify save_session was called with correct arguments
                        assert mock_storage.save_session.called
                        call_args = mock_storage.save_session.call_args[0]
                        guild_id = call_args[0]
                        saved_session = call_args[1]

                        # Verify guild_id was overridden with DISCORD_TEST_GUILD_ID
                        assert guild_id == test_guild_id
                        assert saved_session.guild_id == test_guild_id
                        # Verify answers were loaded correctly
                        assert len(saved_session.answers) == 2
                        assert "user1" in saved_session.answers
                        assert "user2" in saved_session.answers
                        assert saved_session.answers["user1"].text == "Example answer 1"
                        assert saved_session.answers["user2"].username == "TestUser2"


def test_load_example_answers_not_in_dev_mode():
    """Test that example answers are NOT loaded when DEV_MODE is false."""
    # Mock DEV_MODE to False
    with patch('src.bot.DEV_MODE', False):
        with patch('src.bot.DISCORD_TEST_GUILD_ID', "123456"):
            # Mock storage_service.save_session
            with patch('src.bot.storage_service') as mock_storage:
                from src.bot import load_example_answers
                load_example_answers()

                # Verify save_session was NOT called
                assert not mock_storage.save_session.called


def test_load_example_answers_no_test_guild_id():
    """Test that example answers are NOT loaded when DISCORD_TEST_GUILD_ID is not set."""
    # Mock DEV_MODE to True but DISCORD_TEST_GUILD_ID to None
    with patch('src.bot.DEV_MODE', True):
        with patch('src.bot.DISCORD_TEST_GUILD_ID', None):
            with patch('src.bot.storage_service') as mock_storage:
                from src.bot import load_example_answers
                load_example_answers()

                # Verify save_session was NOT called
                assert not mock_storage.save_session.called


def test_load_example_answers_file_not_exists():
    """Test that function handles missing example_answers.json gracefully."""
    with patch('src.bot.DEV_MODE', True):
        with patch('src.bot.DISCORD_TEST_GUILD_ID', "123456"):
            # Mock Path.exists to return False
            with patch('pathlib.Path.exists', return_value=False):
                with patch('src.bot.storage_service') as mock_storage:
                    from src.bot import load_example_answers
                    # Should not raise an error
                    load_example_answers()

                    # Verify save_session was NOT called
                    assert not mock_storage.save_session.called


def test_load_example_answers_handles_json_error():
    """Test that function handles invalid JSON gracefully."""
    with patch('src.bot.DEV_MODE', True):
        with patch('src.bot.DISCORD_TEST_GUILD_ID', "123456"):
            # Mock Path.exists to return True
            with patch('pathlib.Path.exists', return_value=True):
                # Mock open to return invalid JSON
                with patch('builtins.open', mock_open(read_data="{invalid json")):
                    with patch('src.bot.storage_service') as mock_storage:
                        from src.bot import load_example_answers
                        # Should not raise an error (logs it instead)
                        load_example_answers()

                        # Verify save_session was NOT called
                        assert not mock_storage.save_session.called
