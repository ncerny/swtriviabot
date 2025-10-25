<!--
Sync Impact Report
Version change: (template) → 1.0.0
Modified principles: All template placeholders replaced with concrete principles
Added sections: Performance Standards, Development Workflow
Removed sections: Generic placeholder sections
Templates requiring updates:
- .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section present)
- .specify/templates/spec-template.md: ✅ Compatible (user stories and testing already aligned)
- .specify/templates/tasks-template.md: ✅ Compatible (testing and performance hooks present)
- .specify/templates/commands/: ⚠ Directory not found - manual review needed if created
- README.md: ⚠ File not found - should be created to document project and principles
Follow-up TODOs:
- TODO(RATIFICATION_DATE): Original ratification date unknown - set when determined
- Consider creating README.md to introduce the project and reference constitution
- Consider creating perf/ directory for benchmark scripts
- Consider creating waivers.md for tracking governance waivers
-->

# SWTriviaBot Constitution

## Core Principles

### Code Quality

All code MUST be readable, maintainable, and purpose-driven. Static analysis MUST
pass with zero errors. No TODO/FIXME comments are permitted in production code paths
without an associated issue link and expected resolution date. Cyclomatic complexity
exceeding 10 MUST be justified in code review comments. Public functions MUST include
documentation comments describing purpose, inputs, outputs, and error conditions. Dead
code MUST be removed in the same PR that makes it obsolete.

**Rationale**: High internal quality reduces defect rate, improves onboarding velocity,
and accelerates feature iteration.

### Testing Standards

Every code change MUST be covered by at least one automated test at the appropriate
level: unit tests for isolated logic, integration tests for cross-module behavior,
regression tests for fixed bugs. New features MUST begin with test definition following
Red-Green-Refactor discipline (tests written first, must fail, then implement to pass).
Minimum coverage thresholds: 85% statement coverage overall and 90% coverage for critical
paths (authentication, scoring, data persistence). Failing to meet thresholds blocks
merge unless a documented waiver (with issue link and expiration date) is approved.
Flaky tests MUST be quarantined within 24 hours and fixed before the next release.

**Rationale**: Comprehensive testing provides a deterministic safety net that ensures
stability and confidence in continuous delivery.

### User Experience Consistency

All user-facing interactions (CLI prompts, API responses, chat messages, or UI elements)
MUST follow a unified tone and formatting guide. This includes consistent terminology,
predictable field ordering, and clear error messages with actionable next steps.
Accessibility requirements: keyboard navigation MUST work for all UI features, and text
contrast MUST meet WCAG AA standards. Breaking UX changes (terminology shifts, command
structure modifications, response format changes) MUST include a migration guide and
advance announcement.

**Rationale**: Consistency reduces cognitive load, minimizes user friction, and builds
trust through predictability.

### Performance Requirements

All operations MUST meet defined performance budgets: interactive actions p95 latency
< 200ms, background batch jobs p99 < 2 seconds, steady-state memory per process < 100MB,
and the system MUST scale to 10,000 concurrent trivia sessions without degraded
correctness or material latency increase. Any PR that materially impacts performance
MUST include benchmark evidence (before/after measurements). Performance regressions
exceeding 5% against the established baseline block merge.

**Rationale**: Predictable performance sustains user trust, controls operational costs,
and ensures reliable service delivery at scale.

## Performance Standards

All performance benchmarks MUST be version-controlled in a `perf/` directory with
reproducible scripts and baseline measurements. A weekly automated benchmark run MUST
produce a trend report. Three consecutive degradations trigger a mandatory investigation
task added to the backlog. Caching strategies MUST specify cache invalidation rules and
TTL values. External API calls MUST enforce timeout limits and provide fallback behavior.
Any feature exceeding a defined performance budget MUST publish a remediation plan before
release approval.

## Development Workflow

The development workflow consists of these phases: Plan → Spec → Tasks → Implement →
Review → Merge → Release → Observe. Each phase MUST satisfy constitutional gates:

- **Plan**: Documents performance budgets and UX acceptance heuristics for the feature.
- **Spec**: Defines independent user stories with testable acceptance criteria and
  identifies UX patterns to follow.
- **Tasks**: Organized by user story, includes explicit test tasks and performance
  validation tasks where relevant.
- **Implement**: Tests MUST be written first and initially fail; implementation commits
  are logically grouped and documented.
- **Review**: Reviewer MUST verify compliance with all four core principles using a
  checklist.
- **Release**: Changelog MUST flag any UX or performance-impacting changes.
- **Observe**: Post-release monitoring for error rates, latency metrics, and user
  feedback within 24 hours.

## Governance

1. **Authority**: This constitution supersedes informal practices. Conflicts are resolved
   in favor of this document.

2. **Amendments**: Proposals (submitted as PRs) MUST include: diff summary, rationale,
   version bump justification, and migration/transition notes. Approval requires at least
   one maintainer approval and no veto within 48 hours (or explicit consensus in a team
   meeting).

3. **Versioning**: Semantic versioning applies to governance changes:

   - **MAJOR**: Principle added, removed, or redefined; governance rule change impacting
     workflows.
   - **MINOR**: New guidance section added, performance budgets expanded, review checklist
     items added.
   - **PATCH**: Clarifications, formatting improvements, non-semantic wording changes.

4. **Compliance Reviews**: Quarterly audits produce reports covering: test coverage
   percentages, open waivers, performance trend anomalies, and UX guideline violations.

5. **Waivers**: Time-boxed (≤30 days) and tracked in `waivers.md` with assigned owner
   and remediation date. Expired waivers automatically fail code reviews.

6. **Enforcement**: PR templates MUST include a checklist referencing the four core
   principles. PRs with unchecked items are blocked from merge.

7. **Sunset Clause**: Decommissioned principles require an archival note referencing the
   prior version and reasons for removal.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): Original ratification date unknown | **Last Amended**: 2025-10-25
