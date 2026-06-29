# Feature Specification: Password Reset

## User Scenarios & Testing

### User Story 1 - Request a reset link (Priority: P1)

As a registered user, I want to request a password reset by email so that I can
regain access when I forget my password.

**Acceptance criteria**

- Given a registered email, when I request a reset, then a single-use link valid for
  30 minutes is emailed to that address.
- Given an unregistered email, when I request a reset, then I see the same neutral
  confirmation (no account enumeration).

### Edge Cases

- A reset link used twice is rejected on the second use.
- A reset link older than 30 minutes is rejected.

## Requirements

### Functional Requirements

- FR-001: The system shall email a single-use reset link valid for 30 minutes.
- FR-002: The system shall return a neutral confirmation regardless of account existence.

### Key Entities

- ResetToken: id, user_id, expires_at, used_at.

## Success Criteria

### Measurable Outcomes

- 99% of reset emails are delivered within 60 seconds.
- 0 account-enumeration findings in a security review.

## Assumptions

- Email delivery is handled by the existing mail service.
