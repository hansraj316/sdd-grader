# Contract: Export API

`GET /api/tasks/export?status=<status>`

- 200 → `text/csv`, body is an RFC 4180 CSV with header
  `id,title,status,owner,due_date` and one row per task.
- 200 with header-only body when no tasks match.
- 400 when `status` is not a known enum value.

Covered by contract test task T004.
