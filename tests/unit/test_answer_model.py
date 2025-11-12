"""Unit tests for the Answer data model."""

from datetime import datetime, timezone

import pytest

from src.models.answer import Answer


def test_answer_validation_requires_user_fields() -> None:
    """Answer raises descriptive errors for missing identifiers."""

    with pytest.raises(ValueError, match="user_id cannot be empty"):
        Answer(user_id="", username="User", text="answer", timestamp=datetime.now(timezone.utc))

    with pytest.raises(ValueError, match="username cannot be empty"):
        Answer(user_id="1", username="", text="answer", timestamp=datetime.now(timezone.utc))


def test_answer_validation_requires_text() -> None:
    """Empty or oversized answers are rejected."""

    with pytest.raises(ValueError, match="text cannot be empty"):
        Answer(user_id="1", username="User", text="", timestamp=datetime.now(timezone.utc))

    with pytest.raises(ValueError, match="maximum length"):
        Answer(
            user_id="1",
            username="User",
            text="x" * 4001,
            timestamp=datetime.now(timezone.utc),
        )


def test_answer_round_trip_serialization() -> None:
    """Round-trip through dict preserves fields."""

    answer = Answer(
        user_id="1",
        username="User",
        text="Paris",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        is_updated=True,
    )

    as_dict = answer.to_dict()
    restored = Answer.from_dict(as_dict)

    assert restored.user_id == "1"
    assert restored.username == "User"
    assert restored.text == "Paris"
    assert restored.timestamp == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert restored.is_updated is True
