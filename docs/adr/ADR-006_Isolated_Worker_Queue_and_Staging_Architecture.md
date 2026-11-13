# ADR-006: Staged Payload Broker Pattern for Asynchronous Compute Jobs

## Status
**Approved**

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
A fundamental architectural paradox was discovered during consistency auditing (FIND-001):
- Architecture Doc 3 mandated that compute workers run with `--network=none` for total isolation.
- Architecture Doc 2 depicted compute workers pulling jobs from Redis, uploading simulation artifacts to MinIO, and calling the API gateway.
- A container running with `--network=none` has only the loopback interface (`127.0.0.1`); it cannot connect to Redis (`redis:6379`) or MinIO (`minio:9000`).

Furthermore, Stage 0 Requirement R2 mandates:
- Workers must receive **zero direct PostgreSQL credentials**.
- Workers must communicate exclusively through authorized queues, storage abstractions, and staged input/output artifacts.

If compute workers are permitted to connect directly to PostgreSQL or make unconstrained network calls, any vulnerability in mathematical parsing or scientific libraries could lead to complete platform database compromise or data exfiltration.

### Alternatives Considered
- **Alternative 1: True `--network=none` with Host Filesystem Polling**: Rejected. Requires fragile host directory bind mounts, complex file locking, and risks concurrent write corruption.
- **Alternative 2: Workers with Direct Database Connections**: Rejected. Violates Requirement R2; grants workers direct access to user PII and system tables.
- **Alternative 3: Staged Payload Broker Pattern over Isolated Bridge**: Chosen. The Celery worker runs in a dedicated `compute_net` Docker bridge connected exclusively to Redis, processing self-contained staged payloads with zero database access.

## Decision
1. **Self-Contained Staged Payload Pattern**:
   - Mathematical verification tasks are completely self-contained. The FastAPI backend extracts the relevant AST (`ExprNode`), declared variables (`VariableSpec`), and units (`UnitSpec`), packages them into a self-contained JSON `JobBundle`, and pushes it to Redis queue `compute_tasks`.
   - The worker evaluates the mathematical AST purely in memory using pinned SymPy and Pint. It requires **zero database connections**, zero external network calls, and zero MinIO uploads for mathematical verification.
2. **Dedicated Queue Network (`compute_net`)**:
   - The worker container attaches strictly to `compute_net`.
   - It possesses network connectivity only to the Redis broker on port 6379.
   - It has **zero routing** to PostgreSQL, MinIO, the frontend, or the public internet.
3. **Decoupled Result Ingestion**:
   - The worker produces a structured `FindingResult` and writes it to Celery's result backend in Redis or a dedicated completion queue (`compute_results`).
   - The FastAPI backend (inside Zone 2) listens for task completion, validates the result schema, and writes findings to `validation_findings` and `validation_runs` in PostgreSQL.
   - The worker never performs database writes.
4. **Staging Architecture for Heavy Datasets (Stage 2+ Simulations)**:
   - When simulation workloads in future stages require large dataset files:
     - Workers never receive MinIO credentials.
     - The backend generates short-lived, read-only S3 presigned download URLs or stages input files into an ephemeral staging directory.
     - The worker writes simulation outputs to a local staging volume.
     - A backend ingestion service verifies artifact hashes and transfers verified artifacts to permanent object storage.

```
+-----------------------------------------------------------------------------------+
| STAGED PAYLOAD BROKER PATTERN                                                     |
|                                                                                   |
|  [ZONE 2: CONTROL CORE]                                                           |
|    FastAPI Backend                                                                |
|       │  1. Extract AST + Variables + Units                                       |
|       │  2. Package into JSON JobBundle                                           |
|       ▼                                                                           |
|    Redis Broker [compute_tasks queue]                                             |
|       │                                                                           |
|       │  3. Celery Task Dispatch (over compute_net)                               |
|       ▼                                                                           |
|  [ZONE 3: ISOLATED COMPUTE SANDBOX]                                               |
|    Celery Worker (SymPy & Pint)                                                   |
|       │                                                                           |
|       │  4. Pure in-memory AST Evaluation (No DB, No Internet)                    |
|       │  5. Generate FindingResult (PASS / FAIL / WARNING / etc.)                 |
|       ▼                                                                           |
|    Redis Broker [Celery Result Backend]                                           |
|       │                                                                           |
|       │  6. Ingestion Listener (over data_net)                                    |
|       ▼                                                                           |
|  [ZONE 2: CONTROL CORE]                                                           |
|    FastAPI Backend                                                                |
|       │                                                                           |
|       │  7. Write Findings & Update Status in PostgreSQL                          |
|       ▼                                                                           |
|    PostgreSQL 16+ (validation_findings, validation_runs)                          |
+-----------------------------------------------------------------------------------+
```

### Job Bundle Contract Schema
```python
from typing import List, Optional
from pydantic import BaseModel
from shared.schemas import ExprNode, VariableSpec, UnitSpec

class JobBundle(BaseModel):
    job_id: str
    version_id: str
    target_entity_type: str  # 'EQUATION', 'VARIABLE', 'CLAIM'
    target_entity_id: str
    expression_ast: ExprNode
    variables: List[VariableSpec]
    units: List[UnitSpec]
    timeout_seconds: int = 10

class FindingResult(BaseModel):
    job_id: str
    state: str  # 'PASS', 'FAIL', 'WARNING', 'NOT_APPLICABLE', 'INSUFFICIENT_DATA', 'NEEDS_EXPERT_REVIEW', 'NOT_YET_TESTED'
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool
    diagnostics: List[str] = []
```

## Consequences

### Positive
- **Resolves the Network Paradox**: Provides an elegant, secure solution enabling worker task receipt without exposing databases or granting external internet access.
- **Zero Database Attack Surface**: Complete elimination of database credential leakage risk from worker containers.
- **100% Deterministic & Unit-Testable**: Job bundles are self-contained JSON payloads; worker functions can be unit-tested in complete isolation without running a database or network.

### Negative / Trade-Offs
- **Double Serialization**: ASTs and findings are serialized to JSON twice (API -> Redis -> Worker -> Redis -> API).
- **Payload Size Limits**: Redis queues are optimized for payloads under 10 MB. Large simulation datasets require volume staging rather than in-memory queue payloads.

### Risks & Mitigations
- **Risk**: Redis memory exhaustion from uncollected job results.
  - *Mitigation*: Configure Celery task result expiration (`result_expires = 3600`), set maximum memory policies on Redis (`maxmemory 512mb`, `maxmemory-policy volatile-lru`), and purge processed task results immediately after backend database ingestion.

## Compliance & Verification Rules
1. **Worker Isolation Integration Test**: Submit a `JobBundle` to Celery via Redis; verify worker executes task and returns `FindingResult` to Redis without establishing any database connection.
2. **Zero-Postgres Environment Assertion**: Test running in worker environment verifying `os.environ` contains no database keys and attempting `psycopg2.connect` raises an immediate configuration error.
3. **Result Ingestion Test**: Verify backend listener reads `FindingResult` from Redis and correctly persists findings to `validation_findings` table in PostgreSQL.
