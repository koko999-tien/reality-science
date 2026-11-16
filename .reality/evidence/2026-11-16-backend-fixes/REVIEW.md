# Independent read-only review

Reviewer child session: `ses_e1b442c1cffe4gFO0QW271Dhmd`, requested under repository AGENTS.md§36–37. Reviewer inspected source only, no writes, test execution or DB/process operations.

Initial finding P2: pg_ctl start could succeed, then marker/identity/PID verification fail before saving manifest. The cluster would remain running while the manifest still said stopped and retained a historical PID.

Owner fix: extracted start_cluster lifecycle. Before spawning it removes historical postmaster_pid and records stopped=false/starting. It records fresh current PID before marker verification. Failure persists cleanup_required; shutdown first rechecks core server system ID/path/port and the fresh postmaster marker. A DB marker mismatch still prohibits DB writes; a confirmed task-owned server can be stopped. An uncertain server identity refuses shutdown and leaves explicit cleanup_required evidence. Clean shutdown sets stopped=true/stopped.

Added four command lifecycle regressions: successful launch replaces old PID; marker-verification failure cleans up; first PID read failure cleans up after fresh verification; server-identity mismatch prevents stop and preserves the uncertain state. Together with prior guards, runner unit suite22 PASS. Live fault injection evidence is in restart-failure-check/; this is a harness failure injection, not a scientific compute mock.

Reviewer coverage gap: original85 live cases protected the new parent on7 child tables but omitted owner-initiated research_projects.owner_actor_id transfer. Added separate test_decision3_project_owner_transfer.py, private/public cases; original85 remain byte-for-byte unchanged.

Initial reviewer found no further issue in the bounded application changes: SELECT semantics preserved; owner OLD/NEW on8 tables; ENABLE/FORCE retained; revision<=32; eager versions loading after commit; publication assignment removed. Reviewer explicitly excluded persisted publication success because Stage4 uses an in-memory session and the live history path stops at503.

Re-review result: **P2 addressed; no remaining correctness findings in the scoped re-review.** Reviewer confirmed lifecycle state/PID are saved before verification, cleanup independently verifies cluster identity and marker, uncertain identity refuses shutdown, and NEW-owner regression covers42501 plus fresh-connection unchanged ownership. Review remained static and did not independently execute22 unit checks.

Owner subsequently executed the actual failure path: restart-failure-check/result.json confirms injected post-start verification exception, real identity-checked shutdown and no DB marker mutation. Review-live/owner-transfer.log reports2 PASS. Final backend default210 PASS/87 SKIP in backend-default-final.log. These are owner execution results, separate from the reviewer source verdict.
