---
description: Resume the exact next unfinished REALITY SCIENCE task without restarting
agent: reality-orchestrator
---

Resume the active REALITY SCIENCE milestone.

Read `.reality/STATE.md`, `.reality/NEXT_ACTION.md`, `.reality/MILESTONES.md`, `.reality/DECISIONS.md`, `.reality/TEST_MATRIX.md`, and recent `.reality/EXECUTION_LOG.md`. Inspect current git status and re-check the actual files/tests referenced by the saved next action. Treat saved notes as a handoff, not proof that the repository has not changed.

Do not repeat completed work unless verification shows it is invalid or regressed. Execute the exact next unblocked task, verify it, update durable state, then continue through the remaining milestone tasks. Do not stop after one small edit. Respect all approval boundaries. If the milestone is complete, verify the complete acceptance matrix and select the next milestone only if it is already approved and explicitly included in the user's scope; otherwise report completion and recommend the next milestone.
