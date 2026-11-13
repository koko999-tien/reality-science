# REALITY SCIENCE — Master Project Brief Baseline Summary (v1.0)

**Document Reference**: `RS-BRIEF-V1.0`  
**Standard**: Evidence-Driven Scientific Verification Platform  
**Preservation Date**: 2026-11-13  
**Integrity Mode**: Production Architecture Baseline  
**Canonical Workspace**: `D:\Reality_Science\`  

---

## 1. Executive Summary & Epistemic Mission

**REALITY SCIENCE** is an evidence-driven, deterministic-first scientific exploration and verification platform. It establishes an epistemically sound, mathematically rigorous, reproducible framework for computational reality constraints.

### The Epistemic Problem
Modern computational science and academic research face compounding credibility crises:
1. **Mathematical & Dimensional Inconsistency**: Complex theoretical models frequently contain unstated assumptions, ambiguous notation, dimensional mismatches (e.g. adding incompatible physical quantities), and undetected algebraic errors.
2. **Irreproducibility & Black-Box Execution**: Published papers regularly omit complete execution environments, numerical seeds, dependency locks, and raw datasets, rendering independent replication impossible.
3. **AI Hallucination & Pseudo-Science**: Large language models generated ungrounded mathematical proofs, invented paper citations, and hallucinated scientific consensus without rigorous symbolic verification.
4. **Popularity-Driven Truth (Social Validation)**: Scientific consensus is increasingly corrupted by social media engagement metrics, citations gaming, and publication bias rather than reproducible empirical grounding.

### The Platform Mission
REALITY SCIENCE addresses these challenges by implementing an automated **Reality Constraint Engine (RCE)** that subjects every scientific claim, equation, dataset, and simulation to deterministic mathematical verification, dimensional analysis, physical boundary validation, and empirical cross-checks before publication.

---

## 2. Core Architectural Axioms & Product Invariants

The platform enforces six non-negotiable architectural axioms across all subsystems:

1. **Deterministic Verification First, Human Expert Second, Zero AI Truth**:
   - Automated validation engines (SymPy, Pint, NumPy/SciPy) perform deterministic checks.
   - Verified human experts review complex analytical models and epistemological nuances.
   - Generative AI is strictly relegated to an assistive tool (detecting undefined symbols, suggesting literature); it is **strictly forbidden from asserting scientific truth or recording validation outcomes**.
2. **Symbol-First Authoring & Dual Mathematical Representation (Approved Decision 1)**:
   - Free-form LaTeX is semantically ambiguous. Authors must declare a structured table of **Variables & Units** prior to writing equations.
   - Every formula is maintained in dual format: **Display LaTeX** (for visual rendering via KaTeX) and **Canonical Typed AST / SymPy JSON** (for execution and verification).
   - Arbitrary code execution (`eval()`, `exec()`, arbitrary script uploads) is explicitly rejected.
3. **Claim-Centered Knowledge Architecture**:
   - Research is decomposed into granular, addressable **Claims**.
   - Each claim maintains independent validation statuses, supporting/contradicting evidence links, mathematical derivations, and uncertainty bounds.
4. **Strict Three-Axis Status Model**:
   - Every Research Object is evaluated across three decoupled dimensions:
     - `publication_status`: `draft` -> `submitted` -> `preprint` -> `under_review` -> `peer_reviewed` -> `revised` / `retracted`.
     - `validation_status`: `not_tested` -> `in_progress` -> `passed_selected` / `passed_with_warnings` / `failed` / `insufficient_data` / `needs_expert_review` / `independently_reproduced`.
     - `evidence_maturity`: `exploratory_idea` -> `formally_developed` -> `preliminary_evidence` -> `independently_supported` -> `strongly_convergent`.
5. **No Popularity Truth (Zero Engagement Bias)**:
   - "Likes", "upvotes", and "follower counts" are strictly excluded from ranking or determining scientific validity. Credibility is a function of mathematical rigor and empirical convergence.
6. **Immutable Provenance vs Right-to-Erasure (Identity Split - Approved Decision 3)**:
   - Personally Identifiable Information (PII) is isolated in `user_accounts` and encrypted via AES-256-GCM.
   - Academic contributions are linked to pseudonymous `research_actors`.
   - GDPR account deletion nullifies `user_accounts` while preserving `research_actors` as `Contributor-#xxxx`, ensuring citations and version trees remain mathematically intact.

---

## 3. Trust Zones & Security Boundaries (Approved Decision 2)

REALITY SCIENCE operates across three strictly isolated security zones:

```
┌────────────────────────────────────────────────────────┐
│ ZONE 1: CLOUD EDGE (Public / Edge Network)             │
│ Next.js 15+ UI • KaTeX Math Rendering • Plotly CDN     │
│ TLS Termination • WAF • Anti-DDoS • Zero Secrets       │
└───────────────────────────┬────────────────────────────┘
                            │ WireGuard VPN / mTLS Tunnel
┌───────────────────────────▼────────────────────────────┐
│ ZONE 2: PRIVATE DATA CORE (Secure Server / Private VPC)│
│ FastAPI Modular Monolith • PostgreSQL 16+ (ACID + RLS) │
│ MinIO Object Storage (Encrypted) • Redis Queue/Cache   │
│ Tamper-Evident SHA-256 Audit Store • Outbox Relay      │
└───────────────────────────┬────────────────────────────┘
                            │ Isolated Docker Network (`compute_net`)
┌───────────────────────────▼────────────────────────────┐
│ ZONE 3: ISOLATED COMPUTE SANDBOX (Zero Network Route)  │
│ Celery Math Worker (SymPy 1.13+ & Pint 0.24+)          │
│ ZERO PostgreSQL Credentials • Non-Root (UID 10001)     │
│ Read-Only FS • Memory/CPU/PID Limits • 10s/120s Timeout│
└────────────────────────────────────────────────────────┘
```

- **Zone 1 (Cloud Edge)**: Stateless UI. No database connections. No committed secrets.
- **Zone 2 (Private Core)**: The single source of truth. Direct database access is restricted to internal API modules. Row-Level Security (RLS) is enforced on all tables.
- **Zone 3 (Isolated Sandbox)**: Computes mathematical proofs and simulations. Containers operate with zero external internet access and zero PostgreSQL credentials (`DATABASE_URL`, `POSTGRES_*`). All job payloads and results transit via Redis queues and signed temporary storage tokens.

---

## 4. The Reality Constraint Engine (RCE)

The RCE is a 6-layer deterministic verification pipeline:

| Layer | Engine Name | Primary Tooling | Verification Scope |
|---|---|---|---|
| **L1** | **Semantic & Definition Check** | AST Parser / Symbol Table | Undeclared symbols, ambiguous definitions, conflicting notations across equations. |
| **L2** | **Mathematical Consistency** | SymPy (Isolated Sandbox) | Domain boundaries, division by zero, algebraic equivalence ($LHS - RHS = 0$), calculus derivations. |
| **L3** | **Dimensional & Unit Check** | Pint (SI Ontology) | Dimensional homogeneity, illegal operations (e.g. $L + T$), transcendental function argument dimensionality. |
| **L4** | **Physical Constraints** | Boundary Rulesets | Invariants (Conservation of Energy/Momentum, Thermodynamic Laws) checked against explicitly declared applicability conditions. |
| **L5** | **Empirical Validation** | NumPy / SciPy / Parquet | Residual analysis, experimental error bars, calibration vs validation dataset separation. |
| **L6** | **Reproducibility & Replication**| Reproducibility Bundles | Deterministic re-execution with pinned image digests, seeds, and dataset hashes. |

### The Canonical 7-State Finding Taxonomy
Every verification check returns exactly one of seven deterministic states:
1. `PASS`: Mathematical, dimensional, or empirical requirement rigorously verified.
2. `FAIL`: Formally provable mathematical contradiction, dimensional error, or physical violation.
3. `WARNING`: Numerical instability, high condition number, or uncalibrated parameter regime.
4. `NOT_APPLICABLE`: Claim explicitly operates outside the boundary conditions of a physical constraint (e.g., non-equilibrium open system).
5. `INSUFFICIENT_DATA`: Empirical validation lacks observation points or necessary variance.
6. `NEEDS_EXPERT_REVIEW`: Analytical complexity exceeds symbolic solver capabilities (e.g., non-integrable nonlinear PDEs).
7. `NOT_YET_TESTED`: Check scheduled or queued in worker pipeline.

---

## 5. Data Sovereignty & Scientific Immutability

### Research Version Snapshots
- **Draft Mode**: Active editing operates on mutable working tables.
- **Publication Freeze**: Publishing triggers a snapshot freeze (`is_frozen = TRUE`). A database trigger (`trg_freeze_research_versions`) strictly rejects any subsequent `UPDATE` or `DELETE` statements on scholarly content, preserving citation integrity.

### Row-Level Security (RLS) & Multi-Tenancy
- Requests set local session variables:
  ```sql
  SET LOCAL app.current_actor_id = '<actor_uuid>';
  SET LOCAL app.current_org_id = '<org_uuid>';
  ```
- In Stage 0 / MVP, visibility is strictly binary: `private_draft` (accessible only by owner/collaborator) or `public_preprint` (read-only by public).

### Tamper-Evident Audit Chain
Every database modification generates an immutable cryptographic audit record:
$$\text{event\_hash} = \text{SHA256}(\text{prev\_hash} \parallel \text{actor\_id} \parallel \text{action} \parallel \text{resource\_id} \parallel \text{diff\_json} \parallel \text{timestamp})$$
Any manual disk alteration or database tampering instantly breaks the hash chain.

### Zero Lock-In Open Research Bundle
Every published research version can be exported as a standard `.zip` archive containing:
- `manifest.json`: JSON-LD semantic metadata.
- `paper.md`: Full text with LaTeX mathematical formulations.
- `claims_graph.json`: Directed graph of claims and evidence links.
- `datasets/`: Raw and derived datasets (CSV/Parquet) with SHA-256 hashes.
- `validation_report.json`: Verbatim RCE execution logs and certificates.

---

## 6. Phased Implementation Roadmap

1. **Stage 0 — Infrastructure Foundation & Security Boundaries (Current)**:
   - Authorized workspace `D:\Reality_Science\`.
   - Verbatim preservation of reference architecture documents.
   - Architecture Decision Records (ADR-001 through ADR-006).
   - Component scaffolding (Frontend, Backend, Compute Worker, Shared Contracts).
   - Multi-zone Docker Compose (`app_net`, `data_net`, `compute_net`).
   - Pydantic v2 AST mathematical contracts and initial RLS database migrations.
2. **Stage 1 — Knowledge Base & Research Studio MVP**:
   - Versioned Knowledge Base entries and structured Research Object drafting.
   - Claim-centered authoring and immutable preprint snapshots.
3. **Stage 2 — RCE Layers 1–3 & Mathematical Sandbox**:
   - Symbol-First Variable & Unit tables.
   - Pinned SymPy and Pint evaluation in network-isolated worker containers.
   - Golden Test Suite (>150 test cases covering dimensional and symbolic math).
4. **Stage 3 — Evidence Lab & Safe AI Assistant**:
   - Presigned S3 dataset upload with transformation lineage tracking.
   - Tool-gated AI assistant without direct database write permissions.
5. **Stage 4 — RCE Layer 4 (Physical Laws) & Numerical Simulation**:
   - Versioned physical constraints with explicit applicability boundaries.
   - NumPy/SciPy simulation runners with Plotly visualization.
6. **Stage 5–6 — Independent Replication & Knowledge Graph**:
   - Cryptographic Reproducibility Bundles.
   - Cross-claim contradiction graphs and global academic federations.

---

## 7. Lineage Reference & Canonical Architecture Documents

This baseline brief synthesizes and is substantiated by the three canonical architecture specifications preserved verbatim in `docs/architecture/`:
1. `reality_science_prd_and_analysis.md`: Product Requirements Document, Application Sitemap, and Pre-implementation Trade-off Analysis.
2. `reality_science_system_and_data_architecture.md`: Modular Monolith Design, Canonical PostgreSQL Schema, Trust Zones, and API v1 Specifications.
3. `reality_science_validation_security_and_ops.md`: Reality Constraint Engine 6-Layer Architecture, Compute Sandbox Isolation, Risk Register, and Testing Strategy.
