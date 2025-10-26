# Research: GitHub Actions CI/CD Workflows

**Feature**: 002-github-actions-cicd  
**Date**: October 25, 2025  
**Status**: Complete

## Overview

This document consolidates research findings for implementing CI/CD workflows using GitHub Actions. All technical unknowns from the planning phase have been resolved through investigation of GitHub Actions best practices, semantic versioning tools, and artifact optimization strategies.

## Research Tasks Completed

### 1. GitHub Actions Workflow Design for Python Projects

**Question**: What is the optimal GitHub Actions workflow structure for Python projects with pytest?

**Decision**: Use separate workflow files for different triggers (PR testing vs. release) to maintain clarity and allow independent configuration.

**Rationale**:

- **Separation of concerns**: PR workflow focuses on testing/validation; release workflow focuses on versioning/publishing
- **Performance**: Parallel execution of independent workflows
- **Maintainability**: Easier to modify one workflow without affecting others
- **GitHub Actions best practice**: Recommended pattern in official documentation

**Key Components**:

```yaml
# PR Testing Workflow (.github/workflows/pr-tests.yml)
- Trigger: pull_request (opened, synchronize, reopened)
- Python setup: actions/setup-python@v5
- Dependency caching: actions/cache@v4 for pip
- Test execution: pytest with coverage report
- Coverage enforcement: fail if <80%
- Fast fail: -x flag to stop on first failure
```

**Alternatives Considered**:

- Single monolithic workflow with conditional logic: Rejected due to complexity and harder debugging
- Matrix strategy for multiple Python versions: Not needed (project requires only 3.14+)

### 2. Semantic Versioning Automation

**Question**: How to automatically determine semantic version numbers from conventional commits?

**Decision**: Use `cycjimmy/semantic-release-action@v4` with conventional-changelog plugin.

**Rationale**:

- **Industry standard**: Most widely adopted semantic versioning automation tool
- **Conventional commits support**: Parses feat:, fix:, BREAKING CHANGE: automatically
- **Release notes generation**: Automatically groups commits by type
- **GitHub integration**: Native support for creating GitHub releases
- **Zero configuration**: Works with default conventional commit format

**Version Bump Rules**:
| Commit Type | Example | Version Change |
|-------------|---------|----------------|
| `feat:` | `feat: add new command` | Minor (1.2.0 → 1.3.0) |
| `fix:` | `fix: resolve bug` | Patch (1.2.0 → 1.2.1) |
| `feat!:` or `BREAKING CHANGE:` | `feat!: redesign API` | Major (1.2.0 → 2.0.0) |
| `chore:`, `docs:`, `style:` | `chore: update deps` | No release |

**Alternatives Considered**:

- Manual version tagging: Rejected (error-prone, requires human intervention)
- Custom script parsing git log: Rejected (reinventing the wheel, maintenance burden)
- GitHub's auto-generated release notes only: Rejected (doesn't handle versioning logic)

### 3. Production Artifact Optimization

**Question**: How to create optimized deployment artifacts excluding test files and dev dependencies?

**Decision**: Use `tar` with explicit include patterns via `.github/.artifactignore` pattern.

**Rationale**:

- **Control**: Explicit inclusion ensures only necessary files
- **Size reduction**: Excludes tests/, htmlcov/, .pytest_cache/, .git/, .venv/
- **Reproducibility**: Documented include list prevents accidental omissions
- **Native GitHub Actions support**: actions/upload-artifact@v4 handles compression automatically

**Files to Include**:

```
src/                    # Application code
requirements.txt        # Production dependencies only
.env.example           # Configuration template
README.md              # Documentation
Procfile               # Deployment configuration
config/                # Runtime configuration
```

**Files to Exclude**:

```
tests/                 # Test suite
htmlcov/              # Coverage reports
.pytest_cache/        # Pytest cache
.git/                 # Version control
.venv/                # Virtual environment
.github/              # CI/CD workflows
specs/                # Feature specifications
perf/                 # Benchmark scripts
.coverage             # Coverage database
*.pyc, __pycache__/   # Python bytecode
```

**Expected Size Reduction**: 40-60% (based on typical Python project ratios)

**Alternatives Considered**:

- Docker image: Rejected (overkill for simple bot, adds complexity)
- Git archive: Rejected (includes everything, no selective exclusion)
- pip wheel distribution: Rejected (bot is not a library, needs config files)

### 4. Test Execution Performance

**Question**: How to optimize test execution time while maintaining coverage requirements?

**Decision**: Use pytest with `-x` (fail-fast), `--maxfail=5`, and `--tb=short` flags; leverage GitHub Actions caching for dependencies.

**Rationale**:

- **Fail-fast (-x)**: Stops on first failure, saves time on broken builds (aligns with FR-013)
- **Dependency caching**: actions/cache@v4 reduces pip install time from ~60s to ~5s on cache hit
- **Parallel execution**: pytest-xdist not needed (67 tests run in <30s sequentially)
- **Coverage calculation**: pytest-cov integrates seamlessly without performance penalty

**Performance Targets**:

- Cold run (no cache): <3 minutes (dependencies + tests)
- Warm run (cache hit): <1 minute (tests only)
- Both meet SC-001 requirement of <5 minutes

**Alternatives Considered**:

- pytest-xdist for parallel test execution: Not needed (current test count is small)
- Separate coverage calculation: Rejected (adds overhead, pytest-cov is efficient)
- Skip coverage on PR commits: Rejected (violates FR-002 requirement)

### 5. GitHub Actions Runner Configuration

**Question**: Which GitHub Actions runner should be used and what setup is required?

**Decision**: Use `ubuntu-latest` runner with Python 3.14 setup via actions/setup-python@v5.

**Rationale**:

- **Compatibility**: ubuntu-latest matches production deployment environment
- **Python version support**: actions/setup-python@v5 supports Python 3.14
- **Cost**: Free for public repos, included in GitHub free tier for private repos
- **Reliability**: GitHub-hosted runners maintained by GitHub, no self-hosting needed

**Runner Configuration**:

```yaml
runs-on: ubuntu-latest
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: '3.14'
  - uses: actions/cache@v4
    with:
      path: ~/.cache/pip
      key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

**Alternatives Considered**:

- Self-hosted runner: Rejected (unnecessary complexity, maintenance burden)
- Windows runner: Rejected (bot targets Linux deployment)
- Matrix testing across Python versions: Rejected (project locked to 3.14+)

### 6. Error Handling and Notifications

**Question**: How should workflow failures be communicated to developers?

**Decision**: Use GitHub Actions' native PR status checks with detailed step outputs; optionally add job summary via $GITHUB_STEP_SUMMARY.

**Rationale**:

- **Native integration**: PR status checks appear directly in GitHub UI (meets FR-003)
- **Actionable messages**: Step-level output shows exact command failures (meets FR-014)
- **No external dependencies**: Doesn't require Slack/email integration
- **Job summaries**: Markdown-formatted summaries provide additional context

**Failure Output Format**:

```markdown
## ❌ Test Failure

**Failed Test**: tests/integration/test_post_question.py::test_modal_submission
**Error**: AssertionError: Expected status 200, got 500
**Coverage**: 78.5% (below 80% threshold)

**Action Required**: Fix failing test or update coverage exclusions
```

**Alternatives Considered**:

- Email notifications: Rejected (GitHub already sends emails for failed checks)
- Slack integration: Rejected (adds external dependency, not required)
- Issue auto-creation: Rejected (too noisy for transient failures)

### 7. First Release Handling

**Question**: How to handle the initial release when no previous version exists?

**Decision**: Configure semantic-release with `initialVersion: '1.0.0'` in releaserc config.

**Rationale**:

- **Conventional**: 1.0.0 is standard for first stable release
- **Explicit**: Prevents confusion about starting point
- **Semantic-release support**: Built-in handling for initial release (meets FR-015)

**Configuration**:

```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/github"
  ],
  "repositoryUrl": "https://github.com/ncerny/swtriviabot",
  "tagFormat": "v${version}"
}
```

**Alternatives Considered**:

- Start at 0.1.0: Rejected (implies beta status)
- Manual first tag: Rejected (defeats purpose of automation)

## Implementation Dependencies

### GitHub Actions

- **actions/checkout@v4**: Repository checkout
- **actions/setup-python@v5**: Python environment setup
- **actions/cache@v4**: Dependency caching
- **actions/upload-artifact@v4**: Artifact upload to release
- **cycjimmy/semantic-release-action@v4**: Semantic versioning and release creation

### Node.js Dependencies (for semantic-release)

Semantic-release runs on Node.js within the GitHub Actions runner:

```json
{
  "devDependencies": {
    "semantic-release": "^22.0.0",
    "@semantic-release/commit-analyzer": "^11.0.0",
    "@semantic-release/release-notes-generator": "^12.0.0",
    "@semantic-release/github": "^9.0.0"
  }
}
```

### Python Dependencies (existing)

No new Python dependencies required. Existing dependencies used:

- pytest 8.4.2+
- pytest-cov 7.0.0+
- pytest-asyncio 1.2.0+

## Security Considerations

### Secrets and Permissions

- **GITHUB_TOKEN**: Automatically provided by GitHub Actions with required permissions
- **Permissions needed**:
  - `contents: write` - Create releases and tags
  - `pull-requests: write` - Update PR status checks
  - `actions: read` - Read workflow status

### Dependency Security

- **Pin action versions**: Use @v4, @v5 tags (not @main) for reproducibility
- **Dependabot**: GitHub automatically monitors action versions
- **No custom scripts**: Use official GitHub actions to minimize attack surface

## Performance Benchmarks

Based on similar projects and GitHub Actions documentation:

| Workflow | Cold Run  | Warm Run (Cache Hit) | Success Criteria    |
| -------- | --------- | -------------------- | ------------------- |
| PR Tests | 2-3 min   | 45-60 sec            | <5 min (SC-001) ✅  |
| Release  | 1-2 min   | 1-2 min              | <2 min (SC-004) ✅  |
| Artifact | 30-45 sec | 30-45 sec            | <1 min (implied) ✅ |

## Workflow Interaction Diagram

```
Pull Request Created/Updated
    ↓
[pr-tests.yml] Triggered
    ├─ Checkout code
    ├─ Setup Python 3.14
    ├─ Restore pip cache (or install)
    ├─ Run pytest with coverage
    ├─ Check coverage ≥80%
    └─ Update PR status (✅ or ❌)

Pull Request Merged to Main
    ↓
[release.yml] Triggered
    ├─ Checkout code
    ├─ Setup Node.js (for semantic-release)
    ├─ Analyze commits (conventional commits)
    ├─ Determine version bump
    ├─ Create Git tag (e.g., v1.2.3)
    ├─ Generate release notes
    ├─ Create GitHub Release
    └─ Trigger artifact workflow

[artifact.yml] Triggered by Release
    ├─ Checkout code at release tag
    ├─ Create tarball with selected files
    ├─ Compress (gzip)
    ├─ Calculate checksum (sha256)
    └─ Upload to GitHub Release
```

## Open Questions

None. All technical decisions resolved.

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Release Documentation](https://semantic-release.gitbook.io/)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Python Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
