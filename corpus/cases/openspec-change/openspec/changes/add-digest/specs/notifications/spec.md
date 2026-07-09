# Notification Digest

## Requirements

### Requirement: Daily digest

The system SHALL batch a day's notifications into a single digest email that feels
clean and simple.

#### Scenario: Digest sent

- WHEN a user has one or more notifications at digest time
- THEN the system sends exactly one digest email for that day

### Requirement: Digest opt-out

The system SHALL let a user opt out of the digest, restoring immediate emails.
