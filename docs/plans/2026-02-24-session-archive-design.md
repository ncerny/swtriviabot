# Session Archive & Admin DM Design

**Date**: 2026-02-24
**Status**: Proposed

## Problem

When `/post-question` resets the current trivia session, all previous answers are permanently deleted from Firestore. The admin sees them once in an ephemeral message, then they're gone. There is no way to recover yesterday's answers.

## Goals

- Automatically archive answers before session reset
- DM the admin a copy of the archived answers at reset time
- Retain the last 3 sessions per guild as a rolling window
- Zero changes to the existing answer submission and retrieval flow

## Non-Goals

- Public slash command for browsing history (query Firestore directly if needed)
- Leaderboards or analytics
- Indefinite retention

---

## Design

### 1. Data Model Changes

#### New model: `ArchivedSession`

```python
# src/models/archived_session.py
@dataclass
class ArchivedSession:
    guild_id: str
    question_text: str
    answers: dict[str, Answer]      # copied from TriviaSession
    created_at: datetime            # when the original session started
    archived_at: datetime           # when it was archived (reset time)
```

#### Modified model: `TriviaSession`

One new optional field:

```python
question_text: str | None = None
```

Set when `/post-question` creates the session. Carried through to archive.

#### Firestore structure

```
session_archives{SUFFIX}/
  {guild_id}_{ISO_timestamp}/
    guild_id: string
    question_text: string
    answers: { user_id: { user_id, username, text, timestamp, is_updated } }
    created_at: ISO timestamp
    archived_at: ISO timestamp
```

Separate collection from `sessions{SUFFIX}` — no impact on active session operations.

### 2. Storage Layer

Three new functions in `storage_service.py`:

- **`save_archived_session(archived_session)`** — Writes to `session_archives{SUFFIX}`. Document ID: `{guild_id}_{ISO timestamp}`.
- **`load_archived_sessions(guild_id, limit=3)`** — Queries by guild_id, ordered by `archived_at` desc, limited to `limit`. Returns list of `ArchivedSession`.
- **`prune_archived_sessions(guild_id, keep=3)`** — Deletes archives beyond the `keep` threshold for a guild.

Existing storage functions (`save_session`, `load_session`, `delete_session`) are unchanged.

### 3. Answer Service

One new function in `answer_service.py`:

- **`archive_session(guild_id)`** — Loads the current session, constructs an `ArchivedSession`, saves it, then prunes old archives. Returns the `ArchivedSession` or `None` if nothing to archive.

### 4. Post-Question Flow (Modified)

Current flow in `PostQuestionModal.on_submit()`:

1. Load previous session
2. Show answers to admin (ephemeral)
3. Delete session
4. Create new session

New flow:

1. Load previous session
2. **If it has answers → archive it** via `answer_service.archive_session(guild_id)`
3. Show answers to admin (ephemeral) — unchanged
4. **DM the admin** with formatted previous answers
5. Delete session — unchanged
6. Create new session **with `question_text`** from modal input
7. **Prune old archives** (handled inside `archive_session`)

If the DM fails (user has DMs disabled), log a warning and continue. The reset is never blocked by a failed DM.

### 5. DM Format

```
📋 Archived Trivia Answers — [Server Name]

Question: What planet has the most moons?
Session started: Feb 23, 2026 at 3:00 PM UTC
Archived: Feb 24, 2026 at 3:00 PM UTC

Answers (4):
──────────
**user1** (Feb 23, 3:12 PM):
Saturn

**user2** (Feb 23, 3:15 PM):
Jupiter
──────────
```

Paginated across multiple DMs if content exceeds 2000 characters (same logic as `/list-answers`).

---

## Files Changed

| File | Change |
|------|--------|
| `src/models/archived_session.py` | **New** — `ArchivedSession` dataclass |
| `src/models/session.py` | Add optional `question_text` field |
| `src/services/storage_service.py` | Add `save_archived_session`, `load_archived_sessions`, `prune_archived_sessions` |
| `src/services/answer_service.py` | Add `archive_session()` method |
| `src/commands/post_question.py` | Call archive + DM before reset; pass `question_text` to new session |

## What Doesn't Change

- Answer submission flow (buttons, modals, `submit_answer`)
- `/list-answers` command
- `delete_session()` behavior
- Leader election
- Image auto-attachment
- All existing storage service methods

## Testing

- Unit tests for `ArchivedSession` model serialization
- Unit tests for `archive_session()` — with answers, without answers, prune behavior
- Unit tests for DM formatting and pagination
- Integration test for the full post-question archive flow
- Test DM failure graceful handling
