# Quickstart: GitHub Actions CI/CD Workflows

**Feature**: 002-github-actions-cicd  
**Date**: October 25, 2025  
**Audience**: Developers implementing the CI/CD workflows

## Overview

This quickstart guide provides step-by-step instructions for implementing the GitHub Actions CI/CD workflows for automated testing, release creation, and artifact generation. Follow these steps in order.

## Prerequisites

- [x] Repository: `ncerny/swtriviabot` (already exists)
- [x] GitHub Actions enabled (free for public repos)
- [x] Python 3.14+ project with pytest configured (already established)
- [x] Existing test suite with 67 tests (already established)
- [x] Coverage configuration in `.coveragerc` (already established)
- [x] Main branch protection (recommended, configure in GitHub settings)

## Implementation Steps

### Phase 1: PR Testing Workflow (Priority P1)

**Goal**: Automatically run tests on every pull request.

**Files to Create**:

1. `.github/workflows/pr-tests.yml`

**Implementation**:

```yaml
# .github/workflows/pr-tests.yml
name: PR Tests

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main]

permissions:
  contents: read
  pull-requests: write
  actions: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.14
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests with coverage
        run: |
          python -m pytest tests/ \
            --cov=src \
            --cov-report=term-missing \
            --cov-report=html \
            --cov-fail-under=80 \
            -v \
            -x

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 7

      - name: Comment coverage on PR
        if: github.event_name == 'pull_request'
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ github.token }}
```

**Test the Workflow**:

1. Create a new branch: `git checkout -b test-ci-workflow`
2. Make a trivial change (e.g., add comment to README)
3. Commit: `git commit -am "test: verify PR testing workflow"`
4. Push: `git push -u origin test-ci-workflow`
5. Create PR on GitHub
6. Verify workflow runs and shows test results

**Expected Outcome**:

- ✅ Workflow runs automatically
- ✅ All 67 tests pass
- ✅ Coverage shows 86.92% (above 80% threshold)
- ✅ PR shows green checkmark
- ✅ Execution completes in <2 minutes (cache hit)

---

### Phase 2: Release Workflow (Priority P2)

**Goal**: Automatically create releases when PRs are merged to main.

**Files to Create**:

1. `.github/workflows/release.yml`
2. `.releaserc.json` (semantic-release configuration)
3. `package.json` (for semantic-release dependencies)

**Step 1: Create semantic-release configuration**

```json
// .releaserc.json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/github",
      {
        "assets": []
      }
    ]
  ],
  "repositoryUrl": "https://github.com/ncerny/swtriviabot",
  "tagFormat": "v${version}"
}
```

**Step 2: Create package.json for Node.js dependencies**

```json
// package.json
{
  "name": "swtriviabot-release",
  "version": "1.0.0",
  "private": true,
  "description": "Release automation for SWTriviaBot",
  "devDependencies": {
    "semantic-release": "^22.0.0",
    "@semantic-release/commit-analyzer": "^11.0.0",
    "@semantic-release/release-notes-generator": "^12.0.0",
    "@semantic-release/github": "^9.0.0"
  }
}
```

**Step 3: Create release workflow**

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  actions: read

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Full history for semantic-release

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install semantic-release
        run: npm ci

      - name: Run semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx semantic-release
```

**Step 4: Update .gitignore**

Add to `.gitignore`:

```
node_modules/
package-lock.json
```

**Test the Workflow**:

1. Ensure test-ci-workflow PR from Phase 1 has passed tests
2. Merge PR to main (use "Squash and merge" for clean commit)
3. Ensure commit message follows conventional commits: `feat: add CI/CD workflows`
4. Observe GitHub Actions on main branch
5. Verify release is created

**Expected Outcome**:

- ✅ Workflow triggers on merge to main
- ✅ Semantic-release analyzes commits
- ✅ If this is first release: creates v1.0.0
- ✅ If not: creates appropriate version bump (e.g., v1.1.0 for feat:)
- ✅ Release notes auto-generated
- ✅ Execution completes in <2 minutes

---

### Phase 3: Artifact Workflow (Priority P3)

**Goal**: Create production-ready artifacts attached to each release.

**Files to Create**:

1. `.github/workflows/artifact.yml`
2. `.artifactignore` (optional, documents exclusions)

**Step 1: Create artifact ignore file**

```
# .artifactignore
# Files excluded from production artifact
tests/
htmlcov/
.pytest_cache/
.git/
.github/
.venv/
specs/
perf/
.coverage
*.pyc
__pycache__/
.DS_Store
.vscode/
.specify/
waivers.md
pyproject.toml
pytest.ini
.coveragerc
.flake8
```

**Step 2: Create artifact workflow**

```yaml
# .github/workflows/artifact.yml
name: Build Artifact

on:
  release:
    types: [published]

permissions:
  contents: write
  actions: read

jobs:
  artifact:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout code at release tag
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.release.tag_name }}

      - name: Create production artifact
        run: |
          mkdir -p dist

          # Create tarball with production files
          tar -czf dist/swtriviabot-${{ github.event.release.tag_name }}.tar.gz \
            --exclude-vcs \
            --exclude='tests' \
            --exclude='htmlcov' \
            --exclude='.pytest_cache' \
            --exclude='.github' \
            --exclude='specs' \
            --exclude='perf' \
            --exclude='.coverage' \
            --exclude='*.pyc' \
            --exclude='__pycache__' \
            --exclude='.venv' \
            --exclude='.specify' \
            --exclude='waivers.md' \
            --exclude='pyproject.toml' \
            --exclude='pytest.ini' \
            --exclude='.coveragerc' \
            --exclude='.flake8' \
            --exclude='.DS_Store' \
            --exclude='.vscode' \
            src/ \
            requirements.txt \
            .env.example \
            README.md \
            Procfile \
            config/

      - name: Calculate checksum
        run: |
          cd dist
          sha256sum swtriviabot-${{ github.event.release.tag_name }}.tar.gz > \
            swtriviabot-${{ github.event.release.tag_name }}.tar.gz.sha256

      - name: Display artifact info
        run: |
          ls -lh dist/
          echo "Artifact contents:"
          tar -tzf dist/swtriviabot-${{ github.event.release.tag_name }}.tar.gz | head -20

      - name: Upload artifact to release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/swtriviabot-${{ github.event.release.tag_name }}.tar.gz
            dist/swtriviabot-${{ github.event.release.tag_name }}.tar.gz.sha256
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Test the Workflow**:

1. Create another test PR with a conventional commit
2. Example: Add a comment to a file, commit as `fix: test artifact workflow`
3. Merge PR to main
4. Wait for release workflow to create new release
5. Verify artifact workflow triggers and uploads files
6. Download artifact and verify contents

**Expected Outcome**:

- ✅ Workflow triggers when release is published
- ✅ Tarball created with only production files
- ✅ Artifact size is 30-50% smaller than repository
- ✅ Checksum file created
- ✅ Both files uploaded to release
- ✅ Execution completes in <1 minute

---

## Verification Checklist

After implementing all three workflows, verify:

### PR Testing

- [ ] Create test PR → workflow runs automatically
- [ ] Tests pass → PR shows green checkmark
- [ ] Tests fail → PR blocked with clear error message
- [ ] Coverage below 80% → PR blocked with coverage message
- [ ] Execution time <5 minutes (even on cold run)

### Release Creation

- [ ] Merge `feat:` commit → minor version bump (e.g., 1.2.0 → 1.3.0)
- [ ] Merge `fix:` commit → patch version bump (e.g., 1.2.0 → 1.2.1)
- [ ] Merge `feat!:` or `BREAKING CHANGE:` → major version bump (e.g., 1.2.0 → 2.0.0)
- [ ] Release notes include all commits grouped by type
- [ ] Execution time <2 minutes

### Artifact Distribution

- [ ] Release published → artifact workflow triggers
- [ ] Tarball includes: src/, requirements.txt, .env.example, README.md, Procfile, config/
- [ ] Tarball excludes: tests/, .git/, .venv/, specs/, htmlcov/
- [ ] Checksum file present
- [ ] Artifact size reasonable (30-50% reduction)
- [ ] Artifact downloadable from release page
- [ ] Execution time <1 minute

---

## Troubleshooting

### Issue: Workflow doesn't trigger

**Symptom**: PR created but no workflow runs

**Causes**:

1. Workflow file not in `.github/workflows/` directory
2. YAML syntax error
3. GitHub Actions disabled in repository settings

**Fix**:

```bash
# Validate YAML syntax
yamllint .github/workflows/*.yml

# Check GitHub Actions status
# Visit: https://github.com/ncerny/swtriviabot/actions

# If disabled, enable in Settings → Actions → General
```

---

### Issue: Tests fail in CI but pass locally

**Symptom**: Tests pass with `pytest` locally but fail in workflow

**Causes**:

1. Missing environment variable
2. Different Python version
3. Missing dependency
4. File path differences (absolute vs relative)

**Fix**:

```yaml
# Add debug step before tests
- name: Debug environment
  run: |
    python --version
    pip list
    pwd
    ls -la
```

---

### Issue: Semantic-release doesn't create release

**Symptom**: Release workflow runs but no release appears

**Causes**:

1. No releasable commits (only chore:, docs:, etc.)
2. Commit messages don't follow conventional commits format
3. No commits since last release

**Fix**:

```bash
# Check commit messages
git log --oneline origin/main

# Ensure commits follow format:
# feat: add feature
# fix: resolve bug
# chore: update deps  (no release)

# Re-commit with correct format if needed
git commit --amend -m "feat: add feature description"
```

---

### Issue: Artifact too large or missing files

**Symptom**: Artifact >2GB or missing required files

**Causes**:

1. Inclusion patterns too broad
2. .venv/ not excluded
3. Required file in excluded directory

**Fix**:

```bash
# Test tarball creation locally
tar -czf test-artifact.tar.gz \
  --exclude-vcs \
  --exclude='tests' \
  --exclude='.venv' \
  src/ requirements.txt README.md

# Inspect contents
tar -tzf test-artifact.tar.gz

# Check size
ls -lh test-artifact.tar.gz
```

---

## Next Steps

After implementation is complete:

1. **Enable branch protection** (recommended):

   - Require PR before merging
   - Require status checks to pass
   - Require "PR Tests" workflow to succeed

2. **Monitor performance**:

   - Track workflow execution times
   - Optimize if consistently >80% of time budget
   - Consider matrix testing if project grows

3. **Document for team**:

   - Add CI/CD badge to README
   - Document commit message format
   - Explain release process

4. **Optional enhancements**:
   - Add linting step (flake8) to PR workflow
   - Add security scanning (Dependabot, CodeQL)
   - Add performance benchmarking step

---

## Example End-to-End Flow

**Scenario**: Developer adds new feature

1. **Create branch**:

   ```bash
   git checkout -b feature/add-leaderboard
   ```

2. **Develop feature** (with tests):

   ```bash
   # Write code in src/commands/leaderboard.py
   # Write tests in tests/unit/test_leaderboard.py

   # Test locally
   pytest tests/unit/test_leaderboard.py

   # Check coverage
   pytest --cov=src --cov-report=term-missing
   ```

3. **Commit with conventional format**:

   ```bash
   git add .
   git commit -m "feat: add leaderboard command to display top players"
   ```

4. **Push and create PR**:

   ```bash
   git push -u origin feature/add-leaderboard
   # Create PR on GitHub
   ```

5. **CI runs automatically**:

   - PR Tests workflow triggers
   - Tests run (including new tests)
   - Coverage calculated (should still be ≥80%)
   - PR shows ✅ if all pass

6. **Review and merge**:

   - Team reviews code
   - Merge PR to main (squash or rebase)

7. **Release automation**:

   - Release workflow triggers on main push
   - Semantic-release analyzes commit: `feat:` → minor bump
   - Creates new release (e.g., v1.3.0 → v1.4.0)
   - Release notes include: "feat: add leaderboard command..."

8. **Artifact creation**:

   - Artifact workflow triggers on release
   - Creates tarball with production code
   - Uploads to release

9. **Deployment**:
   ```bash
   # On production server
   wget https://github.com/ncerny/swtriviabot/releases/download/v1.4.0/swtriviabot-v1.4.0.tar.gz
   tar -xzf swtriviabot-v1.4.0.tar.gz
   cd swtriviabot-v1.4.0/
   # Deploy...
   ```

**Total time**: ~5 minutes from merge to deployable artifact

---

## Success Metrics

After implementation, measure:

- **Test Automation**: 100% of PRs run full test suite ✅
- **Release Frequency**: Average time from commit to release <2 minutes ✅
- **Artifact Quality**: Zero production incidents due to missing files ✅
- **Developer Experience**: Reduced manual release effort by 100% ✅
- **Code Quality**: Coverage maintained at ≥80% ✅

---

## Support and Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Semantic Release**: https://semantic-release.gitbook.io/
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Pytest Coverage**: https://pytest-cov.readthedocs.io/

For questions or issues, refer to research.md and contracts/workflows.md in this spec directory.
