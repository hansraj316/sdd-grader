# Implementation Plan: Notifications

## Summary

Build a flexible, future-proof notification platform with a plugin architecture so we
can eventually support any channel.

## Technical Context

- Language: TypeScript.
- Architecture: 5 microservices behind an abstraction layer that wraps the framework,
  plus a generic event bus, in case we need more channels later.
- [NEEDS CLARIFICATION: which message broker?]

## Project Structure

### Source Code

Many services.
