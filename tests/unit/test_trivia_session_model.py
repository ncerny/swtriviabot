"""Unit tests for the TriviaSession model."""

from datetime import datetime, timedelta, timezone

import pytest

from src.models.answer import Answer
from src.models.session import TriviaSession


def test_trivia_session_requires_guild_id() -> None:
    """Sessions without guild identifiers are rejected."""

    with pytest.raises(ValueError, match="guild_id cannot be empty"):
        TriviaSession(guild_id="")


def test_trivia_session_validates_last_activity_chronology() -> None:
    """last_activity earlier than created_at raises an error."""

    created_at = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="last_activity cannot be before created_at"):
        TriviaSession(
            guild_id="guild",
            created_at=created_at,
            last_activity=created_at - timedelta(seconds=1),
        )


def test_trivia_session_from_dict_filters_invalid_answers() -> None:
    """from_dict skips malformed answer payloads."""

    payload = {
        "guild_id": "guild",
        "answers": {
            "valid": {
                "user_id": "u1",
                "username": "User",
                "text": "Answer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_updated": False,
            },
            "invalid": "not-a-dict",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
    }

    session = TriviaSession.from_dict(payload)

    assert "valid" in session.answers
    assert "invalid" not in session.answers


def test_trivia_session_add_or_update_flips_flag() -> None:
    """Updating an existing answer marks it as updated."""

    session = TriviaSession(guild_id="guild")
    answer = Answer(
        user_id="1",
        username="User",
        text="First",
        timestamp=datetime.now(timezone.utc),
    )

    is_update_first = session.add_or_update_answer(answer)
    assert is_update_first is False
    assert answer.is_updated is False

    second = Answer(
        user_id="1",
        username="User",
        text="Second",
        timestamp=datetime.now(timezone.utc),
    )

    is_update_second = session.add_or_update_answer(second)
    assert is_update_second is True
    assert second.is_updated is True
