# Backend live verification work log

- [x] Read governing brief, ADR-003, state/matrix; preserve existing dirty tree.
- [x] Replace unsafe port probe/application-DB fallback with explicit target guards.
- [x] Final default verification: 37 guard tests passed; 85 live cases skipped, no target selected.
- [x] Initialize identified disposable PostgreSQL and execute real Alembic migrations (001-003).
- [x] Reproduce live RLS/API defects; retain exact failing evidence for the next owner.
- [x] Full backend default checks: 182 passed, 85 skipped; diff check passed.
- [x] Final hashes, identity-checked clean shutdown and handoff report.
- [ ] Product fixes for public DELETE/takeover/reparenting and project-create serialization; successful isolated compute/history workflow. Deferred to ALL after the scope reduction in message566d7075.

Base HEAD: c6062783f760f126ca87340f3c0736d11010d659 on main. Existing uncommitted work preserved.
Official download chain: https://www.postgresql.org/download/windows/ ->
https://www.enterprisedb.com/download-postgresql-binaries ->
https://sbp.enterprisedb.com/getfile.jsp?fileid=1260667 ->
https://get.enterprisedb.com/postgresql/postgresql-17.12-1-windows-x64-binaries.zip
Downloaded ZIP SHA256: a2cd8a774389347b70be7748ac4a37ef43cb6ee539c5fc3e85ae264b15e4a04c.
This local digest identifies the artifact; it is not a comparison against a separately published vendor checksum.

References read:
- https://www.postgresql.org/docs/17/ddl-rowsecurity.html (superuser/BYPASSRLS, USING vs WITH CHECK, DELETE)
- https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.SessionEvents.after_begin (SQL through event Connection)

Read-only independent source review flags public DELETE/ownership transfer under FOR ALL,
revision003 length beyond Alembic default32, possible async project response loading,
and validation mutating publication status. Each must be reproduced before claiming a runtime defect.
Version-create/editor save/freeze lifecycle endpoints remain absent; no new semantics were added.
Final evidence and exact limitations: REPORT.md. Guard milestone complete; broader backend acceptance remains partial.
