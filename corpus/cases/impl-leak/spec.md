# Feature Specification: Notifications

## User Scenarios & Testing

### User Story 1 - Receive notifications (Priority: P1)

As a user, I want to receive notifications.

**Acceptance criteria**

- Given an event occurs, when it is relevant to me, then I receive a notification.

### Edge Cases

- A muted channel produces no notification.

## Requirements

### Functional Requirements

- FR-001: Build the notification service with React and Postgres and websockets.
- FR-002: We might need a Kafka pipeline in the future for scale.

## Success Criteria

### Measurable Outcomes

- 99% of notifications are delivered within 5 seconds.
