# REALITY SCIENCE

> **Evidence-Driven Scientific Hypothesis & Mathematical Reality Constraint Verification Engine**

REALITY SCIENCE is an open scientific platform designed to verify mathematical equations, dimensional consistency, and empirical claims against physical constants and experimental datasets. It replaces opaque "AI scientist" speculation with formal mathematical AST validation, rigorous dimensional analysis, cryptographic version immutability, and reproducible execution pipelines.

---

## 1. Architecture Overview & Security Zones

The workspace is organized as a security-isolated monorepo adhering strictly to **ADR-001** through **ADR-006**:

```
                       ┌───────────────────────────────┐
                       │  Zone 1: Frontend (Next.js)   │
                       │   KaTeX / Tailwind / React    │
                       └───────────────┬───────────────┘
                                       │ app_net
                                       ▼
                       ┌───────────────────────────────┐
                       │   Zone 2: Backend (FastAPI)   │
                       │   Modular Monolith / IAM /    │
                       │  Research Core / Orchestrator │
                       └───────┬───────────────┬───────┘
                               │               │
                      data_net │               │ compute_net
             (internal: true)  │               │ (internal: true)
                               ▼               ▼
        ┌─────────────────────────┐         ┌─────────────────────────┐
        │ PostgreSQL 16 + RLS     │         │ Redis Broker & Conduit  │
        │ MinIO Research Artifacts│         └────────────┬────────────┘
        └─────────────────────────┘                      │ compute_net
                                                         ▼
                                            ┌─────────────────────────┐
                                            │ Zone 3: Compute Worker  │
                                            │ Celery + SymPy + Pint   │
                                            │ ZERO DATABASE ACCESS    │
                                            └─────────────────────────┘
```

- **Zone 1: `frontend/`** — Next.js 15+ App Router, TypeScript, Tailwind CSS, KaTeX mathematical expression canvas. Isolated on `app_net`.
- **Zone 2: `backend/`** — FastAPI Modular Monolith (IAM, Research Core, Reality Constraint Engine, Compute Orchestrator) backed by PostgreSQL 16 (RLS, version freeze triggers) and MinIO object storage. Bridges `app_net`, `data_net`, and `compute_net`.
- **Zone 3: `worker/`** — Sandboxed Celery compute workers executing pure mathematical ASTs (SymPy) and physical unit checking (Pint). Runs on isolated `compute_net` with **zero database credentials**, **zero SQL drivers**, and non-root UID `10001:10001`.
- **Shared Contracts: `shared/`** — Pydantic v2 data models (`ExprNode`, `VariableSpec`, `UnitSpec`, `JobBundle`, `FindingResult`).
- **Orchestration: `docker/` & `docker-compose.yml`** — Hardened multi-stage Dockerfiles, non-root execution, dropped Linux capabilities (`cap_drop: ALL`), read-only root filesystems, and segmented internal bridge networks.

---

## 2. Prerequisites

- **Python**: Python 3.11+ (Python 3.11 or 3.14 recommended)
- **Node.js**: Node.js 20+ LTS & npm (for `frontend/`)
- **Package Managers**: `uv` (recommended for fast Python dependency management) and `pip`
- **Docker**: Docker Engine 24+ and Docker Compose v2+ (for containerized execution)
- **Git**: Git 2.30+

---

## 3. Directory Layout

```
D:\Reality_Science\
├── backend/                  # Zone 2: FastAPI application & Alembic migrations
│   ├── alembic.ini           # Alembic database migration configuration
│   ├── app/                  # Application modular monolith packages
│   │   ├── api/              # API routers (root /health and /api/v1 endpoints)
│   │   ├── core/             # Configuration, logging, Redis, and security
│   │   ├── db/               # SQLAlchemy async engine, base models, migrations
│   │   └── modules/          # Domain modules (iam, research_core, etc.)
│   ├── tests/                # Unit and integration test suites
│   ├── pyproject.toml        # Backend dependencies & metadata
│   └── requirements.lock     # Fully pinned reproducible lockfile
├── worker/                   # Zone 3: Compute worker sandbox
│   ├── worker/               # Worker celery app, config, core, and tasks
│   │   ├── core/             # SymPy AST evaluator, Pint dimension engine, guards, health
│   │   └── tasks/            # Celery task definitions
│   ├── tests/                # Worker isolation & computational test suites
│   ├── pyproject.toml        # Worker dependencies (SymPy, Pint, Celery, Redis)
│   └── requirements.lock     # Pinned lockfile (strictly NO database drivers)
├── shared/                   # Shared typed AST contracts
│   ├── shared/               # Pydantic v2 schemas for expressions and job bundles
│   ├── tests/                # Unit tests for AST validation and serialization
│   ├── pyproject.toml        # Shared library metadata
│   └── requirements.lock     # Shared dependency lockfile
├── frontend/                 # Zone 1: Next.js user interface
│   ├── app/                  # Next.js App Router pages
│   ├── package.json          # Frontend dependencies (React, KaTeX, Tailwind)
│   └── package-lock.json     # Pinned npm lockfile
├── docker/                   # Hardened multi-stage container definitions
│   ├── backend.Dockerfile    # Non-root (appuser 10001:10001)
│   ├── worker.Dockerfile     # Non-root worker (10001:10001, zero libpq)
│   ├── frontend.Dockerfile   # Non-root standalone runner (nextjs 10001:10001)
│   └── redis.conf            # Hardened Redis configuration
├── docs/                     # Architectural documentation, ADRs, audits
│   ├── adr/                  # ADR-001 through ADR-006 & ADR_INDEX.md
│   ├── architecture/         # Architectural consistency audit & specifications
│   ├── security/             # SAST scan report & threat modeling
│   └── STAGE_0_COMPLETION_REPORT.md # 10-point Stage 0 completion report
├── scripts/                  # Static audit, Docker validation, and SAST runners
│   ├── run_sast_scan.py      # SAST scanner integration with D:\AI_Knowledge_Lab
│   └── validate_m3_docker_env.py # Docker compose and secret hygiene validation
└── docker-compose.yml        # Multi-zone Docker Compose orchestration
```

---

## 4. Environment Configuration

Copy the template environment files to active configuration:

```bash
# Root environment
cp .env.example .env

# Backend environment (Zone 2)
cp backend/.env.example backend/.env

# Worker environment (Zone 3 - ZERO DATABASE VARIABLES)
cp worker/.env.example worker/.env

# Frontend environment (Zone 1)
cp frontend/.env.example frontend/.env.local
```

> **Security Rule**: Never commit `.env` or production credentials to Git. The `.gitignore` file enforces exclusion of active environment files.

---

## 5. Local Setup & Virtual Environments

### 5.1 Backend Setup (Zone 2)
```bash
cd backend
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

uv pip install -r requirements.lock
# Or via pip:
pip install -r requirements.lock
```

### 5.2 Worker Setup (Zone 3)
```bash
cd worker
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.lock
```

### 5.3 Shared Library Setup
```bash
cd shared
pip install -e .
```

---

## 6. Running Tests & Quality Verification

Run all test suites across the project to ensure complete compliance:

### 6.1 Shared Contracts Suite
```bash
pytest shared/tests/ -v
```
*Validates Pydantic v2 AST node serialization, numeric string parsing, and complex number / depth defense.*

### 6.2 Worker Compute & Isolation Suite
```bash
pytest worker/tests/ -v
```
*Validates SymPy AST evaluation, Pint dimensional consistency, exponential complexity bomb guards, worker health checks, and strict Anti-Database Guard invariants.*

### 6.3 Backend API & Database Suite
```bash
backend\.venv\Scripts\pytest.exe backend\tests -v
```
*Validates IAM password hashing, root /health endpoints, relational SQLite emulation for version freeze triggers and actor erasure, and static Alembic DDL generation.*

### 6.4 Offline Database Migration SQL Generation
```bash
cd backend
uv run --with greenlet alembic upgrade head --sql
```
*Emits the complete PostgreSQL 16 DDL migration script including Row-Level Security (`ALTER TABLE ... FORCE ROW LEVEL SECURITY`), version freeze trigger, and research actor constraints.*

### 6.5 Docker & Network Isolation Audit
```bash
python scripts/validate_m3_docker_env.py
```
*Runs 31 static verification checks confirming multi-network definitions, internal network flags, non-root user IDs, read-only root filesystems, tmpfs mount security, and secret hygiene.*

### 6.6 Static Application Security Testing (SAST)
```bash
python scripts/run_sast_scan.py
```
*Executes the official AI Knowledge Lab security scanner (`D:\AI_Knowledge_Lab\tools\secure_coding_scanner`) against `shared/`, `worker/`, and `backend/` for OWASP Top 10 vulnerabilities and Shannon entropy secret detection.*

---

## 7. Health Check Endpoints & Monitoring

### 7.1 Backend API (Zone 2)
The backend exposes comprehensive health check endpoints:
- `GET /health` — Root health check reporting service status, version (`0.1.0`), and component statuses:
  ```json
  {
    "status": "healthy",
    "service": "reality-science-api",
    "version": "0.1.0",
    "environment": "development",
    "components": {
      "api": "healthy",
      "database": "configured",
      "redis": "configured",
      "compute_worker_conduit": "ready"
    }
  }
  ```
- `GET /health/db` — Deep check verifying active PostgreSQL database connectivity.
- `GET /health/redis` — Deep check verifying active Redis conduit connectivity.
- `GET /api/v1/health` — Backward-compatible API v1 ping check.

### 7.2 Compute Worker (Zone 3)
The worker provides both programmatic and CLI health verification:
```bash
cd worker
python -m worker.core.health
```
Reports operational status, compute engine versions (SymPy, Pint), and verifies that the Anti-Database Guard is intact. Exits with returncode `0` when healthy.

---

## 8. Running with Docker Compose

To launch the complete multi-zone environment locally:

```bash
docker compose up --build
```

Services started:
- `rs_frontend` on `http://localhost:3000` (`app_net`)
- `rs_backend_api` on `http://localhost:8000` (`app_net`, `data_net`, `compute_net`)
- `rs_postgres` on `localhost:5432` (`data_net`, internal)
- `rs_redis` on `localhost:6379` (`data_net`, `compute_net`)
- `rs_minio` on `localhost:9000` / Console on `localhost:9001` (`data_net`, internal)
- `rs_compute_worker` background Celery worker (`compute_net`, internal)

---

## 9. Security Mandates & Non-Negotiable Invariants

1. **Zero Database Invariant in Worker (ADR-002)**: Compute workers must NEVER have database credentials or direct network access to PostgreSQL. Inter-zone data flow occurs strictly via Redis task queues and pre-signed MinIO URLs issued by the backend.
2. **Strict Mathematical ASTs (ADR-001)**: All mathematical expressions are parsed and represented as strict `ExprNode` trees. Arbitrary code execution (`eval`, `exec`, arbitrary shell commands) is forbidden.
3. **Scholarly Lineage & Right to Erasure (ADR-003)**: User accounts and research actors are separate relational entities. When a user account is deleted, `research_actors.user_account_id` is set to `NULL`, preserving the immutable scientific version history while honoring GDPR right to erasure.
4. **Frozen Immutability (ADR-003)**: Once a research version is marked `is_frozen = true`, PostgreSQL database triggers abort any update or deletion.
