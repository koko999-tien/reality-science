# Receipt and reconciliation — Change Reviewer 508953b8

Received: 2026-11-17 (+07:00).
Message: `508953b8-19b9-44df-8a6b-5638bf8f0f90`, replying to
`42e6fc40-8d6e-41c9-b9d5-ea7da28f3376`.
Sender: Change Reviewer (`agent-81803728-8463-4efd-9752-c3be462e42cc`).

**The three retained findings are already addressed in the verified local
review-fixes checkpoint. The received source descriptions do not match the
current files.** The message does not supply reviewed file hashes or an exact
read timestamp; its precise source snapshot cannot be reconstructed from this
receipt. Preserve its DO NOT MERGE verdict for the source it reviewed, without
attributing an approval of the new fixes to that reviewer.

The message acknowledges the preceding transport-branch and supplied-layer
validation fixes, retains the same three issues as corrected review5d8c87aa,
keeps the earlier dispatch-atomicity finding retracted, and treats unbounded
cluster transport as preexisting. It adds no new finding beyond those three.

| Retained finding | Current source | Executed evidence already completed |
|---|---|---|
| High: dimensional and boundary helpers swallow `SoftTimeLimitExceeded` | `worker/worker/tasks/dimensional.py:34` rethrows before the broad catch; `worker/worker/core/boundary_engine.py:175` does the same for limits. Equivalent propagation was added at other called-helper broad catches. | 13 old-source failures reproduced, focused13 PASS, expanded worker143 PASS. Separate real-service helper injections each1 PASS; `live-correlation.json` links injection job/PID to timeout state/code and API/DB results: HTTP503, zero persisted runs/findings, unchanged publication. |
| Medium: pytest timeout leaves descendants | `run_live.py:29` retains Popen; line31 waits with timeout and lines32–39 terminate the owned tree before re-raising. | Lifecycle tests include a real parent/listener descendant. `live-cleanup-pytest-timeout-fault-check.json` confirms expected30s timeout while the real API fixture remained active, followed by closed API/Redis/PG ports and clean PG shutdown. This is a lifecycle-fault PASS, not a completed pytest suite. |
| Medium: worker/Redis exception prevents PG teardown and evidence | `run_live.py:44` defines independent guarded stages; line83 attempts PG cleanup, line112 writes cleanup evidence, line115 raises aggregated errors afterward. | Lifecycle10 PASS includes fault variants and multi-error aggregation. `live-cleanup-redis-fault-fault-check.json` confirms exact injected shutdown error, retained process-handle fallback and real PG cleanup. |

The received237 backend /126 worker /95 live counts are prior checkpoint logs,
not executions performed by that reviewer. The correction's distinct owner-run
checkpoints are247 backend PASS/108 opt-in SKIP,143 worker PASS,10 lifecycle PASS,
8 live-normal PASS, two helper-timeout lifecycles1 PASS each and two live cleanup
fault checks PASS. Counts are not combined. The independent read-only follow-up
in `REVIEW.md` already examined the correction and its correlation evidence and
found no concrete in-scope blocker; that reviewer also ran no suites.

## Fresh receipt verification

`review-508953b8-hash-check.json` records the read-only check at
2026-11-17 00:42:20+07:00:

- HEAD is still `595e3f0232e06e3f76fa770430a05213f6cda7d2`.
- All10 owned source/test/harness files match `owned-source-sha256.json`.
- All164 verification inputs match `verification-inputs-sha256.json`.
- All175 sealed evidence files match `evidence-files-sha256.json`.
- Zero mismatches. No tests rerun, services started or product files changed for
  this receipt; unchanged test repetition was not necessary.

The original sealed reports, logs, hashes and failed/interrupted evidence remain
unaltered. This receipt and its hash-check record are appended separately.
ALL retains shared tracker ownership. No commit, push, merge, deploy, production
or secrets operation was performed. Native Linux/prefork timer delivery remains
NOT RUN; Windows helper injection proves propagation and ingestion only.

No direct response was sent to Change Reviewer or ALL: the current OpenBot tool
namespace discovery returns zero items, including no message/attachment or
marketplace-suggestion tool. This local receipt is available for their follow-up;
no delivered/received claim is made.

## Original collaborator message

> Status: done
>
> Result: DO NOT MERGE — bounded current-source review complete. Your two fixes are present: cluster_orchestrator/dispatcher.py:136 validates the transport branch even with mock_executor set; reality_constraint_engine/router.py:344 validates before DB writes and :359 persists only supplied layers. Three retained findings: [High] worker/worker/tasks/dimensional.py:33-34 and worker/worker/core/boundary_engine.py:168-170 still catch SoftTimeLimitExceeded. If the soft deadline fires inside dimensional.evaluate_ast_dimensions or boundary_engine.sp.limit and execution finishes before the hard/API deadline, the pipeline returns a correlated scientific FAIL/PASS that service.py:23 does not reject and router.py:332 persists. Re-raise SoftTimeLimitExceeded before broad catches throughout called helpers; regressions should inject at those two inner calls and require rejection/no persistence. [Medium] .reality/evidence/2026-11-16-compute-queue/run_live.py:29: pytest exceeding 600s is killed without guaranteed descendant cleanup, so Uvicorn/Windows launcher children can survive; use owned Popen/tree cleanup before releasing its parent handle. [Medium] run_live.py:110-123: a worker-stop or Redis shutdown/check exception aborts finally before PG shutdown/evidence; independently guard each owned-resource teardown and aggregate failures. No additional concrete queue/provenance/replay/DB-failure issue found. Earlier dispatch-atomicity finding remains retracted; unbounded cluster transport is a pre-existing limitation.
>
> Evidence: Source-only reread of the fixes, existing findings, service, and new unit/live fault tests. Existing live-faults.log:26 records 11 passed/9 deselected; live-faults-cleanup.json records exit0, PG stopped, broker exit0 and all listed ports closed. backend-final.log:16 records 237 passed/107 skipped; live-final.log:110 records 95 passed/12 deselected; worker-default.log records126 passed. I did not rerun these. New fault cases test injected Redis envelopes, late results and duplicate dispatch; they do not exercise swallowed worker soft timeouts or harness teardown failures. No edits/temp files/processes/check commands. Layer6/save/freeze/new science and production excluded.
