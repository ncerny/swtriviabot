"""Unit tests for ArchivedSession model."""

import pytest
from datetime import datetime, timezone

from src.models.answer import Answer
from src.models.archived_session import ArchivedSession


class TestArchivedSessionInit:
    """Tests for ArchivedSession initialization."""

    def test_creates_with_required_fields(self):
        now = datetime.now(timezone.utc)
        answers = {
            "user1": Answer(
                user_id="user1",
                username="TestUser",
                text="Test answer",
                timestamp=now,
            )
        }
        session = ArchivedSession(
            guild_id="guild123",
            question_text="What is 2+2?",
            answers=answers,
            created_at=now,
            archived_at=now,
        )
        assert session.guild_id == "guild123"
        assert session.question_text == "What is 2+2?"
        assert len(session.answers) == 1
        assert session.created_at == now
        assert session.archived_at == now

    def test_rejects_empty_guild_id(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            ArchivedSession(
                guild_id="",
                question_text="Q",
                answers={},
                created_at=now,
                archived_at=now,
            )

    def test_allows_empty_question_text(self):
        """Sessions archived from before question_text was tracked."""
        now = datetime.now(timezone.utc)
        session = ArchivedSession(
            guild_id="guild123",
            question_text="",
            answers={},
            created_at=now,
            archived_at=now,
        )
        assert session.question_text == ""


class TestArchivedSessionSerialization:
    """Tests for to_dict / from_dict."""

    def _make_session(self):
        now = datetime.now(timezone.utc)
        answers = {
            "user1": Answer(
                user_id="user1",
                username="Alice",
                text="Paris",
                timestamp=now,
            ),
            "user2": Answer(
                user_id="user2",
                username="Bob",
                text="London",
                timestamp=now,
            ),
        }
        return ArchivedSession(
            guild_id="guild456",
            question_text="Capital of France?",
            answers=answers,
            created_at=now,
            archived_at=now,
        )

    def test_to_dict_returns_serializable_data(self):
        session = self._make_session()
        data = session.to_dict()
        assert data["guild_id"] == "guild456"
        assert data["question_text"] == "Capital of France?"
        assert "user1" in data["answers"]
        assert "user2" in data["answers"]
        assert isinstance(data["created_at"], str)
        assert isinstance(data["archived_at"], str)

    def test_roundtrip_serialization(self):
        original = self._make_session()
        data = original.to_dict()
        restored = ArchivedSession.from_dict(data)
        assert restored.guild_id == original.guild_id
        assert restored.question_text == original.question_text
        assert len(restored.answers) == len(original.answers)
        assert restored.answers["user1"].text == "Paris"
        assert restored.answers["user2"].text == "London"

    def test_from_dict_handles_empty_answers(self):
        now = datetime.now(timezone.utc)
        data = {
            "guild_id": "guild789",
            "question_text": "Q?",
            "answers": {},
            "created_at": now.isoformat(),
            "archived_at": now.isoformat(),
        }
        session = ArchivedSession.from_dict(data)
        assert session.guild_id == "guild789"
        assert len(session.answers) == 0


class TestArchivedSessionDocId:
    """Tests for document_id generation."""

    def test_document_id_format(self):
        now = datetime(2026, 2, 24, 15, 30, 0, tzinfo=timezone.utc)
        session = ArchivedSession(
            guild_id="guild123",
            question_text="Q",
            answers={},
            created_at=now,
            archived_at=now,
        )
        doc_id = session.document_id()
        assert doc_id.startswith("guild123_")
        assert "2026-02-24" in doc_id
