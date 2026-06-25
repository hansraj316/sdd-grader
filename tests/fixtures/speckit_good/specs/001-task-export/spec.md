# Feature Specification: Task Export

## User Scenarios & Testing

### User Story 1 - Export tasks to CSV (Priority: P1)

As a project member, I want to export my task list to a CSV file so that I can
share progress with stakeholders who don't use the app.

**Acceptance criteria**

- Given I have at least one task, when I request an export, then a CSV file is
  produced containing one row per task with columns: id, title, status, owner, due_date.
- Given I have zero tasks, when I request an export, then I receive a CSV with only
  the header row and a message "No tasks to export".

### User Story 2 - Filter export by status (Priority: P2)

As a project member, I want to export only tasks in a chosen status so that the
shared file is scoped to what matters.

**Acceptance criteria**

- Given tasks in mixed statuses, when I export with status="open", then only open
  tasks appear in the CSV.

### Edge Cases

- A task with a missing due_date exports an empty due_date cell, not the literal "None".
- Titles containing commas or quotes are correctly escaped per RFC 4180.
- An export of more than 10,000 tasks completes without truncation.

## Requirements

### Functional Requirements

- FR-001: The system shall export the user's tasks as a CSV file on request.
- FR-002: The system shall allow filtering the export by task status.
- FR-003: The system shall escape field values so the CSV conforms to RFC 4180.

### Key Entities

- Task: a unit of work with id, title, status, owner, due_date.

## Success Criteria

### Measurable Outcomes

- 95% of exports of up to 1,000 tasks complete in under 2 seconds.
- 100% of exported CSV files open without error in Excel and Google Sheets.
- Zero data-loss defects: exported row count equals filtered task count in all tests.

## Assumptions

- Users have permission to read every task they export.
