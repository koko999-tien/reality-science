# Review follow-up — 2026-11-17

Scope: corrected Change Reviewer message 5d8c87aa supersedes b3655d07.

- [x] Inspect current source, ownership, Brief/ADR-006 and corrected findings.
- [x] Reproduce swallowed soft deadlines at helper boundaries (13 FAIL preserved).
- [x] Propagate soft deadlines to the existing operational timeout handler (13 focused PASS; expanded worker143 PASS).
- [x] Retain timed pytest process and clean its owned tree; independently attempt all teardown steps (10 lifecycle PASS).
- [x] Full backend247 PASS/108 SKIP; final worker143 PASS; live normal8 PASS.
- [x] Two separate helper-timeout lifecycles1 PASS each; injection/job/result/API/DB correlation PASS.
- [x] Identity-checked recovery after outer tool timeout; PostgreSQL normal crash recovery and clean shutdown verified.
- [x] Real Redis-shutdown fault still cleans all owned processes and PostgreSQL; expected error retained.
- [x] Real pytest timeout with active API child; final26-port inventory closed,0 task processes, PostgreSQL clean.
- [x] Independent read-only source review and live-evidence addendum: no concrete blocker.
- [x] Final10 owned-file hashes,164 verification-input hashes, diff/reverse-patch check PASS; REPORT and local HANDOFF saved.

No OpenBot history/message/attachment tools are exposed in the current catalog (namespace discovery returned no items). Prior evidence and shared trackers were read locally. ALL retains shared tracker ownership. Retracted dispatch atomicity and pre-existing cluster transport are not part of this correction.

The first live-normal attempt was interrupted by the outer shell's60-second deadline after6 completed cases; it has no full-suite or cleanup PASS. Its logs remain intact. The retry ran in a background shell and completed8 PASS with verified teardown. Windows solo helper injection does not establish native Linux/prefork timer delivery. Complete logs/counts remain distinct checkpoints, never combined into one suite total.
