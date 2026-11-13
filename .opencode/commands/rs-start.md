---
description: Start and continuously execute one complete REALITY SCIENCE milestone
agent: reality-orchestrator
---

Start milestone `$ARGUMENTS` in the current REALITY SCIENCE repository.

First inspect the actual repository and authoritative project documents. Read the `.reality` state files and current git status. If the supplied milestone ID is absent, find the closest matching approved milestone in the Master Project Brief and milestone register; do not invent new product scope.

Derive acceptance criteria, dependencies, risk and a verification matrix. Then begin implementation immediately. Do not stop after planning. Execute all unblocked tasks belonging to this milestone across all relevant layers. After each complete unit, verify it, update durable state and continue to the next task.

Do not ask for approval for ordinary reversible work. Do stop for destructive, production, external, credential, deployment, database reset/migration or other critical-risk actions requiring authorization. If a hard execution limit is reached, persist exact continuation state and report `/rs-resume` as the continuation command.

Finish only when the milestone acceptance criteria are verified or a genuine blocker/limit is reached.
