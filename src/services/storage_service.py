"""Disk persistence operations for the Discord Trivia Bot."""

import json
import os
from pathlib import Path
from typing import Optional

from src.models.session import TriviaSession

# Data directory for persistent storage
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir() -> None:
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_session_file_path(guild_id: str) -> Path:
    """Get the file path for a guild's session data.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        Path to session JSON file
    """
    return DATA_DIR / f"{guild_id}.json"


def load_session_from_disk(guild_id: str) -> Optional[TriviaSession]:
    """Load a session from disk.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        TriviaSession if file exists and is valid, None otherwise
    """
    file_path = _get_session_file_path(guild_id)

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return TriviaSession.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Log error but don't crash - return None for corrupted files
        print(f"Error loading session from {file_path}: {e}")
        return None


def save_session_to_disk(guild_id: str, session: TriviaSession) -> None:
    """Save a session to disk.

    Args:
        guild_id: Discord server/guild ID
        session: TriviaSession to save
    """
    _ensure_data_dir()
    file_path = _get_session_file_path(guild_id)

    # Atomic write: write to temp file first, then rename
    temp_path = file_path.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.replace(file_path)
    except Exception as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def delete_session_file(guild_id: str) -> None:
    """Delete a session file from disk.

    Args:
        guild_id: Discord server/guild ID
    """
    file_path = _get_session_file_path(guild_id)

    if file_path.exists():
        file_path.unlink()


def load_all_sessions() -> dict[str, TriviaSession]:
    """Load all sessions from disk at startup.

    Returns:
        Dictionary of sessions keyed by guild_id
    """
    _ensure_data_dir()
    sessions = {}

    for file_path in DATA_DIR.glob("*.json"):
        # Extract guild_id from filename
        guild_id = file_path.stem

        session = load_session_from_disk(guild_id)
        if session:
            sessions[guild_id] = session

    return sessions
