# Implementation Plan: Discord Trivia Bot

**Branch**: `001-discord-trivia-bot` | **Date**: 2025-10-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-discord-trivia-bot/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Discord bot that accepts trivia answers via slash commands, manages in-memory answer storage with duplicate detection and update notifications, provides admin commands for viewing all answers and resetting sessions, and optimizes for minimal hosting costs (<$5/month, <100MB memory). The bot will use Discord's slash command API with permission-based access control for admin functions.

## Technical Context

**Language/Version**: Python 3.14+  
**Primary Dependencies**: discord.py 2.3+, python-dotenv, pytest 7.4+, pytest-asyncio 0.21+  
**Storage**: Local disk persistence (JSON files) - session state keyed by guild_id, persisted to /data/ directory  
**Testing**: pytest with pytest-asyncio for async command testing  
**Target Platform**: Linux server or cloud container (Docker-compatible) - pella.app recommended  
**Project Type**: single (standalone bot application)  
**Performance Goals**: <2s response time for answer submission, <3s for 100 concurrent submissions, <1s for reset  
**Constraints**: <200ms p95 latency for commands, <100MB steady-state memory, <$5/month hosting cost  
**Scale/Scope**: 100 concurrent participants per session, support multi-server deployment with isolated session state per guild

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Code Quality

- [x] Static analysis configured (linter, formatter)
  - **Tools**: flake8 (linting), black (formatting), mypy (type checking)
  - **Config**: Setup in development dependencies, run in CI
- [x] Documentation standards defined for public interfaces
  - **Standard**: Docstrings for all public functions (purpose, params, returns, raises)
  - **Example**: See contracts/slash-commands.md for command documentation format
- [x] Complexity thresholds identified (cyclomatic complexity ≤10 or justified)
  - **Threshold**: Cyclomatic complexity ≤10 for all functions
  - **Justification required**: Complex command handlers must document state transitions

### Testing Standards

- [x] Test strategy defined (unit/integration/regression levels)
  - **Unit**: Services, models, validators in isolation with mocked Discord objects
  - **Integration**: Full command flows (interaction → service → state → response)
  - **Performance**: Concurrent submission benchmarks in perf/scripts/
- [x] Coverage thresholds established (85% statements, 90% critical paths)
  - **Overall**: 85% statement coverage
  - **Critical paths**: 90% coverage for command handlers, answer_service, session management
  - **Tool**: pytest-cov with HTML reports
- [x] Red-Green-Refactor workflow planned for new features
  - **Process**: Write test → Verify failure → Implement → Verify pass → Refactor
  - **Documented**: See quickstart.md testing guide

### User Experience Consistency

- [x] UX patterns and terminology defined
  - **Emoji prefixes**: ✅ success, ❌ error, 🔄 update, 📋 list
  - **Terminology**: "answer" (not "response" or "submission"), "admin" (not "moderator")
  - **Message format**: Clear action + outcome, ephemeral for privacy
- [x] Error message standards documented
  - **Pattern**: "❌ [What went wrong], [What to do next]"
  - **Examples**: See contracts/slash-commands.md for all error messages
  - **Actionable**: Every error includes next steps or context
- [x] Accessibility requirements identified (if applicable)
  - **Discord accessibility**: Slash commands are screen-reader accessible by default
  - **Message clarity**: Plain text responses, no image-only content
  - **Ephemeral messages**: Private responses reduce information overload

### Performance Requirements

- [x] Performance budgets defined (latency, memory, throughput)
  - **Latency**: <2s p95 for /answer, <3s p95 for /list-answers with 100 users, <1s p95 for /reset
  - **Memory**: <100MB steady-state with 10 active guild sessions
  - **Throughput**: 100 concurrent answer submissions within 3s total
- [x] Benchmark approach planned (baseline measurements, trend tracking)
  - **Location**: perf/scripts/bench_concurrent_answers.py
  - **Metrics**: Response time distribution (p50, p95, p99), memory usage, throughput
  - **Baseline**: Established during initial implementation, tracked in CI
- [x] Performance regression thresholds established (≤5% degradation)
  - **Threshold**: ≤5% increase in p95 latency or memory usage
  - **Enforcement**: Benchmark runs in CI, fails on regression
  - **Documented**: Performance test results tracked in perf/ directory

**Status**: ✅ All gates passed - proceeding to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── bot.py (or index.js)     # Main bot entry point, Discord client setup
├── commands/                # Slash command handlers
│   ├── answer.py            # /answer command handler
│   ├── list_answers.py      # /list-answers command handler
│   └── reset_answers.py     # /reset-answers command handler
├── models/
│   ├── answer.py            # Answer entity model
│   └── session.py           # Session state management
├── services/
│   ├── answer_service.py    # Business logic for answer operations
│   ├── permission_service.py # Admin permission validation
│   └── storage_service.py   # Disk persistence operations (load/save/delete)
└── utils/
    ├── formatters.py        # Message formatting utilities
    └── validators.py        # Input validation

data/                        # Persistent session storage (not in git)
└── {guild_id}.json          # One file per active guild session

tests/
├── integration/
│   ├── test_answer_flow.py  # Full answer submission workflow
│   ├── test_admin_flow.py   # Admin commands workflow
│   ├── test_permissions.py  # Permission enforcement
│   └── test_persistence.py  # Disk persistence operations
└── unit/
    ├── test_answer_service.py
    ├── test_session.py
    ├── test_storage_service.py
    └── test_validators.py

config/
└── settings.py (or .env)    # Bot token, configuration

perf/
└── scripts/
    └── bench_concurrent_answers.py  # Performance benchmarking
```

**Structure Decision**: Single project structure selected. This is a standalone Discord bot application with no frontend/backend split needed. All business logic resides in the bot process. The structure separates command handlers (entry points), models (data structures), services (business logic including persistence), and utilities. This aligns with Discord bot best practices and keeps the codebase simple for the minimal feature set. Added `storage_service.py` for disk operations and `/data/` directory for persistent storage.

## Complexity Tracking

> **No violations** - All constitution gates satisfied with this design.

---

## Phases

### Phase 0: Research ✅ COMPLETE

**Objective**: Resolve all NEEDS CLARIFICATION items and establish technology decisions

**Artifacts**:

- ✅ `research.md` - Technology choices with rationale
  - Python 3.14+ selected for maturity and productivity
  - discord.py 2.3+ selected for slash command support
  - pytest + pytest-asyncio for testing
  - pella.app with local disk storage selected for hosting

**Key Decisions**:

1. **Language**: Python 3.14+ (mature Discord ecosystem, memory efficient, testing tools)
2. **Discord Library**: discord.py 2.3+ (native slash commands, active maintenance)
3. **Testing**: pytest with async support (industry standard, fixture system)
4. **Hosting**: pella.app with local disk storage for session persistence

**Outcome**: All technical unknowns resolved, ready for design phase

---

### Phase 1: Design & Contracts ✅ COMPLETE

**Objective**: Define data models, API contracts, and developer onboarding materials

**Artifacts**:

- ✅ `data-model.md` - Answer and TriviaSession entities with disk persistence
- ✅ `contracts/slash-commands.md` - Discord slash command specifications
- ✅ `quickstart.md` - Setup, development, testing, and deployment guide
- ✅ `.github/copilot-instructions.md` - Updated with Python/discord.py context

**Key Design Elements**:

1. **Data Model**:

   - `Answer`: user_id, username, text, timestamp, is_updated
   - `TriviaSession`: guild_id, answers dict, created_at, last_activity
   - Hybrid storage: In-memory cache + disk persistence (`/data/{guild_id}.json`)

2. **Command Contracts**:

   - `/answer text:str` → Submit/update answer
   - `/list-answers` → View all answers (admin only)
   - `/reset-answers` → Clear session (admin only)
   - All responses ephemeral for privacy

3. **State Management**:
   - Guild-isolated sessions (multi-server support)
   - Automatic session creation on first answer
   - Disk persistence: JSON files in `/data/` directory survive bot restarts
   - Lazy loading: Sessions loaded from disk on first access per guild

**Outcome**: Complete technical specification ready for task breakdown

---

### Phase 2: Task Breakdown 🔜 NEXT

**Command**: Run `/speckit.tasks` to generate task breakdown

**Expected Output**: `tasks.md` with:

- Tasks organized by user story (P1, P2, P3)
- Dependencies between tasks
- Effort estimates
- Test tasks for each feature task
- Performance validation tasks

**Next Steps**:

1. Run `/speckit.tasks` from this branch
2. Review generated tasks for completeness
3. Begin implementation starting with P1 tasks
4. Follow Red-Green-Refactor workflow

---

## Implementation Notes

### Startup Sequence

1. Load `DISCORD_BOT_TOKEN` from environment
2. Initialize Discord client with required intents
3. **Load existing sessions from `/data/` directory** (if any exist)
4. Register slash commands to command tree
5. Sync command tree with Discord API
6. Start event loop and listen for interactions

### Session State Structure

```python
# Global state dictionary (in-memory cache)
sessions: dict[str, TriviaSession] = {}

# On startup: Load all existing sessions
for file in os.listdir("/data/"):
    if file.endswith(".json"):
        guild_id = file.replace(".json", "")
        sessions[guild_id] = load_session_from_disk(guild_id)

# On answer submission
guild_id = interaction.guild_id
if guild_id not in sessions:
    sessions[guild_id] = load_session_from_disk(guild_id) or TriviaSession(guild_id)
sessions[guild_id].answers[user_id] = Answer(...)
save_session_to_disk(guild_id, sessions[guild_id])  # Persist to /data/{guild_id}.json

# On reset
if guild_id in sessions:
    del sessions[guild_id]
delete_session_file(guild_id)  # Remove /data/{guild_id}.json
```

### Error Handling Strategy

- **Permission errors**: Check before command execution, clear message
- **Validation errors**: Validate input, actionable error messages
- **Discord API errors**: Log for monitoring, generic user message
- **Timeout prevention**: All operations complete within 2s (Discord 3s timeout)

### Performance Considerations

- **Memory**: ~200 bytes per answer, 20KB for 100 users, 50-70MB total with bot overhead
- **Latency**: Async I/O with discord.py, minimal processing per command
- **Concurrency**: Python GIL + asyncio event loop provides sufficient thread safety
- **Scalability**: Dictionary lookups O(1), linear scan only for /list-answers

---

## Risks & Mitigations

| Risk                         | Impact | Probability | Mitigation                                  |
| ---------------------------- | ------ | ----------- | ------------------------------------------- |
| Bot token leaked             | High   | Low         | Environment variables, never commit         |
| Memory exceeds 100MB         | Medium | Low         | Profile during tests, monitor in production |
| Discord API rate limiting    | Medium | Low         | Exponential backoff, reasonable usage       |
| Concurrent reset race        | Low    | Low         | asyncio.Lock if needed (likely unnecessary) |
| Railway service degradation  | Low    | Low         | Document migration to alternative hosts     |
| Multi-server state isolation | Medium | Low         | Thorough integration tests for guild_id     |

---

## Success Metrics

### Development Metrics

- Test coverage: ≥85% overall, ≥90% critical paths
- Code quality: Zero linter errors, complexity ≤10
- Documentation: All public functions documented

### Performance Metrics

- `/answer` p95 latency: <2s
- `/list-answers` p95 latency: <3s (100 users)
- `/reset-answers` p95 latency: <1s
- Memory usage: <100MB steady-state
- Hosting cost: ≤$5/month

### User Experience Metrics

- Command success rate: ≥95%
- Error message clarity: All errors actionable
- Response consistency: Emoji prefixes, unified terminology

---

## References

- **Feature Spec**: [spec.md](spec.md)
- **Research**: [research.md](research.md)
- **Data Model**: [data-model.md](data-model.md)
- **Contracts**: [contracts/slash-commands.md](contracts/slash-commands.md)
- **Quickstart**: [quickstart.md](quickstart.md)
- **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
- **Discord.py Docs**: https://discordpy.readthedocs.io/
- **Railway Docs**: https://docs.railway.app/
