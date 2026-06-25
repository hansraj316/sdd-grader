# TaskApp Constitution

## Core Principles

### Library-First

Every feature begins as a self-contained module with a clear public interface, so it
can be tested and reused independently of the HTTP layer.

### Test-First

Tests are written and observed failing before implementation. No implementation task
starts without a corresponding failing test.

### Integration-First

Service boundaries are defined as contracts with contract tests before implementation.
Tests use real datastores, not mocks, wherever practical.

### Simplicity

Prefer the standard library and direct framework use. Additional projects, layers, or
dependencies require explicit justification.

## Governance

Amendments require a pull request approved by two maintainers and a version bump.

**Version**: 1.2.0 | **Ratified**: 2025-01-15 | **Last Amended**: 2025-09-30
