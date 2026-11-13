---
description: Verify a milestone against acceptance criteria and independent evidence
agent: reality-orchestrator
---

Perform a verification-focused audit of milestone `$ARGUMENTS`.

Read the authoritative requirements, milestone acceptance criteria, changed code, test matrix and execution logs. Do not assume any prior PASS remains valid if the code has changed.

Run the relevant allowed checks. Ask approval for commands not on the safe allowlist. Verify actual UI/API behavior, persistence, authorization, failure cases, scientific correctness and integration where applicable. Use the read-only reviewer and test analyst for independent challenge.

Classify each gate PASS, FAIL, NOT RUN or NOT APPLICABLE with evidence. Fix in-scope defects and re-run the failed checks. Do not hide failures or mark unexecuted checks as passed. Update the state files and report the exact milestone status.
