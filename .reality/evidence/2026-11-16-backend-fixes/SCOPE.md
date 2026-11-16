# Backend fixes scope and evidence boundaries

Request: ALL message23e7ed68-332b-4896-a88f-7a2d11d8fe0e relays the user's instruction to continue local implementation. Branchmain, base HEADc6062783f760f126ca87340f3c0736d11010d659. Baseline8 files were saved before this slice and matched when work resumed.

## Root causes and bounded fixes

1. Migrations001–003 use FOR ALL with a broad visibility USING predicate. PostgreSQL applies USING to DELETE and to the old UPDATE row. WITH CHECK protects the new row, allowing a reader to delete a public row or move it into their own parent. Migration004 removes each old policy and installs SELECT visibility, INSERT owner WITH CHECK, UPDATE owner USING+WITH CHECK, DELETE owner USING on8 tables. Existing ENABLE/FORCE flags and identity roles are retained. This corrects implementation to Brief§5; it does not approve new collaborator privileges. Downgrade restores the original003 policy semantics and is not a recommended security rollback.
2. create_project committed, then refreshed scalar attributes while versions remained lazy. FastAPI/Pydantic serialization accessed versions synchronously, causing MissingGreenlet after the insert had committed. An awaited SELECT with selectinload(versions) and populate_existing reloads the persisted project and relationship before response serialization. The live test asserts201, fresh GET identity and an independent DB connection read.
3. validate_version explicitly changed draft→verified when compute returned PASS. The assignment is removed; the real compute result is still serialized and persisted to runs/findings. Parameterized Stage4 coverage checks both actual PASS and undeclared-symbol FAIL with draft/preprint/published/retracted preserved. Published is an existing legacy fixture value and is preserved, not introduced as a new publication contract. These tests use an in-memory DB/access override, so they do not prove successful live compute/history persistence.

## Verification distinctions

- Original85 live cases are retained, including HTTP200 and persisted history assertions that previously failed at compute503. They are not skipped, weakened or converted to expected failures.
- Default backend verification explicitly removes only REALITY_TEST_DATABASE_URL and REALITY_TEST_INSTANCE_ID in the child environment; it does not modify global settings.
- The runner's start path rejects bad manifest/offline system ID/unclean state/existing postmaster marker/configuration redirect/unavailable port, then verifies online identity and the DB marker before migration. Historical PIDs are not restart identity. Tests exercise rejection before connection/port check and closure of mismatched online connections.
- The live wrapper keeps PostgreSQL under one bounded job, and executes identity-checked stop in finally. Postmaster marker, offline state and every observed API/DB port are captured. This avoids relying on an unattended server remaining alive across shell lifecycles.
- Review follow-up: start records launch state before spawning and saves the new PID before marker verification. Failed verification triggers cleanup only after an independent server-identity recheck; uncertain identity is left as cleanup_required, never falsely stopped. A separate live fault-injection run exercises this path without changing the DB marker. Two additional live regressions cover owner-initiated project ownership transfer; the original85 remain unchanged.
- No worker, frontend, shared coordination tracker or application environment file belongs to this slice. Worker DB guard remains active; successful queue/compute and full version-save/freeze remain follow-up work.

## Official references read

- PostgreSQL17 CREATE POLICY: https://www.postgresql.org/docs/17/sql-createpolicy.html — USING applies to existing rows, WITH CHECK to inserted/updated rows; policies of different commands combine for required access.
- SQLAlchemy2 asyncio, Preventing Implicit IO: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession — eager relationship loading with selectinload in an awaited query.
- Repository requirements: docs/brief/MASTER_PROJECT_BRIEF_SUMMARY.md lines44–46 (independent axes), line125 (public read-only); docs/adr/ADR-003_Workspace_and_Access_Model.md lines90–99 (illustrative policy being corrected).

See REPORT.md for final counts, diff/hash evidence and remaining limitations.
