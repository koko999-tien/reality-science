# REALITY SCIENCE — timeout propagation and lifecycle review fixes

Date: 2026-11-17 (+07:00). Checkout: `D:/Reality_Science`, branch `main`,
HEAD `595e3f0232e06e3f76fa770430a05213f6cda7d2`.

**Status: completed and verified locally for the three corrected review findings.**
Native Celery timer delivery, deployed isolation and the broader milestone remain
outside this acceptance. No commit, push or deployment was performed.

Authority is the corrected Change Reviewer message
`5d8c87aa-b4e7-4393-8c75-02cda4254b92`, superseding
`b3655d07-044a-48f2-96c9-2494e899f098`. The retracted dispatch-atomicity finding
was not changed. Preexisting remote-cluster transport deadlines and durable
compute recovery remain separate follow-ups. ALL retains shared tracker ownership;
this report and HANDOFF are the local receipt artifacts for integration.

## Delivered behavior

1. **Scientific helpers preserve operational deadlines.** Added explicit
   `except SoftTimeLimitExceeded: raise` before broad fallback catches in six
   worker helper modules. Dimensional evaluation, boundary limits/poles/sampling,
   unit registration/classification/conversion, physical inference, empirical
   evaluation and claim comparisons propagate the exception to the existing
   task-level handler. The result retains job/version/target/input provenance and
   uses `NEEDS_EXPERT_REVIEW` / `COMPUTE_TIMEOUT_EXCEEDED`. API ingestion rejects
   this operational result before persisting scientific layers.
2. **A timed-out pytest process retains its parent handle for tree cleanup.**
   `run_live.py` uses `Popen.wait(timeout=...)`; on timeout it calls bounded
   `taskkill /T /F` while the parent is still available, then re-raises the error.
   This covers the Windows venv launcher and live Uvicorn descendant.
3. **Cleanup stages run independently.** Worker termination, Redis identity and
   shutdown, Redis process fallback, client close, PostgreSQL identity/shutdown,
   manifest/log writes and verification each have guarded execution. Ordinary
   errors are accumulated, cleanup evidence is written, and a failure is raised
   only after the remaining stages have been attempted. Failed ownership checks
   continue to prevent network/DB shutdown of an unverified target.

The six product files are:

- `worker/worker/tasks/dimensional.py`
- `worker/worker/core/boundary_engine.py`
- `worker/worker/core/dimension_engine.py`
- `worker/worker/core/physical_invariants.py`
- `worker/worker/core/empirical_engine.py`
- `worker/worker/core/epistemic_engine.py`

The remaining owned files are the evidence harness
`.reality/evidence/2026-11-16-compute-queue/run_live.py` and three new tests:
`worker/tests/test_soft_deadline.py`,
`backend/tests/unit/test_live_queue_lifecycle.py`, and
`backend/tests/integration/test_compute_soft_deadline_live.py`.
`owned-changes.patch` contains precisely these ten files; seven original input
copies and their hashes are preserved under `baseline/`.

## Executed verification

These are distinct checkpoints, not a combined test total. Every PASS below has
executed evidence; a source review is explicitly identified as such.

| Check | Result | Evidence / scope |
|---|---|---|
| Reproduce old swallowed deadlines | FAIL, expected red: 13 failed | `soft-deadline-red.log`; injected dimensional exception became scientific FAIL, limit exception could produce PASS, and other helpers swallowed the exception |
| Focused regressions after propagation fix | PASS: 13 | `soft-deadline-green.log`, 3.64s |
| Expanded isolated worker suite | PASS: 143 | `worker-final.log`, 19.19s; includes 17 new helper regression cases and zero-DB environment checks |
| Harness lifecycle regressions | PASS: 10 | `lifecycle-focused-fixed.log`, 5.30s; real parent/listener descendant and eight ordinary teardown-fault variants plus multi-error aggregation |
| Default backend suite | PASS: 247; SKIP: 108 | `backend-final.log`, 51.87s; live opt-in tests skipped without disposable target selection |
| Real HTTP / Redis / worker / PostgreSQL normal path | PASS: 8; deselected: 12 | `live-normal-retry1.log`, 51.56s; four interactive outcomes and four persisted run/history/publication cases |
| Dimensional-helper timeout through real services | PASS: 1 | `soft-dimensions.log`, 7.49s; explicit exception injection into dimensional helper |
| Boundary `sp.limit` timeout through real services | PASS: 1 | `soft-limit.log`, 5.18s; explicit exception injection into boundary limit |
| Timeout-specific cross-artifact correlation | PASS: both modes | `live-correlation.json`; injection job/PID, result provenance/code/state and API/DB evidence match |
| Real Redis shutdown-error cleanup | PASS: expected failure handled | `live-cleanup-redis-fault-fault-check.json`; one normal API test passed, injected Redis shutdown error recorded, process fallback and PostgreSQL cleanup completed |
| Real pytest deadline with live API child | PASS: expected timeout handled | `live-cleanup-pytest-timeout-fault-check.json`; hook recorded successful real API test body with active fixture, harness timed out at30s and stopped the tree; this is not a completed pytest-suite PASS |
| Recovery from outer execution interruption | PASS: identified cluster recovered/stopped | `outer-timeout-recovery/result.json` and PostgreSQL recovery log; normal crash recovery, online identity/DB marker verification and clean shutdown |
| Source review | PASS within scope | `REVIEW.md`; independent reviewer found no concrete correctness blocker; did not execute suites |
| Whitespace and owned patch applicability | PASS | `final-diff-check.json`; `git diff --check` and `git apply --reverse --check --whitespace=error` both exit0; no patch was applied |
| Final resource inventory | PASS | `final-cleanup-inventory.json`, 00:38:12+07:00: 26 recorded ports closed, zero task processes, no postmaster marker, cluster `shut down` with matching identity |

The backend log retains the existing Argon2 deprecation warning; pytest-asyncio
also emits its unset fixture-loop-scope configuration notice. Git's final diff
check retains a CRLF conversion notice for a preexisting dirty evidence file.
None was hidden or changed to obtain a passing result.

## Timeout live evidence

Both lifecycles use Windows Celery `solo` with the real
`SoftTimeLimitExceeded` class deliberately raised inside the selected helper.
The API, Redis queue/result backend, separate worker and PostgreSQL are real.

| Helper | Correlated job ID | Worker result | API and fresh DB observations |
|---|---|---|---|
| Dimensional evaluation | `dd663d80-ffdb-4afe-ae19-d4ca5ea1e71a` | `NEEDS_EXPERT_REVIEW`, `COMPUTE_TIMEOUT_EXCEEDED`, `dimensions_verified=false` | HTTP503; history empty; zero runs/findings; publication `preprint` |
| Boundary limit | `fb43d291-208b-4953-8365-b6989a5e6576` | Same operational state/code | HTTP503; history empty; zero runs/findings; publication `preprint` |

`correlate_live.py` requires the injection job ID/PID to match the result and
worker identity; result version/target IDs must match the API persistence
evidence. It also verifies the worker DB guard, absent DB drivers, observed
Redis-only socket destinations and cleanup. HTTP503 alone is not used as proof
of the timeout path. The live hash assertion checks64-character length; it does
not independently recompute the staged-input fingerprint. Fingerprint equality
is exercised separately by the worker unit regression. Network observation does
not prove an enforced sandbox. The independent read-only evidence addendum in
`REVIEW.md` confirms that this correlation supports the stated injection claim.

## Preserved failures and recovery

- `lifecycle-focused.log`: initial8 FAIL/2 PASS because the test fixture replaced
  the global socket module and broke asyncio loop creation. Fixed the fixture to
  replace only the harness reference; final10 PASS. The implementation under test
  was not mocked away.
- `worker-full.log`: initial2 FAIL/141 PASS from a lowercase `derivation` fixture
  value invalid under the schema. Corrected the fixture to `DERIVATION`; final143
  PASS. No scientific assertion or schema was weakened.
- `live-normal.log`: the first live run was interrupted by the outer foreground
  shell at60s after six completed tests. Overall lifecycle **FAIL/interrupted**;
  the remaining assertions and normal teardown were not completed. This log has
  no full-suite PASS claim and was not overwritten.
- After that interruption, a fresh process inventory and port check found no
  server process/listener, but the exact task cluster retained its PID marker and
  `in production` control state. `recover_outer_timeout.py` checked the system
  ID, path, role/database marker, config and current process/port availability.
  PostgreSQL handled its stale marker and performed normal crash recovery, then
  cleanly shut down. No historical PID was killed, marker manually removed, WAL
  reset, cluster reinitialized or data deleted.
- The retry and subsequent lifecycles ran as background shell jobs with their own
  bounded inner waits. Names/logs are distinct and all cleanup artifacts remain.
- `live-cleanup-redis-fault-cleanup.json` intentionally retains one
  `broker-shutdown` error. The wrapper PASS means that expected failure was
  observed and the remaining real resources were cleaned; it does not relabel
  the injected stage as a successful shutdown.

## Commands and artifacts

From `D:/Reality_Science`, using backend Python
`D:/Reality_Science/backend/.venv/Scripts/python.exe`:

```text
.reality/evidence/2026-11-17-review-fixes/run_checks.py worker worker-final tests
.reality/evidence/2026-11-17-review-fixes/run_checks.py backend backend-final tests
.reality/evidence/2026-11-17-review-fixes/live_checks.py live-normal live-normal-retry1
.reality/evidence/2026-11-17-review-fixes/live_checks.py soft-dimensions
.reality/evidence/2026-11-17-review-fixes/live_checks.py soft-limit
.reality/evidence/2026-11-17-review-fixes/correlate_live.py
.reality/evidence/2026-11-17-review-fixes/live_failure_checks.py live-cleanup-redis-fault
.reality/evidence/2026-11-17-review-fixes/live_failure_checks.py live-cleanup-pytest-timeout
.reality/evidence/2026-11-17-review-fixes/finalize_evidence.py
```

`run_checks.py` selects the dedicated worker interpreter at
`C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-worker-verification-20261116/Scripts/python.exe`
for worker tests. Exact expanded pytest commands, cwd and exit codes are in the
named `*-command.json` and `*-cleanup.json` files.

`owned-source-sha256.json` records ten owned files.
`verification-inputs-sha256.json` records164 relevant source/test/config/evidence
inputs at closeout. This is a final source snapshot, not a claim of an unchanged
before/after hash measurement across every earlier suite.
`final-identity.json` confirms HEAD and preserved baseline hashes.

## Remaining limits and handoff

- Native Linux/prefork soft-signal and hard-kill delivery: **NOT RUN**. Explicit
  Windows exception injection verifies propagation and ingestion, not timers.
- Unit-string/Lorentz/energy/momentum and negative-power catches listed in
  `REVIEW.md` were inspected but not each directly fault-injected.
- Failure of taskkill itself, parent exit before tree termination and abrupt OS
  termination of the entire supervisor are not guaranteed by this harness. The
  actual outer-shell interruption required a separate identity-checked recovery.
- Durable compute recovery after failed/uncertain DB commit or API restart,
  native container/network isolation, assigned numeric examples16m/s and6N,
  save/freeze, complete privacy/accessibility and Layer6 acceptance remain open.
  This slice changes none of their acceptance status; M-000/M-002 remain in
  progress under ALL's shared trackers.
- All operations were local against task-owned synthetic resources. Existing
  dirty work was retained; no production DB/reset, `.env.production`, secret or
  global-setting access/change was performed.
- OpenBot message/history/attachment tools remain unavailable (namespace
  discovery returned zero tools). `HANDOFF.md` is saved locally; direct delivery
  or attachment to ALL has **not** been performed or claimed.
