# ADR-005: Modular Monolith Backend Architecture in Python FastAPI

## Status
**Approved**

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
During initial architectural surveying, an early sketch (`web_data_control_architecture.md`) proposed a multi-language polyglot microservices stack:
- TypeScript (NestJS / Fastify) for the Control API.
- Go for a Realtime WebSocket Hub.
- Python (FastAPI + Celery) for AI pipelines and data workers.
- ClickHouse for append-only audit logging.

While polyglot microservices offer independent scalability for large enterprise systems, adopting this architecture in Stage 0/MVP introduces severe operational failure modes:
1. **Massive Operational Overhead**: Managing three separate runtimes (Node.js, Go, Python), three package managers (npm/pnpm, go mod, poetry/uv), and polyglot Docker images drastically increases developer cognitive load and CI build times.
2. **Cross-Language Contract Duplication**: Data contracts (such as mathematical ASTs, equations, and claim models) must be manually maintained across TypeScript, Go, and Python, causing synchronization drift and serialization bugs.
3. **Distributed Transaction Latency**: Splitting domain logic across microservices requires distributed transactions (2-Phase Commit or Sagas) for actions that should be atomic (e.g., publishing a version and recording audit events).
4. **Python Domain Alignment**: REALITY SCIENCE is fundamentally a mathematical and scientific platform. The scientific ecosystem (SymPy, Pint, NumPy, SciPy) is natively Python.

### Alternatives Considered
- **Alternative 1: Polyglot Microservices (TypeScript + Go + Python)**: Rejected for Stage 0. Extreme operational complexity with zero immediate scalability benefit.
- **Alternative 2: Django Monolith**: Rejected. Heavy ORM conventions, awkward async/await support, and opinionated structures that complicate low-level AST manipulation and clean multi-tenant RLS.
- **Alternative 3: Python FastAPI Modular Monolith**: Chosen. High-performance asynchronous Python, native Pydantic v2 validation, OpenAPI 3.1 documentation, unified dependency management, and clean internal domain boundaries.

## Decision
1. **Unified Backend Architecture**:
   - The core backend service (`services/api`) is implemented as a **Modular Monolith** in **Python 3.11+ using FastAPI**.
   - A single, unified Python ecosystem powers the API, data validation, AST processing, and worker coordination.
2. **Internal Domain Module Boundaries**:
   - The monolith is partitioned into decoupled domain modules within `services/api/src/modules/` following an acyclic dependency graph:
     ```
     shared_kernel (Types, Errors, Base Models, Crypto)
          ▲
          ├── iam_governance (Auth, Actors, RLS Context, Audit)
          │        ▲
          │        ├── research_core (Projects, Drafts, Versions, Claims, Equations)
          │        │        ▲
          │        ├── evidence_lab (Datasets, Presigned S3 URLs, Provenance)
          │        │        ▲
          │        └── reality_constraint_engine (RCE Orchestrator, Rules, Findings)
          │
          └── compute_orchestrator (Job Packaging, Redis Dispatch, Status Ingestion)
     ```
3. **Architectural Invariants**:
   - **No Cross-Module Database Table Writes**: A domain module may only write to tables it owns. Cross-module data modifications occur via explicit service interfaces or domain events.
   - **In-Process Interface Calls**: Intra-monolith communication uses direct Python asynchronous method calls (zero network latency, zero serialization overhead).
   - **Transactional Outbox Pattern**: When an entity mutation produces external effects or cross-module events (e.g. `ResearchVersionFrozen`), an event record is written to `outbox_events` inside the same PostgreSQL transaction. A background relay dispatches the event.
4. **Future Microservice Extraction Path**:
   - Because each module owns its data models, schemas, and service interfaces with clean boundaries, any module (such as `reality_constraint_engine` or `evidence_lab`) can be extracted into an independent microservice in Stage 2+ with zero domain refactoring.

## Consequences

### Positive
- **Rapid Engineering Velocity**: Single language and runtime across backend and worker services; unified Pydantic contracts; single test runner (`pytest`).
- **Zero Network Overhead**: Intra-domain calls execute in-memory with zero serialization latency.
- **Atomic ACID Guarantees**: Complex multi-entity operations (e.g. draft freezing, hash chain audit generation, outbox event writing) execute within a single PostgreSQL transaction block.

### Negative / Trade-Offs
- **Discipline Required**: Developers must respect module boundaries and avoid importing internal module details directly.

### Risks & Mitigations
- **Risk**: Architectural decay where modules become tightly coupled over time ("Big Ball of Mud").
  - *Mitigation*: Enforce import boundary linting via `import-linter` or `pytest-archon` in CI, failing builds if unauthorized cross-module imports are introduced.

## Compliance & Verification Rules
1. **Module Architecture Test**: Run `import-linter` to verify that `iam_governance` never imports from `research_core`, and no circular imports exist.
2. **OpenAPI Specification Check**: Automated test validating that `fastapi.testclient` generates a valid OpenAPI 3.1 schema without untyped endpoints.
3. **Transactional Outbox Test**: Integration test verifying that creating a research version writes both a `research_versions` record and an `outbox_events` record within the same transaction.
