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
| 21 | RCE Layer 1 Syntax Engine | Extended mathematical AST parser for advanced operators & symbol-first validation | M6 | Stage 1 (Doc 3 §1) |
| 22 | RCE Layer 2 Dimension Engine | Comprehensive dimensional ontology with 100+ physical units via Pint | M6 | Stage 1 (Doc 3 §1) |
| 23 | RCE Layer 3 Boundary Engine | Numerical stability, asymptote, and singularity detection with Richardson's fallback | M6 | Stage 1 (Doc 3 §1) |
| 24 | RCE Layer 4 Physical Laws | Fundamental physics invariants (energy conservation, speed of light) | Stage 2+ | Doc 3 §1 |
| 25 | RCE Layer 5 Empirical Data | Observation dataset correlation against CERN, NASA, NIST data | Stage 2+ | Doc 3 §1 |
| 26 | RCE Layer 6 Epistemic Logic | Cross-claim contradiction graphs and circularity detection | M10 | Stage 3 (Doc 3 §1) |
| 27 | Interactive Symbolic Canvas UI | Next.js visual node-based mathematical authoring canvas | M7 | Stage 1 (Doc 1 §3) |
| 28 | Open Research ZIP Exporter | Zero lock-in cryptographic zip bundle export with SHA-256 and Ed25519 signatures | M8 | Stage 1 (Doc 2 §2) |
| 29 | Outbox Event Publisher | Transactional outbox relay & asynchronous validation polling contracts | M6 | Stage 1 (Doc 2 §3) |
| 30 | WireGuard mTLS Private Cluster | Hybrid multi-cloud node orchestration | Stage 2+ | Doc 3 §4 |
| 31 | Canonical 7-State Finding Taxonomy | Non-collapsible finding states (PASS, FAIL, WARNING, etc.) | M6 | Stage 1 (Doc 3 §1) |
| 32 | Draft vs Frozen Snapshot Lifecycle | Separation of mutable draft endpoints from immutable version snapshot queries | M8 | Stage 1 (ADR-003) |
| 33 | Citation-Preserving Erasure Engine | GDPR erasure nullifying user_account_id without breaking citation foreign keys | M8 | Stage 1 (ADR-003) |
| 34 | Anti-Database Guard & Network Sentinel | Worker runtime check rejecting DB credentials and verifying network isolation | M6 | Stage 1 (ADR-002) |
| 35 | Tarjan SCC Cycle & Loop Detection | Bounded DFS cycle path extraction and circular reasoning isolation | M10 | Stage 3 (Request R1) |
| 36 | SymPy Cross-Claim Contradiction Engine | Direct equality, boundary interval, and sign contradiction detection | M10 | Stage 3 (Request R1) |
| 37 | Canonical 7-State Topological Status Propagator | Forward monotonic propagation of finding states with antecedent poisoning | M10 | Stage 3 (Request R1) |
| 38 | Stage 3 Child Entity RLS Migration 003 | PostgreSQL RLS enabled and forced on claims and claim_relations tables | M10 | Stage 3 (Request R2) |
| 39 | End-to-End 6-Layer Integrated RCE Pipeline | Unified execution across L1 Syntax, L2 Boundary, L3 Dimensions, L4 Physical Laws, L5 Empirical Data, L6 Epistemic Logic across Frontend, Backend, and Celery | M11 | Stage 4 (Request R1) |
| 40 | Multi-Zone Production Docker Hardening & SAST | Strict zone separation, health checks for all services, production compose, env templates, and comprehensive SAST scan | M12 | Stage 4 (Request R2) |
| 41 | Full-Monorepo Opaque-Box E2E Regression Suite | 4-Tier integration test suite covering L1-L6, multi-zone security, version freeze & ZIP export, 325+ test non-regression | M13 | Stage 4 (Request R3) |
| 42 | Final Project Handover & Architecture Finalization | Exhaustive 9-section handover report, updated TEST_READY.md, production operational runbook | M14 | Stage 4 (Request R4) |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Architecture Audit & ADRs | Preserve reference docs, generate consistency audit report, write comprehensive ADRs | none | DONE |
| M2 | Workspace Scaffolding & Isolation | Git init, directory structure, worker boundary configs with zero Postgres credentials | M1 | DONE |
| M3 | Environment & Docker Orchestration | .env.example, pinned dependencies, multi-zone Docker Compose, static validations | M2 | DONE |
| M4 | Math Contracts & RLS Database Schemas | Typed AST models, SymPy/Pint tests, PostgreSQL DDL migrations, RLS test suite | M3 | DONE (commit e6ee932) |
| M5 | Security QA & Stage 0 Report | SAST scan, health check endpoints, test execution, comprehensive 10-point report | M4 | DONE |
| M6 | Celery Dimensional & Symbolic Pipeline | Layers 1-3 (AST semantics, singularity/boundary solver, Pint 100+ units, Redis conduit, DB migrations) | M5 | DONE |
| M7 | Interactive Symbolic Canvas UI | Next.js 15 / React 19 @xyflow/react node canvas, custom nodes, DAG cycle detection, bidirectional AST | M5 | DONE |
| M8 | Open Research Cryptographic ZIP Export | Zero lock-in ZIP bundle, SHA-256 manifests, Ed25519 signatures, offline verifier, export API | M6 | DONE |
| M9 | Stage 1 Dual-Track E2E Integration Suite | Opaque-box E2E test suite (Tiers 1-4), TEST_READY.md, full validation & export verification | M6, M7, M8 | DONE |
| M10 | Stage 3 Epistemic Logic & Cross-Claim Verification | Feature 26 (RCE Layer 6), cycle detection, contradiction engine, 7-state status propagator, Zone 3 Celery sandbox task, migration 003 with RLS, Stage 3 E2E test suite, and 295 test baseline regression guard | M6, M9 | DONE |
| M11 | 6-Layer End-to-End Pipeline Integration | Celery worker multi-layer pipeline task, Backend validation routes (/api/v1/validation/verify, /versions/{version_id}/validate), Frontend LayerPipelineMatrix UI | M10 | DONE |
| M12 | Production Docker Multi-Zone Hardening & SAST | Strict zone separation (api removed from compute_net), container health checks, docker-compose.prod.yml, .env.production.example, SAST scan report | M11 | DONE |
| M13 | Full Regression & Stage 4 Opaque-Box E2E Suite | 4-tier integration test suite (test_stage4_final_e2e_integration.py) covering L1-L6, multi-zone security, version freeze & ZIP export, 325+ test non-regression | M11, M12 | DONE |
| M14 | Final Project Handover & Handover Documentation | Comprehensive 9-section STAGE_4_FINAL_HANDOVER.md, updated TEST_READY.md, finalized PROJECT.md | M13 | DONE |

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

### 4. Stage 1: Validation & Verification Contracts (Layers 1-3)
- **Layer 1: Syntax & Semantics**:
  - Validates `ExprNode` against `VariableSpec` symbol declarations (zero undeclared symbols).
  - Enforces `complexity_guard`: max depth 15, max node count 100, max polynomial power 20.
  - Rejects booleans, non-numeric strings, and arbitrary code injection.
- **Layer 2: Boundary & Singularity Solver**:
  - Direct SymPy construction via `sp.Add`, `sp.Mul`, `sp.Pow`, `sp.Symbol` (strictly zero `eval()`, `exec()`, or `parse_expr()`).
  - Pole & singularity detection: Denominator root analysis via `sp.solveset(denom, sym, domain=sp.S.Reals)`.
  - Boundary limits ($x \to 0^+$, $x \to \infty$) for divergence checks.
  - Richardson's Theorem 10-point stratified numerical fallback when `sp.simplify(lhs - rhs) != 0`.
- **Layer 3: Dimensional Engine (100+ Units via Pint)**:
  - Dynamically registers custom units from `bundle.units` via `ureg.define()`.
  - Verifies dimensional homogeneity on addition/subtraction.
  - Enforces strictly dimensionless arguments for transcendental functions (`sin`, `cos`, `exp`, `log`).
  - Diagnostic code: `DIMENSIONED_TRANSCENDENTAL_ARGUMENT` on violation.

### 5. Stage 1: Open Research Cryptographic ZIP Export Contract
- **Bundle File Structure**:
  - `manifest.json`: JSON-LD metadata, author ORCID, license, content SHA-256 hashes table.
  - `checksums.sha256`: Standard Linux sha256sum file for all bundle contents.
  - `signature.json`: Platform cryptographic signature over canonical `manifest.json`.
  - `paper.md`: Generated human-readable Markdown paper with equations & variable table.
  - `metadata/`: `project.json`, `version.json`, `actor.json` (zero PII: no emails, no passwords).
  - `math/`: `variables.json`, `units.json`, `equations/eq_*.json` (raw `ExprNode` ASTs).
  - `validation/`: `validation_report.json` with historical findings across Layers 1–3.
  - `verify_bundle.py`: Standalone offline verification script verifying hashes and AST validity.
- **HTTP Endpoint**: `POST /api/v1/versions/{version_id}/export-zip` (enforces `is_frozen = TRUE`).

### 6. Stage 1: Frontend Canvas & Node Contracts
- **Node Types**:
  - `ConstantNode`: Numeric constant with inline input.
  - `VariableNode`: Symbol dropdown referencing active `VariableSpec[]` declarations.
  - `BinaryOpNode`: Two input handles (`left`, `right`), one output handle (`+`, `-`, `*`, `/`, `**`).
  - `UnaryOpNode`: One input handle (`left`), one output handle (`neg`).
  - `FunctionCallNode`: One input handle (`arg0`), one output handle (`sqrt`, `sin`, `cos`, `exp`, `log`).
  - `EquationRootNode`: Single input handle with live KaTeX preview and validation trigger.
- **Bidirectional Translation**:
  - `graphToAst`: DAG cycle detection, depth $\le 15$, node count $\le 100$, strict port connection validation.
  - `astToGraph`: Tree-to-DAG visual layout algorithm placing nodes and edges.

### 7. Stage 3: Layer 6 Epistemic Logic & Cross-Claim Graph Contracts
- **Pydantic v2 Models (`shared/schemas/epistemic_logic.py`)**:
  - `ClaimType`: `AXIOM`, `HYPOTHESIS`, `DERIVATION`, `EMPIRICAL_OBSERVATION`, `PREDICTION`, `DOMAIN_CONSTRAINT`.
  - `RelationType`: `DEPENDS_ON`, `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`, `EQUIVALENT_TO`, `CHALLENGES`, `SUPERSEDES`.
  - `ClaimSpec`: `claim_id`, `claim_code`, `claim_type`, `statement`, `target_variable`, `expression_ast`, `assumptions`, `local_state`, `propagated_state`, `dependency_logic`.
  - `ClaimDependency`: `source_claim_id`, `target_claim_id`, `relation_type`, `justification`, `weight`.
  - `CycleReport`: `cycle_detected: bool`, `cycles: List[List[str]]`, `cyclic_claim_ids: Set[str]`.
  - `ContradictionItem` & `ContradictionReport`: Identifies direct equality, interval boundary, sign conflicts, and explicit contradiction links.
  - `EpistemicFinding` & `ClaimGraphValidationResult`: Overall status and detailed per-claim diagnostic breakdown.
- **Worker Epistemic Algorithms (`worker/core/epistemic_engine.py`)**:
  - Pure Python in-memory graph execution (zero external graph dependencies like `networkx`).
  - Tarjan's Strongly Connected Components (SCC) with bounded DFS cycle path extraction. Cyclic nodes assign `FindingState.FAIL` and `CIRCULAR_DEPENDENCY_DETECTED`.
  - SymPy-safe contradiction detection: algebraic subtraction, interval intersection, and sign check without `eval()`/`exec()`.
  - Monotonic topological status propagation across the canonical 7-state taxonomy (`PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `NEEDS_EXPERT_REVIEW`, `NOT_YET_TESTED`). Antecedent failure poisons dependent claim to `FAIL` with `EPISTEMIC_ANTECEDENT_FAILED`.
- **Database & Security Contracts (`backend/`)**:
  - PostgreSQL tables `claims` and `claim_relations` via migration `003_stage3_claims_and_epistemic_logic.py`.
  - Row-Level Security (RLS) enabled and forced on both tables linking to `owner_actor_id` and `public_preprint` visibility.
  - Immutability enforced on frozen versions (`is_frozen = TRUE`).
  - ZIP export bundles `claims_graph.json` validated by `verify_bundle.py`.

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
