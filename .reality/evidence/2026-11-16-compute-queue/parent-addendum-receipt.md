# Parent receipt — final queue handoff and recovery gap

Recorded: 2026-11-17. Owner: ALL. Repository: `D:/Reality_Science`.

## Received evidence

- Final implementation handoff `f8ddbe96-0702-41d2-904d-9f712667ff80`, replying to assignment `6927175a-fd31-4b86-981d-3cb60ee2b1f9`, is now directly received. Prior parent receipt used the saved checkout report while delivery was queued.
- Addendum `98a215a5-a5d8-47aa-a903-0df2b35d3f7a` relays the original REALITY Test Analyst report `eb8fa3b7-88fc-4c90-9880-3ae36a2d9162`, replying to `9df659d0-95cc-48c5-9d86-96c7189d327d`. The analyst read an earlier source snapshot and ran none of the seven proposed groups. Lực's addendum maps those groups to later owner evidence and remaining gaps. This is distinct from the independent source review in `REVIEW.md`.
- Addendum source: `C:/Users/TIEN PC/OpenBot/Shared/Transfers/98a215a5-a5d8-47aa-a903-0df2b35d3f7a/reality-science-compute-queue-analyst-eb8fa3b7.md` and companion JSON. ALL recomputed the Markdown SHA256 as `e866886331576afc7187a06e8cd59eba7d6f9c277c84e362a8d883f2d9ce6006`, matching the supplied JSON.
- Existing owner checkpoints remain: final live95 PASS, separate no-worker1 PASS and fault-injection11 PASS; backend237 PASS/107 opt-in SKIP; worker126 PASS; shared53 PASS. They are separate executions. ALL did not rerun them in this receipt. The old ZIP is unchanged; this receipt is an additive document outside that archive.

## Precise HTTP503 correction

The earlier failure occurred at **POST `/versions/{id}/validate`**, before assertions about a successful run and history. It does not establish that GET `/versions/{id}/validation-runs` returned503. Earlier shorthand “compute/history503” describes the workflow blocked by POST validation. The successful queue slice subsequently demonstrated actual persisted findings and fresh history reads.

## Source-confirmed recovery gap

Same-job recovery after database failure or API restart is **NOT IMPLEMENTED** at this checkpoint. Its acceptance tests are **NOT RUN**, not passed by the successful-history tests.

| Source | Observed behavior | Consequence |
|---|---|---|
| `backend/app/modules/compute_orchestrator/service.py:57` | After successful dispatch, `finally` calls `discard_finding_result`, including when caller persistence raises. | A valid result is deleted when database saving fails; retention is not conditional on a durable commit. |
| `backend/app/modules/compute_orchestrator/dispatcher.py:56` | A one-day `SET NX` dispatch claim prevents reusing the job ID. | Calling the same dispatch path cannot recover that job; the claim is not a durable pending-job/input registry. |
| `backend/app/modules/compute_orchestrator/ingestion.py:33` | Disposal deletes the Redis result key. | No acknowledgement protocol links that deletion to PostgreSQL commit. |
| `backend/app/modules/reality_constraint_engine/router.py:314` | The request creates the job/bundle; `_persist_validation` inserts the run/findings and commits only after computation. | Input identity and recovery intent are not durably staged before dispatch; run primary-key uniqueness alone cannot restore missing input/result or coordinate ingestion retries. |
| `backend/tests/unit/test_compute_queue_boundary.py:90` | The current test asserts cleanup after a synthetic DB commit failure. | Its passing result verifies current cleanup behavior, not recoverability. |

Inspection of the compute path and a targeted backend source search found no connected durable pending registry or restart recovery consumer. Existing source claims explicitly exclude background ingestion after timeout/cancellation. Runtime crash/commit-failure recovery was not exercised by ALL.

## Requirements and current upstream reference check

- Approved ADR-006 requires API-owned result ingestion and says to purge processed results after backend database ingestion. Workers retain zero PostgreSQL access. Its one-hour result expiry also means retention alone cannot guarantee indefinite recovery.
- Approved ADR-005 specifies transactional outbox and explicit module interfaces. A recovery implementation must inspect existing infrastructure and preserve these boundaries.
- Brief §§2, 3 and 5 require traceable inputs, separate publication/validation/evidence statuses, API-owned database access and immutable published content. Recovery must integrate with draft revision/provenance checks rather than label an old result current after semantic editing.
- Official Celery tasks documentation read on2026-11-17: <https://docs.celeryq.dev/en/v5.6.3/userguide/tasks.html>. The worker lock pins Celery5.6.3; that URL currently renders a5.6.2 title. It documents that `acks_late` can execute a task more than once and `Task.retry` sends the same task ID. Neither establishes recovery of an API database transaction. The stable URL rendered5.7, so its newly added behavior is not attributed to the pinned runtime.
- Official PostgreSQL17 INSERT reference: <https://www.postgresql.org/docs/17/sql-insert.html>. `ON CONFLICT` supplies row-level conflict handling; it does not replace full input/correlation checks or atomic persistence of run plus findings. No blind overwrite of a conflicting scientific run is approved by this reference check.

## Remaining analyst coverage

The following retain NOT RUN status: reverse completion of two successful jobs; direct queue-side-effect measurement following unauthorized requests; the complete pending/null/timeout0/121/empty-ID matrix; live broker loss, worker loss, commit interruption and API restart; API-only image and deployed network isolation. Current JobBundle IDs lack `min_length`, and AST is optional for claim payloads; no blanket empty/null rejection claim is supported. Worker soft timeout is deliberately converted to API503 without scientific persistence. Assigned numerical examples16m/s and6N remain unproven.

## Implementation order and ownership

1. Preserve queued draft-save request `c5dc40e6-49c6-403d-970c-d7eefee5880b`. Lực completes and hands off that slice before recovery edits. At the status read Lực was working with two queued messages; the draft-save evidence directory did not yet exist. Neither observation identifies the active task or proves that no work has begun.
2. New recovery request `4e310270-7d74-4eeb-ab0d-e3adc7605f87`, delivery `7d4d0c0c-2c66-4c6f-8bf3-49d3cba1028d`, was queued as its own turn at position3. It explicitly follows draft-save and targets API-owned durable job/input staging, commit-aware retention, bounded restart recovery and idempotent ingestion. Evidence destination: `.reality/evidence/2026-11-17-compute-recovery/`.
3. Required execution evidence: pre-commit rollback/transient failure then recovery of the same job; restart after result-before-persistence; commit success followed by lost response/cleanup and safe retry; concurrent duplicate ingestion; unknown/mismatched/unauthorized jobs; pending job across draft semantic edits; reversed successful completions. Check through fresh API/DB reads, one run and six findings per accepted job, current authorization/RLS and publication independence. Keep operational errors distinct from scientific findings and preserve the worker zero-DB boundary.
4. Lực owns implementation/tests and slice evidence; ALL owns the four shared trackers. No overlapping application writer was opened. Independent source review and appropriate regressions are required after implementation; no claim of exactly-once compute execution is made.

## Parent verification and limits

At `2026-11-17T00:01:21.6619449+07:00`, HEAD was still `595e3f0232e06e3f76fa770430a05213f6cda7d2`. The five files directly inspected for this gap match the earlier slice inventory:

| File under repository root | SHA256 |
|---|---|
| `backend/app/modules/compute_orchestrator/service.py` | `0d081b60696609868277a40d705f12af8218a49c0caa0948e8c847881a340a80` |
| `backend/app/modules/compute_orchestrator/dispatcher.py` | `32aeda83e5fa7a27beffaf5e7a6fad6155f0e9014b2beabbc104f6a09db8e285` |
| `backend/app/modules/compute_orchestrator/ingestion.py` | `5163183779568bc182d5cff0f92f1da3053cc4bd6ad42dec104b5836825b03eb` |
| `backend/app/modules/reality_constraint_engine/router.py` | `3d5d0ed83005297c57df3682bf5c641b04130c070acb3e2e1d33f88e10fdff64` |
| `backend/tests/unit/test_compute_queue_boundary.py` | `5a7b27d11c62733724295dd0bdc002db7e749eb8a104218cf0996e9246d0cddc` |

The earlier parent check at23:54:10+07:00 covered all19 slice hashes and37 listener ports. That cleanup inventory is a historical checkpoint, not a new process scan in this receipt. This turn made source/documentation reads, a targeted hash check, coordination and evidence/tracker edits. No application/test change, suite execution, runtime start, database operation, commit/push/deployment or secret access occurred. Whole-commit and current deployment verification remain unknown. M-000/M-002 remain IN PROGRESS.
