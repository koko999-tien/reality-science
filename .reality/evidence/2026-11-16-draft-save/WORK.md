# Draft-save continuation — 2026-11-17

Request: ALL f3948b2b-8028-49b9-9707-9d00177966c2, after prior provider interruption. This slice only; durable compute recovery remains next and NOT IMPLEMENTED.

Ownership: Lực implementation, tests and slice evidence. ALL owns STATE, NEXT_ACTION, EXECUTION_LOG, TEST_MATRIX. Preserve baseline dirty work and previous evidence; local synthetic database only, no commit/push/deploy/production/secrets access.

## Plan and checkpoints

- [x] Read current AGENTS, Brief, ADR001/003/005/006, all shared trackers, failures and relevant source.
- [x] Rerun three focused frontend suites and four isolated worker suites after the existing two fixes: 86 PASS (11.225s), 78 PASS (8.90s). Logs review-frontend-green-02.log / review-worker-green-02.log. Historical failing logs retained.
- [x] Fresh migration005 and API/PostgreSQL acceptance at pre-round2 checkpoint: live-api-06.log. Preserve its bounded snapshot scope.
- [x] Browser acceptance via OpenBot private browser: live-openbot-01.log and browser-observations.jsonl. Passed before round2 source fixes. Browser tools absent after continuation catalog update; post-fix browser check NOT RUN.
- [ ] Relevant integrated frontend/backend/isolated worker gates; bounded independent read-only review.
- [ ] Final CONTRACT/REPORT/REVIEW/HANDOFF, commands/results/limits, source hashes/diff, cleanup and delivery to ALL.

Independent review requested from Change Reviewer: message a0def28c-02d5-4a9c-9612-3602727c812f, delivery9338389d. No review result at this checkpoint.

## Root causes of the last recorded failures

- Frontend green-01: recovery Map entries leaked between anonymous test fixtures, restoring an earlier invalid canvas into later cases. Source now requires an access-session token before recording/restoring pending edits. All ten failures now pass without weakening assertions.
- Worker green-01: regression tried assigning scale_factor on frozen UnitSpec. Test now copies model_dump payload for the second job; preserves scientific state, scaled value and registry-isolation assertions. All78 cases pass in worker-only environment.

The six earlier review fixes (exact AST/LaTeX, custom units in physical checks, equation ordering, create lock, audit sequence, navigation recovery) still require final integrated acceptance.

## Round 2 continuation

- [x] Read checkpoint and inspect three additional review findings. Historical frontend227, isolated worker152, backend247/132SKIP and browser1 PASS logs predate round2 fixes.
- [x] Reproduce: worker7 FAIL (unit-definition alias injection and length variables v/u); frontend1 FAIL/8PASS (cross-version recovery) after correcting the new test's canvas callback names. Red logs retained.
- [x] Apply scoped fixes: recovery attempts keyed per session/project/version; reject definition delimiters and invalid unit scale before Pint parsing; explicit non-velocity dimensions override velocity symbol heuristics.
- [ ] Focused green tests, surrounding regressions, bounded independent source review.
- [ ] Final hashes/diff, current resource check, REPORT/REVIEW/HANDOFF. ALL retains four shared trackers. Durable compute recovery remains next, NOT IMPLEMENTED.
