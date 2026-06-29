# auth (delta)

## ADDED Requirements

### Requirement: OAuth login

The system SHALL allow a user to authenticate via Google OAuth.

#### Scenario: Google sign-in

- WHEN a user completes the Google OAuth flow
- THEN the system issues a session token valid for 24 hours
