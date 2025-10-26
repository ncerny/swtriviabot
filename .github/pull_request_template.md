## Pull Request Checklist

Thank you for your contribution! Please ensure all items are checked before requesting review:

### Code Quality

- [ ] Code follows PEP 8 style guidelines
- [ ] All new code has appropriate unit tests
- [ ] Test coverage is ≥80% (enforced by CI)
- [ ] All tests pass locally (`pytest`)
- [ ] No linting errors (`flake8 src/`)

### Commit Format

- [ ] **Commits follow [Conventional Commits](https://www.conventionalcommits.org/) format**
  - `feat:` for new features (triggers minor version bump)
  - `fix:` for bug fixes (triggers patch version bump)
  - `docs:` for documentation changes (no version bump)
  - `test:` for test additions/changes (no version bump)
  - `refactor:` for code refactoring (no version bump)
  - `perf:` for performance improvements (triggers patch version bump)
  - `chore:` for maintenance tasks (no version bump)
  - Use `!` or `BREAKING CHANGE:` for breaking changes (triggers major version bump)

### Documentation

- [ ] README.md updated if user-facing changes
- [ ] DEPLOYMENT.md updated if deployment process changes
- [ ] Code comments added for complex logic
- [ ] Docstrings added/updated for new/modified functions

### Testing

- [ ] Manual testing performed in development environment
- [ ] Edge cases considered and tested
- [ ] Error handling verified

### Context

**What does this PR do?**
<!-- Brief description of the changes -->

**Why is this change needed?**
<!-- Link to issue or describe the problem being solved -->

**Related Issues:**
<!-- Closes #123, Fixes #456 -->

**Example Conventional Commits:**
```bash
# Good examples:
git commit -m "feat: add /leaderboard command"
git commit -m "fix: prevent duplicate submissions"
git commit -m "docs: update installation instructions"
git commit -m "feat!: redesign answer storage format

BREAKING CHANGE: answers now stored as objects instead of strings"

# Bad examples (won't trigger proper versioning):
git commit -m "Update code"
git commit -m "Fixed bug"
git commit -m "Changes"
```

---

**Note:** All PRs are automatically tested by GitHub Actions. Your PR must pass all tests with ≥80% coverage before it can be merged. Upon merge to `main`, a new release will be automatically created with version calculated from your commit messages.
