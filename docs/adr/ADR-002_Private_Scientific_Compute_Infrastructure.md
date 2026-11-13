# ADR-002: Three-Tier Network Isolation & Credential-Free Compute Workers

## Status
**Approved** (Governing Mandate: Approved Decision 2)

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
Compute workers in REALITY SCIENCE execute complex symbolic algebra, numerical evaluations, and data processing. Because compute workloads process untrusted scientific user inputs, workers represent the highest risk component for system compromise.

In typical web architectures, backend APIs, background workers, and databases reside on a single flat private network, and workers are provided direct database credentials (`DATABASE_URL`) to update job status. If a worker process is exploited:
1. An attacker can connect directly to PostgreSQL, exfiltrating all user accounts, private drafts, and tamper-evident audit logs.
2. An attacker can establish outbound network connections to command-and-control (C2) servers to download malware or exfiltrate datasets.
3. An attacker can exhaust system resources or perform lateral network scanning against internal services.

### Alternatives Considered
- **Alternative 1: Flat Docker Network with Shared Database Access**: Rejected. Violates defense-in-depth; single worker exploit compromises the entire platform.
- **Alternative 2: Public Cloud Serverless Workers (AWS Lambda / Cloud Run)**: Rejected for Stage 0/MVP. Violates the requirement for a private, reproducible, self-contained scientific infrastructure, introduces third-party telemetry leakage, and complicates long-running simulation workloads.
- **Alternative 3: Multi-Zone Docker Network Topology with Credential-Free Workers**: Chosen. Strict network boundary segregation into 3 zones with zero database credentials injected into worker containers.

## Decision
1. **Three Trust Zones**:
   - **Zone 1: Cloud Edge / DMZ (`app_net`)**: Next.js frontend, KaTeX, Plotly.js, reverse proxy. Stateless. Zero database access.
   - **Zone 2: Private Core (`data_net`)**: FastAPI Modular Monolith, PostgreSQL 16+, MinIO S3 object storage, Redis broker, append-only audit log.
   - **Zone 3: Isolated Compute Sandbox (`compute_net`)**: Celery compute workers executing SymPy and Pint under strict container hardening.
2. **Network Topology Constraints**:
   - `app_net`: Isolated bridge between `web` and `api`.
   - `data_net`: Isolated internal bridge connecting `api`, `postgres`, `minio`, and `redis`. Compute workers **MUST NOT** join `data_net`.
   - `compute_net`: Isolated internal bridge connecting `api`, `redis`, and `compute_worker`. PostgreSQL and MinIO **MUST NOT** join `compute_net`.
3. **Zero Database Credentials in Worker**:
   - Compute workers receive **zero** PostgreSQL credentials (`DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` must be completely absent from worker container environments).
   - Workers communicate exclusively through Redis task queues and staged artifact buffers.
4. **Container Hardening Standards**:
   - Execution as non-root user (UID `10001:10001` or `nobody`).
   - Read-only root filesystem (`read_only: true`).
   - All Linux capabilities dropped (`cap_drop: [ALL]`).
   - Temporary write access restricted to memory-backed tmpfs (`/tmp:rw,noexec,nosuid,size=64m`).
5. **cgroups Resource Limits**:
   - CPU quota: `1.0 vCPU` (`cpus: 1.0`).
   - Memory limit: `1024 MB` hard cap (`mem_limit: 1024m`).
   - Process limit: Max 100 PIDs (`pids_limit: 100`).

```
+-----------------------------------------------------------------------------------+
| THREE-TIER NETWORK ISOLATION TOPOLOGY                                             |
|                                                                                   |
|  [app_net] (Bridge)                                                               |
|    ├── Frontend (Next.js 14+)                                                     |
|    └── FastAPI Monolith (services/api)                                            |
|                                                                                   |
|  [data_net] (Bridge - Internal - NO WORKER ACCESS)                                |
|    ├── FastAPI Monolith (services/api)                                            |
|    ├── PostgreSQL 16+ (Port 5432)                                                 |
|    ├── MinIO S3 Storage (Port 9000)                                               |
|    └── Redis Broker (Port 6379)                                                   |
|                                                                                   |
|  [compute_net] (Bridge - Internal - NO POSTGRES ACCESS)                           |
|    ├── FastAPI Monolith (services/api)                                            |
|    ├── Redis Broker (Port 6379)                                                   |
|    └── Celery Compute Worker (services/compute_worker)                            |
|             ├── Zero Postgres Credentials                                         |
|             ├── Non-Root Execution (UID 10001)                                    |
|             ├── Read-Only Root Filesystem                                         |
|             └── cgroups: 1 vCPU, 1GB RAM, 100 PIDs                                |
+-----------------------------------------------------------------------------------+
```

## Consequences

### Positive
- **Airtight Containment**: Even if a compute worker process is fully compromised via a zero-day in a scientific library, the attacker cannot reach PostgreSQL, read persistent storage, or access user credentials.
- **Exfiltration Prevention**: Workers have no route to external networks or the public internet, rendering data exfiltration and reverse shells inoperable.
- **Resource Protection**: Memory and CPU quotas prevent rogue computation from starving the host or degrading database performance.

### Negative / Trade-Offs
- **Asynchronous Result Ingestion**: The backend must handle task result persistence. The API must receive results from Redis and perform database writes inside Zone 2.
- **Multi-Network Compose Complexity**: Development and CI environments require explicit multi-network bridge definitions in `docker-compose.yml`.

### Risks & Mitigations
- **Risk**: Redis serves as a shared bridge between `data_net` and `compute_net`, potentially acting as a lateral transit vector.
  - *Mitigation*: Redis is configured with authentication. Compute workers are restricted to unprivileged queue operations (`BRPOP`, `LPUSH` on specific queue keys) and cannot execute administrative Redis commands (`CONFIG`, `SAVE`, `EVAL`).

## Compliance & Verification Rules
1. **Network Configuration Test**: Automated configuration checks must inspect `docker-compose.yml` and assert that `compute_worker` is attached only to `compute_net`.
2. **Credential Audit**: Static environment checks must assert that `compute_worker` environment contains zero variables matching `POSTGRES*` or `*DATABASE_URL*`.
3. **Network Penetration Test**: An automated container test executed inside `compute_worker` must attempt to connect to `postgres:5432` and assert that the connection fails (name resolution fails or connection times out).
4. **Non-Root Check**: Container runtime test must execute `id -u` inside worker and assert that output equals `10001`.
