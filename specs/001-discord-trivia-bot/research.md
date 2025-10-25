# Research: Discord Trivia Bot

**Feature**: 001-discord-trivia-bot  
**Phase**: 0 - Outline & Research  
**Date**: 2025-10-25

## Purpose

Resolve all NEEDS CLARIFICATION items from Technical Context and identify best practices for building a cost-optimized Discord bot with slash commands.

## Research Questions

1. **Language/Version**: Which language and version provides the best balance of Discord API maturity, memory efficiency, and developer productivity?
2. **Primary Dependencies**: Which Discord API library is most suitable for slash commands with minimal resource overhead?
3. **Testing Framework**: Which testing approach aligns with the chosen language and provides good integration testing support?
4. **Hosting Solution**: Which hosting platform meets the <$5/month, <100MB memory, always-on requirements?

---

## Decision 1: Language & Version

### Decision

**Python 3.14+** with asyncio support

### Rationale

- **Mature Discord ecosystem**: discord.py 2.x has excellent slash command support and extensive documentation
- **Memory efficiency**: Python with proper async patterns can stay well under 100MB for this use case
- **Developer productivity**: Python's simplicity enables rapid development and easy maintenance
- **Testing maturity**: pytest ecosystem provides excellent unit and integration testing support
- **Hosting compatibility**: Widely supported across all hosting platforms

### Alternatives Considered

1. **JavaScript/Node.js 18+**

   - **Pros**: discord.js is also mature, Node has good async performance, smaller base memory footprint
   - **Cons**: Type safety requires TypeScript (adds complexity), slightly less intuitive for data modeling
   - **Rejected because**: Python's simplicity and testing ecosystem outweigh Node's marginal memory advantage for this scale

2. **Go 1.21+**
   - **Pros**: Excellent memory efficiency, compiled binary, very low resource usage
   - **Cons**: Discord libraries less mature (discordgo), more verbose for simple CRUD operations, steeper learning curve
   - **Rejected because**: Overengineered for this use case; Python's maturity and simplicity are more valuable than Go's efficiency at this scale

---

## Decision 2: Primary Dependencies

### Decision

**discord.py 2.3+** (latest stable with slash command support)

### Rationale

- **Native slash command support**: Built-in decorators and command tree system for slash commands
- **Permission handling**: First-class support for checking Discord permissions
- **Memory efficient**: Async architecture with proper event handling keeps memory usage low
- **Well-documented**: Extensive examples for slash commands and bot patterns
- **Active maintenance**: Regular updates and security patches

### Alternatives Considered

1. **Pycord (discord.py fork)**

   - **Pros**: Similar API, also supports slash commands
   - **Cons**: Smaller community, less frequent updates
   - **Rejected because**: discord.py 2.x now has full slash command support, making the fork unnecessary

2. **discord.js**
   - **Pros**: Would pair with Node.js choice
   - **Cons**: Requires JavaScript/TypeScript (not selected)
   - **Rejected because**: Language choice drives this decision

### Additional Dependencies

- **python-dotenv**: Environment variable management for bot token
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support for Discord interactions

---

## Decision 3: Testing Framework

### Decision

**pytest 7.4+** with **pytest-asyncio 0.21+** for async support

### Rationale

- **Industry standard**: Most widely used Python testing framework
- **Async support**: pytest-asyncio handles Discord's async patterns naturally
- **Fixture system**: Makes it easy to mock Discord interactions and bot state
- **Integration testing**: Can test command handlers end-to-end without real Discord API calls
- **Coverage integration**: Works seamlessly with coverage.py for tracking 85%/90% thresholds

### Testing Strategy

1. **Unit tests**: Services, models, validators in isolation

   - Mock Discord objects and bot state
   - Test business logic without Discord API

2. **Integration tests**: Full command workflows

   - Mock Discord client but test real command flow
   - Verify permission checks and state changes
   - Test edge cases (empty answers, concurrent submissions)

3. **Performance tests**: Concurrent answer submission benchmarks
   - Located in `perf/scripts/`
   - Measure response times under load

### Alternatives Considered

1. **unittest (standard library)**
   - **Pros**: No external dependency
   - **Cons**: More verbose, less intuitive fixtures, no built-in async support
   - **Rejected because**: pytest's simplicity and fixtures are worth the dependency

---

## Decision 4: Hosting Solution

### Decision

**pella.app** with local disk storage

### Rationale

- **Cost**: Within $5/month budget for small bot deployments
- **Local Storage**: Provides persistent local disk storage for session data files
- **Always-on**: Supports persistent services with no cold starts
- **Deployment**: Simple deployment process for Python applications
- **Memory**: Sufficient allocation for bot overhead + session state
- **Docker Support**: Container-based deployment for consistent environments

### Data Persistence Strategy

- **Storage Location**: `/data/` directory with JSON files per guild
- **File Structure**: `{guild_id}.json` containing session state
- **Write Strategy**: Write-on-change for answer submissions and resets
- **Read Strategy**: Load on first command per guild after bot restart
- **Backup**: Files persist across bot restarts, no data loss
- **Memory**: Active sessions cached in memory, synced to disk on changes

### Resource Allocation

- **Memory**: 100MB expected steady-state (in-memory cache + bot overhead), sufficient headroom
- **CPU**: Shared CPU sufficient for Discord API calls and file I/O operations
- **Storage**: Minimal disk usage (~1KB per active guild session, <100KB for 100 guilds)
- **Network**: Unlimited outbound for Discord API, sufficient for webhook interactions

### Alternatives Considered

1. **Railway.app** ($5/month for 512MB shared-cpu-1x)

   - **Pros**: Well-known platform, good documentation, 5x memory headroom
   - **Cons**: Ephemeral filesystem (in-memory only without persistent volumes), more expensive for persistent storage needs
   - **Rejected because**: pella.app provides local storage without additional cost/complexity

2. **Fly.io** ($1.94/month for 256MB shared-cpu-1x)

   - **Pros**: Cheaper, multiple regions, persistent volumes available
   - **Cons**: Less memory headroom, more complex volume configuration
   - **Rejected because**: pella.app simpler with sufficient resources at similar price point

3. **Heroku** (Eco plan: $5/month)

   - **Pros**: Well-known platform, good documentation
   - **Cons**: Ephemeral filesystem by default, requires add-ons for persistence
   - **Rejected because**: pella.app offers simpler persistence model

4. **Self-hosted VPS** (e.g., DigitalOcean $4/month droplet)

   - **Pros**: Full control, persistent storage included
   - **Cons**: Requires server management, security updates, monitoring setup, deployment pipeline
   - **Rejected because**: Spec requires "minimal setup and maintenance overhead" - managed platform preferred

5. **AWS Lambda / Cloud Functions**
   - **Pros**: True pay-per-use could be cheaper
   - **Cons**: Cold starts conflict with Discord's 3-second timeout requirement, need API Gateway, complex setup, no persistent local storage
   - **Rejected because**: Always-on requirement and 3s timeout make serverless unsuitable

### Deployment Strategy

1. **Initial setup**: Deploy to pella.app with Docker container or Python runtime
2. **Environment variables**: Configure `DISCORD_BOT_TOKEN` in pella.app dashboard
3. **Data directory**: Ensure `/data/` directory is mounted with persistent storage
4. **Data directory**: Ensure `/data/` directory is mounted with persistent storage
5. **Build**: pella.app auto-detects Python and runs `pip install -r requirements.txt`
6. **Run**: Procfile or start command specifies `python src/bot.py`
7. **Monitoring**: pella.app dashboard shows memory/CPU usage, logs

---

## Best Practices Research

### Discord Bot Patterns

1. **Slash Command Registration**: Use command tree sync during bot startup
2. **Permission Checks**: Leverage `discord.app_commands.checks.has_permissions()` decorator
3. **Error Handling**: Global error handler for command failures with user-friendly messages
4. **Rate Limiting**: Discord auto-rate-limits bot API calls; handle gracefully with backoff
5. **Graceful Shutdown**: Handle SIGTERM/SIGINT to clean up connections and flush data to disk

### Local File Storage Management

1. **Data Structure**: JSON files per guild in `/data/{guild_id}.json`
2. **Atomic Writes**: Write to temp file, then rename to ensure consistency
3. **Read-Through Cache**: Load from disk on first access, keep in memory, sync on changes
4. **Error Handling**: Handle file I/O errors (disk full, permissions) gracefully
5. **Backup Strategy**: Files are the source of truth; regular backups recommended for production

### Performance Optimization

1. **Async I/O**: All Discord interactions and file operations are async
2. **Minimize Disk I/O**: Write only on state changes (answer submit, reset), not on reads
3. **Lazy Loading**: Load guild sessions only when first command received
4. **Connection Pooling**: discord.py handles this internally
5. **Memory Management**: Unload inactive guild sessions after configurable timeout (optional future enhancement)

### Testing Discord Bots

1. **Mock Discord Objects**: Use `unittest.mock` to create fake Interaction objects
2. **Fixture Factories**: Create helper functions to generate test users, guilds, answers
3. **Async Test Patterns**: Mark tests with `@pytest.mark.asyncio` and use `await`
4. **Integration Test Structure**: Test command → service → model → storage flow

---

## Technical Context Updates

Based on research, update Technical Context in plan.md:

**Language/Version**: Python 3.14+  
**Primary Dependencies**: discord.py 2.3+, python-dotenv, pytest 7.4+, pytest-asyncio 0.21+  
**Storage**: Local disk persistence (JSON files) - session state keyed by guild_id, persisted to /data/ directory  
**Testing**: pytest with pytest-asyncio for async command testing  
**Hosting**: pella.app with local disk storage for session persistence

All NEEDS CLARIFICATION items resolved.

---

## Implementation Notes

### Startup Sequence

1. Load bot token from environment variable
2. Initialize Discord client with intents
3. **Load existing sessions from /data/ directory (if any)**
4. Register slash commands to command tree
5. Sync command tree with Discord (first run or on command changes)
6. Start bot event loop

### Session State Management with Persistence

```text
# In-memory cache
sessions = {
    "guild_id_1": {
        "user_id_1": Answer(text="answer1", timestamp=...),
        "user_id_2": Answer(text="answer2", timestamp=...)
    },
    "guild_id_2": { ... }
}

# Persistence strategy
On answer submit or update:
  1. Update in-memory session
  2. Write session to /data/{guild_id}.json

On bot startup:
  1. Scan /data/ directory
  2. Load all {guild_id}.json files into memory cache

On reset:
  1. Clear in-memory session
  2. Delete /data/{guild_id}.json file
```

### File Format

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

### Error Handling Strategy

1. **Permission errors**: "You don't have permission to use this command"
2. **Empty input**: "Please provide an answer"
3. **Discord API errors**: Log error, show "Something went wrong, please try again"
4. **Timeout errors**: Discord handles 3s timeout; ensure all commands respond within 2s

---

## Risks & Mitigations

| Risk                              | Impact | Mitigation                                     |
| --------------------------------- | ------ | ---------------------------------------------- |
| Bot token leaked                  | High   | Use environment variables, never commit token  |
| Memory exceeds 100MB              | Medium | Profile during testing, optimize data models   |
| Discord API rate limiting         | Medium | Implement exponential backoff, cache data      |
| Concurrent reset race condition   | Low    | Use asyncio.Lock for reset operation           |
| Railway.app service degradation   | Low    | Document migration path to alternative hosts   |
| Multi-server state isolation bugs | Medium | Thorough integration tests for guild_id keying |

---

## Next Steps

✅ All research complete - proceed to Phase 1 (Design & Contracts)
