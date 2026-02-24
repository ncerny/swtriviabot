# Session Archive & Admin DM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Archive trivia answers before session reset, DM the admin, and retain a rolling 3-session window in Firestore.

**Architecture:** New `ArchivedSession` model stored in a separate `session_archives{SUFFIX}` Firestore collection. Archive + DM happens inside `PostQuestionModal.on_submit()` before the existing reset logic. Prune enforces the 3-session cap per guild.

**Tech Stack:** Python 3.13, discord.py, Firebase Firestore, pytest, dataclasses

---

### Task 1: ArchivedSession Model

**Files:**
- Create: `src/models/archived_session.py`
- Modify: `src/models/__init__.py:1-6`
- Test: `tests/unit/test_archived_session_model.py`

**Step 1: Write the failing test**

Create `tests/unit/test_archived_session_model.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_archived_session_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.models.archived_session'`

**Step 3: Write minimal implementation**

Create `src/models/archived_session.py`:

```python
"""Archived trivia session model for the Discord Trivia Bot."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.models.answer import Answer


@dataclass
class ArchivedSession:
    """A snapshot of a trivia session preserved before reset.

    Attributes:
        guild_id: Discord server/guild ID
        question_text: The trivia question that was asked
        answers: Map of user_id to Answer objects (copied from TriviaSession)
        created_at: When the original session started
        archived_at: When the session was archived (reset time)
    """

    guild_id: str
    question_text: str
    answers: dict[str, Answer]
    created_at: datetime
    archived_at: datetime

    def __post_init__(self) -> None:
        """Validate archived session attributes after initialization."""
        if not self.guild_id:
            raise ValueError("guild_id cannot be empty")

    def document_id(self) -> str:
        """Generate a Firestore document ID for this archived session.

        Returns:
            String in format '{guild_id}_{ISO timestamp}'
        """
        return f"{self.guild_id}_{self.archived_at.isoformat()}"

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore serialization.

        Returns:
            Dictionary representation of the archived session
        """
        return {
            "guild_id": self.guild_id,
            "question_text": self.question_text,
            "answers": {
                user_id: answer.to_dict()
                for user_id, answer in self.answers.items()
            },
            "created_at": self.created_at.isoformat(),
            "archived_at": self.archived_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchivedSession":
        """Create ArchivedSession from dictionary (Firestore deserialization).

        Args:
            data: Dictionary containing archived session data

        Returns:
            ArchivedSession instance
        """
        answers_data = data.get("answers", {})
        if not isinstance(answers_data, dict):
            answers_data = {}

        answers = {
            user_id: Answer.from_dict(answer_data)
            for user_id, answer_data in answers_data.items()
            if isinstance(answer_data, dict)
        }

        return cls(
            guild_id=str(data["guild_id"]),
            question_text=str(data.get("question_text", "")),
            answers=answers,
            created_at=datetime.fromisoformat(str(data["created_at"])),
            archived_at=datetime.fromisoformat(str(data["archived_at"])),
        )
```

Update `src/models/__init__.py`:

```python
"""Data models for the Discord Trivia Bot."""

from src.models.answer import Answer
from src.models.archived_session import ArchivedSession
from src.models.session import TriviaSession

__all__ = ["Answer", "ArchivedSession", "TriviaSession"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_archived_session_model.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add src/models/archived_session.py src/models/__init__.py tests/unit/test_archived_session_model.py
git commit -m "feat: add ArchivedSession model with serialization"
```

---

### Task 2: Add question_text to TriviaSession

**Files:**
- Modify: `src/models/session.py:19-44` (constructor), `src/models/session.py:85-96` (to_dict), `src/models/session.py:98-123` (from_dict)
- Test: `tests/unit/test_trivia_session_model.py`

**Step 1: Write the failing test**

Append to `tests/unit/test_trivia_session_model.py`:

```python
class TestTriviaSessionQuestionText:
    """Tests for question_text field on TriviaSession."""

    def test_defaults_to_none(self):
        session = TriviaSession(guild_id="guild123")
        assert session.question_text is None

    def test_accepts_question_text(self):
        session = TriviaSession(guild_id="guild123", question_text="What is 2+2?")
        assert session.question_text == "What is 2+2?"

    def test_to_dict_includes_question_text(self):
        session = TriviaSession(guild_id="guild123", question_text="Q?")
        data = session.to_dict()
        assert data["question_text"] == "Q?"

    def test_to_dict_includes_none_question_text(self):
        session = TriviaSession(guild_id="guild123")
        data = session.to_dict()
        assert data["question_text"] is None

    def test_from_dict_restores_question_text(self):
        session = TriviaSession(guild_id="guild123", question_text="Q?")
        data = session.to_dict()
        restored = TriviaSession.from_dict(data)
        assert restored.question_text == "Q?"

    def test_from_dict_handles_missing_question_text(self):
        """Backward compatibility: old sessions without question_text."""
        from datetime import datetime, timezone

        data = {
            "guild_id": "guild123",
            "answers": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }
        session = TriviaSession.from_dict(data)
        assert session.question_text is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_trivia_session_model.py::TestTriviaSessionQuestionText -v`
Expected: FAIL — `TypeError: TriviaSession.__init__() got an unexpected keyword argument 'question_text'`

**Step 3: Write minimal implementation**

Modify `src/models/session.py`:

In `__init__` — add `question_text` parameter:
```python
def __init__(
    self,
    guild_id: str,
    answers: Optional[dict[str, Answer]] = None,
    created_at: Optional[datetime] = None,
    last_activity: Optional[datetime] = None,
    question_text: Optional[str] = None,
) -> None:
```

In `__init__` body — add assignment after `self.last_activity`:
```python
self.question_text = question_text
```

In `to_dict` — add `question_text` to returned dict:
```python
return {
    "guild_id": self.guild_id,
    "answers": {user_id: answer.to_dict() for user_id, answer in self.answers.items()},
    "created_at": self.created_at.isoformat(),
    "last_activity": self.last_activity.isoformat(),
    "question_text": self.question_text,
}
```

In `from_dict` — add `question_text` to constructor call:
```python
return cls(
    guild_id=str(data["guild_id"]),
    answers=answers,
    created_at=datetime.fromisoformat(str(data["created_at"])),
    last_activity=datetime.fromisoformat(str(data["last_activity"])),
    question_text=data.get("question_text"),
)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_trivia_session_model.py -v`
Expected: All tests PASS (including existing ones — backward compatible since `question_text` defaults to None)

**Step 5: Commit**

```bash
git add src/models/session.py tests/unit/test_trivia_session_model.py
git commit -m "feat: add optional question_text field to TriviaSession"
```

---

### Task 3: Storage Service Archive Functions

**Files:**
- Modify: `src/services/storage_service.py:1-14` (imports), append new functions after line 185
- Test: `tests/unit/test_storage_service.py`

**Step 1: Write the failing tests**

Append to `tests/unit/test_storage_service.py`:

```python
from src.models.archived_session import ArchivedSession


class TestSaveArchivedSession:
    """Tests for save_archived_session."""

    def test_saves_to_correct_collection(self, mock_firestore):
        now = datetime.now(timezone.utc)
        archived = ArchivedSession(
            guild_id="guild123",
            question_text="Q?",
            answers={},
            created_at=now,
            archived_at=now,
        )

        storage_service.save_archived_session(archived)

        mock_firestore['db'].collection.assert_called_with(
            f"session_archives{storage_service.COLLECTION_SUFFIX}"
        )
        mock_firestore['collection'].document.assert_called_with(archived.document_id())
        mock_firestore['document'].set.assert_called_once()

    @patch('src.services.storage_service._get_db')
    def test_handles_none_db(self, mock_get_db):
        mock_get_db.return_value = None
        now = datetime.now(timezone.utc)
        archived = ArchivedSession(
            guild_id="guild123",
            question_text="Q?",
            answers={},
            created_at=now,
            archived_at=now,
        )
        # Should not raise
        storage_service.save_archived_session(archived)


class TestLoadArchivedSessions:
    """Tests for load_archived_sessions."""

    def test_returns_empty_list_when_no_archives(self, mock_firestore):
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []
        mock_firestore['db'].collection.return_value = mock_query

        result = storage_service.load_archived_sessions("guild123")
        assert result == []

    def test_returns_archived_sessions(self, mock_firestore):
        now = datetime.now(timezone.utc)
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "guild_id": "guild123",
            "question_text": "Q?",
            "answers": {},
            "created_at": now.isoformat(),
            "archived_at": now.isoformat(),
        }

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_firestore['db'].collection.return_value = mock_query

        result = storage_service.load_archived_sessions("guild123", limit=3)
        assert len(result) == 1
        assert result[0].guild_id == "guild123"

    @patch('src.services.storage_service._get_db')
    def test_handles_none_db(self, mock_get_db):
        mock_get_db.return_value = None
        result = storage_service.load_archived_sessions("guild123")
        assert result == []


class TestPruneArchivedSessions:
    """Tests for prune_archived_sessions."""

    def test_deletes_excess_archives(self, mock_firestore):
        now = datetime.now(timezone.utc)

        # Create 4 mock docs (keep=3 means 1 should be deleted)
        mock_docs = []
        for i in range(4):
            doc = MagicMock()
            doc.id = f"guild123_{i}"
            doc.reference = MagicMock()
            mock_docs.append(doc)

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.stream.return_value = mock_docs
        mock_firestore['db'].collection.return_value = mock_query

        storage_service.prune_archived_sessions("guild123", keep=3)

        # The 4th doc (index 3) should be deleted
        mock_docs[3].reference.delete.assert_called_once()
        # The first 3 should NOT be deleted
        mock_docs[0].reference.delete.assert_not_called()
        mock_docs[1].reference.delete.assert_not_called()
        mock_docs[2].reference.delete.assert_not_called()

    def test_no_deletion_when_under_limit(self, mock_firestore):
        mock_docs = []
        for i in range(2):
            doc = MagicMock()
            doc.id = f"guild123_{i}"
            doc.reference = MagicMock()
            mock_docs.append(doc)

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.stream.return_value = mock_docs
        mock_firestore['db'].collection.return_value = mock_query

        storage_service.prune_archived_sessions("guild123", keep=3)

        for doc in mock_docs:
            doc.reference.delete.assert_not_called()

    @patch('src.services.storage_service._get_db')
    def test_handles_none_db(self, mock_get_db):
        mock_get_db.return_value = None
        # Should not raise
        storage_service.prune_archived_sessions("guild123", keep=3)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_storage_service.py::TestSaveArchivedSession -v`
Expected: FAIL — `AttributeError: module 'src.services.storage_service' has no attribute 'save_archived_session'`

**Step 3: Write minimal implementation**

Add import at top of `src/services/storage_service.py` (after line 12):
```python
from src.models.archived_session import ArchivedSession
```

Append to `src/services/storage_service.py` after `migrate_local_data`:

```python
def save_archived_session(archived_session: ArchivedSession) -> None:
    """Save an archived session to Firestore.

    Args:
        archived_session: ArchivedSession to persist
    """
    db = _get_db()
    if not db:
        return

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        doc_id = archived_session.document_id()
        db.collection(collection).document(doc_id).set(archived_session.to_dict())
    except Exception as e:
        logger.error(f"Error saving archived session for guild {archived_session.guild_id}: {e}")
        raise


def load_archived_sessions(guild_id: str, limit: int = 3) -> list[ArchivedSession]:
    """Load recent archived sessions for a guild from Firestore.

    Args:
        guild_id: Discord server/guild ID
        limit: Maximum number of archived sessions to return (default: 3)

    Returns:
        List of ArchivedSession objects, newest first
    """
    db = _get_db()
    if not db:
        return []

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        query = (
            db.collection(collection)
            .where("guild_id", "==", guild_id)
            .order_by("archived_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            try:
                results.append(ArchivedSession.from_dict(doc.to_dict()))
            except Exception as e:
                logger.error(f"Error parsing archived session {doc.id}: {e}")
        return results
    except Exception as e:
        logger.error(f"Error loading archived sessions for guild {guild_id}: {e}")
        return []


def prune_archived_sessions(guild_id: str, keep: int = 3) -> None:
    """Delete archived sessions beyond the retention limit for a guild.

    Args:
        guild_id: Discord server/guild ID
        keep: Number of most recent archives to retain (default: 3)
    """
    db = _get_db()
    if not db:
        return

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        query = (
            db.collection(collection)
            .where("guild_id", "==", guild_id)
            .order_by("archived_at", direction=firestore.Query.DESCENDING)
        )
        docs = list(query.stream())
        for doc in docs[keep:]:
            doc.reference.delete()
    except Exception as e:
        logger.error(f"Error pruning archived sessions for guild {guild_id}: {e}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_storage_service.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add src/services/storage_service.py tests/unit/test_storage_service.py
git commit -m "feat: add archive storage functions (save, load, prune)"
```

---

### Task 4: Answer Service archive_session Method

**Files:**
- Modify: `src/services/answer_service.py:1-9` (imports), append new function
- Test: `tests/unit/test_answer_service.py`

**Step 1: Write the failing tests**

Append to `tests/unit/test_answer_service.py`:

```python
from src.models.archived_session import ArchivedSession


class TestArchiveSession:
    """Tests for archive_session."""

    @patch('src.services.answer_service.storage_service')
    def test_archives_session_with_answers(self, mock_storage):
        now = datetime.now(timezone.utc)
        session = TriviaSession(
            guild_id="guild123",
            question_text="What is 2+2?",
            created_at=now,
            last_activity=now,
        )
        session.add_or_update_answer(Answer(
            user_id="user1", username="Alice", text="4", timestamp=now
        ))
        mock_storage.load_session.return_value = session

        result = answer_service.archive_session("guild123")

        assert result is not None
        assert result.guild_id == "guild123"
        assert result.question_text == "What is 2+2?"
        assert len(result.answers) == 1
        assert result.answers["user1"].text == "4"
        mock_storage.save_archived_session.assert_called_once()
        mock_storage.prune_archived_sessions.assert_called_once_with("guild123", keep=3)

    @patch('src.services.answer_service.storage_service')
    def test_returns_none_when_no_session(self, mock_storage):
        mock_storage.load_session.return_value = None

        result = answer_service.archive_session("guild123")

        assert result is None
        mock_storage.save_archived_session.assert_not_called()

    @patch('src.services.answer_service.storage_service')
    def test_returns_none_when_no_answers(self, mock_storage):
        session = TriviaSession(guild_id="guild123")
        mock_storage.load_session.return_value = session

        result = answer_service.archive_session("guild123")

        assert result is None
        mock_storage.save_archived_session.assert_not_called()

    @patch('src.services.answer_service.storage_service')
    def test_handles_missing_question_text(self, mock_storage):
        """Old sessions without question_text should archive with empty string."""
        now = datetime.now(timezone.utc)
        session = TriviaSession(guild_id="guild123", created_at=now, last_activity=now)
        session.add_or_update_answer(Answer(
            user_id="user1", username="Alice", text="answer", timestamp=now
        ))
        mock_storage.load_session.return_value = session

        result = answer_service.archive_session("guild123")

        assert result is not None
        assert result.question_text == ""
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_answer_service.py::TestArchiveSession -v`
Expected: FAIL — `AttributeError: module 'src.services.answer_service' has no attribute 'archive_session'`

**Step 3: Write minimal implementation**

Add import at top of `src/services/answer_service.py` (after line 8):
```python
from src.models.archived_session import ArchivedSession
```

Append to `src/services/answer_service.py`:

```python
def archive_session(guild_id: str) -> Optional[ArchivedSession]:
    """Archive the current session before reset.

    Saves a snapshot of the session to the archive collection,
    then prunes old archives beyond the retention limit.

    Args:
        guild_id: Discord server/guild ID

    Returns:
        ArchivedSession if archived, None if nothing to archive
    """
    session = storage_service.load_session(guild_id)
    if not session or not session.answers:
        return None

    archived = ArchivedSession(
        guild_id=guild_id,
        question_text=session.question_text or "",
        answers=dict(session.answers),
        created_at=session.created_at,
        archived_at=datetime.now(timezone.utc),
    )

    storage_service.save_archived_session(archived)
    storage_service.prune_archived_sessions(guild_id, keep=3)

    return archived
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_answer_service.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add src/services/answer_service.py tests/unit/test_answer_service.py
git commit -m "feat: add archive_session to answer service"
```

---

### Task 5: Post-Question Archive + Admin DM

**Files:**
- Modify: `src/commands/post_question.py:413-533` (on_submit method)
- Test: `tests/integration/test_post_question.py`

**Step 1: Write the failing tests**

Append to `tests/integration/test_post_question.py` (read the existing file first to match its fixture style):

```python
class TestPostQuestionArchiveAndDM:
    """Tests for archive + DM behavior during post-question."""

    @pytest.fixture
    def modal(self, mock_channel):
        modal = PostQuestionModal(guild_id=987654321098765432, channel=mock_channel)
        modal.yesterday_answer = MagicMock()
        modal.yesterday_answer.value = ""
        modal.yesterday_winners = MagicMock()
        modal.yesterday_winners.value = ""
        modal.todays_question = MagicMock()
        modal.todays_question.value = "New question?"
        return modal

    @patch('src.commands.post_question.answer_service')
    @patch('src.commands.post_question.storage_service')
    async def test_archives_session_before_reset(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(Answer(
            user_id="u1", username="Alice", text="answer", timestamp=now
        ))
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(
            guild_id="987654321098765432"
        )

        await modal.on_submit(mock_interaction)

        mock_answer_svc.archive_session.assert_called_once_with("987654321098765432")

    @patch('src.commands.post_question.answer_service')
    @patch('src.commands.post_question.storage_service')
    async def test_dms_admin_on_archive(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(Answer(
            user_id="u1", username="Alice", text="answer", timestamp=now
        ))
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(
            guild_id="987654321098765432"
        )

        mock_interaction.user.send = AsyncMock()

        await modal.on_submit(mock_interaction)

        mock_interaction.user.send.assert_called()
        dm_content = mock_interaction.user.send.call_args[0][0]
        assert "Alice" in dm_content
        assert "answer" in dm_content

    @patch('src.commands.post_question.answer_service')
    @patch('src.commands.post_question.storage_service')
    async def test_dm_failure_does_not_block_reset(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(Answer(
            user_id="u1", username="Alice", text="answer", timestamp=now
        ))
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(
            guild_id="987654321098765432"
        )

        # DM fails
        mock_interaction.user.send = AsyncMock(side_effect=discord.Forbidden(
            MagicMock(), "Cannot send messages to this user"
        ))

        await modal.on_submit(mock_interaction)

        # Reset still happened
        mock_answer_svc.reset_session.assert_called_once()

    @patch('src.commands.post_question.answer_service')
    @patch('src.commands.post_question.storage_service')
    async def test_new_session_gets_question_text(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        mock_answer_svc.get_session.return_value = None
        mock_answer_svc.create_session.return_value = TriviaSession(
            guild_id="987654321098765432"
        )

        await modal.on_submit(mock_interaction)

        # create_session should be called with question_text
        mock_answer_svc.create_session.assert_called_once_with(
            "987654321098765432", question_text="New question?"
        )
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_post_question.py::TestPostQuestionArchiveAndDM -v`
Expected: FAIL — tests reference `archive_session` call that doesn't exist in `on_submit` yet

**Step 3: Write minimal implementation**

Modify `src/commands/post_question.py` `on_submit` method (lines 460-533). The key changes:

After loading previous session (line 461), add archive call:
```python
# Archive previous session before reset
if previous_session and previous_session.answers:
    archived = answer_service.archive_session(self.guild_id)
```

After the existing ephemeral message block (after line 528), add the DM:
```python
# DM the admin with archived answers
if previous_session and previous_session.answers:
    try:
        dm_lines = []
        guild_name = interaction.guild.name if interaction.guild else "Unknown Server"
        dm_lines.append(f"📋 **Archived Trivia Answers — {guild_name}**\n")
        if archived and archived.question_text:
            dm_lines.append(f"**Question:** {archived.question_text}")
        dm_lines.append(
            f"Session started: {previous_session.created_at.strftime('%b %d, %Y at %I:%M %p UTC')}"
        )
        dm_lines.append(
            f"Archived: {datetime.now(timezone.utc).strftime('%b %d, %Y at %I:%M %p UTC')}"
        )
        dm_lines.append(f"\n**Answers ({len(previous_session.answers)}):**")
        dm_lines.append("──────────")
        for answer in previous_session.answers.values():
            timestamp_str = answer.timestamp.strftime("%b %d, %I:%M %p")
            dm_lines.append(f"**{answer.username}** ({timestamp_str}):\n{answer.text}\n")
        dm_lines.append("──────────")

        dm_content = "\n".join(dm_lines)

        # Paginate if needed
        if len(dm_content) <= 2000:
            await interaction.user.send(dm_content)
        else:
            # Split at 1800 char boundaries on newlines
            chunks = []
            current = ""
            for line in dm_lines:
                if len(current) + len(line) + 1 > 1800 and current:
                    chunks.append(current)
                    current = ""
                current += line + "\n"
            if current:
                chunks.append(current)
            for chunk in chunks:
                await interaction.user.send(chunk)
    except Exception as e:
        logger.warning(f"Failed to DM admin {interaction.user.id} with archived answers: {e}")
```

Add import at top of file:
```python
from datetime import datetime, timezone
```

Modify the `create_session` call (line 532) to pass question_text:
```python
session = answer_service.create_session(self.guild_id, question_text=self.todays_question.value.strip())
```

Also update `answer_service.create_session` to accept `question_text`:

In `src/services/answer_service.py`, modify `create_session`:
```python
def create_session(guild_id: str, question_text: Optional[str] = None) -> TriviaSession:
    """Create a new trivia session for a guild.

    Args:
        guild_id: Discord server/guild ID
        question_text: The trivia question being asked

    Returns:
        The newly created TriviaSession
    """
    session = TriviaSession(guild_id=guild_id, question_text=question_text)
    storage_service.save_session(guild_id, session)
    return session
```

**Step 4: Run all tests to verify they pass**

Run: `pytest -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/commands/post_question.py src/services/answer_service.py tests/integration/test_post_question.py
git commit -m "feat: archive session + DM admin on post-question reset"
```

---

### Task 6: Full Test Suite Verification

**Files:** None (verification only)

**Step 1: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS, coverage >= 75%

**Step 2: Run linting and type checks**

Run: `black src/ tests/ && flake8 src/ tests/ && mypy src/`
Expected: No errors

**Step 3: Final commit if any formatting changes**

```bash
git add -A
git commit -m "chore: formatting and lint fixes"
```
