# Project: REALITY SCIENCE

## Mission
Evidence-Driven Scientific Platform establishing an epistemically sound, mathematically rigorous, reproducible framework for computational reality constraints.

## Architecture
- **Zone 1: Cloud Edge**: Public Next.js frontend, API Gateway, TLS termination, CDN static caching.
- **Zone 2: Private Core**: FastAPI Modular Monolith, PostgreSQL 16+ with session-based Row-Level Security (RLS), Redis Broker.
- **Zone 3: Isolated Compute Sandbox**: Celery compute workers in isolated network (`compute_net`), zero direct PostgreSQL access, non-root execution, cgroups resource and time limits, executing typed mathematical AST via pinned SymPy and Pint.

## Approved Architectural Decisions (Decisions 1–4)
1. **Decision 1: Structured Mathematical Input**
   - Symbol-First Authoring: Variables (`VariableSpec`) and units (`UnitSpec`) declared before equations.
   - Equations parsed into typed Abstract Syntax Tree (`ExprNode`).
   - Strict ban on `eval()`, `exec()`, and raw script execution. SymPy and Pint evaluate only validated AST nodes.
2. **Decision 2: Private Scientific Compute Infrastructure with Strict Network Isolation**
   - Workers reside in dedicated `compute_net` with zero route to PostgreSQL or external internet.
   - Zero PostgreSQL credentials (`DATABASE_URL`, `POSTGRES_*`) injected into compute workers.
   - Communication exclusively via Redis task queues and staged artifact buffers.
3. **Decision 3: Workspace and Access Model**
   - Identity Split: `user_accounts` (PII encrypted with AES-256-GCM) separated from `research_actors` (pseudonymous academic handle).
   - Right-to-erasure sets `user_account_id = NULL` without corrupting academic citation lineage.
   - Two MVP visibility states: `private_draft` and `public_preprint`.
   - Nullable `organization_id` prepared for multi-tenant institutional governance.
   - PostgreSQL Row-Level Security (RLS) enforced across all project and child entity tables.
4. **Decision 4: Official Project Location**
   - Authorized root workspace: `D:\Reality_Science\`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Reference Architecture Preservation | Preserve 3 architecture documents verbatim in `docs/architecture/` and Master Brief in `docs/brief/` | M1 | Request R1 |
| 2 | Architecture Consistency Audit Report | Comprehensive audit analyzing FIND-001 through FIND-010 across the architecture docs | M1 | Request R1 |
| 3 | Architecture Decision Register (ADR) | Formal ADR index documenting Approved Decisions 1-4 and ADR-001 through ADR-006 | M1 | Request R1 |
| 4 | Workspace Pre-Flight & Preservation | Verify Drive D:, inventory existing workspace, preserve all files | M2 | Request R2 |
| 5 | Clean Directory Boundary Scaffolding | Establish frontend/, backend/, worker/, shared/, docs/ boundaries | M2 | Request R2 |
| 6 | Compute Worker Security Isolation | Non-root execution, CPU/memory/PIDs limits, zero PostgreSQL credentials | M2 | Request R2 |
| 7 | Multi-Zone Docker Network Isolation | Define `app_net`, `data_net`, `compute_net` network zones | M3 | Request R3 |
| 8 | Zero-Secret Environment Templates | Provide `.env.example` templates for all services without committed secrets | M3 | Request R3 |
| 9 | Pinned Dependency Management | Reproducible lockfiles/requirements across frontend, backend, worker | M3 | Request R3 |
| 10 | Dockerfile Static Validation & Local Runner | Static checks for container definitions and local run scripts when Docker unavailable | M3 | Request R3 |
| 11 | Typed Mathematical AST Models | Pydantic v2 `ExprNode`, `VariableSpec`, `UnitSpec` models rejecting arbitrary code | M4 | Request R4 (Dec 1) |
| 12 | SymPy & Pint Validation Engine | Unit tests validating dimensional consistency and symbolic equivalence via pinned libraries | M4 | Request R4 (Dec 1) |
| 13 | Identity Split & PII Separation | Schema separating `user_accounts` from `research_actors` with right-to-erasure | M4 | Request R4 (Dec 3) |
| 14 | Version Snapshot Freeze Trigger | PostgreSQL trigger `trg_freeze_research_versions` preventing edit of frozen preprints | M4 | Request R4 (Dec 3) |
| 15 | Row-Level Security (RLS) Policies | Enforced RLS for `private_draft` vs `public_preprint` with `owner_actor_id` | M4 | Request R4 (Dec 3) |
| 16 | SAST Security Scanner Integration | Run static application security testing using `D:\AI_Knowledge_Lab\tools\secure_coding_scanner\` | M5 | Request R4 |
| 17 | Service Health Checks | Implement backend and worker health check endpoints and Docker health checks | M5 | Request R4 |
| 18 | Stage 0 Verification Suite Execution | Execute all unit, integration, and security tests reporting honest results | M5 | Request R5 |
| 19 | 10-Point Stage 0 Completion Report | Author exhaustive 10-point report halting strictly at Stage 0 | M5 | Request R5 |
| 20 | Developer Onboarding Documentation | Local setup, testing, and deployment instructions in README.md | M5 | Request R5 |
| 21 | RCE Layer 1 Syntax Engine | Extended mathematical AST parser for advanced operators | Stage 1+ | Doc 3 §1 |
| 22 | RCE Layer 2 Dimension Engine | Comprehensive dimensional ontology with 100+ physical units | Stage 1+ | Doc 3 §1 |
| 23 | RCE Layer 3 Boundary Engine | Numerical stability, asymptote, and singularity detection | Stage 1+ | Doc 3 §1 |
| 24 | RCE Layer 4 Physical Laws | Fundamental physics invariants (energy conservation, speed of light) | Stage 2+ | Doc 3 §1 |
| 25 | RCE Layer 5 Empirical Data | Observation dataset correlation against CERN, NASA, NIST data | Stage 2+ | Doc 3 §1 |
| 26 | RCE Layer 6 Epistemic Logic | Cross-claim contradiction graphs and circularity detection | Stage 3+ | Doc 3 §1 |
| 27 | Interactive Symbolic Canvas UI | Next.js visual node-based mathematical authoring canvas | Stage 1+ | Doc 1 §3 |
| 28 | Open Research ZIP Exporter | Zero lock-in cryptographic zip bundle export | Stage 1+ | Doc 2 §2 |
| 29 | Outbox Event Publisher | Debezium / Kafka transactional outbox relay | Stage 1+ | Doc 2 §3 |
| 30 | WireGuard mTLS Private Cluster | Hybrid multi-cloud node orchestration | Stage 2+ | Doc 3 §4 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Architecture Audit & ADRs | Preserve reference docs, generate consistency audit report, write comprehensive ADRs | none | DONE |
| M2 | Workspace Scaffolding & Isolation | Git init, directory structure, worker boundary configs with zero Postgres credentials | M1 | DONE |
| M3 | Environment & Docker Orchestration | .env.example, pinned dependencies, multi-zone Docker Compose, static validations | M2 | IN_PROGRESS |
| M4 | Math Contracts & RLS Database Schemas | Typed AST models, SymPy/Pint tests, PostgreSQL DDL migrations, RLS test suite | M3 | PLANNED |
| M5 | Security QA & Stage 0 Report | SAST scan, health check endpoints, test execution, comprehensive 10-point report | M4 | PLANNED |

---

## Interface Contracts

### 1. Decision 1: Mathematical AST Contract
```python
class UnitSpec(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    symbol: str
    dimensionality: str  # e.g., '[length] ** 2 / [time]'
    scale_factor: float = 1.0

class VariableSpec(BaseModel):
    symbol: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    name: str
    unit: str
    domain: Literal["real", "positive_real", "integer", "complex"] = "real"
    latex_presentation: Optional[str] = None

class ExprNode(BaseModel):
    node_type: Literal["constant", "variable", "binary_op", "unary_op", "function_call"]
    value: Optional[Union[float, int, str]] = None
    op: Optional[Literal["+", "-", "*", "/", "**", "neg", "sqrt", "sin", "cos", "exp", "log"]] = None
    left: Optional["ExprNode"] = None
    right: Optional["ExprNode"] = None
    args: Optional[List["ExprNode"]] = None
```

### 2. Decision 2: Compute Worker Job Bundle
- Format: JSON payload passed via Redis queue or staging storage.
- Payload schema:
  - `job_id`: UUID
  - `expression_ast`: `ExprNode`
  - `variables`: List[`VariableSpec`]
  - `units`: List[`UnitSpec`]
  - `timeout_seconds`: int (max 10s interactive, 120s batch)
- Return schema:
  - `finding_status`: `Literal['PASS', 'FAIL', 'WARNING', 'NOT_APPLICABLE', 'INSUFFICIENT_DATA', 'NEEDS_EXPERT_REVIEW', 'NOT_YET_TESTED']`
  - `symbolic_simplification`: Optional[str]
  - `dimensions_verified`: bool
  - `diagnostics`: List[str]

### 3. Decision 3: Identity Split & RLS
- Session context: `SET LOCAL app.current_actor_id = '<uuid>';`
- RLS Policy on `research_projects`:
  - `owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID` OR `visibility = 'public_preprint'`

---

## Code Layout
```
D:\Reality_Science\
├── .agents/                    # Coordination metadata (read-only to app code)
├── docs/                       # Architecture, Briefs, ADRs, and QA documentation
│   ├── adr/                    # Architecture Decision Register (ADR-001 through ADR-006)
│   ├── architecture/           # Preserved baseline architecture documents & consistency audit
│   └── brief/                  # Preserved Master Project Brief summary
├── shared/                     # Shared type definitions and mathematical AST schemas
│   ├── schemas/                # Pydantic v2 AST schemas (ExprNode, VariableSpec, UnitSpec)
│   └── models/                 # Shared data contract definitions
├── backend/                    # Python 3.11+ FastAPI modular monolith
│   ├── app/
│   │   ├── api/                # FastAPI routes & health checks
│   │   ├── core/               # App configuration, security, session management
│   │   ├── db/                 # Database migrations, models, session provider
│   │   └── modules/            # Modular domain sub-packages (projects, versions)
│   ├── tests/                  # Backend unit, integration, and RLS database tests
│   └── pyproject.toml          # Pinned backend dependencies
├── worker/                     # Isolated Celery compute worker (Zone 3)
│   ├── tasks/                  # Celery mathematical verification tasks
│   ├── core/                   # SymPy & Pint AST evaluation engine (NO eval/exec)
│   ├── tests/                  # Worker AST, dimensional, and isolation unit tests
│   └── pyproject.toml          # Pinned worker dependencies (ZERO Postgres drivers)
├── frontend/                   # Next.js 15+ TypeScript frontend (Zone 1)
│   ├── src/                    # React components, pages, client libraries
│   ├── tests/                  # Frontend unit and component tests
│   └── package.json            # Pinned frontend dependencies
├── docker/                     # Dockerfiles and container configurations
├── docker-compose.yml          # Multi-zone Docker Compose orchestration
└── .env.example                # Zero-secret environment template
```
