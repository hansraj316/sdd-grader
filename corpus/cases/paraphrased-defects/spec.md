# Feature Specification: Team Activity Dashboard

## User Scenarios & Testing

### User Story 1 - View team activity (Priority: P1)

As an engineering manager, I want a dashboard of my team's activity so that I can
spot blocked work without asking in standup.

**Acceptance criteria**

- Given my team has activity, when I open the dashboard, then I see one panel per
  project with its latest activity.

### Edge Cases

- A team with no projects sees an onboarding hint instead of empty panels.

## Requirements

### Functional Requirements

- FR-001: The dashboard shall feel snappy and lightweight when a manager opens it.
- FR-002: The dashboard shall keep working smoothly when the whole company checks it
  at the same moment.
- FR-003: The dashboard could later grow a spreadsheet export once teams ask for it.
- FR-004: The dashboard shall store snapshots in CockroachDB, rendering panels with Svelte.

## Success Criteria

### Measurable Outcomes

- Managers say the dashboard helps them plan their week.
