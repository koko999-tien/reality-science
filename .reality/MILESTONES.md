# REALITY SCIENCE — Milestone Register

> Populate from Master Project Brief and approved architecture. This file is not authority to invent or reorder product scope.

| ID | Milestone | Source requirement IDs | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|---|
| M-000 | Repository reality audit | TBD | Actual stack, architecture, existing functionality, test commands and blockers documented | None | IN PROGRESS |
| M-001 | [Import approved milestone title] | TBD | Observable end-to-end criteria copied from approved requirements | M-000 | NOT STARTED |
| M-002 | Research Workspace UI and Verification Integrity | User request (2026-11-15): modern, non-AI-styled web aligned with scientific research purpose; Master Brief v1.0 §§1-4; ADR-001, ADR-003 | No synthetic project/version/results on API failure; backend provenance and offline/error states are explicit; project/version context remains explicit; editable AST and declared variables only report a scientific result after a real backend response; known-answer and negative scientific cases are covered; validation/history/publication/evidence statuses remain distinct; responsive and keyboard-accessible research workflow verified at 320px and other target widths; WCAG contrast, accessible names, visible focus, reduced-motion, form error announcements, and tab/panel/focus semantics pass; no unsupported Layer 6 semantics | M-000 audit evidence; requirements decision for Layer 6 before any Layer 6-specific UI | IN PROGRESS |

## Rules
- Do not mark a milestone complete based on number of changed files.
- Every milestone must contain acceptance criteria that can be tested.
- Split milestones only when necessary to create independently verifiable vertical slices.
- Do not add product scope that is not supported by the Master Project Brief or user instruction.
- Status values: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED WITH WARNINGS, IMPLEMENTED AND VERIFIED.

## Current Scope Note
- Initial implementation is restricted to local UI and functionality modernization. No push, deployment, production migration, or production secret access is authorized.
- Dataset ingestion and signed reproducibility export remain documented P0 project requirements, but are outside the first bounded workspace slice unless the existing contracts permit completion without new backend/security decisions.
- Layer 6 semantics are disputed between authoritative documents and must not be inferred from UI labels or implementation code.
