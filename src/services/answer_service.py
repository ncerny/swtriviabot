"""Business logic for answer operations in the Discord Trivia Bot."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.models.answer import Answer
from src.models.session import TriviaSession
from src.services import storage_service
from src.utils.validators import validate_answer_text

logger = logging.getLogger(__name__)

# Session TTL: 7 days (safety net in case questions aren't posted regularly)
SESSION_TTL_DAYS = 7


def _cleanup_stale_sessions() -> None:
    """Remove sessions older than SESSION_TTL_DAYS with no activity.
    
    This is a safety net to prevent memory leaks if questions aren't posted regularly.
    Normally /post-question resets sessions daily.
    """
    # With Firestore, we might want to do this differently (e.g. scheduled function),
    # but for now we can scan on write or just rely on manual cleanup.
    # Scanning all sessions on every write is too expensive for Firestore.
    # We will skip automatic cleanup for now or implement it as a separate admin command.
    pass


def submit_answer(guild_id: str, user_id: str, username: str, text: str) -> tuple[Answer, bool]:
    """Submit or update an answer for a user in a guild.

    Args:
        guild_id: Discord server/guild ID
        user_id: Discord user ID
        username: Discord username for display
        text: Answer text content

    Returns:
        Tuple of (Answer object, is_update flag)
        is_update is True if replacing an existing answer, False if new

    Raises:
        ValueError: If answer text is invalid
    """
    # Validate answer text
    sanitized_text = validate_answer_text(text)

    # Get or create session for this guild
    session = storage_service.load_session_from_disk(guild_id)
    if not session:
        session = TriviaSession(guild_id=guild_id)

    # Create answer object
    answer = Answer(
        user_id=user_id,
        username=username,
        text=sanitized_text,
        timestamp=datetime.now(timezone.utc),
    )

    # Add or update answer in session
    is_update = session.add_or_update_answer(answer)

    # Persist to Firestore
    storage_service.save_session_to_disk(guild_id, session)

    return answer, is_update


def get_session(guild_id: str) -> Optional[TriviaSession]:
    """Get the active trivia session for a guild.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        TriviaSession if exists, None otherwise
    """
    return storage_service.load_session_from_disk(guild_id)


def reset_session(guild_id: str) -> None:
    """Clear all answers for a guild's trivia session.

    Args:
        guild_id: Discord server/guild ID
    """
    # We can either delete the document or clear the answers.
    # Clearing answers keeps the session object alive (preserves created_at potentially).
    # But usually reset means "start over".
    # Let's delete the file/doc to be consistent with previous behavior.
    storage_service.delete_session_file(guild_id)


def create_session(guild_id: str) -> TriviaSession:
    """Create a new trivia session for a guild.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        The newly created TriviaSession
    """
    session = TriviaSession(guild_id=guild_id)
    storage_service.save_session_to_disk(guild_id, session)
    return session


def get_all_sessions() -> dict[str, TriviaSession]:
    """Get all active sessions.

    Returns:
        Dictionary of all sessions keyed by guild_id
    """
    return storage_service.load_all_sessions()


def load_sessions(sessions: dict[str, TriviaSession]) -> None:
    """Load sessions into memory.
    
    Deprecated: No longer needed as we read from Firestore directly.
    Kept for compatibility if called by bot.py before update.
    """
    pass
