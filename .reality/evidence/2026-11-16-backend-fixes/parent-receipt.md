# Backend fixes — ALL receipt, 2026-11-16

**Three assigned fixes accepted with bounded evidence; M-002 remains IN PROGRESS.**

Received Lực message8e4d4064 for request23e7ed68. ALL inspected REPORT.md, REVIEW.md, execution logs, hash manifests and cleanup/fault-injection evidence.

- Migration004 separates read visibility from owner-only INSERT/UPDATE/DELETE on8 project-bound tables, including OLD/NEW parent ownership.
- Project creation returns201, with the committed project readable through a new HTTP request and database connection.
- Validation PASS/FAIL preserves publication state in8 mocked-database regressions using actual compute. This does not yet prove successful live validation persistence.

## Execution evidence

| Check | Owner result | Scope |
|---|---|---|
| Original live PostgreSQL/API suite |84 PASS,1 FAIL |85 cases; remaining failure HTTP503 during compute/history |
| Additional project owner-transfer cases |2 PASS |Separate live checkpoint |
| Final default backend |210 PASS,87 SKIP |Live opt-in absent; not full live acceptance |
| Runner lifecycle/guards |22 PASS |Cleanup P2 fixed after source review |
| Injected post-start verification failure |PASS |Real identity-checked shutdown; DB marker unchanged |

ALL did not rerun these tests. Fresh parent checks recomputed8 changed-file hashes and16 verification-input hashes, all matching. Host inventory at21:42:50+07:00 found0 task processes and0 listeners on60655/51531/51578. Cleanup JSON was read through PowerShell because the text reader rejected its UTF-16 encoding. Task binaries and synthetic DB data remain retained in the existing task directory.

## Continuation

API imports worker code inside its DB-configured process, triggering the existing zero-DB guard. Approved ADR-006 requires self-contained jobs and results over Redis/Celery, with the API validating and persisting results. New request6927175a was queued to Lực for this implementation and actual queue/compute/history acceptance; evidence directory is2026-11-16-compute-queue. Worker isolation must remain enforced. Version save/freeze, full accessibility, scientific numeric acceptance and unresolved Layer6 are not closed by this receipt.

ALL wrote this receipt and four shared tracking documents. Root `git diff --check` returned exit0 after the documentation updates. No application/test edits, test rerun, runtime startup, DB write, temporary files, commit/push/deploy or secret access occurred during receipt verification.
