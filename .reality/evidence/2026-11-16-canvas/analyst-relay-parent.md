# Parent receipt of the original Test Analyst report — 2026-11-16

## Provenance

Received REALITY Test Analyst relay `d2fe2b9d-2d5c-4f2d-876a-020307228b72`, replying to parent relay request `fbc6b2e3-7f40-435b-a060-be7b403ccf75`. Original analysis request: `8a6f7ff5-187a-4a4e-9054-686e594e96c4`; original reply to the implementation owner: `407d499d-3f07-40e7-9042-c23cac3f978a`.

The analyst used history only for this relay: no project reread, test execution or edits. All eight original groups were proposals, NOT RUN by that analyst. Historical editor observations about `syncAst` in updaters and variable changes leaving stale previews are not findings against the subsequent implementation. The report's old line references describe inspected snapshots only.

## Parent reconciliation

Parent read the owner's `analyst-reconciliation.md` and checked current test anchors against its independently executed results in `test-expansion-parent.md`. All eight proposal groups have corresponding executed regression coverage:

| Group | Behavior covered | Current test anchors |
|---|---|---|
| P0-1 | StrictMode mixed batches preserve graph, IDs, geometry and selection without unsolicited validation | `equation_canvas_state.test.tsx:33` |
| P0-2 | Stale success/error/finally cannot overwrite newer work; manual edit1→2→1 does not restore an obsolete finding | Hook tests at302/320/342; editor tests at298 |
| P0-3 | Cancel deletion preserves state; confirmed deletion clears previews/findings; redeclaration submits new units/domain | Hook tests at164/180/205/226/246; editor tests at264/364 |
| P0-4 | Position/selection/measurement/layout preserve valid pending/completed findings and shared identity | Hook tests at105/400 |
| P0-5 | Omitted/null plus explicit handles reject duplicate semantic inputs; missing binary ports and disconnected cycles reject | `ast_graph_converter.test.ts:445/456/483` |
| P0-6 | Shared non-leaf expression yields exact AST and local16; subtraction/division preserve operand order; presets round-trip | Converter tests at505/510/578/614 |
| P1-7 | Depth15/16 and expanded count100/101 boundaries with/without root; compact DAG expanding to127 rejects | Converter tests at298/309/320/336/355 |
| P1-8 | StrictMode cleanup and delayed project/equation/variable responses preserve the current route's context | `editor_validation_integrity.test.tsx:429/506` |

Parent execution remains two separate checkpoints: full15 suites/219 tests PASS23.549s, then final editor1 suite/20 tests PASS8.551s after the editor test changed during the full run. TypeScript and affected-file lint passed. The owner's separate focused104/full219 results and limits are recorded in `analyst-reconciliation.md`. Counts are not added together, and the parent's219 result is not presented as a final-tree full-suite run.

Current read-only hash comparison against `source-checkpoint-test-expansion-final-parent.json`:71 inputs,0 mismatches. No application/test changes or unresolved new failures justified another test/build run.

## Disposition and limits

The pending-original-analysis receipt item is resolved. During this reconciliation the implementation owner also updated shared STATE/NEXT_ACTION/TEST_MATRIX to record its bounded handoff and report mapping. Those newer edits were preserved. The parent's older pending-report wording is historical and is superseded by this receipt.

All API/canvas mocks retain their stated limitations. Local arithmetic16 is not the separate live unit-bearing16 m/s scientific acceptance case. Live authentication/API success, PostgreSQL/RLS, durable editor persistence, scientific known-answer API runs, full accessibility and Layer6 definition remain open. M-000/M-002 remain IN PROGRESS.

Parent writes for this receipt: this report, evidence cross-references and a verified workspace copy for attachment. No application/test code change, test rerun, server, commit, push, deployment, database operation or secret change.
