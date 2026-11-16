# Selected final live check — NOT RUN

Command through `scripts/disposable_postgres.py test`, selecting force_rls, read visibility, insert persistence, actor context and exception rollback cases, stopped in runner `admin_connection` before pytest started.

Exact failure: `ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection` at `asyncpg.connect` for the task manifest's loopback60655.

No `selected-live-final.log` was produced because `execute(pytest)` was never reached. A subsequent read-only identity capture attempt had the same connection-refused result. Process/listener inspection confirmed the task cluster was stopped with stale PID11164. `cleanup.log` records verified recovery/read-only metadata capture/clean shutdown. Do not count the selected cases as PASS or an assertion FAIL.
