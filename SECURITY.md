# Security Policy

## Supported versions

Security fixes go into the latest release. Upgrade with `uv tool upgrade sddgrade`.

## Reporting a vulnerability

**Do not open a public issue.** Report the problem privately through
[GitHub private vulnerability reporting](https://github.com/hansraj316/sdd-grader/security/advisories/new),
or email **hansraj136@gmail.com**.

Include the affected version, steps to reproduce, and the impact. Expect an
acknowledgement within 5 business days.

## Scope notes

- **Judge tampering.** A spec author can try to steer the LLM judge with prompt
  injection. That is a documented limitation (see the README section "What the
  judge can and can't prove"), not a vulnerability. Two cases *are* in scope:
  a bypass of the deterministic `SPEC-PROMPT-INJECTION-SUSPECT` lint check, and
  any path where artifact content gets executed.
- **API keys.** sddgrade reads `ANTHROPIC_API_KEY` / `TYPESAFE_API_KEY` from the
  environment only and never writes them to reports, history, or logs. Report
  any leak of a key.
