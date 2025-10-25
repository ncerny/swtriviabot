"""Business logic for answer operations in the Discord Trivia Bot."""

from datetime import datetime, timezone
from typing import Optional

from src.models.answer import Answer
from src.models.session import TriviaSession
from src.utils.validators import validate_answer_text

# Global in-memory session storage (keyed by guild_id)
_sessions: dict[str, TriviaSession] = {}


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
    if guild_id not in _sessions:
        _sessions[guild_id] = TriviaSession(guild_id=guild_id)

    session = _sessions[guild_id]

    # Create answer object
    answer = Answer(
        user_id=user_id,
        username=username,
        text=sanitized_text,
        timestamp=datetime.now(timezone.utc),
    )

    # Add or update answer in session
    is_update = session.add_or_update_answer(answer)

    return answer, is_update


def get_session(guild_id: str) -> Optional[TriviaSession]:
    """Get the active trivia session for a guild.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        TriviaSession if exists, None otherwise
    """
    return _sessions.get(guild_id)


def reset_session(guild_id: str) -> None:
    """Clear all answers for a guild's trivia session.

    Args:
        guild_id: Discord server/guild ID
    """
    if guild_id in _sessions:
        del _sessions[guild_id]


def create_session(guild_id: str) -> TriviaSession:
    """Create a new trivia session for a guild.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        The newly created TriviaSession
    """
    _sessions[guild_id] = TriviaSession(guild_id=guild_id)
    return _sessions[guild_id]


def get_all_sessions() -> dict[str, TriviaSession]:
    """Get all active sessions (for startup loading).

    Returns:
        Dictionary of all sessions keyed by guild_id
    """
    return _sessions


def load_sessions(sessions: dict[str, TriviaSession]) -> None:
    """Load sessions into memory (for startup from disk).

    Args:
        sessions: Dictionary of sessions to load
    """
    global _sessions
    _sessions = sessions
