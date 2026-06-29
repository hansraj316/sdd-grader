# auth Specification

## Purpose

Authentication for the application.

## Requirements

### Requirement: Email login

The system SHALL authenticate users with an email and password.

#### Scenario: Valid credentials

- WHEN a user submits a correct email and password
- THEN the system issues a session token valid for 24 hours

### Requirement: Account lockout

The system SHALL lock an account after 5 failed attempts within 10 minutes.

#### Scenario: Too many attempts

- WHEN a user fails authentication 5 times within 10 minutes
- THEN the system locks the account for 15 minutes
