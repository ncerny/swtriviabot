# Discord Slash Commands Contract

**Feature**: 001-discord-trivia-bot  
**Protocol**: Discord Slash Commands API  
**Date**: 2025-10-25

## Overview

This document defines the Discord slash command contracts for the trivia bot. Discord slash commands use a specific interaction pattern rather than traditional REST APIs.

---

## Command: `/answer`

**Description**: Submit or update your answer to the current trivia question

**Permission Required**: None (available to all server members)

**Parameters**:

| Name   | Type   | Required | Description                        | Max Length |
| ------ | ------ | -------- | ---------------------------------- | ---------- |
| `text` | string | Yes      | Your answer to the trivia question | 4000 chars |

**Request Context** (provided by Discord):

```python
{
    "interaction": {
        "guild_id": "987654321098765432",  # Server ID
        "user": {
            "id": "123456789012345678",     # User ID
            "username": "TriviaPlayer",     # Username
            "discriminator": "1234"         # User tag
        },
        "options": [
            {
                "name": "text",
                "value": "The capital of France is Paris"
            }
        ]
    }
}
```

**Success Response** (Interaction Reply):

```python
# First submission
{
    "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
    "data": {
        "content": "✅ Your answer has been recorded!",
        "flags": 64  # EPHEMERAL (only visible to user)
    }
}

# Update submission (user already answered)
{
    "type": 4,
    "data": {
        "content": "🔄 You've already answered this question - updating your answer!",
        "flags": 64
    }
}
```

**Error Responses**:

```python
# Empty answer
{
    "type": 4,
    "data": {
        "content": "❌ Please provide an answer",
        "flags": 64
    }
}

# Answer too long
{
    "type": 4,
    "data": {
        "content": "❌ Answer exceeds maximum length (4000 characters)",
        "flags": 64
    }
}

# Generic error
{
    "type": 4,
    "data": {
        "content": "❌ Something went wrong, please try again",
        "flags": 64
    }
}
```

**Performance Requirement**: Response within 2 seconds (p95)

---

## Command: `/list-answers`

**Description**: View all submitted answers (admin only)

**Permission Required**: Administrator permission in the server

**Parameters**: None

**Request Context** (provided by Discord):

```python
{
    "interaction": {
        "guild_id": "987654321098765432",
        "user": {
            "id": "234567890123456789",
            "username": "AdminUser",
            "guild_permissions": "8"  # Administrator permission bit
        }
    }
}
```

**Success Response** (Interaction Reply):

```python
# With answers
{
    "type": 4,
    "data": {
        "content": """📋 **Trivia Answers** (3 submissions)

**TriviaPlayer#1234**: The capital of France is Paris
**QuizMaster#5678**: Paris
**Contestant#9012**: Paris, France

_Use /reset-answers to clear for next question_""",
        "flags": 64  # EPHEMERAL (only visible to admin)
    }
}

# No answers yet
{
    "type": 4,
    "data": {
        "content": "📋 No answers submitted yet",
        "flags": 64
    }
}
```

**Error Responses**:

```python
# Permission denied
{
    "type": 4,
    "data": {
        "content": "❌ You don't have permission to use this command",
        "flags": 64
    }
}

# Generic error
{
    "type": 4,
    "data": {
        "content": "❌ Something went wrong, please try again",
        "flags": 64
    }
}
```

**Performance Requirement**: Response within 3 seconds even with 100 answers

**Formatting Rules**:

- Include answer count in header
- One line per answer: `**Username**: Answer text`
- Sort by submission timestamp (earliest first)
- Include hint about reset command
- Truncate very long answers to 200 chars with "..." if needed for readability

---

## Command: `/reset-answers`

**Description**: Clear all submitted answers to start fresh (admin only)

**Permission Required**: Administrator permission in the server

**Parameters**: None

**Request Context** (provided by Discord):

```python
{
    "interaction": {
        "guild_id": "987654321098765432",
        "user": {
            "id": "234567890123456789",
            "username": "AdminUser",
            "guild_permissions": "8"
        }
    }
}
```

**Success Response** (Interaction Reply):

```python
{
    "type": 4,
    "data": {
        "content": "🔄 All answers have been reset - ready for next question!",
        "flags": 64  # EPHEMERAL
    }
}
```

**Error Responses**:

```python
# Permission denied
{
    "type": 4,
    "data": {
        "content": "❌ You don't have permission to use this command",
        "flags": 64
    }
}

# Generic error
{
    "type": 4,
    "data": {
        "content": "❌ Something went wrong, please try again",
        "flags": 64
    }
}
```

**Performance Requirement**: Response within 1 second (p95)

**Behavior Notes**:

- Clearing empty session is not an error (returns success message)
- Operation is immediate and cannot be undone
- All guild members lose their submitted answers

---

## Discord API Integration Notes

### Command Registration

Commands must be registered with Discord on bot startup using the command tree:

```python
@bot.tree.command(name="answer", description="Submit your trivia answer")
async def answer_command(interaction: discord.Interaction, text: str):
    # Handler implementation
    pass

@bot.tree.command(name="list-answers", description="View all submitted answers (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def list_answers_command(interaction: discord.Interaction):
    # Handler implementation
    pass

@bot.tree.command(name="reset-answers", description="Clear all answers (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def reset_answers_command(interaction: discord.Interaction):
    # Handler implementation
    pass

# Sync commands with Discord
await bot.tree.sync()
```

### Interaction Response Pattern

All commands must respond within 3 seconds or Discord shows "Application did not respond":

1. **Immediate response** (preferred): Call `interaction.response.send_message()` within 3s
2. **Deferred response**: Call `interaction.response.defer()` immediately, then `interaction.followup.send()` later
3. **Error handling**: Always respond, even on errors

### Permission Checking

- Use `@app_commands.checks.has_permissions(administrator=True)` decorator
- Discord automatically shows permission error to user if check fails
- Can also manually check: `interaction.user.guild_permissions.administrator`

### Message Flags

- `flags=64` (EPHEMERAL): Message only visible to command user
- Prevents answer leakage in public channels
- Admin responses are also ephemeral to avoid channel clutter

---

## Rate Limiting

Discord enforces rate limits on bot API calls:

- **Slash commands**: 5 requests per 5 seconds per user
- **Bot global**: 50 requests per second
- **Message sends**: Varies by route

The bot should:

- Not hit these limits under normal usage (100 users/session)
- Handle rate limit errors gracefully with retry + exponential backoff
- Log rate limit warnings for monitoring

---

## Security Considerations

1. **Permission validation**: Always verify admin permissions before executing privileged commands
2. **Input sanitization**: Discord handles this for slash command parameters
3. **Guild isolation**: Always key session state by guild_id to prevent cross-server leakage
4. **Bot token**: Store in environment variable, never in code or logs
5. **User privacy**: Answers are ephemeral responses visible only to user (except list command for admins)

---

## Testing Strategy

### Unit Tests

- Mock Discord Interaction objects
- Test permission checking logic
- Test answer validation
- Test response formatting

### Integration Tests

- Simulate full command flow: receive interaction → process → respond
- Test error paths (permission denied, empty input, etc.)
- Test state changes (answer added, session reset)
- Verify response message content and format

### Performance Tests

- Simulate 100 concurrent `/answer` submissions
- Measure response times (must be < 3s for p95)
- Verify memory usage stays < 100MB
- Test `/list-answers` with 100 answers (format and timing)

---

## Monitoring & Observability

Metrics to track:

- **Command success rate**: % of commands that complete without error
- **Response times**: p50, p95, p99 latency for each command
- **Error rate**: Frequency of each error type
- **Session count**: Number of active guild sessions
- **Answer count**: Total answers across all sessions
- **Memory usage**: Bot process memory over time

Logging events:

- Command received (guild_id, user_id, command_name)
- Answer submitted (guild_id, user_id, is_update)
- Answers listed (guild_id, answer_count)
- Session reset (guild_id)
- Errors (guild_id, user_id, error_type, error_message)

---

## Next Steps

✅ Contracts defined - proceed to quickstart guide
