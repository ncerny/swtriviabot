# Discord Trivia Bot

[![PR Tests](https://github.com/ncerny/swtriviabot/actions/workflows/pr-tests.yml/badge.svg)](https://github.com/ncerny/swtriviabot/actions/workflows/pr-tests.yml)
[![Release](https://github.com/ncerny/swtriviabot/actions/workflows/release.yml/badge.svg)](https://github.com/ncerny/swtriviabot/actions/workflows/release.yml)
[![Latest Release](https://img.shields.io/github/v/release/ncerny/swtriviabot)](https://github.com/ncerny/swtriviabot/releases/latest)

A Discord bot for managing trivia game answers with slash commands. Players submit answers, admins view and reset sessions.

## Features

- **View Submissions**: Admins list all answers with `/list-answers` command
- **Auto-Reset**: Posting a new question automatically archives previous answers and starts a fresh session
- **Auto-Attach Images**: Post a question, then immediately post an image or GIF - the bot automatically re-posts it and cleans up your follow-up message
- **Native Image Support**: Works with Discord's GIF picker, Tenor embeds, uploaded images, and direct links
- **Multi-Server Support**: Isolated session state per Discord server
- **Cloud Persistence**: Session data stored in Firebase Firestore for durability and accessibility
- **High Availability**: Active-Standby architecture with Leader Election for resiliency

## Quick Start

### How to Post Questions with Images

1. Run `/post-question` and fill out the question text
2. The bot posts a complete message with yesterday's results, today's question, and answer button
3. Within 5 minutes, post your image or GIF in the same channel
4. The bot automatically adds the image to the question message and deletes your follow-up message
5. Everything appears as one cohesive message

### Prerequisites

## Requirements

- Python 3.13 or higher
- Discord bot token ([Get one here](https://discord.com/developers/applications))
- **Firebase Project**:
  - Firestore Database enabled
  - Service Account Private Key (`serviceAccountKey.json`)
- Discord bot invited to your server with:
  - `applications.commands` scope
  - `bot` scope with permissions:
    - `Send Messages` - Post questions and responses
    - `Embed Links` - Display question embeds
    - `Manage Messages` - (Optional) Delete follow-up image messages in auto-attach feature

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

4. Add Firebase credentials:
   - Place your `serviceAccountKey.json` in the project root

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

**Click "Submit Your Answer"** - Click the button on the question message to open the answer form.

Example:

1. Click **Submit Your Answer** button
2. Type your answer in the popup form
3. Click **Submit**

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

**Note on Resetting:**

There is no manual `/reset-answers` command. The session is automatically reset when you run `/post-question` to start a new round. The bot will display the previous day's answers to you before clearing them.

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
- Ensure Python 3.13+ is installed: `python3 --version`

### Automatic image attachment not working

The bot can automatically attach images when you post a question without an image, then post an image separately within 3 minutes. If this isn't working:

1. **Restart the bot** - The feature requires the latest code to be running
2. **Check bot logs** - Look for messages like:
   - `📸 Tracking question <id> for image upload from user <id>` (when question is posted)
   - `🖼️  Found image in message` (when image is detected)
   - `✅ Auto-attached image to question` (when successful)
3. **Verify timing** - Image must be posted within 3 minutes of the question
4. **Check channel** - Image must be posted in the same channel as the question
5. **Check permissions** - Bot needs permission to edit messages and delete messages
6. **Image requirements**:
   - Must be an actual image attachment (not a link in text)
   - Message should have minimal text (≤50 characters)
   - Works with image attachments and embedded images

**Debug command:**

```bash
# Check if there are pending image uploads being tracked
python check_tracker.py
```

### Images/GIFs not displaying in questions

The bot supports adding images or GIFs to trivia questions. Here's what works:

**✅ Recommended Methods:**

1. **Upload directly to Discord** (automatic):

   - Post question without image URL
   - Within 3 minutes, post an image in the same channel
   - Bot automatically attaches it and cleans up your follow-up message
   - Works with file uploads or image URLs

2. **Discord CDN** (manual):

   - Send your GIF in any Discord channel
   - Right-click the GIF → "Copy Image Address"
   - Paste that URL in the image field (format: `cdn.discordapp.com/...`)
   - Most reliable for direct URLs

3. **Any direct image URL**:
   - URLs ending in `.gif`, `.png`, `.jpg`, `.jpeg`, `.webp`, etc.
   - Works with most image hosting services
   - Just paste the direct link to the image

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
6. **Use conventional commits**: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, etc.
   - `feat: add new command` → Minor version bump
   - `fix: correct answer validation` → Patch version bump
   - `feat!: change API` or `BREAKING CHANGE:` → Major version bump
7. Push changes and create a pull request
   - All PRs are automatically tested (see badge above)
   - Tests must pass with ≥80% coverage
8. Wait for review and address feedback

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic semantic versioning:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `docs`: Documentation only
- `test`: Adding or updating tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement (patch version bump)
- `chore`: Maintenance tasks

**Breaking Changes:**

- Add `!` after type: `feat!: redesign command interface`
- Or include `BREAKING CHANGE:` in footer (major version bump)

**Examples:**

```bash
git commit -m "feat: add /leaderboard command"
git commit -m "fix: prevent duplicate submissions in same second"
git commit -m "docs: update deployment instructions"
git commit -m "feat!: change answer storage format

BREAKING CHANGE: Answer format changed from string to object"
```

### Release Process

Releases are automated via GitHub Actions:

1. PRs are tested automatically (PR Tests workflow)
2. Merging to `main` triggers semantic-release (Release workflow)
3. Version is calculated from conventional commits
4. Release notes are auto-generated
5. Production artifact is attached to release (Artifact workflow)
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
│   ├── list_answers.py      # /list-answers handler
│   └── post_question.py     # /post-question handler & AnswerButton
└── utils/                    # Utilities
    ├── validators.py        # Input validation
    └── formatters.py        # Message formatting
```

### Data Flow

1. **Answer Submission**: User → Click Button → Modal → answer_service → storage_service → Firestore
2. **List Answers**: Admin → `/list-answers` → answer_service → formatters → Discord
3. **New Question**: Admin → `/post-question` → Modal → answer_service.reset_session → storage_service → Firestore

### Storage Model

- **Firestore**: All session data is stored in the `sessions` collection.
- **Leader Election**: Bot instances coordinate via `bot_status/leader` document in Firestore.
- **Stateless**: No local state is maintained, allowing any instance to serve requests.

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

- [x] Answer submission via Button/Modal
- [x] Admin view all answers
- [x] Automatic session reset on new question
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

## Repository Configuration

### Recommended Branch Protection (main branch)

To ensure code quality and automated releases work correctly, configure the following branch protection rules:

1. **Go to**: Repository Settings → Branches → Branch protection rules → Add rule
2. **Branch name pattern**: `main`
3. **Enable**:
   - ✅ Require a pull request before merging
     - Require approvals: 1 (or more for larger teams)
   - ✅ Require status checks to pass before merging
     - Require branches to be up to date before merging
     - **Required status checks**: `Run Tests` (from PR Tests workflow)
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings (for admins)
4. **Save changes**

**Why this matters:**

- Prevents untested code from reaching main
- Ensures all PRs have passing tests before merge
- Triggers automatic releases only for tested code
- Enforces conventional commit messages through PR review

**Workflow Monitoring:**

- PR Tests workflow must pass (≥80% coverage)
- Release workflow runs automatically on merge to main
- Artifact workflow attaches deployment-ready files to release
- Check Actions tab for workflow execution status

---

## License

[To be determined]
