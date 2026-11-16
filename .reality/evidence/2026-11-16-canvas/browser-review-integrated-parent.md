# Review-integrated browser checks — parent, 2026-11-16

Scope: later undeclared-variable display and shared-DAG layout fixes, plus real browser transport failure/preflight behavior. OpenBot private Chromium tab `0703c4d1-4035-45e5-92e7-b87694ae5354`, desktop viewport about1520x730; route `http://127.0.0.1:3101/projects/local-qa/editor`.

Server: production frontend via `npm.cmd run start -- --hostname 127.0.0.1 --port 3101`, background job `sh_1e3e3f550001jtDVYXPG66Em9Q`, launcher PID13336; `production-browser-parent.log`. The parent production build succeeded before startup. No environment file changed. Port8000 had zero listeners; the compiled API URL was `http://localhost:8000/api/v1`. Unlike the earlier port1 browser run, diagnostics here explicitly show `ERR_CONNECTION_REFUSED`.

## Verified outcomes

| Scenario | Status | Direct observations |
|---|---|---|
| Failed project lookup | PASS | GET `/projects/local-qa` refused; explicit lookup error, heading Local equation draft, non-persistence copy and NOT YET TESTED. |
| Used declaration removed while another remains | PASS for resulting application state | Removed `a`, explicitly selected `v`, then removed used `v` while `t` remained. Fresh DOM inspection: control value `v`, `aria-invalid=true`, disabled option `v (undeclared)`, remaining option `t (Time)`, no cached unit, explicit undeclared diagnostic, absent AST preview and NOT YET TESTED. The first deletion confirmation was accepted by the tool; the second dialog closed before the handler answered, so its closer is unknown. Resulting app state was verified independently. |
| Explicitly select a remaining declaration | PASS for application state | Selecting `v` after removing `a` produced actual value `v`, `[meter / second]`, restored AST and no invalid flag. The native select tool reported a postcondition error, but its returned snapshot and subsequent DOM inspection confirmed the requested value; the selection was not repeated. |
| Redeclare with changed metadata | PASS | Through the real form declared `v` as Length, unit meter. Same existing variable node displayed `v`, `[meter]`, no invalid flag and a restored AST; status remained NOT YET TESTED. |
| Shared-operand layout | PASS | Cleared canvas through an accepted confirmation, added constant `draft_101` and binary addition `draft_102`, connected the same output to both left/right inputs using trusted clicks on inspected handles. Formula1+1/local calculation2. Before and after Auto Layout: same two node IDs, exactly one constant input, same edge IDs `xy-edge__draft_101output-draft_102left` and `xy-edge__draft_101output-draft_102right`. |
| Edit shared operand after layout | PASS | Typed2 into constant `draft_101`; formula2+2, local calculation `R ≈ 4`, AST left/right both2. NOT YET TESTED remains; this local numeric preview is not a backend scientific finding. |
| Validation transport rejection | PASS | Validate AST on the valid shared graph: POST `/validation/verify` reports ERR_CONNECTION_REFUSED (OPTIONS ERR_FAILED), visible Failed to fetch, NOT YET TESTED. Resource Timing recorded one validation fetch. |
| Extra roots block another request | PASS | Added two explicit equation roots and clicked Validate AST. Explicit Multiple equation roots diagnostic, AST preview absent, NOT YET TESTED. Resource Timing still contained the same single validation fetch; no additional validation request appeared. |

## Automation diagnostics and limits

- A drag tool reported no native HTML drag operation, but subsequent node-position inspection showed the binary node moved. No successful drag-tool assertion is claimed. Graph connections were made through supported handle clicks and verified by actual edges/AST.
- The sticky header covered one toolbar click. After re-observing/scrolling, a fresh semantic click succeeded; no forced DOM click was used. A `Control+Home` attempt targeting body was refused as not focusable. These intermediate automation failures did not invalidate the later observed app outcomes.
- Chromium reported KaTeX font `ERR_CACHE_MISS`/fallback messages. No clean-network or full visual-render claim.
- No API successes or delayed real backend responses were fabricated. Same-batch and stale-response timing remain the Jest proof, not this browser check.
- No live authentication, database persistence/RLS, scientific known answers with units, full accessibility, mobile/zoom usability or deployed acceptance was exercised. Earlier width/login checks remain separate historical evidence; this was a focused desktop run.
- Startup emitted the existing `output: standalone` warning advising use of the standalone server entry point; `next start` nevertheless reached Ready and served the exercised routes. This local runtime run does not verify standalone deployment packaging/startup.
- The task's private tab was closed after verification. Identity-checked `next start` PID29144 matched this checkout and port3101, was stopped, and subsequent TCP inspection returned0 listeners. The background server exit1 followed intentional termination; it is not a build failure. Cleanup is in `final-integrity-parent.log`.
