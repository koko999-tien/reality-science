# Independent read-only review — timeout and cleanup correction

Reviewer session: `ses_e1a9c6dd8ffejb0N9NRhf0Q5q0` (completed).

Verdict: **No concrete correctness blocker found in the current in-scope fixes.**
The reviewer made no edits and executed no tests or services. The reviewer read
the owner-run logs reporting 10 lifecycle tests and 143 worker tests passing.

The helper catches rethrow `SoftTimeLimitExceeded` to the existing handler in
`worker/worker/tasks/compute_tasks.py`. The task wrapper retains provenance and
`backend/app/modules/compute_orchestrator/service.py` rejects
`COMPUTE_TIMEOUT_EXCEEDED` before accepting pipeline layers.

`run_live.py` retains pytest's Popen handle and attempts process-tree termination
while its parent is alive on timeout. Its teardown guards each resource stage,
collects ordinary exceptions, attempts PostgreSQL cleanup after worker/Redis
failures, writes cleanup evidence and then raises.

Coverage limits reported by the reviewer:

- Negative-power denominator, physical unit-string, Lorentz evaluation,
  energy-dimension and momentum-dimension catches are correct by inspection but
  are not individually injected by the new deadline tests.
- Windows solo uses explicit exception injection. Native Celery soft timer
  delivery remains NOT RUN.
- HTTP 503 and zero persistence alone do not identify a timeout result. The
  parent must correlate bootstrap injection and worker-result evidence before
  claiming the timeout-specific live path passed. The bootstrap now records the
  active job ID with its injection; final correlation is recorded separately.
- Lifecycle tests cover a live parent/descendant timeout and mocked ordinary
  teardown failures. They do not establish recovery if taskkill itself fails or
  the parent independently exits before tree termination.
- The broad catch in `worker/worker/tasks/symbolic.py` is preexisting and no caller
  was found in the active pipeline; it is not an omitted in-scope fix.

This review does not approve the entire dirty tree, deployment, native timer
delivery, scientific taxonomy, or unrelated compute recovery behavior.

## Read-only live-evidence addendum

The same reviewer completed the follow-up after the live lifecycles. Verdict:
**No new in-scope correctness blocker found.** No edits or commands were run.

- `correlate_live.py` sufficiently links injection mode, active job ID and worker
  PID to the timeout result, then matches version/target to API evidence. The
  records agree on `COMPUTE_TIMEOUT_EXCEEDED`, `NEEDS_EXPERT_REVIEW`, HTTP503,
  zero persisted runs/findings and completed cleanup. Native timer delivery is
  correctly NOT RUN. Its hash check establishes64-character length only; it does
  not independently recompute the staged-input fingerprint.
- The new lifecycle wrappers were source-reviewed. Redis shutdown injection
  requires its exact error plus completed fallback cleanup. The timeout hook
  pauses after the successful API test call and before fixture teardown; the
  wrapper requires the marker and closed recorded ports. No false-PASS path was
  found in the reviewed checks. Parent execution is recorded in REPORT, not
  attributed to the reviewer.
- Recovery evidence shows matching identities, an empty pre-start process
  inventory, automatic PostgreSQL crash recovery and shutdown. No manual marker
  deletion or WAL reset appears in the script. This proves recovery after the
  outer interruption, not teardown surviving abrupt supervisor termination.
- The reviewer read owner logs reporting8 +1 +1 passing live tests. These are
  separate owner checkpoints; the reviewer independently executed nothing.
