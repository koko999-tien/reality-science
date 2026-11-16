# Backend fixes work log

Scope: follow-up23e7ed68, owner Lực. Baseline8 files retained before edits; no competing backend writer.

- [x] Confirm baseline hashes and current brief/ADR/source/previous failing evidence.
- [x] Add fail-closed restart of the identified stopped cluster; verify system ID, path, config, marker and current PID.
- [x] New migration004: separate visibility SELECT from owner-only INSERT/UPDATE/DELETE on8 tables.
- [x] Fix project response eager loading and add publication PASS/FAIL regressions.
- [x] Execute all85 live cases:84 PASS/1 FAIL (existing compute503); targeted88 PASS. After review, owner-transfer2 PASS, runner22 PASS and final default210 PASS/87 SKIP. Checkpoints are separate, not summed.
- [x] Independent read-only review; fix P2 restart cleanup and re-review clean.
- [x] Actual post-start failure injection cleanly shuts down identified cluster; separate owner-transfer live regressions2 PASS.
- [x] Final diff/hashes and clean-shutdown evidence verified; report ready for ALL.
- [x] Report and57-artifact ZIP queued to ALL, message8e4d4064-70fb-4357-bca6-435471cae702, replyTo23e7ed68, expectsReply=false. Backend ownership released; receipt not yet confirmed.

Implementation authority: Brief§5 public read-only overrides ADR-003 illustrative FOR ALL policy; no collaboration permissions added. Publication, validation and evidence maturity remain independent under Brief§3.
Shared coordination files remain owned by ALL. New logs only in this evidence directory.

Runtime checkpoint: migration003→004 PASS; eight exact SELECT expressions preserved, owner OLD/NEW predicates match; app role still unprivileged and marker read-only. All85 live test definitions retain their baseline hashes. Shutdown verified by offline control state, absent PID marker, closed DB60655/API51531/API51578 and fresh OS process/listener inventory.
