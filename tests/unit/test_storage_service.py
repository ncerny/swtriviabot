"""Unit tests for storage_service module with Firestore."""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

from src.services import storage_service
from src.models.session import TriviaSession
from src.models.answer import Answer


def test_save_session_to_firestore(mock_firestore):
    """Test saving a session to Firestore."""
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    session.add_or_update_answer(Answer(
        user_id="user_123",
        username="TestUser",
        text="Test answer",
        timestamp=datetime.now(timezone.utc),
    ))
    
    storage_service.save_session_to_disk(guild_id, session)
    
    # Verify Firestore was called correctly
    mock_firestore['collection'].document.assert_called_with(str(guild_id))
    mock_firestore['document'].set.assert_called_once()


def test_load_session_from_firestore(mock_firestore):
    """Test loading a session from Firestore."""
    guild_id = "test_guild_123"
    
    # Setup mock to return session data
    mock_firestore['snapshot'].exists = True
    mock_firestore['snapshot'].to_dict.return_value = {
        "guild_id": guild_id,
        "answers": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    
    session = storage_service.load_session_from_disk(guild_id)
    
    assert session is not None
    assert session.guild_id == guild_id
    mock_firestore['collection'].document.assert_called_with(str(guild_id))


def test_load_nonexistent_session(mock_firestore):
    """Test loading a session that doesn't exist."""
    mock_firestore['snapshot'].exists = False
    
    session = storage_service.load_session_from_disk("nonexistent_guild")
    assert session is None


def test_delete_session_from_firestore(mock_firestore):
    """Test deleting a session from Firestore."""
    guild_id = "test_guild_123"
    
    storage_service.delete_session_file(guild_id)
    
    mock_firestore['collection'].document.assert_called_with(str(guild_id))
    mock_firestore['document'].delete.assert_called_once()


def test_load_all_sessions_from_firestore(mock_firestore):
    """Test loading all sessions from Firestore."""
    # Setup mock documents
    mock_doc1 = MagicMock()
    mock_doc1.id = "guild_1"
    mock_doc1.to_dict.return_value = {
        "guild_id": "guild_1",
        "answers": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    
    mock_doc2 = MagicMock()
    mock_doc2.id = "guild_2"
    mock_doc2.to_dict.return_value = {
        "guild_id": "guild_2",
        "answers": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    
    mock_firestore['collection'].stream.return_value = [mock_doc1, mock_doc2]
    
    all_sessions = storage_service.load_all_sessions()
    
    assert len(all_sessions) == 2
    assert "guild_1" in all_sessions
    assert "guild_2" in all_sessions


def test_load_all_sessions_empty(mock_firestore):
    """Test loading sessions when none exist."""
    mock_firestore['collection'].stream.return_value = []
    
    all_sessions = storage_service.load_all_sessions()
    assert len(all_sessions) == 0


@patch('src.services.storage_service.DATA_DIR')
@patch('src.services.storage_service._get_db')
def test_migrate_local_data_migrates_json_files(mock_get_db, mock_data_dir, tmp_path):
    """Test that migrate_local_data migrates JSON files to Firestore."""
    # Setup mock Firestore
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Create test JSON file
    test_file = tmp_path / "test_guild.json"
    test_data = {
        "guild_id": "test_guild",
        "answers": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    
    import json
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    # Setup DATA_DIR to point to tmp_path
    mock_data_dir.exists.return_value = True
    mock_data_dir.glob.return_value = [test_file]
    
    # Run migration
    with patch('src.services.storage_service.save_session_to_disk') as mock_save:
        storage_service.migrate_local_data()
        
        # Verify save was called
        assert mock_save.called


@patch('src.services.storage_service.DATA_DIR')
def test_migrate_local_data_handles_no_directory(mock_data_dir):
    """Test that migrate_local_data handles missing data directory."""
    mock_data_dir.exists.return_value = False
    
    # Should not raise an error
    storage_service.migrate_local_data()


@patch('src.services.storage_service._get_db')
def test_save_session_handles_none_db(mock_get_db):
    """Test that save_session handles None database gracefully."""
    mock_get_db.return_value = None
    
    guild_id = "test_guild"
    session = TriviaSession(guild_id=guild_id)
    
    # Should not raise an error
    storage_service.save_session_to_disk(guild_id, session)


@patch('src.services.storage_service._get_db')
def test_load_session_handles_none_db(mock_get_db):
    """Test that load_session handles None database gracefully."""
    mock_get_db.return_value = None
    
    session = storage_service.load_session_from_disk("test_guild")
    assert session is None


@patch('src.services.storage_service._get_db')
def test_delete_session_handles_none_db(mock_get_db):
    """Test that delete_session handles None database gracefully."""
    mock_get_db.return_value = None
    
    # Should not raise an error
    storage_service.delete_session_file("test_guild")


@patch('src.services.storage_service._get_db')
def test_load_all_sessions_handles_none_db(mock_get_db):
    """Test that load_all_sessions handles None database gracefully."""
    mock_get_db.return_value = None
    
    sessions = storage_service.load_all_sessions()
    assert sessions == {}


def test_collection_suffix_in_dev_mode():
    """Test that DEV_MODE=true adds -test suffix."""
    with patch.dict('os.environ', {'DEV_MODE': 'true'}):
        # Reimport to pick up env var
        import importlib
        importlib.reload(storage_service)
        
        assert storage_service.DEV_MODE == True
        assert storage_service.COLLECTION_SUFFIX == "-test"


def test_collection_suffix_in_prod_mode():
    """Test that DEV_MODE=false has no suffix."""
    with patch.dict('os.environ', {'DEV_MODE': 'false'}):
        import importlib
        importlib.reload(storage_service)
        
        assert storage_service.DEV_MODE == False
        assert storage_service.COLLECTION_SUFFIX == ""


def test_save_session_handles_firestore_error(mock_firestore):
    """Test that save_session handles Firestore errors gracefully."""
    guild_id = "test_guild_123"
    session = TriviaSession(guild_id=guild_id)
    
    # Make Firestore raise an error
    mock_firestore['document'].set.side_effect = Exception("Firestore error")
    
    with pytest.raises(Exception):
        storage_service.save_session_to_disk(guild_id, session)


def test_load_session_handles_firestore_error(mock_firestore):
    """Test that load_session handles Firestore errors gracefully."""
    mock_firestore['document'].get.side_effect = Exception("Firestore error")
    
    session = storage_service.load_session_from_disk("test_guild")
    assert session is None


def test_load_all_sessions_handles_parse_error(mock_firestore):
    """Test that load_all_sessions handles parsing errors gracefully."""
    # Setup mock document with invalid data
    mock_doc = MagicMock()
    mock_doc.id = "guild_1"
    mock_doc.to_dict.return_value = {"invalid": "data"}  # Missing required fields
    
    mock_firestore['collection'].stream.return_value = [mock_doc]
    
    # Should return empty dict, not crash
    all_sessions = storage_service.load_all_sessions()
    assert len(all_sessions) == 0


@patch('src.services.storage_service.DATA_DIR')
@patch('src.services.storage_service._get_db')
def test_migrate_local_data_handles_migration_error(mock_get_db, mock_data_dir, tmp_path):
    """Test that migrate_local_data handles errors during migration."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Create test JSON file with invalid data
    test_file = tmp_path / "test_guild.json"
    with open(test_file, 'w') as f:
        f.write("invalid json{")
    
    mock_data_dir.exists.return_value = True
    mock_data_dir.glob.return_value = [test_file]
    
    # Should not raise an error, just log it
    storage_service.migrate_local_data()


@patch('src.services.storage_service.DATA_DIR')
@patch('src.services.storage_service._get_db')
def test_migrate_local_data_renames_migrated_files(mock_get_db, mock_data_dir, tmp_path):
    """Test that migrate_local_data renames successfully migrated files."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Create test JSON file
    test_file = tmp_path / "test_guild.json"
    test_data = {
        "guild_id": "test_guild",
        "answers": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }
    
    import json
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    mock_data_dir.exists.return_value = True
    mock_data_dir.glob.return_value = [test_file]
    
    with patch('src.services.storage_service.save_session_to_disk'):
        storage_service.migrate_local_data()
        
        # Original file should be renamed
        assert not test_file.exists()
        assert (tmp_path / "test_guild.json.migrated").exists()
