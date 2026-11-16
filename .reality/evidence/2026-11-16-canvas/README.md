# Local canvas integrity verification

Latest report receipt: `analyst-relay-parent.md` records the parent's received original analyst relay, its8 proposed groups mapped to existing executed coverage, unchanged71 hashes and remaining live acceptance gaps. Any earlier pending-receipt wording is historical.

Scope: single-expression whole-canvas preflight, pure editor state, stale-result protection, Next 15 and React 19.0 compatible patches. Test/build logs in this directory are local source evidence only; they do not establish deployed behavior, live database persistence, or scientific validation through a live API.

Commands and final results are recorded in `.reality/EXECUTION_LOG.md`.

- `npm-install.log`: completed compatible frontend package installation.
- `jest-full.log`: 15 suites / 168 tests PASS before the final auto-layout, Navbar/login and additional-test edits.
- `build.log`: Next 15.5.29 production build PASS at that same pre-final checkpoint.
- `lint.log`: no ESLint warnings or errors at that checkpoint; Next's lint-command deprecation notice is informational.
- `dev-server.log`: local dev server startup/compilation.
- `browser-checks.md`: earlier browser behavior, responsive measurements, screenshots and limitations before the last source-review fixes.
- `declaration-follow-up.md`: declaration-change/stale-response regressions, directly checked advisory applicability, initial blocked attempts and subsequent successful verification.
- `source-review-follow-up.md`: three independent source findings, their fixes and successful bounded source re-review.
- `jest-final.log`: final full frontend run, 15 suites / 188 tests PASS after the review fixes.
- `jest-declarations.log`: focused declaration/layout/state/custom-node run, 3 suites / 33 tests PASS (PowerShell UTF-16 output; readable with `Get-Content`).
- `lint-final.log`: no ESLint warnings or errors on the reviewed final source; `next lint` deprecation notice remains informational.
- `build-final.log`: final Next15.5.29 production build PASS, type check and all7 static pages complete.
- `versions-final.log`: final installed package-version check.
- `verified-source-sha256.txt`: hashes of the verified hook/converter/editor/variable control, Navbar/login, focused tests and dependency manifests, recorded after the final build so later edits can be distinguished from this checkpoint.

- `parent-verification-attempts.md`: original blocked attempts, verified one-line global shell repair, identified dev-server cleanup and historical183-test/build checkpoint superseded after concurrent source edits.
- `review-integrated-parent.md`: stable parent full15/188 in18.237s, lint/build/diff PASS and exact limits; application inputs remain unchanged after later test additions.
- `source-checkpoint-review-integrated.json`:71 input hashes captured before parent verification; post-build comparison confirms unchanged content and membership.
- `jest-review-integrated-parent.log`, `lint-review-integrated-parent.log`, `build-review-integrated-parent.log`: parent outputs for the stable188-test build checkpoint, each native exit0.
- `final-integrity-parent.log`: source/membership comparison, Git diff and port cleanup evidence.
- `browser-review-integrated-parent.md`: focused desktop browser run on latest production build; removed-symbol/redeclaration, shared-DAG layout, real connection refusal and extra-root request blocking PASS with automation limits recorded.
- `production-browser-parent.log`: local port3101 test-server log; includes existing standalone-output startup warning. Server later intentionally stopped.
- `test-expansion-parent.md`: subsequent test-only additions; full219 PASS, then final editor20 PASS after that test changed during the full run. Types/affected-file lint PASS; exact scope and writes recorded.
- `source-checkpoint-test-expansion-parent.json`, `source-checkpoint-test-expansion-final-parent.json`: separate71-input checkpoints before those checks; final hashes/membership remained unchanged.
- `jest-test-expansion-parent.log`, `typecheck-test-expansion-parent.log`, `lint-test-expansion-parent.log`: full219/types/three-file lint outputs.
- `jest-editor-final-parent.log`, `typecheck-editor-final-parent.log`, `lint-editor-final-parent.log`, `integrity-test-expansion-final-parent.log`: final focused editor20/types/lint and stable-input evidence.
- `analyst-reconciliation.md`: bounded owner handoff, received original Analyst/Reviewer reports, all8 proposed groups mapped to executed coverage, fixture failure/fix and remaining limits.
- `jest-analyst-focused.log`, `jest-analyst-full.log`: separate owner final runs after all test edits, PASS3/104 in13.876s and15/219 in16.587s. These are not the parent's219/20 checkpoints.
- `types-analyst.log`, `lint-analyst.log`: expanded-test TypeScript exit0/no diagnostics and full lint exit0/no ESLint errors; TypeScript log intentionally empty.
- `analyst-source-checkpoint.json`, `analyst-parent-checkpoint-comparison.json`: owner final hashes compared with earlier inputs; only3 tests changed, application/config/package inputs match the prior build. Current71 hashes also match the parent's final focused checkpoint.

Earlier pre-launch WindowsApps `pwsh.exe` OS5 failures were resolved by the parent adding the supported global `shell` setting for System32 Windows PowerShell; this was verified repeatedly, not unexplained retry recovery. Parent stopped the identified old port3100 dev tree, then the owner observed zero listeners. Parent browser integration worked despite the owner's catalog limitation; focused browser checks completed and its port3101 server/tab were cleaned up. Both original Change Reviewer and Test Analyst reports are received and reconciled; owner final104/219 runs and handoff are documented. M-002 remains IN PROGRESS for live API/persistence/RLS/scientific/accessibility/homepage and Layer6 acceptance.

Sources used to select compatible patches and pure-state rules:

- https://nextjs.org/blog/november-2026-security-release — Next 15.5.29 maintenance release.
- https://registry.npmjs.org/next/15.5.29 and https://registry.npmjs.org/eslint-config-next/15.5.29 — matching package versions and peers.
- https://api.github.com/repos/facebook/react/releases/tags/v19.0.9 — official React 19.0.9 release, 2026-10-14.
- https://registry.npmjs.org/react/19.0.9 and https://registry.npmjs.org/react-dom/19.0.9 — ReactDOM requires React ^19.0.9.
- https://react.dev/reference/react/useState — updater purity and StrictMode replay.

Advisory scope clarification: GHSA-xqc2-xf4c-x3h3 concerns the `react-server-dom-*` packages under server/framework conditions, not the client `react` package alone. Next GHSA-673q-mjm6-r5xr lists versions 16.0.0–16.4.0; it is not evidence for that specific flaw in Next 15. Treat the installed patch set as a compatible maintenance/security update, with application-specific advisory applicability assessed separately. Exact upstream links and observations are in `declaration-follow-up.md`.
