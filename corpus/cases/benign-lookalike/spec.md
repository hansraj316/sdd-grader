# Feature Specification: Catalog Bulk Import

## User Scenarios & Testing

### User Story 1 - Import a catalog file (Priority: P1)

As an operations manager, I want to import a product catalog file so that new
products appear without manual entry.

**Acceptance criteria**

- Given a valid catalog file of up to 50,000 rows, when I import it, then every row
  appears in the catalog within 10 minutes.
- Given a file containing invalid rows, when I import it, then each invalid row is
  reported with its line number plus a reason code, while valid rows still import.

### Edge Cases

- A file exceeding 50,000 rows is rejected before any row is processed.
- Two imports of the same file produce no duplicate products (idempotent by SKU).

## Requirements

### Functional Requirements

- FR-001: The system shall import catalog files of up to 50,000 rows within 10 minutes.
- FR-002: The system shall keep p95 import-status latency under 500 ms while an import is running.
- FR-003: The system shall remain scalable to 250,000 imported rows per day without exceeding the 10-minute window per file.
- FR-004: The system shall report every rejected row with its line number plus one reason code drawn from the documented list.

## Success Criteria

### Measurable Outcomes

- 99% of 50,000-row imports complete within 10 minutes.
- 100% of rejected rows carry a line number plus a reason code.

## Out of Scope

- A simple quick-add form for single products (the existing manual flow already covers this).
- Making the import faster than the 10-minute target is not a goal for this release.
