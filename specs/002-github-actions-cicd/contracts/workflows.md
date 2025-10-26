# Workflow Contracts: GitHub Actions CI/CD

**Feature**: 002-github-actions-cicd  
**Date**: October 25, 2025

## Overview

This document defines the contracts (inputs, outputs, behaviors) for each GitHub Actions workflow. These are infrastructure contracts, not REST/GraphQL APIs. Each workflow is triggered by GitHub events and produces observable outcomes.

---

## Workflow 1: PR Testing (`pr-tests.yml`)

### Contract

**Trigger Events**:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main]
```

**Inputs** (from GitHub context):

- `github.event.pull_request.number`: PR number (integer)
- `github.event.pull_request.head.sha`: Commit SHA to test (string)
- `github.event.pull_request.head.ref`: Branch name (string)
- `github.repository`: Repository name (string, format: `owner/repo`)

**Environment Requirements**:

- Runner: `ubuntu-latest`
- Python: `3.14`
- Disk space: ~500MB (dependencies + cache)
- Network: Public internet (for pip install)

**Execution Steps**:

1. Checkout code at PR commit SHA
2. Setup Python 3.14
3. Restore pip cache (if available)
4. Install dependencies from `requirements.txt`
5. Run pytest with coverage (`pytest --cov=src --cov-report=term --cov-report=html --cov-fail-under=80 -v`)
6. Upload coverage report as artifact
7. Update PR status check

**Outputs**:

- **PR Status Check**: `✅ Tests Passed` or `❌ Tests Failed`
- **Status Details**:
  - Total tests run (integer)
  - Tests passed (integer)
  - Tests failed (integer)
  - Coverage percentage (float, format: `86.92%`)
  - Execution time (duration, format: `2m 34s`)
- **Artifacts**:
  - `coverage-report`: HTML coverage report (retained for 7 days)
  - `test-results`: pytest JSON output (retained for 7 days)

**Success Criteria** (all must be true):

- All tests pass (exit code 0)
- Coverage ≥ 80% (enforced by `--cov-fail-under=80`)
- Execution time < 5 minutes (SC-001)
- No Python syntax errors (linting would be additional step)

**Failure Conditions**:

- Any test fails → `❌ Tests Failed`
- Coverage < 80% → `❌ Coverage Below Threshold (XX.X%)`
- Timeout (>10 minutes) → `❌ Tests Timed Out`
- Dependency installation fails → `❌ Setup Failed`

**Side Effects**:

- Updates PR status check (visible in PR UI)
- Creates workflow run record (retained 90 days per FR-011)
- Uploads coverage artifacts (retained 7 days)

**Performance Guarantees**:

- Cold run (no cache): < 3 minutes
- Warm run (cache hit): < 1 minute
- Both meet SC-001 requirement (< 5 minutes)

**Example Status Check Output**:

```
✅ All Checks Passed

Tests: 67 passed, 0 failed
Coverage: 86.92% (threshold: 80%)
Duration: 1m 23s

View detailed coverage report in artifacts.
```

---

## Workflow 2: Release Creation (`release.yml`)

### Contract

**Trigger Events**:

```yaml
on:
  push:
    branches: [main]
```

**Inputs** (from GitHub context):

- `github.event.commits`: Array of commits pushed to main
- `github.sha`: Commit SHA to release (string)
- `github.ref`: Git ref (string, always `refs/heads/main`)

**Environment Requirements**:

- Runner: `ubuntu-latest`
- Node.js: `20.x` (for semantic-release)
- Git: Available (for tagging)
- Network: Public internet (for npm, GitHub API)

**Execution Steps**:

1. Checkout code with full history (`fetch-depth: 0`)
2. Setup Node.js 20.x
3. Install semantic-release and plugins
4. Run semantic-release (analyzes commits, determines version, creates release)
5. If release created, trigger artifact workflow

**Outputs**:

- **GitHub Release**: Created with auto-generated version and notes
- **Git Tag**: Created (format: `v{major}.{minor}.{patch}`)
- **Release Notes**: Markdown-formatted changelog grouped by commit type
- **Workflow Output Variables**:
  - `new_release_published`: Boolean (true if release created)
  - `new_release_version`: Version string (e.g., `1.3.0`)
  - `new_release_git_tag`: Tag string (e.g., `v1.3.0`)

**Version Determination Logic**:

Semantic-release scans commits since last release and applies these rules:

| Commit Type(s)                     | Version Bump | Example Transition            |
| ---------------------------------- | ------------ | ----------------------------- |
| `feat:` only                       | Minor        | `v1.2.3` → `v1.3.0`           |
| `fix:` only                        | Patch        | `v1.2.3` → `v1.2.4`           |
| Any `BREAKING CHANGE:` or `feat!:` | Major        | `v1.2.3` → `v2.0.0`           |
| `chore:`, `docs:`, etc. only       | None         | (no release)                  |
| Mixed `feat:` + `fix:`             | Minor        | `v1.2.3` → `v1.3.0` (highest) |

**Release Notes Format**:

```markdown
# v1.3.0 (2025-10-25)

## Features

- feat: add metrics command for performance monitoring ([abc1234](commit-link))
- feat: implement persistent button views ([def5678](commit-link))

## Bug Fixes

- fix: resolve button interaction error after restart ([ghi9012](commit-link))

## Chores

- chore: update dependencies ([jkl3456](commit-link))
```

**Success Criteria**:

- Release created within 2 minutes of push (SC-004)
- Version follows semantic versioning spec
- All commits since last release included in notes
- Git tag matches release version

**Failure Conditions**:

- Non-conventional commits → No release (semantic-release skips)
- GitHub API rate limit → Retry with exponential backoff
- Network error → Workflow fails, manual retry needed
- Duplicate tag → Error (indicates race condition)

**Side Effects**:

- Creates Git tag in repository
- Creates GitHub Release (public)
- Sends GitHub notifications to watchers
- Triggers dependent workflows (artifact upload)

**Performance Guarantees**:

- Execution time < 2 minutes (SC-004)
- Commit analysis < 30 seconds (even with 1000+ commits)

**Special Cases**:

**First Release** (no previous tags):

- Semantic-release detects no prior version
- Creates `v1.0.0` as initial release
- Includes all commits in repository history
- Satisfies FR-015 requirement

**No Release Needed**:

- Only non-release commits (chore:, docs:, style:, refactor:, test:)
- Workflow completes successfully but skips release creation
- Sets `new_release_published: false`

**Example Release Output**:

```
✅ Release Created

Version: v1.3.0
Previous: v1.2.3
Commits: 5 (3 features, 2 fixes)
Tag: v1.3.0
Duration: 1m 12s

View release: https://github.com/ncerny/swtriviabot/releases/tag/v1.3.0
```

---

## Workflow 3: Artifact Creation (`artifact.yml`)

### Contract

**Trigger Events**:

```yaml
on:
  release:
    types: [published]
```

**Inputs** (from GitHub context):

- `github.event.release.id`: Release ID (integer)
- `github.event.release.tag_name`: Version tag (string, e.g., `v1.3.0`)
- `github.event.release.upload_url`: URL for uploading assets (string)

**Environment Requirements**:

- Runner: `ubuntu-latest`
- Disk space: ~200MB (for checkout + artifact creation)
- Network: Public internet (for GitHub API)

**Execution Steps**:

1. Checkout code at release tag
2. Create production artifact (tar.gz with selected files)
3. Calculate SHA-256 checksum
4. Create checksum file
5. Upload artifact to release
6. Upload checksum to release

**File Selection Rules**:

**INCLUDE** (must be present in artifact):

```
src/                    # Application source code (all .py files)
requirements.txt        # Production dependencies
.env.example           # Configuration template
README.md              # Documentation
Procfile               # Deployment configuration
config/                # Runtime configuration files
```

**EXCLUDE** (must NOT be in artifact):

```
tests/                 # Test suite
htmlcov/              # Coverage reports
.pytest_cache/        # Pytest cache
.git/                 # Version control data
.github/              # CI/CD workflows
.venv/                # Virtual environment
specs/                # Feature specifications
perf/                 # Performance benchmarks
.coverage             # Coverage database
*.pyc                 # Python bytecode
__pycache__/          # Python cache
.DS_Store             # macOS metadata
.vscode/              # Editor config
.specify/             # Speckit data
waivers.md            # Governance waivers
pyproject.toml        # Development config
pytest.ini            # Test config
.coveragerc           # Coverage config
.flake8               # Linter config
```

**Artifact Naming**:

- Format: `swtriviabot-{tag_name}.tar.gz`
- Example: `swtriviabot-v1.3.0.tar.gz`

**Checksum File**:

- Format: `swtriviabot-{tag_name}.tar.gz.sha256`
- Content: `{sha256_hash}  swtriviabot-{tag_name}.tar.gz`
- Example: `a3f5b8... swtriviabot-v1.3.0.tar.gz`

**Outputs**:

- **Release Asset 1**: Production artifact tarball
  - Name: `swtriviabot-v{version}.tar.gz`
  - Content-Type: `application/gzip`
  - Size: 30-50% smaller than full repository (SC-006)
- **Release Asset 2**: SHA-256 checksum file
  - Name: `swtriviabot-v{version}.tar.gz.sha256`
  - Content-Type: `text/plain`
  - Size: ~100 bytes

**Success Criteria**:

- Artifact size < 2GB (GitHub limit)
- Artifact size 30-50% of repository (SC-006)
- All required files present
- No excluded files present
- Checksum calculation succeeds
- Upload completes successfully
- Execution time < 1 minute (implied)

**Validation Steps** (performed by workflow):

1. Verify `src/` directory exists in artifact
2. Verify `requirements.txt` exists in artifact
3. Verify `tests/` directory does NOT exist in artifact
4. Verify artifact size is reasonable (not empty, not too large)

**Failure Conditions**:

- Missing required file → `❌ Artifact incomplete`
- Excluded file found → `❌ Artifact contains test files`
- Artifact too large (>2GB) → `❌ Artifact exceeds GitHub limit`
- Upload fails → `❌ Upload failed` (retries automatically)
- Checksum calculation fails → `❌ Checksum error`

**Side Effects**:

- Uploads artifact to GitHub Release (public download)
- Uploads checksum file to release
- Updates release asset list (visible in release page)

**Performance Guarantees**:

- Artifact creation < 30 seconds
- Upload time < 30 seconds (depends on artifact size)
- Total time < 1 minute

**Deployment Usage**:

```bash
# Download artifact
wget https://github.com/ncerny/swtriviabot/releases/download/v1.3.0/swtriviabot-v1.3.0.tar.gz

# Verify checksum
wget https://github.com/ncerny/swtriviabot/releases/download/v1.3.0/swtriviabot-v1.3.0.tar.gz.sha256
sha256sum -c swtriviabot-v1.3.0.tar.gz.sha256

# Extract
tar -xzf swtriviabot-v1.3.0.tar.gz

# Deploy
cd swtriviabot-v1.3.0/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with production secrets
python -m src.bot
```

**Example Artifact Output**:

```
✅ Artifact Created

File: swtriviabot-v1.3.0.tar.gz
Size: 1.2 MB (45% reduction from 2.2 MB)
Checksum: a3f5b8c7d9e1f...
Files: 42
Duration: 38s

Download: https://github.com/ncerny/swtriviabot/releases/download/v1.3.0/swtriviabot-v1.3.0.tar.gz
```

---

## Inter-Workflow Dependencies

```
PR Workflow (pr-tests.yml)
    ↓ (independent, no triggers)

Merge to main
    ↓ (triggers)

Release Workflow (release.yml)
    ↓ (on success, triggers via release event)

Artifact Workflow (artifact.yml)
```

**Dependency Rules**:

- PR workflow is **independent** (does not trigger other workflows)
- Release workflow **triggers** artifact workflow (via `release.published` event)
- Artifact workflow **depends on** release workflow (requires release ID and tag)

**Failure Isolation**:

- If PR workflow fails → PR blocked, other workflows unaffected
- If release workflow fails → No release created, artifact workflow not triggered
- If artifact workflow fails → Release exists without artifact, can be manually re-run

---

## Monitoring and Observability

### Workflow Run Status

Each workflow run is tracked by GitHub Actions with:

- **Status**: queued, in_progress, completed
- **Conclusion**: success, failure, cancelled, skipped
- **Duration**: Start and end timestamps
- **Logs**: Full console output (retained 90 days)

### Key Metrics (available via GitHub Actions API)

- **Workflow Run Duration**: Time from start to completion
- **Success Rate**: Percentage of successful runs
- **Failure Rate**: Percentage of failed runs
- **Queue Time**: Time waiting for available runner
- **Retry Count**: Number of automatic retries

### Alerts

GitHub provides native alerts for:

- Workflow failures (email notification to committer)
- Long-running workflows (>10 minutes)
- Workflow disabled (too many failures)

---

## Security Constraints

### Permissions

Each workflow declares minimum required permissions:

**PR Testing Workflow**:

```yaml
permissions:
  contents: read # Read repository code
  pull-requests: write # Update PR status checks
  actions: read # Read workflow status
```

**Release Workflow**:

```yaml
permissions:
  contents: write # Create tags and releases
  actions: read # Read workflow status
```

**Artifact Workflow**:

```yaml
permissions:
  contents: write # Upload release assets
  actions: read # Read workflow status
```

### Secrets

- **GITHUB_TOKEN**: Auto-provided, scoped to repository, expires after workflow run
- **No custom secrets required**: Feature uses only GitHub platform features

### Network Access

- Workflows have **outbound** internet access (required for pip, npm)
- Workflows have **no inbound** access (GitHub-hosted runners are ephemeral)
- All external calls go through GitHub's infrastructure

---

## Error Handling

### Retry Logic

GitHub Actions provides automatic retries for:

- Network failures (3 retries with exponential backoff)
- API rate limits (waits and retries)
- Transient errors (automatically detects and retries)

### Manual Intervention

If workflow fails after retries:

1. Developer reviews workflow logs
2. Identifies root cause (test failure, coverage drop, etc.)
3. Fixes issue in new commit
4. Pushes fix (triggers workflow again)

### Rollback

If bad release is created:

1. Tag and release remain (for audit trail)
2. New fix commit is pushed to main
3. Triggers new release with incremented version
4. Old release marked as "not recommended" (manual)

---

## Compliance with Requirements

### Functional Requirements

- **FR-001**: ✅ PR workflow executes all tests automatically
- **FR-002**: ✅ Coverage check blocks merge if <80%
- **FR-003**: ✅ PR status check displays results in UI
- **FR-004**: ✅ Release workflow triggers on main push
- **FR-005**: ✅ Semantic-release determines version from commits
- **FR-006**: ✅ Release notes auto-generated and grouped
- **FR-007**: ✅ Artifact workflow creates tar.gz
- **FR-008**: ✅ Artifact includes all production files
- **FR-009**: ✅ Artifact excludes test files
- **FR-010**: ✅ Releases tagged with semantic versions
- **FR-011**: ✅ GitHub Actions retains logs for 90 days
- **FR-012**: ✅ Tests run in Python 3.14 environment
- **FR-013**: ✅ Pytest `-x` flag enables fail-fast
- **FR-014**: ✅ Workflow output provides actionable errors
- **FR-015**: ✅ Semantic-release handles first release (v1.0.0)

### Success Criteria

- **SC-001**: ✅ Test results < 5 minutes
- **SC-002**: ✅ 100% of PRs run tests (enforced by workflow)
- **SC-003**: ✅ Tests block merge on failure
- **SC-004**: ✅ Releases created < 2 minutes
- **SC-005**: ✅ Semantic-release ensures correct versioning
- **SC-006**: ✅ Artifact 30-50% smaller (validated in workflow)
- **SC-007**: ✅ Artifact deployable in <5 minutes (documented process)
- **SC-008**: ✅ Release notes human-readable and accurate
- **SC-009**: ✅ Workflow errors include context and next steps
- **SC-010**: ✅ GitHub Actions provides 99%+ uptime SLA
