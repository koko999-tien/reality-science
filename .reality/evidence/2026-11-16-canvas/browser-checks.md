# Current-tree browser checks — 2026-11-16

Environment: OpenBot private Chromium tab `8e47af85-ccec-4926-94a5-663b10aea2d4`; local Next 15.5.29 development server at `http://127.0.0.1:3100`. The server command set process-local `NEXT_PUBLIC_API_URL=http://127.0.0.1:1/api/v1`; no env file was edited. Chromium rejects this port (`net::ERR_UNSAFE_PORT`), producing a real browser fetch failure without contacting a backend. These checks cover transport failure, not a live API response or a TCP connection-refused response.

## Observed behavior

| Check | Result | Evidence |
|---|---|---|
| Homepage keyboard tabs | PASS | Click Kinematics, ArrowRight: focused and selected tab both Newton's second law; linked panel renders F=ma and declared quantities |
| Initial narrow-width check | FAIL, then fixed | At 320px homepage scrollWidth was 391px; overflowing elements were global Navbar links. Added flex wrapping to Navbar |
| Homepage and editor document width after fix | PASS | Measured all five widths below; document width equals available client width |
| Project lookup fetch failure | PASS (bounded offline behavior) | `/projects/local-qa/editor` displays explicit lookup failure, Local equation draft and non-persistence copy; badge NOT YET TESTED |
| Validation fetch failure | PASS | Validate AST returns `Canvas Notice: Failed to fetch`; badge NOT YET TESTED, no scientific finding |
| Whole-canvas ambiguous root | PASS | Add Equation Root to valid draft, then Validate AST: explicit Multiple equation roots error, AST preview absent, both result nodes show connection prompt. A pass-through fetch counter stayed at 1 after the earlier failing validation; invalid canvas sent no additional request |
| Remove a used variable | PASS for resulting state | After loading kinematics and deleting `a`, the confirmation dialog closed before handle_dialog could answer. Fresh state confirmed `a` absent, undeclared-symbol diagnostic and no AST preview. Who closed the native dialog is unknown; no assertion about dialog automation success |
| Invalid auto-layout | PASS | Auto Layout preserved the undeclared-symbol error and absent preview |
| Preset restoration and layout | PASS | Reload kinematics then Auto Layout: valid AST preview, one equation root, no translation error, NOT YET TESTED |
| Login accessible names | PASS | `login-email` label Email Address / autocomplete username; `login-password` label Password / autocomplete current-password |
| Login failed submit | PASS (bounded offline behavior) | Synthetic fixture email `ui-probe@example.invalid` and test-only password submitted to disabled API origin: visible Failed to fetch, path remains `/login`, Authenticate enabled, email retained, no session token |
| Login keyboard focus at 320px | PASS (bounded) | Tab from Email Address focuses login-password; computed cyan focus box-shadow present; scrollWidth=305, clientWidth=305 |

## Width measurements

Scrollbar consumes 15px. For both homepage and editor, after the Navbar fix:

| window.innerWidth | document.clientWidth | document.scrollWidth |
|---:|---:|---:|
| 320 | 305 | 305 |
| 375 | 360 | 360 |
| 390 | 375 | 375 |
| 768 | 753 | 753 |
| 1440 | 1425 | 1425 |

No body overflow hiding was added. This is a document-width check; it does not establish complete graph usability on mobile, zoom behavior or visual acceptance of all sections.

## Images and limitations

- Desktop homepage before the Navbar wrap: `C:/Users/TIEN PC/OpenBot/Agents/agent-2bb14df5-9506-4184-b3ca-37c409d9961c/browser-screenshots/screenshot-2026-11-16T09-35-31-080Z-92fbcb4d.png`.
- Mobile 320px homepage after wrap: `C:/Users/TIEN PC/OpenBot/Agents/agent-2bb14df5-9506-4184-b3ca-37c409d9961c/browser-screenshots/screenshot-2026-11-16T09-52-29-935Z-e340445e.png`.
- Browser diagnostics included expected API `ERR_UNSAFE_PORT` and intermittent font `ERR_CACHE_MISS`; no claim of a clean network log. Screenshots show duplicate global/home navigation and retained FeaturePillars content; full visual acceptance is open.
- Live authenticated success, API timeout/4xx/5xx matrix, actual scientific calculations, persistence/RLS, screen-reader announcements, 200% zoom, contrast, reduced motion, and complete graph keyboard interaction were not verified here.
- Stale-success/error, overlapping requests and React StrictMode behavior have Jest evidence at the checkpoint recorded in `EXECUTION_LOG.md`; browser tests here did not mock a scientific PASS.
- The local QA tab was closed after evidence capture. The old shell subsequently completed with exit code 1; its dev log contains no shutdown diagnosis. Resumed TCP inspection found zero listeners on port 3100 (`dev-listener-status.json`), so no listener cleanup remains for that server. The separate parent verification record reports identified-process cleanup after its shell repair.
- These browser checks precede the later event-snapshot, DAG-preserving layout and undeclared-variable display changes. Current Jest/build verification must be recorded separately; the browser matrix has not been rerun for those changes.
