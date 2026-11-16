# Independent source review follow-up — 2026-11-16

Reviewer: bounded read-only subagent session `ses_e1c2e15a3ffetxf0YM1CTNLaLU`, requested under repository `AGENTS.md`. The reviewer inspected local source and tests and made no changes. This is source review, not runtime evidence or a full milestone/security approval.

## First review

Three concrete P2 findings:

1. Auto-layout reconstructed a graph from its AST, replacing node IDs and splitting a shared operand into independent copies. Editing one constant after layout could change the result from the intended shared-input behavior. Layout-before-edit in a single batch could also lose an edit targeting an old draft ID.
2. Deleting declaration `x` while `y` remained left a controlled select with value `x` but no matching option. The displayed option could become `y` while canvas state/diagnostic still referred to `x`. Stale cached unit metadata could also remain visible.
3. An edit followed immediately by validation in the same batch validated the render-captured old canvas while using the new request ID, allowing a stale result to be accepted. This was a hook-level gap; the inspected page did not compose those calls in one handler.

The reviewer confirmed that the earlier report about isolated `setVariables` was obsolete: the shared canvas state already drove derived previews and invalidated prior pending requests. Initial updater bodies contained no observed side effects.

## Implemented responses

- `frontend/src/hooks/useEquationCanvas.ts`: graph layout now validates, computes levels/positions for existing node IDs and changes only positions. Shared operands, edges, IDs and node data remain intact. Every canvas write now goes through one event/effect-only gateway: a pure transform consumes the latest snapshot, the ref advances outside render/state updaters, and React receives that same snapshot. Validation reads it synchronously, including earlier edits in the same batch. Existing result/error/finally request-ID guards remain.
- `frontend/src/components/equations/canvas/nodes/VariableNode.tsx`: a removed symbol has a matching disabled `x (undeclared)` option when other declarations remain; the control is marked invalid and no stale unit is shown. Restoring or explicitly selecting a declaration restores current metadata.
- `frontend/tests/equation_canvas_state.test.tsx`: shared-input layout/ID/edge preservation, pending validation surviving layout, layout-before-edit, same-batch edit/validate and declaration-removal/validate, plus declaration-specific stale-result cases.
- `frontend/tests/CustomNodes.test.tsx`: remove with another declaration or no declarations, select the remaining option, restore with a changed unit.
- `frontend/tests/editor_validation_integrity.test.tsx`: real declaration form deletion/redeclaration and late response behavior with API/canvas rendering mocked.

## Second review

The same independent reviewer read the changed source and regressions and reported: **all three previously reported defects addressed at source level; no concrete new regression found in the reviewed changes**. The reviewer checked that every canvas write uses the gateway, no ref mutation occurs during render or React state updaters, layout maps are local and request guards remain.

The reviewer did not execute tests/build/lint/browser checks. Its statement that shell was blocked reflects the earlier checkpoint; the owner subsequently ran the focused 3 suites / 33 tests and full 15 suites / 188 tests successfully. Runtime commands/results are recorded separately in `EXECUTION_LOG.md`, `jest-declarations.log` and `jest-final.log`. Source review scope does not cover the full dirty checkout, deployed behavior, API security, PostgreSQL/RLS or complete browser acceptance. Original OpenBot Analyst/Reviewer replies have since arrived and are reconciled in `analyst-reconciliation.md`, with expanded owner final104/219 tests PASS. The parent's focused browser follow-up is documented separately in `browser-review-integrated-parent.md`.
