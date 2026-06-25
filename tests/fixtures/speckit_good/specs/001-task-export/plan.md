# Implementation Plan: Task Export

## Summary

Add a task-export capability that streams the user's filtered tasks as an
RFC-4178-conformant CSV. Reuses the existing task query layer; no new storage.

## Technical Context

- Language/runtime: Python 3.11 (matches the existing service).
- CSV generation: standard-library `csv` module — chosen because it handles RFC 4180
  escaping correctly and adds no dependency (rationale: satisfies FR-003 with zero risk).
- Delivery: synchronous HTTP download endpoint — chosen because exports are bounded
  (<10k rows, <2s) per the spec's success criteria, so async/queueing is unjustified.

## Constitution Check

- Simplicity: PASS — one project, no new services, standard library only.
- Anti-Abstraction: PASS — uses the `csv` module directly, no wrapper.
- Integration-First: PASS — a contract test for the export endpoint is defined before
  implementation (see contracts/export-api.md and tasks T004).
- Test-First: PASS — tests precede implementation in tasks.md.

Result: PASS. No violations.

## Project Structure

### Documentation (this feature)

specs/001-task-export/

### Source Code (repository root)

src/export/ — single project.

### Structure Decision

Single project; the export module lives beside the existing task module.

## Complexity Tracking

No violations to justify.
