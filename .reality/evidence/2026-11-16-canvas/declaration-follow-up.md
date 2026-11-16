# Declaration integrity and advisory scope follow-up — 2026-11-16

Status: IMPLEMENTED WITH WARNINGS. Normal shell execution recovered after the initial blocked attempts below. Final focused3 suites/33 tests and full15 suites/188 tests, production build, lint and Git diff check PASS after independent review fixes. New browser verification is unavailable; M-002 remains IN PROGRESS. Earlier15/168 logs remain historical.

## Current-source finding

The earlier concern about `handleVariablesChange` using an isolated `setVariables` reflects the pre-refactor editor. Current `frontend/src/hooks/useEquationCanvas.ts` updates declarations inside the shared canvas snapshot. `previewCanvas` derives the AST, LaTeX and local calculation from that snapshot on the next render. Invalidation advances the request ID and clears the prior finding outside the state updater. `frontend/src/app/(dashboard)/projects/[slug]/editor/page.tsx` passes this handler to the real `VariableDeclarationPanel`.

This is source evidence, not a new runtime result. No extra production-code change was needed for that reported AST-refresh issue. The existing bounded browser record observed declaration deletion clearing the AST; it does not cover all cases below.

## Regression coverage added

- `frontend/tests/equation_canvas_state.test.tsx`: under React StrictMode, remove or rename a used declaration; immediately require an undeclared-symbol diagnostic, cleared AST/LaTeX/calculation/root preview and no finding. Validation of the invalid input must not call the API. Restoring the declaration restores only the preview and sends the new unit/domain on an explicit validation.
- The same suite tests unit-only and domain-only edits while a response is pending. The AST remains identical, but the old response must be ignored **before any subsequent validation starts**. The next explicit request must carry the changed declaration.
- `frontend/tests/editor_validation_integrity.test.tsx`: use the real declaration panel to delete a used symbol while validation is pending, require an immediate error and cleared preview, resolve the old success before another request and require no restored PASS, then redeclare through the form. Require restored preview, no automatic API request, and the updated declaration in the next explicit validation payload. Graph rendering/API remain mocked; this is a component integration test, not live end-to-end evidence.

## Advisory applicability checked directly

Read these upstream pages during this follow-up:

- [React GHSA-xqc2-xf4c-x3h3](https://github.com/react/react/security/advisories/GHSA-xqc2-xf4c-x3h3): affected packages are `react-server-dom-parcel`, `react-server-dom-turbopack`, and `react-server-dom-webpack`. Patched lines include 19.0.9, 19.1.10, 19.2.9 and 19.3.1. The advisory describes server/framework conditions involving React Server Components. It does not establish that the client `react@19.0.0` package alone has this vulnerability; updating the client package alone is not evidence of a server remediation.
- [Next GHSA-673q-mjm6-r5xr](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr): affected `next` range is `>=16.0.0 <=16.4.0`, patched in 16.4.1, for the described `use cache`/typed-array behavior. Do not attribute this specific advisory to the project's Next 15 line.
- [Next November 2026 release](https://nextjs.org/blog/november-2026-security-release): identifies 15.5.29 as Maintenance LTS and 16.4.5 as Active LTS. The existing upgrade to Next/eslint-config-next 15.5.29 plus compatible React/ReactDOM 19.0.9 is a maintenance/security update within the approved major versions. The release includes conditional findings; this record does not claim every listed advisory applies to this application or that the dependency tree is free of vulnerabilities.

Package manifests were read; no package changes were made in this follow-up.

## Initial attempted verification and limits (superseded for automatic checks below)

- `D:/Reality_Science`: `git status --short` — NOT RUN. The tool could not spawn `C:/Users/TIEN PC/AppData/Local/Microsoft/WindowsApps/pwsh.exe`: `Access is denied. (os error 5)`.
- `D:/Reality_Science/frontend`: attempted command below — NOT RUN for the same pre-launch error. Jest and redirection did not start; `jest-declarations.log` was not created by this attempt.

```powershell
npm.cmd test -- --runInBand tests/equation_canvas_state.test.tsx tests/editor_validation_integrity.test.tsx *> '../.reality/evidence/2026-11-16-canvas/jest-declarations.log'
exit $LASTEXITCODE
```

- Dedicated file read confirmed the test edits. A trailing-whitespace scan of the two test files returned no matches; this is not a Git diff check, compilation or test result.
- Final full Jest/lint/build and `git diff --check` remain NOT RUN. Dev-server process identification/cleanup remains pending; it must be resolved before building against the same `.next` directory.
- OpenBot/browser namespaces were removed from the active tool catalog during this follow-up. History, existing teammate replies, browser QA and file attachment could not be retrieved through them. No alternate browser or execution path was used to bypass the launch restriction.
- A bounded independent read-only source review was requested through the available subagent route under repository `AGENTS.md`. Its eventual findings must be recorded separately from runtime verification.
- No live PostgreSQL/RLS/persistence, API authentication, numeric scientific acceptance or complete accessibility check ran. Layer 6 remains unresolved and M-002 remains IN PROGRESS.

Local writes at that initial checkpoint: the two test files and `.reality` evidence/state documents. No new test cache or test/build output was produced by the failed command.

## Completed follow-up

- Independent read-only source review found3 P2 defects: auto-layout rebuilt IDs/shared operands, a removed declaration could display a different select option, and same-batch edit/validation read the old render snapshot. Fixed these in `useEquationCanvas.ts` and `VariableNode.tsx`, with behavior tests in `equation_canvas_state.test.tsx` and `CustomNodes.test.tsx`. The re-review found all3 resolved at source level. Details in `source-review-follow-up.md`.
- Retried the focused command, adding `tests/CustomNodes.test.tsx`: PASS3 suites/33 tests8.666s, `jest-declarations.log` now exists. The earlier statement about no log refers only to the failed attempt.
- Full `npm.cmd test -- --runInBand`: PASS15 suites/188 tests20.066s, `jest-final.log`.
- `npm.cmd run lint`: PASS, no ESLint warnings/errors, only the Next lint-command deprecation notice; `lint-final.log`.
- `npm.cmd run build`: PASS, Next15.5.29, compiled4.1s, type checking and7 static pages; `build-final.log`.
- `npm.cmd ls next react react-dom eslint-config-next --depth=0`: installed Next/config15.5.29 and React/ReactDOM19.0.9, `versions-final.log`.
- Root Git status/HEAD verified `main...origin/main` at `c6062783f760f126ca87340f3c0736d11010d659`; existing dirty work retained. `git diff --check`: PASS.
- Before building, `Get-NetTCPConnection -State Listen -ErrorAction Stop` filtered to port3100 returned0 listeners. Targeted `Get-CimInstance Win32_Process` inspection found no matching project Next/Node process. No process was killed; no new dev server was started.
- PowerShell formats native stderr as `NativeCommandError` in some captured logs, even when the native exit code is0; the recorded Jest summary and build/lint completion establish the outcomes. No failing test or lint error was suppressed.
- Final writes: two application files, three test files, `.reality` state/review/source/evidence documents and logs, and test/build caches including `.next`. No live API/database/browser operation, commit, push, deployment or secret change occurred.
