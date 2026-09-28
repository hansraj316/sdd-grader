# Data Model: Task Export

## Entities

### Task

| Field | Type | Notes |
|-------|------|-------|
| id | string | Stable identifier |
| title | string | Human-readable |
| status | enum | open / in_progress / done |
| owner | string | User id |
| due_date | date \| null | Optional |
| created_at | timestamp | Set at INSERT, immutable |
| updated_at | timestamp | Updated on every modification |

No new entities are introduced by this feature.
