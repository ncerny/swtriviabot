# Governance Waivers

This file tracks time-boxed waivers for constitutional compliance. All waivers must have an owner, expiration date (≤30 days), and remediation plan.

## Active Waivers

<!-- Example:
### Waiver-001: Test Coverage for Legacy Module X
- **Principle**: Testing Standards (85% coverage threshold)
- **Owner**: @username
- **Created**: YYYY-MM-DD
- **Expires**: YYYY-MM-DD (max 30 days from creation)
- **Reason**: Legacy module being refactored; temporary exemption during transition
- **Remediation Plan**:
  1. Complete refactoring by [date]
  2. Add unit tests for new code
  3. Bring coverage to 85% before expiration
- **Status**: Active
-->

_No active waivers currently._

## Expired Waivers

<!-- Moved here when expired or resolved -->

## Waiver Process

1. **Request**: Submit PR with waiver entry including all required fields
2. **Approval**: Requires maintainer approval with explicit justification
3. **Tracking**: Waiver added to "Active Waivers" section
4. **Monitoring**: Reviewed in weekly team sync and quarterly compliance audits
5. **Resolution**: On completion, move to "Expired Waivers" with resolution notes
6. **Enforcement**: PRs referencing expired waivers are blocked from merge

## Template

```markdown
### Waiver-XXX: [Brief Description]

- **Principle**: [Which principle is being waived]
- **Owner**: @username
- **Created**: YYYY-MM-DD
- **Expires**: YYYY-MM-DD (max 30 days from creation)
- **Reason**: [Why this waiver is necessary]
- **Remediation Plan**:
  1. [Specific action with date]
  2. [Specific action with date]
- **Status**: Active
```
