# Tasks: GitHub Actions CI/CD Workflows

**Feature**: 002-github-actions-cicd  
**Input**: Design documents from `/specs/002-github-actions-cicd/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/workflows.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested in specification. Focus on infrastructure implementation and validation through actual workflow execution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Repository root**: `.github/workflows/` for workflow files
- **Configuration files**: Repository root for semantic-release config
- All paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and workflow directory structure

- [x] T001 Create .github/workflows/ directory structure if it doesn't exist
- [x] T002 [P] Create .gitignore entries for Node.js dependencies (node_modules/, package-lock.json) used by semantic-release
- [x] T003 [P] Verify existing pytest configuration in pytest.ini and .coveragerc meets workflow requirements

**Checkpoint**: Directory structure ready for workflow files

---

### Phase 2: Foundational (Priority: P1)
**Purpose**: Create semantic-release configuration and artifact exclusion rules

#### T004: Create package.json with semantic-release dependencies
- [x] Create `package.json` at repository root
- [x] Add devDependencies: semantic-release, commit-analyzer, release-notes-generator, github plugin
- [x] Set repository URL and basic package metadata
- [x] Verify file is valid JSON

#### T005: Create .releaserc.json configuration
- [x] Create `.releaserc.json` at repository root
- [x] Configure branches: ["main"]
- [x] Configure plugins: commit-analyzer, release-notes-generator, github
- [x] Set tagFormat: "v${version}"
- [x] Configure conventional commit rules (feat=minor, fix=patch, BREAKING CHANGE=major)

#### T006: Create .artifactignore file
- [x] Create `.github/.artifactignore`
- [x] Document exclusion patterns: tests/, .venv/, .git/, .github/, docs/, specs/
- [x] Include development files: pytest.ini, .coveragerc, package.json, .releaserc.json
- [x] Add comment explaining purpose (referenced by artifact workflow)

---

## Phase 3: User Story 1 - Pull Request Quality Gate (Priority: P1) 🎯 MVP

**Goal**: Automatically run all tests and validation checks on every pull request to verify changes don't break existing functionality

**Independent Test**: Create a test PR with any code change and verify that all tests execute automatically with results reported to PR interface

### Implementation for User Story 1

- [x] T007 [US1] Create pr-tests.yml workflow file in .github/workflows/ with pull_request trigger configuration
- [x] T008 [US1] Add Python 3.14 setup step using actions/setup-python@v5 in pr-tests.yml
- [x] T009 [US1] Add pip dependency caching step using actions/cache@v4 in pr-tests.yml
- [x] T010 [US1] Add dependency installation step (pip install -r requirements.txt) in pr-tests.yml
- [x] T011 [US1] Add pytest execution step with coverage enforcement (--cov=src --cov-fail-under=80 -v -x) in pr-tests.yml
- [x] T012 [US1] Add coverage report upload step using actions/upload-artifact@v4 in pr-tests.yml
- [x] T013 [US1] Configure workflow permissions (contents: read, pull-requests: write) in pr-tests.yml
- [x] T014 [US1] Set workflow timeout to 10 minutes in pr-tests.yml
- [x] T015 [US1] Add step to display test summary in workflow output in pr-tests.yml

**Validation Steps**:

1. Create test branch: `git checkout -b test-pr-workflow`
2. Make trivial change (add comment to README)
3. Commit with conventional format: `git commit -am "test: verify PR testing workflow"`
4. Push and create PR
5. Verify workflow runs, tests execute, coverage calculated, PR shows status

**Checkpoint**: User Story 1 complete and independently testable - PR testing workflow functional

---

## Phase 4: User Story 2 - Automated Release Creation (Priority: P2)

**Goal**: Automatically create tagged releases with semantic versioning when code is merged to main branch

**Independent Test**: Merge a PR with conventional commit to main and verify new GitHub release is created with correct semantic version and auto-generated release notes

**Dependencies**: US1 must be working (ensures only tested code reaches main)

### Implementation for User Story 2

- [x] T016 [US2] Create release.yml workflow file in .github/workflows/ with push to main trigger configuration
- [x] T017 [US2] Add repository checkout step with full history (fetch-depth: 0) in release.yml
- [x] T018 [US2] Add Node.js 20.x setup step using actions/setup-node@v4 in release.yml
- [x] T019 [US2] Add semantic-release installation step (npm ci) in release.yml
- [x] T020 [US2] Add semantic-release execution step with GITHUB_TOKEN in release.yml
- [x] T021 [US2] Configure workflow permissions (contents: write, actions: read) in release.yml
- [x] T022 [US2] Set workflow timeout to 10 minutes in release.yml
- [x] T023 [US2] Add output variables for release information (new_release_version, new_release_git_tag) in release.yml

**Validation Steps**:

1. Ensure test PR from US1 has passing tests
2. Merge PR with conventional commit: `feat: add CI/CD workflows`
3. Wait for release workflow to trigger on main
4. Verify release created with appropriate version bump
5. Verify release notes auto-generated and grouped by type
6. Execution completes in <2 minutes

**Checkpoint**: User Stories 1 AND 2 both work independently - PR testing prevents bad merges, releases auto-created

---

## Phase 5: User Story 3 - Production-Ready Artifact Distribution (Priority: P3)

**Goal**: Create compressed artifacts containing only production code attached to each release for efficient deployment

**Independent Test**: Download release artifact and verify it contains src/ and runtime files but excludes tests/ and development files, and artifact is 30-50% smaller than repository

**Dependencies**: US2 must be working (release must exist to attach artifact)

### Implementation for User Story 3

- [x] T024 [US3] Create artifact.yml workflow file in .github/workflows/ with release.published trigger configuration
- [x] T025 [US3] Add repository checkout step at release tag in artifact.yml
- [x] T026 [US3] Add tarball creation step with production file inclusion patterns in artifact.yml
- [x] T027 [US3] Configure tar exclusion patterns for tests/, htmlcov/, .pytest_cache/, .git/, .github/, .venv/, specs/, perf/ in artifact.yml
- [x] T028 [US3] Add SHA-256 checksum calculation step for artifact integrity verification in artifact.yml
- [x] T029 [US3] Add artifact information display step (size, contents preview) in artifact.yml
- [x] T030 [US3] Add artifact upload step using softprops/action-gh-release@v1 in artifact.yml
- [x] T031 [US3] Add checksum file upload step to release in artifact.yml
- [x] T032 [US3] Configure workflow permissions (contents: write, actions: read) in artifact.yml
- [x] T033 [US3] Set workflow timeout to 10 minutes in artifact.yml

**Validation Steps**:

1. Create test PR with conventional commit: `fix: test artifact workflow`
2. Merge to main
3. Wait for release workflow to create release
4. Wait for artifact workflow to trigger
5. Download artifact from release page
6. Verify contents: includes src/, requirements.txt, .env.example, README.md, Procfile, config/
7. Verify exclusions: no tests/, .venv/, .git/, htmlcov/
8. Verify artifact size is 30-50% smaller than repository
9. Extract and verify bot can start with production dependencies

**Checkpoint**: All three user stories independently functional - complete CI/CD pipeline operational

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, optimization, and validation across all workflows

- [x] T034 [P] Add CI/CD status badges to README.md showing workflow status
- [x] T035 [P] Document commit message format (conventional commits) in CONTRIBUTING.md or README.md
- [x] T036 [P] Update .github/copilot-instructions.md with recent changes marker
- [x] T037 Create pull request template in .github/pull_request_template.md with commit format reminder
- [x] T038 Test end-to-end flow per quickstart.md validation scenario
- [x] T039 [P] Verify workflow execution times meet performance budgets (<5min tests, <2min release, <1min artifact)
- [x] T040 [P] Add workflow failure notification documentation in README.md or docs/
- [x] T041 Document deployment process using artifact in DEPLOYMENT.md
- [x] T042 Validate branch protection settings recommendation in documentation

**Checkpoint**: Documentation complete, workflows optimized and validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Can start immediately after
- **User Story 2 (Phase 4)**: Depends on Foundational phase AND US1 (requires tested code) - Sequential dependency
- **User Story 3 (Phase 5)**: Depends on Foundational phase AND US2 (requires release) - Sequential dependency
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

```
Setup (Phase 1)
    ↓
Foundational (Phase 2) ← CRITICAL BLOCKER
    ↓
User Story 1 (P1) ← MVP - Must complete first
    ↓
User Story 2 (P2) ← Depends on US1 (needs tested code)
    ↓
User Story 3 (P3) ← Depends on US2 (needs release)
    ↓
Polish (Phase 6)
```

**Note**: Unlike typical features where user stories are independent, this CI/CD pipeline has sequential dependencies because each workflow builds on the previous one:

- PR testing must work before releases (tested code requirement)
- Releases must work before artifacts (need release to attach to)

### Within Each User Story

- All workflow steps must be added in order (checkout → setup → execute → upload)
- Workflow file structure must be valid YAML before testing
- Core workflow logic before optimization/monitoring steps

### Parallel Opportunities

**Phase 1 (Setup)**:

- T002 and T003 can run in parallel (different files)

**Phase 2 (Foundational)**:

- T004, T005, T006 can all be created in parallel (different files)

**Phase 3 (User Story 1)**:

- All tasks are sequential (building same pr-tests.yml file)

**Phase 4 (User Story 2)**:

- All tasks are sequential (building same release.yml file)

**Phase 5 (User Story 3)**:

- All tasks are sequential (building same artifact.yml file)

**Phase 6 (Polish)**:

- T034, T035, T036, T039, T040 can run in parallel (different files)

---

## Parallel Example: Foundational Phase

```bash
# Launch all foundational config files together:
Task T004: "Create package.json with semantic-release dependencies"
Task T005: "Create .releaserc.json configuration for semantic-release"
Task T006: "Create .artifactignore file documenting exclusions"

# All three files are independent and can be created simultaneously
```

---

## Parallel Example: Polish Phase

```bash
# Launch all documentation updates together:
Task T034: "Add CI/CD status badges to README.md"
Task T035: "Document commit message format in CONTRIBUTING.md"
Task T036: "Update .github/copilot-instructions.md"
Task T039: "Verify workflow execution times"
Task T040: "Add workflow failure notification documentation"

# All operate on different files and have no dependencies
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup → Directory structure ready
2. Complete Phase 2: Foundational → Semantic-release configured (even though not used yet)
3. Complete Phase 3: User Story 1 → PR testing workflow
4. **STOP and VALIDATE**:
   - Create test PR
   - Verify tests run automatically
   - Verify coverage enforcement works
   - Verify PR status check appears
5. **MVP DEPLOYED**: Basic CI protection in place

**At this point you have a working MVP** - PRs are automatically tested and blocked if they fail. This alone provides significant value.

### Incremental Delivery

1. **Setup + Foundational** → Configuration files in place
2. **Add User Story 1** → Test independently → **MVP DEPLOYED!**
   - PRs now require passing tests
   - Coverage enforced at 80%
   - Broken code blocked from merge
3. **Add User Story 2** → Test independently → **Release automation deployed!**
   - Merges to main auto-create releases
   - Semantic versioning automated
   - Release notes auto-generated
4. **Add User Story 3** → Test independently → **Complete pipeline deployed!**
   - Releases include production artifacts
   - Deployment artifacts optimized
   - Checksums for integrity verification
5. **Polish** → Documentation and optimization

Each stage adds value without breaking previous functionality.

### Sequential Team Strategy

Due to sequential dependencies in this feature, parallel team work is limited:

1. **Phase 1-2** (Setup + Foundational): Single developer - Quick (30 min)
2. **Phase 3** (User Story 1): Single developer - PR workflow (2-3 hours)
3. **Phase 4** (User Story 2): Single developer - Release workflow (2-3 hours)
4. **Phase 5** (User Story 3): Single developer - Artifact workflow (1-2 hours)
5. **Phase 6** (Polish): Can split among team (parallel documentation tasks)

**Total estimated time**: 6-9 hours for complete implementation

**Minimum viable time**: 3-4 hours for MVP (Phases 1-3 only)

---

## Validation Checklist

After completing each user story, validate independently:

### User Story 1 (PR Testing) Validation

- [ ] Create test branch with code change
- [ ] Create PR to main
- [ ] Workflow triggers automatically within 30 seconds
- [ ] Tests execute and complete in <5 minutes
- [ ] Coverage calculated and displayed
- [ ] PR shows green checkmark if tests pass
- [ ] PR blocked with clear error if tests fail
- [ ] PR blocked if coverage <80%
- [ ] Coverage report available as artifact

### User Story 2 (Release Automation) Validation

- [ ] Merge PR with `feat:` commit to main
- [ ] Release workflow triggers automatically
- [ ] Minor version bumped (e.g., 1.2.0 → 1.3.0)
- [ ] Release created within 2 minutes
- [ ] Release notes include commit message
- [ ] Release notes grouped by type (Features, Fixes)
- [ ] Git tag created matching version
- [ ] Merge PR with `fix:` commit → patch bump (1.3.0 → 1.3.1)
- [ ] Merge PR with `BREAKING CHANGE:` → major bump (1.3.1 → 2.0.0)

### User Story 3 (Artifact Distribution) Validation

- [ ] Release creation triggers artifact workflow
- [ ] Workflow completes in <1 minute
- [ ] Tarball attached to release
- [ ] Checksum file attached to release
- [ ] Download and extract artifact
- [ ] Verify includes: src/, requirements.txt, .env.example, README.md, Procfile, config/
- [ ] Verify excludes: tests/, .venv/, .git/, htmlcov/, .pytest_cache/, specs/
- [ ] Artifact size 30-50% smaller than repository
- [ ] Checksum validation passes: `sha256sum -c artifact.tar.gz.sha256`
- [ ] Bot starts successfully with artifact: `pip install -r requirements.txt && python -m src.bot`

---

## Edge Cases Handling

The specification identified these edge cases. Ensure they're addressed:

- **GitHub Actions quota exceeded**: Workflow will fail with quota error - user must upgrade or wait for quota reset
- **Test timeout**: Workflow timeout set to 10 minutes - exceeding this fails the workflow
- **Simultaneous PR merges**: GitHub Actions queues workflows automatically - releases created sequentially
- **Release creation failure**: Semantic-release handles retries automatically - manual intervention for persistent failures
- **Non-conventional commits**: Semantic-release skips release creation - no error, just no release
- **First release**: Semantic-release creates v1.0.0 automatically per .releaserc.json configuration
- **Artifact upload failure**: softprops/action-gh-release has built-in retry logic

---

## Task Summary

### Total Tasks: 42

**By Phase**:

- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (User Story 1): 9 tasks
- Phase 4 (User Story 2): 8 tasks
- Phase 5 (User Story 3): 10 tasks
- Phase 6 (Polish): 9 tasks

**By User Story**:

- User Story 1 (PR Testing): 9 tasks
- User Story 2 (Release Automation): 8 tasks
- User Story 3 (Artifact Distribution): 10 tasks
- Infrastructure & Polish: 15 tasks

**Parallel Tasks**: 10 tasks marked [P] (23.8% of total)

**Sequential Dependencies**: Due to CI/CD pipeline nature, user stories must be implemented sequentially (US1 → US2 → US3)

### Suggested MVP Scope

**Minimum Viable Product** (Phases 1-3):

- Setup infrastructure
- Foundational configuration
- User Story 1: PR Testing workflow

**Estimated MVP time**: 3-4 hours

**MVP Value**: Automated testing on all PRs with coverage enforcement - prevents broken code from being merged

### Next Increment (Add Phase 4)

Add User Story 2: Release automation  
**Additional time**: 2-3 hours  
**Added value**: Automated releases with semantic versioning

### Complete Implementation (Add Phase 5-6)

Add User Story 3 + Polish  
**Additional time**: 2-3 hours  
**Added value**: Production artifacts + complete documentation

---

## Notes

- All workflow files use YAML syntax - validate with `yamllint` before testing
- Test each workflow independently by creating appropriate trigger (PR, merge, release)
- Conventional commit format is CRITICAL for semantic-release: `type: description`
  - Valid types: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `style:`
  - Breaking changes: `BREAKING CHANGE:` in commit body OR `feat!:` / `fix!:`
- GitHub Actions free tier: 2000 minutes/month for private repos, unlimited for public repos
- Workflow run history retained for 90 days automatically
- Use quickstart.md as implementation guide - includes complete workflow YAML examples
- Each user story builds on previous one - cannot skip or reorder
- Commit after each task to preserve incremental progress
- Stop at any checkpoint to validate story independently before proceeding
