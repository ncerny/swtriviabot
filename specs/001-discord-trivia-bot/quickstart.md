# Quickstart Guide: Discord Trivia Bot

**Feature**: 001-discord-trivia-bot  
**Date**: 2025-10-25

## Overview

This guide walks through setting up, developing, and deploying the Discord trivia bot from scratch.

---

## Prerequisites

- Python 3.14 or higher
- Discord account with bot application created
- Git installed
- Railway.app account (for deployment)

---

## 1. Discord Bot Setup

### Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application", name it "SWTriviaBot"
3. Navigate to "Bot" section in left sidebar
4. Click "Add Bot"
5. Under "Token" section, click "Reset Token" and copy the token (save securely!)
6. Under "Privileged Gateway Intents", enable:
   - ❌ PRESENCE INTENT (not needed)
   - ❌ SERVER MEMBERS INTENT (not needed)
   - ✅ MESSAGE CONTENT INTENT (optional, for debugging)

### Configure Bot Permissions

1. Navigate to "OAuth2" → "URL Generator" in left sidebar
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Use Slash Commands
4. Copy the generated URL
5. Paste URL in browser and add bot to your test server

---

## 2. Local Development Setup

### Clone Repository

```bash
git clone https://github.com/ncerny/swtriviabot.git
cd swtriviabot
git checkout 001-discord-trivia-bot
```

### Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt contents**:

```txt
discord.py>=2.3.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

### Configure Environment

Create `.env` file in project root:

```bash
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_test_server_id_here  # Optional, for faster command sync
```

**⚠️ Important**: Add `.env` to `.gitignore` to prevent token leakage!

---

## 3. Project Structure

```text
swtriviabot/
├── src/
│   ├── bot.py                    # Main entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── answer.py             # /answer command
│   │   ├── list_answers.py       # /list-answers command
│   │   └── reset_answers.py      # /reset-answers command
│   ├── models/
│   │   ├── __init__.py
│   │   ├── answer.py             # Answer entity
│   │   └── session.py            # TriviaSession manager
│   ├── services/
│   │   ├── __init__.py
│   │   ├── answer_service.py     # Business logic
│   │   └── permission_service.py # Permission checks
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py         # Message formatting
│       └── validators.py         # Input validation
├── tests/
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/
│   │   ├── test_answer_service.py
│   │   ├── test_validators.py
│   │   └── test_formatters.py
│   └── integration/
│       ├── test_answer_flow.py
│       ├── test_admin_flow.py
│       └── test_permissions.py
├── perf/
│   └── scripts/
│       └── bench_concurrent_answers.py
├── .env                          # Environment variables (not in git)
├── .gitignore
├── requirements.txt
├── README.md
└── Procfile                      # For Railway deployment
```

---

## 4. Development Workflow

### Run Bot Locally

```bash
python src/bot.py
```

Expected output:

```text
2025-10-25 10:00:00 INFO     discord.client Logging in using static token
2025-10-25 10:00:01 INFO     discord.gateway Shard ID None has connected to Gateway
2025-10-25 10:00:02 INFO     bot Syncing command tree...
2025-10-25 10:00:03 INFO     bot Commands synced! Bot is ready.
```

### Test Commands in Discord

1. Go to your test Discord server
2. Type `/` and you should see three commands:
   - `/answer` - Submit your answer
   - `/list-answers` - View all answers (admin only)
   - `/reset-answers` - Clear all answers (admin only)
3. Test the flow:

   ```
   User: /answer text:Paris
   Bot: ✅ Your answer has been recorded!

   User: /answer text:France
   Bot: 🔄 You've already answered this question - updating your answer!

   Admin: /list-answers
   Bot: 📋 **Trivia Answers** (1 submission)
        **YourUsername#1234**: France

   Admin: /reset-answers
   Bot: 🔄 All answers have been reset - ready for next question!
   ```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_answer_service.py

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Check Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

---

## 5. Testing Guide

### Unit Tests Example

```python
# tests/unit/test_validators.py
import pytest
from src.utils.validators import validate_answer_text

def test_validate_answer_text_success():
    result = validate_answer_text("  Valid answer  ")
    assert result == "Valid answer"

def test_validate_answer_text_empty():
    with pytest.raises(ValueError, match="Answer cannot be empty"):
        validate_answer_text("")

def test_validate_answer_text_too_long():
    long_text = "a" * 4001
    with pytest.raises(ValueError, match="exceeds maximum length"):
        validate_answer_text(long_text)
```

### Integration Tests Example

```python
# tests/integration/test_answer_flow.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.commands.answer import answer_command

@pytest.mark.asyncio
async def test_submit_answer_first_time(mock_interaction):
    mock_interaction.user.id = "123456"
    mock_interaction.user.name = "TestUser"
    mock_interaction.guild_id = "999888"

    await answer_command(mock_interaction, text="Test answer")

    mock_interaction.response.send_message.assert_called_once_with(
        "✅ Your answer has been recorded!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_update_existing_answer(mock_interaction, mock_session):
    # Setup: User already has an answer
    mock_interaction.user.id = "123456"
    mock_session.has_answer("123456")

    await answer_command(mock_interaction, text="Updated answer")

    mock_interaction.response.send_message.assert_called_once_with(
        "🔄 You've already answered this question - updating your answer!",
        ephemeral=True
    )
```

### Performance Tests

```bash
# Run performance benchmarks
python perf/scripts/bench_concurrent_answers.py

# Expected output:
# Concurrent answer submissions: 100 users
# Total time: 2.3s
# Average response time: 0.023s
# P95 response time: 0.145s
# P99 response time: 0.287s
# Memory usage: 68.4 MB
```

---

## 6. Deployment to Railway

### Prepare for Deployment

1. **Create Procfile**:

   ```text
   bot: python src/bot.py
   ```

2. **Verify requirements.txt** is up to date:

   ```bash
   pip freeze > requirements.txt
   ```

3. **Create runtime.txt** (optional, specifies Python version):
   ```text
   python-3.11.6
   ```

### Deploy to Railway

1. **Connect Repository**:

   - Go to [Railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Authorize Railway to access your repository
   - Select `swtriviabot` repository
   - Select `001-discord-trivia-bot` branch

2. **Configure Environment Variables**:

   - In Railway dashboard, go to "Variables" tab
   - Add: `DISCORD_BOT_TOKEN` = `your_bot_token_here`
   - Save changes

3. **Configure Service**:

   - Railway auto-detects Python and installs dependencies
   - Procfile tells Railway to run `python src/bot.py`
   - Service starts automatically after build

4. **Monitor Deployment**:
   - Check "Deployments" tab for build logs
   - Check "Logs" tab for runtime output
   - Should see "Bot is ready" message

### Verify Production Bot

1. Bot should come online in Discord (green status)
2. Slash commands should work in all servers where bot is installed
3. Check Railway metrics:
   - Memory usage: Should be 50-70MB steady-state
   - CPU usage: Should be minimal (<5% average)
   - Restarts: Should be zero (unless you redeploy)

---

## 7. Monitoring & Maintenance

### Railway Dashboard

Monitor these metrics in Railway:

- **Memory**: Should stay under 100MB (alert if approaching limit)
- **CPU**: Should be minimal except during command spikes
- **Restarts**: Unexpected restarts indicate crashes (check logs)
- **Build time**: Typically 30-60 seconds
- **Deployment status**: Should show "Active"

### Discord Bot Health

- **Online status**: Bot should show as online (green dot)
- **Command responses**: Test each command periodically
- **Latency**: Discord API latency visible in bot status
- **Error rate**: Check Railway logs for exceptions

### Troubleshooting

**Bot offline**:

- Check Railway deployment status
- Verify bot token hasn't been regenerated
- Check Railway logs for startup errors

**Commands not appearing**:

- Verify bot has `applications.commands` scope
- Try syncing commands manually: restart bot or call `await bot.tree.sync()`
- Check bot permissions in Discord server settings

**Permission errors**:

- Verify bot role has "Send Messages" permission
- Check channel-specific permission overrides
- Ensure admin users have "Administrator" permission

**Memory issues**:

- Check number of active guild sessions
- Profile memory usage: `python -m memory_profiler src/bot.py`
- Consider implementing session cleanup for inactive guilds

---

## 8. Common Development Tasks

### Add a New Command

1. Create command file: `src/commands/new_command.py`
2. Implement command handler with `@bot.tree.command()` decorator
3. Register in `src/bot.py`
4. Add tests: `tests/integration/test_new_command.py`
5. Update contracts: `specs/001-discord-trivia-bot/contracts/slash-commands.md`
6. Sync commands: Restart bot or call `await bot.tree.sync()`

### Update Dependencies

```bash
pip install --upgrade discord.py
pip freeze > requirements.txt
pytest  # Verify tests still pass
git commit -am "chore: update discord.py to vX.Y.Z"
git push  # Railway auto-deploys
```

### Debug Production Issues

```bash
# View Railway logs (real-time)
railway logs --follow

# Search logs for errors
railway logs | grep ERROR

# Check specific time range
railway logs --since 1h
```

---

## 9. Constitutional Compliance

This feature adheres to the project constitution:

### Code Quality

- ✅ Linting with flake8, formatting with black
- ✅ Type hints with mypy
- ✅ Docstrings for all public functions
- ✅ Cyclomatic complexity checked in CI

### Testing Standards

- ✅ 85% statement coverage target
- ✅ 90% coverage for critical paths (command handlers, answer service)
- ✅ Unit + integration + performance tests
- ✅ Tests run in CI before merge

### User Experience Consistency

- ✅ Clear emoji prefixes for all messages (✅ ❌ 🔄 📋)
- ✅ Consistent terminology ("answer", not "response" or "submission")
- ✅ Ephemeral messages for privacy
- ✅ Helpful error messages with next steps

### Performance Requirements

- ✅ <2s response time for answer submission (measured in perf tests)
- ✅ <100MB memory usage (measured in Railway)
- ✅ <$5/month hosting cost (Railway Starter plan)
- ✅ Benchmarks in `perf/` directory

---

## 10. Next Steps

After completing this feature:

1. **Merge to main**:

   ```bash
   git checkout main
   git merge 001-discord-trivia-bot
   git push origin main
   ```

2. **Tag release**:

   ```bash
   git tag -a v1.0.0 -m "feat: Discord trivia bot with slash commands"
   git push origin v1.0.0
   ```

3. **Update Railway** to deploy from `main` branch

4. **Monitor production** for 24 hours to ensure stability

5. **Gather user feedback** and create follow-up issues for improvements

---

## Support

- **Spec**: [spec.md](../spec.md)
- **Plan**: [plan.md](../plan.md)
- **Constitution**: [.specify/memory/constitution.md](../../../.specify/memory/constitution.md)
- **Discord.py docs**: https://discordpy.readthedocs.io/
- **Railway docs**: https://docs.railway.app/

For issues, create GitHub issues in the repository.
