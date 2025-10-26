# GitHub Actions Workflows Documentation

## Overview

This repository uses GitHub Actions for continuous integration and deployment. Three workflows automate testing, releases, and artifact distribution.

## Workflows

### 1. PR Tests (`pr-tests.yml`)

**Trigger**: Pull requests to `main` branch  
**Purpose**: Validate code changes before merge  
**Expected Duration**: 2-5 minutes

**What it does:**
#### Steps
1. Checks out code (actions/checkout@v4)
2. Sets up Python 3.13 environment
3. Installs dependencies
4. Runs pytest with coverage enforcement (≥80%)
5. Uploads coverage reports as artifacts

**Failure Scenarios:**
- **Tests fail**: Fix the failing tests in your PR
- **Coverage below 80%**: Add tests to increase coverage
- **Dependency installation fails**: Check `requirements.txt` syntax
#### Common Issues

- **Python setup fails**: Verify Python 3.13 is specified correctly

**Artifacts Produced:**
- `coverage-report` (HTML): Browse-able coverage report (retention: 30 days)
- `coverage-xml` (XML): Machine-readable coverage for external tools (retention: 30 days)

---

### 2. Release (`release.yml`)

**Trigger**: Push to `main` branch (typically from merged PR)  
**Purpose**: Create semantic versioned releases automatically  
**Expected Duration**: 1-2 minutes

**What it does:**
1. Checks out code with full Git history
2. Sets up Python 3.13 and Node.js 20
3. Runs tests as safety check (≥80% coverage)
4. Installs semantic-release
5. Analyzes commits since last release
6. Calculates new version number
7. Creates GitHub release with auto-generated notes
8. Tags repository with version

**Version Calculation:**
- `feat:` commits → Minor version bump (1.0.0 → 1.1.0)
- `fix:` commits → Patch version bump (1.0.0 → 1.0.1)
- `feat!:` or `BREAKING CHANGE:` → Major version bump (1.0.0 → 2.0.0)
- Other commits (`docs:`, `test:`, etc.) → No release

**Failure Scenarios:**
- **Tests fail on main**: CRITICAL - main should only have tested code (check PR workflow)
- **No releasable commits**: No release created (expected for `docs:`, `chore:`, etc.)
- **Token permission error**: Check GITHUB_TOKEN has `contents: write` permission
- **semantic-release error**: Check commit message format, verify `.releaserc.json`

**Outputs:**
- New GitHub Release with version tag (e.g., `v1.2.3`)
- Auto-generated release notes grouped by commit type
- Triggers Artifact workflow

---

### 3. Build Artifact (`artifact.yml`)

**Trigger**: Release published (from Release workflow)  
**Purpose**: Create production-ready deployment artifact  
**Expected Duration**: 30-60 seconds

**What it does:**
1. Checks out code at release tag
2. Creates compressed tarball with production files only
3. Excludes tests, dev tools, documentation (per `.github/.artifactignore`)
4. Verifies artifact contents
5. Uploads artifact to release
6. Appends deployment instructions to release notes

**Artifact Contents:**
- ✅ Included: `src/`, `requirements.txt`, `.env.example`, `Procfile`, `config/`
- ❌ Excluded: `tests/`, `.venv/`, `.git/`, `.github/`, `docs/`, `specs/`, dev tools

**Failure Scenarios:**
- **Tar creation fails**: Check `.github/.artifactignore` patterns syntax
- **Upload fails**: Check release exists and token has `contents: write` permission
- **Artifact too large**: Review exclusion patterns, check for unexpected large files

**Artifacts Produced:**
- `swtriviabot-vX.Y.Z.tar.gz`: Production-ready deployment archive (attached to release)
- Deployment instructions appended to release notes

---

## Workflow Monitoring

### Check Workflow Status

1. **GitHub Actions Tab**: `https://github.com/ncerny/swtriviabot/actions`
   - View all workflow runs
   - Filter by workflow name or branch
   - Download artifacts (coverage reports)

2. **PR Page**: Status checks appear at bottom of PR
   - Green checkmark = tests passed
   - Red X = tests failed (click Details to see logs)
   - Yellow circle = workflow running

3. **Releases Page**: `https://github.com/ncerny/swtriviabot/releases`
   - View all releases with artifacts
   - Download production artifacts
   - Read auto-generated release notes

### Email Notifications

GitHub sends email notifications for:
- ❌ Workflow failures on your commits
- ✅ Successful workflow runs (if configured in settings)

Configure in: GitHub Settings → Notifications → Actions

### Status Badges (README.md)

The README displays live workflow status:
- [![PR Tests](badge-url)](workflow-url)
- [![Release](badge-url)](workflow-url)
- [![Build Artifact](badge-url)](workflow-url)

---

## Performance Budgets

All workflows have timeout limits to prevent hanging:

| Workflow | Timeout | Expected | Budget Met? |
|----------|---------|----------|-------------|
| PR Tests | 10 min  | 2-5 min  | ✅ Yes      |
| Release  | 15 min  | 1-2 min  | ✅ Yes      |
| Artifact | 10 min  | 0.5-1 min| ✅ Yes      |

**If a workflow exceeds timeout:**
- Workflow is automatically cancelled
- Check logs for hanging processes
- Review dependency installation (may need caching fixes)
- Consider optimizing test suite or exclusion patterns

---

## Troubleshooting

### PR Tests Keep Failing

1. **Run tests locally first**: `pytest --cov=src --cov-fail-under=80`
2. **Check coverage**: Ensure ≥80% coverage with `pytest --cov=src --cov-report=term-missing`
3. **Review logs**: Click "Details" on failed status check in PR
4. **Common issues**:
   - Missing test fixtures
   - Incorrect Python version (must be 3.13+)
   - Import errors (check `requirements.txt`)

### Release Not Created After Merge

1. **Check commit messages**: Must use conventional commits (`feat:`, `fix:`, etc.)
2. **View Release workflow logs**: Actions tab → Release workflow → Latest run
3. **No releasable commits?**: `docs:`, `test:`, `chore:` don't trigger releases
4. **Common issues**:
   - Commit message format incorrect
   - Only docs/test commits merged
   - semantic-release configuration error

### Artifact Not Attached to Release

1. **Verify release exists**: Check Releases page
2. **Check Artifact workflow logs**: Actions tab → Build Artifact workflow
3. **Review `.artifactignore`**: Ensure patterns are correct
4. **Common issues**:
   - Release workflow failed (artifact depends on it)
   - Token permissions insufficient
   - Tar exclusion pattern syntax error

### Workflow Stuck/Hanging

1. **Cancel workflow**: Actions tab → Select run → Cancel workflow
2. **Check timeout settings**: All workflows have 10-15 min timeouts
3. **Review logs**: Look for hanging processes or stuck installations
4. **Common causes**:
   - Network issues downloading dependencies
   - Test hanging (add `pytest -x` for fail-fast)
   - Infinite loop in code

---

## Local Development

Test workflows locally before pushing:

```bash
# Run tests with coverage (matches PR workflow)
pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80

# Validate commit message format
git log -1 --pretty=%B | grep -E "^(feat|fix|docs|test|refactor|perf|chore)(\(.+\))?: .+"

# Simulate artifact creation
tar --exclude-from=.github/.artifactignore -czf test-artifact.tar.gz .
tar -tzf test-artifact.tar.gz | head -n 50  # Preview contents
```

---

## Maintenance

### Update Workflow Dependencies

When updating workflow actions (e.g., `actions/checkout@v4` → `@v5`):

1. Review action changelog for breaking changes
2. Update in all workflow files
3. Test with PR to verify workflows still pass
4. Document changes in commit message: `chore: update GitHub Actions to v5`

### Modify Coverage Threshold

Currently set to 80% in:
- `.coveragerc` (Python pytest-cov)
- `pr-tests.yml` (workflow enforcement)
- `release.yml` (safety check)

To change:
1. Update `fail_under` in `.coveragerc`
2. Update `--cov-fail-under` in workflow files
3. Use conventional commit: `chore: adjust coverage threshold to 85%`

### Add New Status Checks

To require additional checks before PR merge:

1. Add check to `pr-tests.yml` (e.g., linting, type checking)
2. Update branch protection rules to require new check
3. Document in README.md Contributing section
