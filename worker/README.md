# REALITY SCIENCE — Isolated Compute Worker (`worker/`)

## Architecture & Security Model
The compute worker runs in **Zone 3 (Compute Sandbox)** under strict process and network isolation:
- **Zero Database Invariant**: Compute workers have zero database credentials and zero database drivers installed. Any attempt to supply database credentials triggers a fatal configuration violation at startup.
- **Network Isolation**: Compute workers join strictly `compute_net`, connecting only to Redis. They have no network path to relational databases or object stores.
- **Least-Privilege Execution**: Containers run under dedicated non-root UID `10001:10001` with a read-only root filesystem, dropped Linux capabilities (`ALL`), and `no-new-privileges: true`.
- **Resource Boundaries**: Hard cgroups quotas bound CPU (1.0 vCPU), memory (512MB RAM), and processes (100 PIDs). Execution timeouts enforce a 10s interactive limit and 120s batch limit.
- **Programmatic SymPy AST**: Mathematical formulas are parsed from typed Pydantic `ExprNode` trees without ever using Python's `eval()` or `exec()`.

## Directory Layout
- `worker/core/`: Mathematical evaluation engine, Pint dimension checker, and AST complexity guards.
- `worker/tasks/`: Celery task definitions receiving `JobBundle` and emitting `FindingResult`.
- `worker/config.py`: Worker configuration with pre-flight zero database credential validation.
- `tests/`: Worker isolation test suite, AST evaluation tests, and complexity limit tests.
