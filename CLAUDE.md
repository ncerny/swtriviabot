# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests with coverage (≥75% required)
pytest

# Run specific test file
pytest tests/unit/test_answer_service.py

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Format code with black (line length 100)
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type check with mypy
mypy src/
```

### Running the Bot
```bash
# Set up environment
cp .env.example .env
# Edit .env and add your DISCORD_BOT_TOKEN

# Place serviceAccountKey.json in project root for Firebase

# Run bot
python src/bot.py
```

## Architecture Overview

This is a Discord trivia bot with Firebase Firestore persistence and leader election for high availability.

### Core Components

- **src/bot.py**: Main entry point with leader election and Discord client setup
- **src/models/**: Data models (Answer, TriviaSession, Image)
- **src/services/**: Business logic (answer_service, storage_service, image_service)
- **src/commands/**: Slash command handlers (/list-answers, /post-question)
- **src/utils/**: Utilities (validators, formatters, performance monitoring)

### Data Flow

1. **Answer Submission**: Button interaction → Modal → answer_service → storage_service → Firestore
2. **Question Posting**: /post-question → auto-reset previous session → image tracking
3. **Image Auto-attachment**: Image message detection → automatic attachment to question → cleanup

### Storage Model

- **Firestore Collections**: 
  - `sessions{SUFFIX}`: Trivia session data keyed by guild_id
  - `bot_status{SUFFIX}`: Leader election coordination
- **Collection Suffix**: `-test` for DEV_MODE=true, empty for production
- **Leader Election**: Active-Standby architecture using Firestore locking

### Key Features

- Multi-server support with isolated session state
- Automatic session reset when posting new questions
- Image auto-attachment (3-minute window after question posting)
- Resource monitoring and performance tracking
- Comprehensive error handling with user-friendly messages

## Development Standards

### Code Quality Requirements
- ≥85% test coverage overall, ≥90% for critical paths
- Zero flake8 errors
- All public functions must have docstrings
- Type hints required (mypy enforcement)
- Conventional commits for semantic versioning

### Testing Strategy
- Red-Green-Refactor: Write tests first
- Unit tests for isolated logic
- Integration tests for cross-module behavior
- Async test support with pytest-asyncio

### Environment Isolation
- Use DEV_MODE=true for test collections
- Virtual environment required
- Firebase service account for Firestore access

### Performance Standards
- Interactive actions: <200ms p95 latency
- Memory usage: <100MB per process
- Supports 10,000 concurrent trivia sessions

## Project Management - Integrated Beads + Spec-Kit

This project uses **Beads** for issue tracking and state management, integrated with **Spec-Kit** methodology for larger features.

### Beads - Issue Tracking & State Management
[Beads](https://github.com/steveyegge/beads) handles all issue creation, tracking, and state management.

```bash
# List all issues
bd list

# Show ready work (no blockers)
bd ready

# Create new issue
bd create --type [bug|feature|task|epic] --priority [1-4] --title "Issue Title" --description "Description"

# Show issue details
bd show swtriviabot-[id]

# Update issue status
bd update swtriviabot-[id] --status [open|in-progress|closed]

# Add labels
bd label add swtriviabot-[id] enhancement,spec-kit

# Check project status
bd status
```

### Spec-Kit - Development Methodology
[Spec-Kit](https://github.com/github/spec-kit) provides structured methodology for complex features.

```bash
# Core workflow (use as slash commands with Claude Code)
/speckit.constitution    # Establish/update project principles
/speckit.specify        # Create feature specification
/speckit.plan          # Create implementation plan  
/speckit.tasks         # Generate actionable tasks
/speckit.implement     # Execute implementation

# Optional commands
/speckit.clarify       # Ask structured questions before planning
/speckit.checklist     # Generate quality checklists
/speckit.analyze       # Cross-artifact consistency report
```

### Integrated Workflow

**For Simple Issues (Bug fixes, small improvements):**
1. Create issue directly in Beads: `bd create --type bug --priority 2 --title "Fix validation error"`
2. Work on issue and update status: `bd update issue-id --status in-progress`
3. Complete and close: `bd close issue-id`

**For Complex Features (New functionality, architecture changes):**
1. Create epic in Beads: `bd create --type epic --priority 1 --title "User Authentication System" --labels spec-kit`
2. Follow Spec-Kit methodology:
   - `/speckit.specify` - Create detailed specification
   - `/speckit.plan` - Generate implementation plan
   - `/speckit.tasks` - Break down into actionable tasks
3. Convert tasks to Beads issues: Create individual issues for each task with appropriate labels and dependencies
4. Track progress in Beads: Use `bd ready` to see what's unblocked, update statuses as work progresses
5. `/speckit.implement` - Execute with Beads issue tracking

### Issue Organization in Beads
- **Types**: bug, feature, task, epic, chore
- **Priority Levels**: 1 (highest) to 4 (lowest)  
- **Labels**: 
  - `spec-kit` - Issues following Spec-Kit methodology
  - `enhancement`, `bugfix`, `testing`, `docs` - Standard categorization
  - `constitutional` - Issues related to governance/standards
- **Dependencies**: Use Beads dependency system to link Spec-Kit generated tasks

### Best Practices
- All work items live in Beads (persistent state, ready work detection)
- Use Spec-Kit for complex planning and specification
- Label Spec-Kit derived work for traceability
- Reference Beads issue IDs in conventional commits
- Check `bd ready` before starting work sessions

## Configuration

- **pyproject.toml**: Black formatting, MyPy type checking
- **pytest.ini**: Test discovery, coverage settings, async mode
- **requirements.txt**: Python 3.13+ dependencies
- **.env**: Environment variables (DISCORD_BOT_TOKEN, DEV_MODE)
- **serviceAccountKey.json**: Firebase credentials (not in git)
- **.beads/**: Beads database for issue tracking

## Constitutional Compliance

This project follows principles defined in `.specify/memory/constitution.md`:
- All code changes require automated test coverage
- Performance budgets must be maintained
- UX consistency with unified terminology and error messages
- Static analysis must pass without errors