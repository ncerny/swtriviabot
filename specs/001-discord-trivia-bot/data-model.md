# Data Model: Discord Trivia Bot

**Feature**: 001-discord-trivia-bot  
**Phase**: 1 - Design & Contracts  
**Date**: 2025-10-25

## Purpose

Define the data entities, their relationships, validation rules, and state transitions for the Discord trivia bot's in-memory storage.

---

## Entities

### Answer

Represents a user's response to the current trivia question.

**Attributes**:

- `user_id` (str): Discord user ID (unique identifier from Discord API)
- `username` (str): Discord username for display purposes
- `text` (str): The answer content provided by the user
- `timestamp` (datetime): When the answer was submitted (UTC)
- `is_updated` (bool): Whether this answer replaces a previous submission

**Validation Rules**:

- `user_id`: MUST be non-empty string, validated by Discord API
- `username`: MUST be non-empty string, obtained from Discord user object
- `text`: MUST be non-empty after stripping whitespace, length ≤ 4000 characters
- `timestamp`: MUST be valid UTC datetime
- `is_updated`: Boolean flag set to True if replacing previous answer

**Business Rules**:

- One answer per user per guild (user_id is unique within guild session)
- Previous answer is completely replaced when user submits again
- Answer text is stored exactly as submitted (no normalization)
- Username is captured at submission time (not updated if user changes Discord username)

**Example**:

```python
Answer(
    user_id="123456789012345678",
    username="TriviaPlayer#1234",
    text="The capital of France is Paris",
    timestamp=datetime.utcnow(),
    is_updated=False
)
```

---

### TriviaSession

Represents the current active trivia round for a Discord server.

**Attributes**:

- `guild_id` (str): Discord server/guild ID (unique identifier from Discord API)
- `answers` (dict[str, Answer]): Map of user_id to Answer objects
- `created_at` (datetime): When first answer was submitted (session start time)
- `last_activity` (datetime): Timestamp of most recent answer submission or reset

**Validation Rules**:

- `guild_id`: MUST be non-empty string, validated by Discord API
- `answers`: Dictionary with user_id (str) as keys and Answer objects as values
- `created_at`: MUST be valid UTC datetime
- `last_activity`: MUST be valid UTC datetime, ≥ created_at

**Business Rules**:

- One active session per guild at any time
- Session is automatically created when first answer is submitted
- Session is cleared when admin runs reset command
- Session state persists only while bot is running (no disk persistence)
- Sessions are isolated per guild (multi-server support)

**State Transitions**:

```text
[No Session]
    → User submits first answer
    → [Active Session created]

[Active Session]
    → User submits answer
    → [Answer added/updated in session]

[Active Session]
    → Admin runs reset
    → [Session cleared, returns to No Session]

[Active Session]
    → Bot restarts
    → [All sessions lost]
```

**Example**:

```python
TriviaSession(
    guild_id="987654321098765432",
    answers={
        "123456789012345678": Answer(...),
        "234567890123456789": Answer(...)
    },
    created_at=datetime(2025, 10, 25, 10, 0, 0),
    last_activity=datetime(2025, 10, 25, 10, 15, 30)
)
```

---

## Relationships

```text
TriviaSession (1) ──contains──> (0..*) Answer
  - One session contains zero or more answers
  - Each answer belongs to exactly one session (guild)
  - Relationship is composition: answers don't exist independently

Discord Guild (1) ──has──> (0..1) TriviaSession
  - Each Discord guild has at most one active session
  - Session is implicitly created on first answer
  - Session is destroyed on reset or bot restart

Discord User (1) ──submits──> (0..1) Answer per Guild
  - Each user can submit at most one answer per guild
  - Same user can have different answers in different guilds
  - Submitting again replaces previous answer
```

---

## In-Memory Storage Structure with Disk Persistence

The bot maintains a hybrid storage approach:

1. **In-Memory Cache**: Active session state for fast access
2. **Disk Persistence**: JSON files in `/data/` directory for durability

```python
# Type: dict[str, TriviaSession]
sessions = {
    "guild_id_1": TriviaSession(...),
    "guild_id_2": TriviaSession(...),
    ...
}

# Persisted to: /data/{guild_id}.json
```

**File Format** (`/data/{guild_id}.json`):

```json
{
  "guild_id": "987654321098765432",
  "created_at": "2025-10-25T10:00:00Z",
  "last_activity": "2025-10-25T10:15:30Z",
  "answers": {
    "123456789012345678": {
      "user_id": "123456789012345678",
      "username": "TriviaPlayer#1234",
      "text": "Paris",
      "timestamp": "2025-10-25T10:05:00Z",
      "is_updated": false
    }
  }
}
```

**Access Patterns**:

1. **Submit Answer** (user action):

   ```python
   guild_id = interaction.guild_id
   user_id = interaction.user.id

   # Load from disk if not in memory
   if guild_id not in sessions:
       sessions[guild_id] = load_session_from_disk(guild_id) or TriviaSession(guild_id)

   is_updated = user_id in sessions[guild_id].answers
   sessions[guild_id].answers[user_id] = Answer(...)

   # Persist to disk after update
   save_session_to_disk(guild_id, sessions[guild_id])
   ```

2. **List Answers** (admin action):

   ```python
   guild_id = interaction.guild_id

   # Load from disk if not in memory
   if guild_id not in sessions:
       sessions[guild_id] = load_session_from_disk(guild_id)

   if not sessions[guild_id] or not sessions[guild_id].answers:
       return "No answers submitted yet"

   answers = sessions[guild_id].answers.values()
   return format_answer_list(answers)
   ```

3. **Reset Session** (admin action):

   ```python
   guild_id = interaction.guild_id

   # Clear from memory
   if guild_id in sessions:
       del sessions[guild_id]

   # Delete from disk
   delete_session_file(guild_id)  # Removes /data/{guild_id}.json
   ```

**Persistence Strategy**:

- **Write**: After every answer submit/update (atomic write: temp file → rename)
- **Read**: On bot startup (load all guild files) or lazy load on first command per guild
- **Delete**: On session reset (remove JSON file)
- **Format**: Pretty-printed JSON for debugging and manual inspection
- **Atomic Writes**: Write to `/data/{guild_id}.tmp`, then rename to ensure consistency
- **Error Handling**: Log I/O errors, continue with in-memory state only if disk operations fail

**Memory Estimation**:

- Answer object: ~200 bytes (user_id: 20B, username: 50B, text: avg 100B, metadata: 30B)
- 100 users: 20KB in memory
- 10 guilds with 100 users each: 200KB in memory
- Bot overhead (discord.py): ~30-50MB
- Total steady state: ~50-70MB (well under 100MB limit)

**Disk Estimation**:

- JSON file per guild: ~1KB (10 users), ~5KB (50 users), ~10KB (100 users)
- 100 guilds with avg 20 users each: ~200KB total disk usage
- Minimal disk space requirements (<1MB for typical deployments)
  ```

  ```

3. **Reset Session** (admin action):

   ```python
   guild_id = interaction.guild_id

   if guild_id in sessions:
       del sessions[guild_id]
   ```

**Memory Estimation**:

- Answer object: ~200 bytes (user_id: 20B, username: 50B, text: avg 100B, metadata: 30B)
- 100 users: 20KB
- 10 guilds with 100 users each: 200KB
- Bot overhead (discord.py): ~30-50MB
- Total steady state: ~50-70MB (well under 100MB limit)

---

## Validation Rules Summary

### Answer Text Validation

```python
def validate_answer_text(text: str) -> str:
    """
    Validates answer text and returns cleaned version.

    Raises:
        ValueError: If text is empty or exceeds length limit
    """
    if not text or not text.strip():
        raise ValueError("Answer cannot be empty")

    if len(text) > 4000:
        raise ValueError("Answer exceeds maximum length (4000 characters)")

    return text.strip()
```

### Permission Validation

```python
def validate_admin_permission(interaction: discord.Interaction) -> bool:
    """
    Checks if user has administrator permission in the guild.

    Returns:
        bool: True if user is admin, False otherwise
    """
    return interaction.user.guild_permissions.administrator
```

---

## State Management Considerations

### Thread Safety

- Python GIL provides basic thread safety for dictionary operations
- discord.py uses asyncio (single-threaded event loop)
- No explicit locking needed for this use case
- If adding background cleanup tasks, use `asyncio.Lock` for session modifications

### Memory Cleanup (Optional Future Enhancement)

```python
# Not implemented in MVP, but documented for future consideration
async def cleanup_inactive_sessions():
    """
    Remove sessions with no activity in last 24 hours.
    Run periodically to prevent memory growth in long-running bots.
    """
    now = datetime.utcnow()
    threshold = timedelta(hours=24)

    for guild_id in list(sessions.keys()):
        if now - sessions[guild_id].last_activity > threshold:
            del sessions[guild_id]
```

### Data Retention

- **Normal operation**: Data persists for bot lifetime (until restart or reset)
- **Bot restart**: All session data is lost (by design, per requirements)
- **Guild session**: Isolated per guild, no cross-contamination
- **User privacy**: No data exported, logged, or persisted to disk

---

## Error Scenarios

| Scenario                         | Validation | Error Message                                            |
| -------------------------------- | ---------- | -------------------------------------------------------- |
| Empty answer submitted           | Pre-submit | "Please provide an answer"                               |
| Answer > 4000 characters         | Pre-submit | "Answer exceeds maximum length (4000 characters)"        |
| Non-admin uses admin command     | Pre-submit | "You don't have permission to use this command"          |
| List answers with no submissions | Runtime    | "No answers submitted yet"                               |
| Reset with no active session     | Runtime    | "All answers have been reset - ready for next question!" |
| Discord API timeout              | Runtime    | "Command timed out, please try again"                    |

---

## Next Steps

✅ Data model complete - proceed to contract definitions
