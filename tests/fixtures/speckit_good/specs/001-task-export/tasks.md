# Tasks: Task Export

## Format: [ID] [P?] [Story] Description

## Path Conventions

Single project: source in `src/export/`, tests in `tests/export/`.

## Phase 1: Setup

- [ ] T001 Create the export module skeleton in src/export/__init__.py

## Phase 2: Foundational

- [ ] T002 Add Task query helper in src/export/query.py

## Phase 3: User Story 1

### Tests for User Story 1

- [ ] T003 [P] [US1] Write CSV-shape test in tests/export/test_csv_shape.py
- [ ] T004 [P] [US1] Write contract test for the export endpoint in tests/export/test_contract.py

### Implementation for User Story 1

- [ ] T005 [US1] Create Task export serializer in src/export/serializer.py
- [ ] T006 [US1] Add export HTTP endpoint in src/export/api.py

## Phase 4: User Story 2

### Tests for User Story 2

- [ ] T007 [P] [US2] Write status-filter test in tests/export/test_filter.py

### Implementation for User Story 2

- [ ] T008 [US2] Add status filter to the export query in src/export/query.py

## Dependencies & Execution Order

### Phase Dependencies

Setup → Foundational → US1 → US2.

### Within Each User Story

Tests precede implementation.

### Parallel Opportunities

T003 and T004 may run in parallel.
