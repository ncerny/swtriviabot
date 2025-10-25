# Discord Trivia Bot

A Discord bot for managing trivia game answers with slash commands. Players submit answers, admins view and reset sessions.

## Features

- **Submit Answers**: Users submit answers via `/answer` command with duplicate detection
- **View Submissions**: Admins list all answers with `/list-answers` command
- **Reset Sessions**: Admins clear all answers with `/reset-answers` command
- **Multi-Server Support**: Isolated session state per Discord server
- **Persistent Storage**: Session data saved to disk for durability

## Quick Start

### Prerequisites

- Python 3.14 or higher
- Discord bot token ([Get one here](https://discord.com/developers/applications))
- Discord bot invited to your server with:
  - `applications.commands` scope
  - `bot` scope with `Send Messages` permission

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/ncerny/swtriviabot.git
   cd swtriviabot
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure your bot token:

   ```bash
   cp .env.example .env
   # Edit .env and add your DISCORD_BOT_TOKEN
   ```

4. Run the bot:
   ```bash
   python src/bot.py
   ```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it
3. Go to "Bot" section and click "Add Bot"
4. Under "Token", click "Copy" to get your bot token
5. Save the token in your `.env` file as `DISCORD_BOT_TOKEN`
6. Go to "OAuth2 → URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select permissions: `Send Messages`
9. Copy the generated URL and open it in a browser to invite the bot

## Usage

### Player Commands

**`/answer [text]`** - Submit your answer to the current question

Example:

```
/answer The capital of France is Paris
```

Response on first submission:

```
✅ Your answer has been recorded!
```

Response on updating your answer:

```
🔄 You've already answered this question - updating your answer!
```

**Notes:**

- Responses are private (only you can see them)
- You can update your answer as many times as you want
- Only your most recent answer is saved
- Answer length limited to 4000 characters

### Admin Commands (requires Administrator permission)

**`/list-answers`** - View all submitted answers

Example response:

```
📋 **Submitted Answers:**

1. **Player1**: The capital of France is Paris
2. **Player2**: Paris, France
3. **Player3**: Paris
```

When no answers submitted:

```
📋 No answers submitted yet
```

**`/reset-answers`** - Clear all answers and start fresh

Example response:

```
🔄 All answers have been reset - ready for next question!
```

**Notes:**

- Only users with Administrator permission can use these commands
- `/reset-answers` permanently deletes all session data
- After reset, users can submit new answers

---

## Troubleshooting

### Bot is offline

- Check bot token is correct in `.env` file
- Verify bot process is running: `ps aux | grep bot.py`
- Check logs for error messages

### Commands not appearing

- Bot needs `applications.commands` scope when invited
- Wait up to 1 hour for commands to sync globally
- Try restarting the bot to trigger command sync

### Permission errors

- Admin commands require Administrator permission in Discord
- Regular `/answer` command works for all users
- Check bot has "Send Messages" permission in channel

### Answers not persisting

- Verify `/data/` directory exists and is writable
- Check disk space: `df -h`
- Look for "Saved X session(s)" messages in logs

### Bot crashes or restarts

- Check memory usage: `free -h`
- Review error logs for Python exceptions
- Ensure Python 3.14+ is installed: `python3 --version`

---

## Development

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_answer_service.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code with black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type check with mypy
mypy src/
```

### Project Structure

```
src/
├── bot.py                    # Main bot entry point
├── commands/                 # Slash command handlers
├── models/                   # Data models (Answer, Session)
├── services/                 # Business logic
└── utils/                    # Utilities (validators, formatters)

tests/
├── unit/                     # Unit tests
└── integration/              # Integration tests

data/                         # Persistent session storage (not in git)
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions including:

- Deploying to pella.app (recommended)
- Deploying to Railway.app, Heroku, or Docker
- Configuring persistent storage
- Monitoring and maintenance
- Troubleshooting deployment issues

**Quick Start for pella.app:**

1. Push code to GitHub
2. Create new app on pella.app
3. Add `DISCORD_BOT_TOKEN` environment variable
4. Configure volume mount: `/app/data` (100MB)
5. Deploy!

---

## Contributing

Contributions are welcome! Please follow these guidelines:

### Before Contributing

1. Read the [constitution](.specify/memory/constitution.md) for code quality standards
2. Check existing issues and pull requests
3. Open an issue to discuss major changes

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests first (Red-Green-Refactor)
4. Implement your changes
5. Run tests and linting: `pytest && flake8 src/`
6. Format code: `black src/ tests/`
7. Commit with conventional commit message: `feat: add new feature`
8. Push and create pull request

### Pull Request Requirements

- ✅ All tests passing
- ✅ Code coverage ≥85% (90% for critical paths)
- ✅ No linter errors (flake8)
- ✅ Code formatted with black
- ✅ Type hints verified with mypy
- ✅ Docstrings for all public functions
- ✅ Updated README if user-facing changes

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Build/tooling changes

Example:

```
feat: add support for multiple choice questions

- Add multiple_choice field to Answer model
- Update /answer command to accept choice index
- Add validation for choice ranges
```

---

## Architecture

### Project Structure

```
src/
├── bot.py                    # Main entry point, Discord client
├── models/                   # Data models
│   ├── answer.py            # Answer entity
│   └── session.py           # TriviaSession entity
├── services/                 # Business logic
│   ├── answer_service.py    # Answer operations
│   ├── permission_service.py # Permission checks
│   └── storage_service.py   # Disk persistence
├── commands/                 # Slash command handlers
│   ├── answer.py            # /answer handler
│   ├── list_answers.py      # /list-answers handler
│   └── reset_answers.py     # /reset-answers handler
└── utils/                    # Utilities
    ├── validators.py        # Input validation
    └── formatters.py        # Message formatting
```

### Data Flow

1. **Answer Submission**: User → Discord → `/answer` command → answer_service → storage_service → disk
2. **List Answers**: Admin → Discord → `/list-answers` command → answer_service → formatters → Discord
3. **Reset Session**: Admin → Discord → `/reset-answers` command → answer_service → storage_service → disk cleanup

### Storage Model

- **In-memory cache**: `dict[guild_id, TriviaSession]` for fast access
- **Disk persistence**: JSON files in `/data/{guild_id}.json` for durability
- **Hybrid approach**: Read from disk on startup, write on every change

---

## Project Governance

This project follows constitutional principles defined in [`.specify/memory/constitution.md`](.specify/memory/constitution.md):

1. **Code Quality**: Static analysis, documentation, complexity controls
2. **Testing Standards**: 85% coverage, Red-Green-Refactor workflow
3. **UX Consistency**: Emoji prefixes, unified terminology
4. **Performance Requirements**: <2s latency, <100MB memory

All contributions must comply with these principles.

---

## Roadmap

### Completed ✅

- [x] Answer submission with duplicate detection
- [x] Admin view all answers
- [x] Admin reset session
- [x] Disk persistence
- [x] Multi-server support

### Future Enhancements 🔮

- [ ] Multiple questions per session
- [ ] Scoring and leaderboards
- [ ] Timed questions with auto-close
- [ ] Question categories
- [ ] Export answers to CSV
- [ ] Custom emoji responses
- [ ] Answer reveal command

See [specs/](specs/) directory for detailed feature specifications.

---

## License

[To be determined]
