# Remaining acceptance prerequisites — 2026-11-16

This read-only check accompanies the resumed frontend verification. It does not establish live scientific, persistence or accessibility acceptance.

## Local database environment

`Get-Command` found none of `docker.exe`, `psql.exe`, or `pg_ctl.exe` in the current PATH. This is a bounded command-availability result, not proof that no PostgreSQL installation exists anywhere on the host. No database instance was identified as disposable and no database connection/write was attempted.

The existing `backend/tests/integration/test_decision3_postgres_rls.py` uses reachability of localhost:5432 as its skip condition, defaults to a named local application database, and commits fixture inserts. Running it unchanged would not identify a disposable test database. It remains unexecuted until a dedicated test database and correct fixtures/cleanup are established.

## Numeric known-answer contract

Source inspection of `backend/app/modules/reality_constraint_engine/schemas.py:68`, `shared/shared/schemas/job_bundle.py:11`, and `shared/shared/schemas/math_ast.py:45` found AST, declared symbols/units/domains and optional physical/empirical context, but no numeric variable-binding field in the interactive verification request or job bundle. `SystemContext` contains physical assumptions rather than numeric variable assignments.

The current verification route invokes the scientific worker and returns a finding; this does not by itself supply an API workflow for binding `v_0=10 m/s`, `a=2 m/s^2`, `t=3 s` and returning `16 m/s`, or `m=2 kg`, `a=3 m/s^2` and returning `6 N`. Numeric local preview and dimensional consistency are separate capabilities. Those exact live numeric acceptance cases remain NOT RUN. The next slice needs an explicit typed numeric-input/output contract or an existing approved numeric endpoint identified from the authoritative architecture. Do not label dimensional PASS as a numeric known-answer result.

## Browser acceptance

The previously used OpenBot private-browser tools are absent from this session's active catalog. The existing `browser-checks.md` is historical runtime evidence for its documented source checkpoint. The subsequent event-snapshot, DAG-preserving layout and undeclared-variable display changes have Jest/build evidence; they still need a real-browser pass. No alternate browser controller was activated.

Remaining browser scope includes visual cleanup of duplicate navigation, graph keyboard/focus behavior, reduced motion, contrast, 200% zoom, screen-reader announcements and live authenticated error/success flows.

Layer 6 remains unresolved under ADR-000; M-000 and M-002 remain IN PROGRESS.
