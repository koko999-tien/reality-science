# REALITY SCIENCE — STAGE 1 TEST READY GUIDE & VERIFICATION MATRIX

**Project Location**: `D:\Reality_Science\`  
**Stage**: Stage 1 — Core Research Computation Engine  
**Status**: All Stage 1 Milestones (M6, M7, M8, M9) Implemented, Tested, and Verified  
**Date**: 2026-11-15  

---

## 1. Architectural Scope & Multi-Zone Security Boundaries

Stage 1 activates the **Core Research Computation Engine** on top of the Stage 0 hardened infrastructure:

- **Zone 1: Cloud Edge (Public Frontend)**
  - Interactive Symbolic Canvas UI built with Next.js 15 App Router, React 19, and `@xyflow/react`.
  - Visual authoring of mathematical equations using 6 custom nodes (`ConstantNode`, `VariableNode`, `BinaryOpNode`, `UnaryOpNode`, `FunctionCallNode`, `EquationRootNode`).
  - Strict **Symbol-First Authoring** via `VariableDeclarationPanel` enforcing variable symbols and SI units before connections.
  - Bidirectional lossless AST conversion (`graphToAst` $\leftrightarrow$ `astToGraph`) with DAG cycle prevention, depth $\le 15$, and node count $\le 100$.
  - Synchronized KaTeX mathematical formula rendering.

- **Zone 2: Private Core (Backend & Identity)**
  - FastAPI Modular Monolith running Python 3.11 with asynchronous SQLAlchemy 2.0 and Alembic.
  - Relational schema migration `002_stage1_validation_and_math.py` with PostgreSQL Row-Level Security (RLS) on `equations`, `variables`, `validation_runs`, and `validation_findings`.
  - Identity split separating `user_accounts` (PII encrypted with AES-256-GCM) from pseudonymous `research_actors`.
  - Immutable version freeze trigger `trg_freeze_research_versions` blocking mutations and deletions on published research.
  - Open Research Cryptographic ZIP Exporter (`exporter.py`) with JSON-LD `manifest.json`, Linux `checksums.sha256`, digital `signature.json`, zero PII guarantee, and standalone offline `verify_bundle.py`.

- **Zone 3: Isolated Compute Sandbox (Celery Worker)**
  - Celery compute workers executing within network-isolated `compute_net` (strictly ZERO PostgreSQL access).
  - Runtime `assert_zero_database_credentials()` guard rejecting database credentials and drivers (`psycopg2`, `asyncpg`, `sqlalchemy`).
  - Pure programmatic SymPy AST construction without `eval()`, `exec()`, or unparsed strings.
  - Three-layer Reality Constraint Engine (RCE):
    - **Layer 1: Syntax & Semantics Engine** (`semantic_validator.py`): Symbol verification, domain checks, complexity gates.
    - **Layer 2: Boundary & Singularity Solver** (`boundary_engine.py`): Physical pole detection, asymptotic limits ($t \to \infty$), Richardson's Theorem 10-point stratified numerical fallback.
    - **Layer 3: Dimension Engine** (`dimension_engine.py`): 100+ physical units via Pint, dynamic custom unit registration, strictly dimensionless transcendental arguments.

---

## 2. Verification Suite Matrix

| Package / Domain | Target Directory | Tests Collected | Passed | Skipped | Failed | Execution Time |
|---|---|---|---|---|---|---|
| **Shared Contracts** | `shared/tests/` | 14 | **14** | 0 | 0 | ~0.5s |
| **Worker Compute & Isolation** | `worker/tests/` | 55 | **55** | 0 | 0 | ~20.0s |
| **Backend API, RLS & Exporter** | `backend/tests/` | 40 | **39** | 1 (offline RLS) | 0 | ~30.0s |
| **Frontend Canvas UI** | `frontend/tests/` | 39 | **39** | 0 | 0 | ~9.0s |
| **Stage 1 E2E Integration Suite** | `backend/tests/integration/test_stage1_e2e_integration.py` | 5 | **5** | 0 | 0 | ~4.3s |
| **TOTAL** | | **148** | **147** | **1** | **0** | **~64.0s** |

---

## 3. Independent Verification Instructions

To execute the test suites independently on the host:

### 3.1. Verify Shared Contracts (14 tests)
```powershell
Set-Location D:\Reality_Science
$env:PYTHONPATH="D:\Reality_Science\shared"
& "C:\Python314\python.exe" -m pytest "D:\Reality_Science\shared\tests" -v
```
*Expected*: `14 passed in ~0.5s`.

### 3.2. Verify Worker Compute Sandbox & Anti-Database Isolation (55 tests)
```powershell
Set-Location D:\Reality_Science
$env:PYTHONPATH="D:\Reality_Science\shared;D:\Reality_Science\worker"
& "C:\Python314\python.exe" -m pytest "D:\Reality_Science\worker\tests" -v
```
*Expected*: `55 passed in ~20.0s` (including all 5 worker isolation tests).

### 3.3. Verify Backend API, RLS Schemas, Exporter & E2E Integration (40 tests)
```powershell
Set-Location D:\Reality_Science
$env:PYTHONPATH="D:\Reality_Science\shared;D:\Reality_Science\backend"
& "D:\Reality_Science\backend\.venv\Scripts\pytest.exe" "D:\Reality_Science\backend\tests" -v
```
*Expected*: `39 passed, 1 skipped in ~30.0s`.

### 3.4. Verify Frontend Symbolic Canvas UI (39 tests)
```powershell
Set-Location D:\Reality_Science\frontend
npm test
```
*Expected*: `Test Suites: 6 passed, 6 total`, `Tests: 39 passed, 39 total`.

### 3.5. Verify Dedicated Stage 1 Dual-Track E2E Integration Suite (5 tests)
```powershell
Set-Location D:\Reality_Science
$env:PYTHONPATH="D:\Reality_Science\shared;D:\Reality_Science\backend"
& "D:\Reality_Science\backend\.venv\Scripts\pytest.exe" "D:\Reality_Science\backend\tests\integration\test_stage1_e2e_integration.py" -v
```
*Expected*: `5 passed in ~4.3s`.

---

## 4. Four-Tier E2E Integration Architecture (Milestone 9)

The Stage 1 E2E integration test suite (`backend/tests/integration/test_stage1_e2e_integration.py`) validates four sequential operational tiers:

1. **Tier 1 — Frontend AST & Visual Flow Contracts**:
   - Programmatic construction of mathematical expressions ($E = 0.5 \cdot m \cdot v^2$).
   - Static evaluation of constant expressions and functions (`try_eval_constant_ast`).
   - Prevention of imaginary numbers ($\sqrt{-16} \to \text{None}$).
   - Rejection of boolean values and arbitrary string constants.
   - AST complexity gates (depth $\le 15$, node count $\le 100$, powers $\le 20$).

2. **Tier 2 — Backend Domain, Identity Split & Immutability**:
   - Verification of identity split between `UserAccount` (PII) and `ResearchActor` (citations).
   - GDPR Right to Erasure: deleting user account preserves research actor and citations with `ON DELETE SET NULL`.
   - Immutable version snapshot: `is_frozen = TRUE` rejects mutations.

3. **Tier 3 — Compute Sandbox & RCE Orchestration**:
   - Packaging typed `JobBundle` into Celery v2 envelope with headers and base64 payload.
   - Dispatching to Redis `compute_tasks` queue.
   - Ingestion and mapping of `FindingResult` to canonical 7-state taxonomy (`PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `NEEDS_EXPERT_REVIEW`, `NOT_YET_TESTED`).

4. **Tier 4 — Cryptographic Research ZIP Export & Autonomous Verification**:
   - Exporting frozen version to complete `.zip` archive via `generate_research_zip_bundle`.
   - Unpacking into clean temporary directory and executing standalone `verify_bundle.py`.
   - Verification of intact bundle (`[PASS] All bundle verification checks passed successfully.`).
   - Archive mode verification (`verify_bundle.py --zip bundle.zip`).
   - Tamper-evidence test: altering `paper.md` fails verification.
   - Untracked file test: injecting unauthenticated files fails verification.
   - Anti-Poisoning test (FINDING-M8-02 remediation): injecting untracked file and updating `checksums.sha256` fails verification because `manifest.json` is the signed authority.

---

## 5. Security & Anti-Cheating Invariants Summary

1. **Zero Database Credentials in Compute Workers**:
   - Worker environment contains strictly zero database connection strings.
   - Worker container image has zero database drivers installed (`psycopg2`, `asyncpg`, `sqlalchemy`).
   - Worker health check enforces `assert_zero_database_credentials()`.

2. **Zero Arbitrary Code Execution**:
   - Zero occurrences of `eval()`, `exec()`, `compile()`, or `parse_expr()`.
   - AST evaluation converts pure Pydantic nodes directly into native SymPy objects (`sp.Add`, `sp.Mul`, `sp.Pow`, `sp.Symbol`).

3. **Cryptographic Integrity & Zero Vendor Lock-in**:
   - Export bundle can be independently verified on any computer running standard Python 3 without installing any third-party packages or database servers.
   - Authoritative signed manifest prevents checksum poisoning attacks.
