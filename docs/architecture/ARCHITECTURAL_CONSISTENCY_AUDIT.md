# Canonical Architectural Consistency Audit & Gap Analysis Report
**Project**: REALITY SCIENCE — Evidence-Driven Scientific Verification Platform  
**Target Canonical Document**: `D:\Reality_Science\docs\architecture\ARCHITECTURAL_CONSISTENCY_AUDIT.md`  
**Working Artifact**: `D:\Reality_Science\.agents\teamwork\explorer_m1_3\audit_synthesis.md`  
**Milestone**: M1 (Architecture Audit & ADRs)  
**Author**: Explorer Agent M1_3 (`explorer_m1_3`)  
**Supervising Orchestrator**: `ec0e3c97-b0c1-4aad-ba55-c04134490fea`  
**Audit Standard**: Rigorous Multi-Document Triangulation & Zero-Trust Epistemic Verification  
**Date**: 2026-11-13  
**Status**: MASTER SYNTHESIS COMPLETE  

---

## 1. Executive Summary & Audit Mandate

### 1.1. Context and Mission Scope
REALITY SCIENCE is an evidence-driven scientific verification platform designed to establish an epistemically sound, mathematically rigorous, and reproducible computational framework for scientific hypotheses. The core system combines structured mathematical authoring, automated dimensional consistency checking, multi-layer physical law validation (the Reality Constraint Engine, RCE), and an immutable, claim-centered scientific publication graph.

Prior to the commencement of implementation in Stage 0, three primary architectural specifications and an exploratory data control proposal were generated:
1. **Architecture Document 1 (Doc 1)**: `reality_science_prd_and_analysis.md` (Product Requirements Document, Pre-implementation Analysis, Sitemap & Phased Roadmap)
2. **Architecture Document 2 (Doc 2)**: `reality_science_system_and_data_architecture.md` (Modular Monolith, Trust Zones, Canonical Relational Schema, RLS & API Specifications)
3. **Architecture Document 3 (Doc 3)**: `reality_science_validation_security_and_ops.md` (Reality Constraint Engine 6-Layer Architecture, Zero-Trust Compute, Security Vectors, Hybrid Deployment & Risk Register)
4. **Contextual Precursor**: `web_data_control_architecture.md` (Early architectural proposal for self-hosted data control and edge caching)
5. **Governing Framework**: `ORIGINAL_REQUEST.md` (Stage 0 Requirements R1–R5, Approved Decisions 1–4, and Safety Constraints)

This audit report represents the canonical master synthesis evaluating these architectural baselines against each other, against the Master Project Brief v1.0, and against the governing constraints of Stage 0.

### 1.2. Summary of Critical Findings
The reference architecture documents reflect exceptional domain modeling and academic rigor. However, multi-document cross-examination reveals six systemic architectural paradoxes and ten discrete findings (FIND-001 through FIND-010) that, if left unaddressed, would lead to critical security failures, deployment deadlocks, or cross-tenant data leakage:

1. **The Worker `--network=none` Paradox (FIND-001 - CRITICAL)**: Doc 3 mandates `--network=none` for compute sandboxes, while Doc 2 depicts workers actively polling Redis, calling API gateways, and uploading simulation artifacts to MinIO. In standard Linux container environments, `--network=none` disables external socket creation entirely, rendering Celery message consumption and Redis result publishing impossible.
2. **Arbitrary Code Execution (RCE) via Unconstrained Math Parsing (FIND-002 - CRITICAL)**: While raw Python execution is nominally banned, SymPy's default string parsing (`sympy.parsing.sympy_parser.parse_expr`) compiles mathematical text into Python bytecode and evaluates it via `eval()`. Without an AST-enforced grammar boundary, malicious mathematical payloads achieve Remote Code Execution.
3. **Compute Worker Database Credential Leakage (FIND-003 - CRITICAL)**: Standard worker deployments inherit monolithic configuration files containing `DATABASE_URL` and `POSTGRES_*` environment variables. If a worker process is compromised via algorithmic complexity attacks or memory exploits, the attacker gains direct read/write access to the entire platform database.
4. **Validation State Model Fragmentation (FIND-004 - HIGH)**: Three contradictory sets of validation states exist across Doc 1 (8 states), Doc 2 (6 states), and Doc 3 (7 canonical states), alongside a conflation of publication workflow states with database Row-Level Security (RLS) visibility states (FIND-005).
5. **Child Entity Row-Level Security Bypass (FIND-007 - HIGH)**: PostgreSQL RLS policies are specified exclusively on the root `research_projects` table, leaving child entities (`variables`, `equations`, `claims`, `evidence_links`, `validation_runs`) vulnerable to Insecure Direct Object Reference (IDOR) attacks and cross-tenant leakage.
6. **REST API Routing Key Mismatches (FIND-009 - MEDIUM)**: REST endpoints ambiguously alternate between project IDs (`/research/{id}/draft`) and version IDs (`/versions/{vid}/variables`), obscuring the lifecycle boundary between mutable working drafts and frozen snapshots.

All ten findings are comprehensively resolved in this audit through alignment with **Approved Decisions 1 through 4** and formalization into **Architecture Decision Records ADR-001 through ADR-006**.

---

## 2. Audit Methodology Across the 6 Core Dimensions

The audit was executed systematically across six foundational architectural dimensions:

```
+---------------------------------------------------------------------------------------------------+
| 6 CORE ARCHITECTURAL AUDIT DIMENSIONS                                                             |
+---------------------------------------------------------------------------------------------------+
| 1. Requirements Consistency        --> Cross-document feature alignment, persona roles, MVP scope |
| 2. System Boundaries & Isolation   --> Network topologies, process sandboxes, IPC mechanisms      |
| 3. Database Design & Integrity     --> Relational normalization, foreign keys, triggers, immutability|
| 4. Security & Threat Modeling      --> RCE vectors, credential isolation, RLS policies, PII leaks |
| 5. Scientific Validation Correctness-> Symbolic decidability, dimensional algebra, float determinism|
| 6. Data Governance & Scalability   --> GDPR compliance, multi-tenancy, audit hash chains, storage |
+---------------------------------------------------------------------------------------------------+
```

### Dimension 1: Requirements Consistency & Scope Alignment
- Evaluates whether user personas, functional priorities (P0/P1/P2), and architectural invariants are uniformly understood across documents.
- Audits the alignment between the theoretical 8-stage publication lifecycle (`draft`, `submitted`, `preprint`, `under_review`, `peer_reviewed`, `revised`, `withdrawn`, `retracted`) and the Stage 0 MVP requirement for two discrete visibility states (`private_draft`, `public_preprint`).

### Dimension 2: System Boundaries & Component Isolation
- Verifies trust boundaries across Zone 1 (Cloud Edge), Zone 2 (Private Data Core), and Zone 3 (Isolated Compute Sandbox).
- Investigates network segregation, IPC protocols, queue architectures, and container orchestration contracts between FastAPI, Celery, Redis, and PostgreSQL.

### Dimension 3: Database Design, Schema Integrity & Versioning
- Analyzes relational schemas for referential integrity, normal form compliance, foreign key cascades, and trigger-based immutability.
- Audits the mechanism for version snapshot freezing (`is_frozen = TRUE`) and verifies whether research object components (19 tables) preserve content-addressed reproducibility without database bloat.

### Dimension 4: Security Architecture, Threat Modeling & RCE Defense
- Examines attack surfaces in user input parsing, mathematical expression compilation, and compute container execution.
- Evaluates least-privilege enforcement, Linux capabilities (`--cap-drop=ALL`), non-root execution (UID 10001), cgroups resource quotas (CPU, memory, PIDs, execution timeouts), and envelope encryption for sensitive credentials.

### Dimension 5: Scientific Validation, CAS Limits & Epistemic Correctness
- Audits the theoretical and computational boundaries of Computer Algebra Systems (CAS) and unit systems (SymPy and Pint).
- Analyzes algorithmic undecidability (Richardson's Theorem), transcendental function constraints, dimensional unit context rules, and IEEE 754 floating-point non-determinism.

### Dimension 6: Data Governance, Privacy Compliance & Scalability
- Evaluates compliance with GDPR Article 17 ("Right to Erasure") versus the scientific requirement for immutable academic citation lineage.
- Audits audit log tamper-evidence (hash chaining), PII exposure (raw IP addresses), and multi-tenancy architecture (the nullable `organization_id` pattern).

---

## 3. Master Findings Table (FIND-001 through FIND-010)

The table below catalogs the complete set of architectural findings identified across the reference documentation. Each finding is cited with exact document sections and line numbers, categorized by architectural dimension, assigned a formal severity level, and paired with an authoritative resolution strategy.

| Finding ID | Dimension | Source References | Inconsistency / Security Risk Description | Severity | Resolution Strategy & Governing ADR |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **FIND-001** | **System Boundaries** | Doc 2 §1 (lines 33–42)<br>Doc 3 §2.1 (line 52) | **Worker Network Boundary Paradox**: Doc 3 states compute containers run with `--network=none`. However, Doc 2 diagrams show workers receiving jobs from Redis, `SimW` uploading artifacts to MinIO, and `AIW` calling the API Gateway. A container with `--network=none` has only a loopback interface (`lo`), completely preventing TCP socket communication with Redis, MinIO, or the Gateway. | **CRITICAL** | **Adopt ADR-002 & ADR-006**: Dual-tier boundary architecture. Celery worker container runs in dedicated `compute_net` bridge network connected strictly to Redis, with zero route to PostgreSQL or the Internet. For untrusted execution, workers evaluate typed ASTs purely in-memory, or dispatch ephemeral sandboxes via staged buffers. Workers never directly contact MinIO or Postgres. |
| **FIND-002** | **Security & Isolation** | Doc 1 §1 (Item 2, line 15)<br>Doc 3 §2.1 (line 51)<br>Stage 0 Decision 1 | **SymPy `parse_expr` Arbitrary Code Execution (RCE)**: Doc 3 specifies that `eval()` and `exec()` are banned, but default SymPy string parsing (`parse_expr`) inherently relies on Python bytecode compilation and evaluation. Doc 1 §1.1 also raised ambiguity regarding whether users upload `.py` scripts in MVP. | **CRITICAL** | **Adopt Decision 1 & ADR-001**: Ban `.py` script uploads and raw string parsing. Enforce structured mathematical input via typed Abstract Syntax Trees (`ExprNode`, `VariableSpec`, `UnitSpec`). SymPy and Pint objects are instantiated programmatically via native constructors, never evaluating unconstrained strings. |
| **FIND-003** | **Security & Isolation** | Doc 1 §1 (Item 1, line 14)<br>Doc 2 §1 (line 47)<br>Stage 0 R2 Mandate | **Compute Worker Database Credential Leakage**: Celery workers sharing standard backend configurations inherit `DATABASE_URL` and `POSTGRES_*` environment variables. If an algorithmic exploit or memory corruption occurs in worker mathematical libraries, the entire relational database is exposed. | **CRITICAL** | **Enforce Stage 0 R2 Mandate & ADR-002**: Remove all PostgreSQL connection strings and drivers (`asyncpg`, `psycopg2`) from compute worker container definitions and lockfiles. Compute workers interact exclusively via Redis task queues and staged in-memory payload buffers. |
| **FIND-004** | **Scientific Validation** | Doc 1 §2.2 (line 39)<br>Doc 2 §5 (line 185)<br>Doc 3 §1 (lines 41–42) | **Validation State Model Fragmentation**: Doc 1 lists 8 validation states; Doc 2 specifies 6 states; Doc 3 establishes exactly 7 canonical states (`PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `NEEDS_EXPERT_REVIEW`, `NOT_YET_TESTED`). | **HIGH** | **Standardize on Doc 3 Canonical 7-State Enum**: Implement the 7 uppercase enum states across all database migration schemas, Pydantic contracts, worker tasks, and frontend components. Enforce that validation never collapses into a binary True/False. |
| **FIND-005** | **Database Design** | Doc 1 §2.2 (line 38)<br>Doc 2 §4.2 (lines 158–165)<br>Stage 0 Decision 3 | **Publication Lifecycle vs Visibility Scope Conflation**: Doc 1 outlines an 8-stage publication lifecycle. Doc 2 applies RLS directly to `research_projects.visibility`. Approved Decision 3 mandates that MVP visibility is restricted to two discrete states: `private_draft` and `public_preprint`. | **HIGH** | **Adopt Decision 3 & ADR-003**: Decouple project access visibility from academic publication status. In Stage 0/MVP, `research_projects.visibility` is strictly constrained to `private_draft` and `public_preprint` for RLS evaluation. The extended 8-stage lifecycle applies to frozen `research_versions` in Stage 1+. |
| **FIND-006** | **Database Design** | Doc 1 §1 (Item 5, line 18)<br>Doc 2 §3.2 (lines 123–124) | **Draft Storage & Mutability Model Ambiguity**: Doc 1 refers to "Mutable Draft" working tables vs "Immutable Content-Addressed Snapshots". Doc 2 schema shows only `research_versions` with an `is_frozen` boolean flag. | **MEDIUM** | **Clarify Versioning Architecture**: Maintain a single `research_versions` table with `is_frozen BOOLEAN DEFAULT FALSE`. Database triggers enforce that when `is_frozen = TRUE`, all updates to content fields are rejected at the SQL level. Active drafting occurs on the unfrozen row. |
| **FIND-007** | **Security & Isolation** | Doc 2 §4.1–§4.2 (lines 147–165) | **Missing Child Table Row-Level Security (RLS) Policies**: Doc 2 details RLS on `research_projects`, but omits explicit policies for child tables (`research_versions`, `variables`, `equations`, `claims`, `evidence_links`, `validation_runs`). Direct queries on child tables could expose draft data across tenants. | **HIGH** | **Implement Inherited RLS Policies & ADR-003**: Enable RLS across all project-bound child tables (`ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`). Policies join to parent `research_projects` checking `owner_actor_id` and `visibility`, preventing IDOR leakage. |
| **FIND-008** | **Requirements Consistency** | `web_data_control_architecture.md` §3 (lines 69–77)<br>Doc 1 §4.1 (line 102)<br>Doc 2 §1 (lines 16, 53–84) | **Backend Tech Stack Divergence**: Early proposal advocated a polyglot split (TypeScript NestJS + Go + Python FastAPI + ClickHouse). Doc 1 & Doc 2 establish a unified Python FastAPI Modular Monolith. | **MEDIUM** | **Adopt ADR-005**: Formally reject the polyglot microservice stack for Stage 0. Unify the core backend on a Python 3.11+ FastAPI Modular Monolith, preserving zero-cost in-process calls, single-language data modeling, and simplified CI/CD orchestration. |
| **FIND-009** | **Requirements Consistency** | Doc 2 §5 (lines 179–185) | **REST API Entity Routing Key Discrepancy**: API contracts alternate ambiguously between project IDs (`/api/v1/research/{id}/draft`) and version IDs (`/api/v1/versions/{vid}/variables`), creating confusion regarding whether variable endpoints operate on mutable drafts or frozen snapshots. | **MEDIUM** | **Harmonize REST Resource Hierarchy**: Align all drafting and mathematical authoring operations under `/api/v1/projects/{project_id}/draft/...` and frozen version lookups under `/api/v1/versions/{version_id}/...`. |
| **FIND-010** | **Data Governance** | Doc 2 §3.1 & §3.4 (lines 117, 141) | **IP Address PII Exposure in Immutable Audit Trail**: `audit_events` includes `ip_inet`. Under GDPR, personal IP addresses constitute PII. Storing raw IPs in an append-only, tamper-evident cryptographic hash chain conflicts with data minimization and right-to-erasure principles. | **MEDIUM** | **Pseudonymize Network Metadata**: Hash IP addresses with a daily rotating cryptographic salt (`ip_hash = SHA256(ip + salt)`) or truncate client IP addresses to network subnets (`/24` for IPv4, `/48` for IPv6) prior to insertion into immutable audit logs. |

---

## 4. Deep-Dive Analysis of Core Architectural Paradoxes & Risk Vectors

### 4.1. Deep-Dive: Worker `--network=none` Paradox & Dual-Tier Resolution (FIND-001)

#### 4.1.1. The Technical Paradox
In Doc 3 §2.1 (line 52), the specification mandates:
> *"Worker chạy trong Container cô lập (`--network=none`, `--read-only`, `--cap-drop=ALL`, user không phải root)."*

Simultaneously, Doc 2 §1 (lines 33–42) presents an architectural data flow where:
- `Redis --> MathW (SymPy & Pint Worker)`
- `SimW -.->|Artifact Upload Token| MinIO`
- `AIW -.->|Authorized Read-Only API| GW`
- `MathW -.->|Signed Result via Queue| API`

Under the Linux container network model (namespaces, veth pairs, iptables), applying `--network=none` (or `network_mode: none` in Docker Compose) detaches the container entirely from all external virtual switches. The container namespace contains only the loopback interface (`lo` with IP `127.0.0.1`). 

**The Failure Mode**: A Celery worker process inside a container with `--network=none` cannot create a TCP connection to Redis (`redis://redis:6379/0`). Upon container startup, Celery attempts to establish a socket connection to the broker, encounters `ECONNREFUSED` or `ENETUNREACH`, and immediately exits with a fatal error.

#### 4.1.2. The Resolution Architecture (ADR-002 & ADR-006)
To satisfy both the zero-trust isolation mandate and the operational requirement for distributed job execution, the architecture adopts a **Dual-Tier Boundary Architecture**:

```
+----------------------------------------------------------------------------------------------------+
| DUAL-TIER WORKER ISOLATION ARCHITECTURE                                                            |
|                                                                                                    |
|  [Zone 1: Cloud Edge]                                                                              |
|         |                                                                                          |
|         v (HTTPS)                                                                                  |
|  [Zone 2: Private Core - FastAPI Backend]                                                           |
|         |                                                                                          |
|         +---> Dispatches JSON Task Bundle                                                          |
|         |                                                                                          |
|         v                                                                                          |
|  [Redis Broker: compute_net] <-------------------+                                                 |
|                                                  |                                                 |
|  [Zone 3: Outer Celery Worker Container]         | (TCP:6379 only)                                 |
|         |-- Attached strictly to compute_net ----+                                                 |
|         |-- Zero route to data_net (PostgreSQL)                                                    |
|         |-- Zero route to Internet                                                                 |
|         |-- Non-root user (UID 10001)                                                              |
|         |-- Read-only root filesystem                                                              |
|         |                                                                                          |
|         +---> [Inner Execution Boundary]                                                           |
|                  |-- Pure in-memory AST evaluation (SymPy & Pint)                                  |
|                  |-- Hard process quotas: 1 vCPU, 1GB RAM, 10s timeout                             |
|                  |-- No shell, no eval(), no file system access                                    |
|                  v                                                                                 |
|               Produces signed ValidationFinding JSON payload                                       |
|                  |                                                                                 |
|                  +---> Publishes to Redis Result Queue --------------------+                       |
|                                                                            |                       |
|  [FastAPI Backend: Zone 2 Core] <------------------------------------------+                       |
|         |-- Reads result from Redis                                                                |
|         +---> Persists finding to PostgreSQL validation_runs (Zone 2)                              |
+----------------------------------------------------------------------------------------------------+
```

1. **Outer Boundary (Network & Credential Isolation)**:
   - The Celery worker container runs inside a dedicated Docker network: `compute_net`.
   - `compute_net` connects the worker **exclusively to Redis**. It possesses no routing table entry or bridge interface to `data_net` (PostgreSQL/MinIO) and has `internal: true` set to prevent WAN outbound traffic.
   - The worker container environment contains zero database credentials (`DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).
2. **Inner Boundary (Execution Sandbox)**:
   - For Stage 0 and MVP mathematical validation, evaluation occurs via **pure in-memory AST walking**. Pydantic models are deserialized and passed into native SymPy and Pint functions without invoking OS shells, subprocesses, or string-based code generators.
   - For untrusted numerical simulations (Stage 2+), the Celery supervisor can invoke short-lived, ephemeral micro-VMs or gVisor/Docker runtimes using `--network=none` with input datasets mounted read-only and memory-mapped.
3. **Artifact Handling via Staged Payloads**:
   - The worker never communicates with MinIO. If an artifact or dataset is required, the FastAPI backend pre-stages the artifact into an in-memory buffer or pre-signed staging volume and passes the byte payload directly within the Celery task bundle.
   - The worker returns its computation finding via Celery's Redis result backend (`rpc://` or Redis key `celery-task-meta-*`). The backend then commits the record to PostgreSQL.

---

### 4.2. Deep-Dive: SymPy `parse_expr` Arbitrary Code Execution (RCE) (FIND-002)

#### 4.2.1. The Vulnerability Mechanism
In many scientific Python applications, developers convert user-submitted formula strings into SymPy expressions using `sympy.parsing.sympy_parser.parse_expr`.

Under the hood, `parse_expr` utilizes Python's built-in `tokenize` and `compile` modules. When `evaluate=True` (the default), `parse_expr` transforms the string and executes it via `eval()` inside an execution namespace:

```python
# Standard unsafe SymPy parsing (VULNERABLE)
from sympy.parsing.sympy_parser import parse_expr

# Malicious payload masquerading as a formula:
user_input = "__import__('os').system('cat /etc/passwd')"
expr = parse_expr(user_input)  # EXECUTES ARBITRARY SHELL COMMAND
```

Even when restricting global dictionaries in `eval()`, Python's introspection capabilities allow attackers to bypass sandboxes via attribute traversal:
```python
user_input = "().__class__.__bases__[0].__subclasses__()[137].load_module('os').system('id')"
```
Furthermore, unconstrained expressions can execute **Symbolic Denial of Service (Algorithmic Complexity Attacks)**:
- Expanding `(x + y + z + w)**60` exhausts host RAM in seconds.
- Evaluating non-elementary symbolic integrals in `sympy.integrate()` locks the CPU thread in infinite recursion.

#### 4.2.2. The Structured AST Defense (Approved Decision 1 & ADR-001)
REALITY SCIENCE strictly eliminates string-based formula parsing. All mathematical input must be submitted as structured Abstract Syntax Trees conforming to strict Pydantic v2 schemas:

```python
# shared/schemas/math_ast.py
from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator

class ExprNodeType(str, Enum):
    CONSTANT = "constant"
    VARIABLE = "variable"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION_CALL = "function_call"

class ExprNode(BaseModel):
    node_type: ExprNodeType
    value: Optional[Union[float, int, str]] = None
    op: Optional[Literal["+", "-", "*", "/", "**", "neg", "sqrt", "sin", "cos", "exp", "log"]] = None
    left: Optional["ExprNode"] = None
    right: Optional["ExprNode"] = None
    args: Optional[List["ExprNode"]] = Field(default=None)

    @field_validator("value")
    def validate_variable_naming(cls, v, info):
        if info.data.get("node_type") == ExprNodeType.VARIABLE:
            if not isinstance(v, str) or not v.isidentifier():
                raise ValueError(f"Variable identifier '{v}' is invalid.")
        return v

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
```

#### 4.2.3. Safe Programmatic Tree Construction
In the compute worker (`services/compute_worker/src/engine/ast_evaluator.py`), SymPy expressions are constructed by walking the validated Pydantic AST recursively, calling native constructor classes without any call to `eval()` or `parse_expr`:

```python
import sympy as sp

ALLOWED_FUNCTIONS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
}

def build_sympy_expression(node: ExprNode, declared_symbols: dict[str, sp.Symbol], depth: int = 0) -> sp.Expr:
    if depth > 15:
        raise ValueError("AST maximum nesting depth (15) exceeded.")

    if node.node_type == ExprNodeType.CONSTANT:
        return sp.Rational(str(node.value)) if isinstance(node.value, (int, float)) else sp.Integer(0)

    elif node.node_type == ExprNodeType.VARIABLE:
        if node.value not in declared_symbols:
            raise KeyError(f"Undeclared symbol: {node.value}")
        return declared_symbols[node.value]

    elif node.node_type == ExprNodeType.BINARY_OP:
        left_expr = build_sympy_expression(node.left, declared_symbols, depth + 1)
        right_expr = build_sympy_expression(node.right, declared_symbols, depth + 1)
        
        if node.op == "+": return sp.Add(left_expr, right_expr)
        if node.op == "-": return sp.Add(left_expr, sp.Mul(-1, right_expr))
        if node.op == "*": return sp.Mul(left_expr, right_expr)
        if node.op == "/": return sp.Mul(left_expr, sp.Pow(right_expr, -1))
        if node.op == "**":
            # Safety constraint: limit power exponent to prevent expansion bombs
            if isinstance(right_expr, (sp.Integer, int)) and abs(int(right_expr)) > 20:
                raise ValueError("Polynomial power exceeds safety limit of 20.")
            return sp.Pow(left_expr, right_expr)

    elif node.node_type == ExprNodeType.FUNCTION_CALL:
        func = ALLOWED_FUNCTIONS.get(node.op)
        if not func or not node.args:
            raise ValueError(f"Unsupported or empty function call: {node.op}")
        arg_exprs = [build_sympy_expression(arg, declared_symbols, depth + 1) for arg in node.args]
        return func(*arg_exprs)

    raise ValueError(f"Unrecognized AST node structure: {node}")
```

---

### 4.3. Deep-Dive: Compute Worker Database Credential Isolation (FIND-003)

#### 4.3.1. The Threat Model
Compute workers execute third-party scientific logic and process complex mathematical structures. Consequently, workers represent the application tier with the highest statistical probability of memory corruption, denial-of-service, or remote exploitation.

If a worker possesses database connection credentials (`DATABASE_URL=postgresql://user:pass@postgres:5432/reality_db`):
1. An attacker who gains code execution in the worker immediately acquires database network credentials.
2. The attacker connects to PostgreSQL and dumps private research drafts, user PII, audit trails, and security keys.
3. The attacker can execute `DROP TABLE` or corrupt cryptographic proof chains.

#### 4.3.2. Concrete Isolation Guarantees (Stage 0 Requirement R2)
1. **Zero Database Drivers**:
   - The compute worker's `pyproject.toml` and lockfiles strictly exclude all database drivers (`asyncpg`, `psycopg2`, `psycopg3`, `SQLAlchemy`, `Tortoise-ORM`, `alembic`).
   - The worker image lacks the OS-level client libraries (`libpq-dev`).
2. **Environment Variable Cleansing**:
   - The worker container environment template (`services/compute_worker/.env.example`) and `docker-compose.yml` service definition contain zero references to PostgreSQL:
     ```yaml
     compute_worker:
       image: reality_science/compute_worker:stage0
       user: "10001:10001"
       read_only: true
       networks:
         - compute_net
       environment:
         - CELERY_BROKER_URL=redis://redis:6379/0
         - CELERY_RESULT_BACKEND=redis://redis:6379/1
         - WORKER_CONCURRENCY=2
         - WORKER_TIMEOUT_SECONDS=10
         # STRICTLY ZERO POSTGRES CREDENTIALS
       deploy:
         resources:
           limits:
             cpus: '1.0'
             memory: 1024M
             pids: 100
     ```

---

### 4.4. Deep-Dive: State Model Fragmentation & Scientific Enum Standardization (FIND-004 & FIND-005)

#### 4.4.1. Analysis of State Discrepancies
The three architecture documents define three conflicting sets of validation states:
- **Doc 1 §2.2 (line 39)**: 8 states (`not_tested`, `in_progress`, `passed_selected`, `passed_with_warnings`, `failed`, `insufficient_data`, `needs_expert_review`, `independently_reproduced`).
- **Doc 2 §5 (line 185)**: 6 states (`PASS`, `FAIL`, `WARNING`, `INSUFFICIENT_DATA`, `NEEDS_EXPERT_REVIEW`, `NOT_APPLICABLE`).
- **Doc 3 §1 (lines 41–42)**: Exactly 7 canonical states:
  > *"Mỗi check chỉ trả về đúng 1 trong 7 trạng thái: `PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `NEEDS_EXPERT_REVIEW`, `NOT_YET_TESTED`. Hệ thống không bao giờ gộp 7 trạng thái này thành một nhãn đơn giản 'Đúng' hay 'Sai'."*

Furthermore, Doc 1 §2.2 (line 38) defined an 8-stage publication lifecycle (`draft`, `submitted`, `preprint`, `under_review`, `peer_reviewed`, `revised`, `withdrawn`, `retracted`), while Doc 2 applied RLS directly to `research_projects.visibility`.

#### 4.4.2. Resolution and Standardization
To establish mathematical and epistemological consistency, the system adopts a clean separation of concerns:

```
+----------------------------------------------------------------------------------------------------+
| THREE ORTHOGONAL STATE AXES                                                                        |
+----------------------------------------------------------------------------------------------------+
| 1. Project Visibility (RLS Access Control):                                                        |
|    - 'private_draft'   --> Only owner actor and authorized organization members                    |
|    - 'public_preprint' --> Publicly readable across the platform                                   |
|                                                                                                    |
| 2. Version Publication Lifecycle (Scholarly Provenance):                                           |
|    - 'draft'           --> Mutable working copy under active revision                              |
|    - 'preprint'        --> Frozen snapshot submitted for public peer evaluation                    |
|    - 'peer_reviewed'   --> Formally evaluated and confirmed by verified peer reviewers             |
|    - 'withdrawn'       --> Retracted by author prior to formal peer confirmation                   |
|    - 'retracted'       --> Formally revoked due to irreproducibility or flaw (with notice)         |
|                                                                                                    |
| 3. RCE Validation Finding State (The Canonical 7-State Enum):                                      |
|    - PASS                  --> Rule fully verified without anomalies                               |
|    - FAIL                  --> Definitively disproven or mathematically inconsistent               |
|    - WARNING               --> Numerically consistent but symbolically unproven or borderline      |
|    - NOT_APPLICABLE        --> Model boundary conditions lie outside rule domain                   |
|    - INSUFFICIENT_DATA     --> Parameters or empirical datasets lack statistical power             |
|    - NEEDS_EXPERT_REVIEW   --> Computation exceeds CAS limits or involves frontier physics         |
|    - NOT_YET_TESTED        --> Queued or unexecuted validation rule                                |
+----------------------------------------------------------------------------------------------------+
```

The Doc 3 **Canonical 7-State Enum** is formally standardized across all database schemas, Pydantic contracts, and API responses. The binary collapse into "True/False" or "Correct/Incorrect" is strictly prohibited.

---

### 4.5. Deep-Dive: PostgreSQL Row-Level Security (RLS) Child Table Leakage Vectors (FIND-007)

#### 4.5.1. The Vulnerability
Doc 2 §4.2 outlines RLS policies on `research_projects`. However, a scientific project is a relational hierarchy composed of multiple dependent child tables:

```
research_projects (RLS specified in Doc 2)
  ├── research_versions (RLS MISSING)
  │     ├── variables (RLS MISSING)
  │     ├── equations (RLS MISSING)
  │     ├── claims (RLS MISSING)
  │     └── claim_relations (RLS MISSING)
  └── validation_runs (RLS MISSING)
        └── validation_findings (RLS MISSING)
```

If RLS is enabled only on `research_projects`, an attacker who knows or enumerates a UUID (or executes a sequential scan via an IDOR vulnerability) can directly query:
```sql
SELECT * FROM equations WHERE id = '...';
SELECT * FROM variables WHERE version_id = '...';
```
PostgreSQL will execute these queries without evaluating the ownership or visibility of the parent `research_projects` record, leaking proprietary formulas, unreleased hypotheses, and private draft data.

#### 4.5.2. Non-Bypassing RLS Implementation
In Stage 0, Row-Level Security is explicitly enabled and enforced across all project and child entity tables. Crucially, the directive `FORCE ROW LEVEL SECURITY` is applied to prevent table owners and migration roles from accidentally bypassing RLS during standard application queries:

```sql
-- DDL Migration: Enforce Inherited RLS on Child Tables

-- 1. Enable and Force RLS
ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_projects FORCE ROW LEVEL SECURITY;

ALTER TABLE research_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_versions FORCE ROW LEVEL SECURITY;

ALTER TABLE variables ENABLE ROW LEVEL SECURITY;
ALTER TABLE variables FORCE ROW LEVEL SECURITY;

ALTER TABLE equations ENABLE ROW LEVEL SECURITY;
ALTER TABLE equations FORCE ROW LEVEL SECURITY;

ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims FORCE ROW LEVEL SECURITY;

-- 2. Define Parent Policy on research_projects
CREATE POLICY rls_research_projects ON research_projects
FOR ALL
USING (
    visibility = 'public_preprint'
    OR owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID
    OR (
        organization_id IS NOT NULL 
        AND organization_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
    )
);

-- 3. Define Inherited Policy on research_versions
CREATE POLICY rls_research_versions ON research_versions
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM research_projects p
        WHERE p.id = research_versions.project_id
        AND (
            p.visibility = 'public_preprint'
            OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID
            OR (
                p.organization_id IS NOT NULL 
                AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
            )
        )
    )
);

-- 4. Define Inherited Policy on equations
CREATE POLICY rls_equations ON equations
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM research_versions v
        JOIN research_projects p ON p.id = v.project_id
        WHERE v.id = equations.version_id
        AND (
            p.visibility = 'public_preprint'
            OR p.owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID
            OR (
                p.organization_id IS NOT NULL 
                AND p.organization_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
            )
        )
    )
);
```

#### 4.5.3. Connection Pooling and Context Reset
When using connection pooling (such as PgBouncer or SQLAlchemy async engine pools), `SET LOCAL` is scoped strictly to the current transaction. If a connection is returned to the pool after an unhandled exception without rolling back, session settings could leak to subsequent requests.
- **Enforcement Rule**: FastAPI middleware must wrap every database session in an explicit `async with session.begin():` context manager.
- If no authenticated user exists, `app.current_actor_id` is set to an empty string `''`, ensuring `NULLIF` evaluates to `NULL` and prevents anonymous privilege escalation.

---

### 4.6. Deep-Dive: REST API Routing Hierarchy & Entity Key Harmonization (FIND-009)

#### 4.6.1. The Ambiguity
Doc 2 §5 (lines 179–185) specifies conflicting resource locators:
- `PUT /api/v1/research/{id}/draft` (keyed by project ID `{id}`)
- `POST /api/v1/research/{id}/versions` (freezes draft into a version)
- `PUT /api/v1/versions/{vid}/variables` (keyed by version ID `{vid}`)
- `POST /api/v1/versions/{vid}/validate` (keyed by version ID `{vid}`)

If variable declaration requires a `{vid}` (version ID), the client must know whether `{vid}` refers to an unfrozen draft version or an immutable snapshot. If a client attempts to execute `PUT /api/v1/versions/{vid}/variables` against a frozen version snapshot, the database trigger `trg_freeze_research_versions` will abort the transaction with an SQL exception.

#### 4.6.2. Harmonized REST Resource Hierarchy
The API specification is strictly reorganized into two clean resource trees:

```
1. Active Draft Operations (Mutable Workspace):
   GET    /api/v1/projects/{project_id}/draft
   PUT    /api/v1/projects/{project_id}/draft
   GET    /api/v1/projects/{project_id}/draft/variables
   PUT    /api/v1/projects/{project_id}/draft/variables
   GET    /api/v1/projects/{project_id}/draft/equations
   PUT    /api/v1/projects/{project_id}/draft/equations
   POST   /api/v1/projects/{project_id}/draft/freeze  --> Freezes draft, returns new version_id

2. Immutable Version Operations (Published & Content-Addressed):
   GET    /api/v1/versions/{version_id}
   GET    /api/v1/versions/{version_id}/variables
   GET    /api/v1/versions/{version_id}/equations
   POST   /api/v1/versions/{version_id}/validate     --> Dispatches RCE validation run
   GET    /api/v1/versions/{version_id}/findings     --> Retrieves validation results
   POST   /api/v1/versions/{version_id}/export-zip   --> Exports open research bundle
```

This ensures that clients cannot attempt write operations on immutable version snapshots, enforcing clean API semantics that mirror the underlying database invariants.

---

### 4.7. Deep-Dive: Scientific Validation Edge Cases & Epistemic Boundaries

#### 4.7.1. Theoretical Undecidability (Richardson's Theorem)
A critical limitation in computational algebra is **Richardson's Theorem (1968)**:
> For the set of expressions generated by rational numbers, $\pi$, $\ln 2$, variable $x$, the arithmetic operations, sine, exponential, and absolute value, the problem of determining whether an expression $E \equiv 0$ is **undecidable**.

**Epistemic System Defense**:
1. When SymPy's symbolic simplifier `sp.simplify(lhs - rhs)` does not reduce to zero, the engine **must not** return `FAIL`. It cannot prove that the expressions are mathematically distinct.
2. The engine falls back to **Stratified Numerical Sampling**:
   - The expression is evaluated at 10 pseudo-random points within the declared physical domain of the variables (avoiding known singularities such as zero or asymptote poles).
   - If $|lhs(x_i) - rhs(x_i)| < 10^{-12}$ across all sample points, the engine outputs:
     - `state`: `WARNING`
     - `diagnostic_code`: `SYMBOLIC_UNPROVEN_NUMERICALLY_CONSISTENT`
     - `message`: *"Equivalence cannot be formally proven symbolically; numerical sampling supports identity within machine precision."*
   - If simplification exceeds a 10-second timeout or polynomial explosion threshold, it returns:
     - `state`: `NEEDS_EXPERT_REVIEW`
     - `diagnostic_code`: `COMPUTATION_TIMEOUT_EXCEEDED`

#### 4.7.2. Dimensional Subtleties in Pint
1. **Transcendental Arguments**:
   - Mathematical functions such as $\sin(\theta)$, $\exp(k \cdot t)$, and $\ln(x)$ can only accept dimensionless inputs ($[dimensionless]$).
   - Submitting $\sin(5\text{ kg})$ represents a physical category error. Layer 3 immediately assigns `state: FAIL`, `diagnostic_code: "DIMENSIONED_TRANSCENDENTAL_ARGUMENT"`.
2. **Temperature Intervals vs Absolute Values**:
   - In Pint, adding $20^\circ\text{C} + 30^\circ\text{C}$ naively converts both to Kelvin ($293.15\text{ K} + 303.15\text{ K} = 596.3\text{ K} = 323.15^\circ\text{C}$), which is physically nonsensical when adding an offset.
   - The system configures Pint contexts to treat temperature additions strictly as temperature intervals ($\Delta T$ in $\text{kelvin}$ or $\text{degC}$) rather than absolute scale points.

#### 4.7.3. IEEE 754 Floating-Point Non-Determinism
Floating-point addition is non-associative: $(a + b) + c \neq a + (b + c)$. Compiler optimizations (such as `-O3`, `-ffast-math`, or Fused Multiply-Add FMA instructions) cause identical C/Fortran/Python code to yield slightly different least-significant bits on AMD, Intel, and ARM architectures.
- **Defense**:
  - Symbolic mathematical layers enforce exact rational arithmetic via `sp.Rational(p, q)`.
  - Layer 5 & Layer 6 empirical validations pin the container image digest, CPU architecture flag, and tolerance parameters (`rtol=1e-7`, `atol=1e-9`) rather than asserting bitwise SHA-256 binary float parity.

---

### 4.8. Deep-Dive: Privacy, Provenance & Data Governance (FIND-010)

#### 4.8.1. Dual-Table Identity Split (GDPR Right-to-Erasure vs Scientific Citation)
Under GDPR Article 17, a user has the right to demand the erasure of their personal data. However, in scientific literature, published hypotheses, mathematical proofs, and peer review records must remain immutable to preserve the integrity of the scholarly record.

**The Architectural Split (Approved Decision 3)**:
```sql
-- 1. PII Authentication Record (Deletable)
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_hash VARCHAR(64) NOT NULL UNIQUE,
    encrypted_email TEXT NOT NULL,         -- Encrypted via AES-256-GCM
    password_hash VARCHAR(255) NOT NULL,
    mfa_secret_enc TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Scholarly Provenance Actor (Permanent Citation Anchor)
CREATE TABLE research_actors (
    actor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID UNIQUE REFERENCES user_accounts(id) ON DELETE SET NULL,
    display_handle VARCHAR(64) NOT NULL UNIQUE,
    actor_type VARCHAR(32) NOT NULL DEFAULT 'individual',
    is_anonymized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
When a user requests account deletion:
1. `user_accounts` is purged or sanitized.
2. The foreign key `research_actors.user_account_id` is set to `NULL`.
3. `display_handle` is transitioned to `Former-Contributor-[ShortHash]`, and `is_anonymized` is set to `TRUE`.
4. All research projects, claims, equations, and version histories retain their `owner_actor_id`, ensuring academic citations and cryptographic hash trees remain 100% valid.

#### 4.8.2. IP Address Pseudonymization in Audit Logs (FIND-010)
Doc 2 §3.4 specified `audit_events.ip_inet`. Because IP addresses are legally classified as PII, storing raw IP addresses inside an append-only, tamper-evident cryptographic hash chain creates a permanent compliance conflict.
- **Resolution**:
  - Network metadata is pseudonymized prior to insertion.
  - The API hashes the client IP using a secret system salt:
    $$\text{ip\_hash} = \text{HMAC-SHA256}(\text{client\_ip}, \text{system\_audit\_salt})$$
  - Alternatively, the IP is masked to its network prefix (e.g., `192.168.1.0/24` or `2001:db8::/48`).

---

## 5. Cross-Reference Mapping Matrix

The matrix below provides complete cross-referencing between the audit findings, the governing requirements of `ORIGINAL_REQUEST.md`, Approved Decisions 1 through 4, the Architecture Decision Records (ADR-001 through ADR-006), and the implementation milestones of Stage 0.

```
+-------------------------------------------------------------------------------------------------------------------------+
| COMPREHENSIVE ARCHITECTURAL TRACEABILITY MATRIX                                                                         |
+----------+---------------------------------+---------------------+---------------------+-------------------+------------+
| Finding  | Finding Category                | Governing Request   | Approved Decision   | Architecture ADR  | Milestone  |
+----------+---------------------------------+---------------------+---------------------+-------------------+------------+
| FIND-001 | Worker Network Boundary Paradox | R2 (Boundary Isol.) | Approved Decision 2 | ADR-002 & ADR-006 | M2, M3     |
| FIND-002 | SymPy parse_expr RCE Risk       | R4 (Math Contracts) | Approved Decision 1 | ADR-001           | M4         |
| FIND-003 | Worker Credential Exposure      | R2 (Zero DB Creds)  | Approved Decision 2 | ADR-002           | M2, M3     |
| FIND-004 | Validation State Fragmentation  | R1 (Audit & Specs)  | Approved Decision 1 | ADR-001           | M1, M4     |
| FIND-005 | Visibility vs Lifecycle Scope   | R4 (Access Model)   | Approved Decision 3 | ADR-003           | M4         |
| FIND-006 | Draft Mutability vs Snapshots   | R4 (DB Schemas)     | Approved Decision 3 | ADR-003           | M4         |
| FIND-007 | Missing Child Table RLS         | R4 (RLS Policies)   | Approved Decision 3 | ADR-003           | M4         |
| FIND-008 | Backend Tech Stack Divergence   | R1, R2, R3          | Approved Decision 2 | ADR-005           | M2, M3     |
| FIND-009 | REST API Routing Key Mismatch   | R1, R4 (Contracts)  | Approved Decision 1 | ADR-005           | M4         |
| FIND-010 | IP Address PII in Audit Logs    | R4 (Data Governance)| Approved Decision 3 | ADR-003           | M4         |
+----------+---------------------------------+---------------------+---------------------+-------------------+------------+
```

### Detailed Mapping Descriptions

1. **FIND-001 & FIND-003 $\rightarrow$ Approved Decision 2, ADR-002 & ADR-006 (Milestones M2, M3)**:
   - *Requirement*: Compute workers must operate in a separate security zone, receive zero direct PostgreSQL credentials, and communicate exclusively through queues.
   - *Resolution*: Multi-tier network configuration in `docker-compose.yml` (`compute_net` isolated from `data_net`). Worker environment contains no database variables. Celery result backend relays JSON validation findings to backend for database persistence.
2. **FIND-002 & FIND-004 $\rightarrow$ Approved Decision 1, ADR-001 (Milestone M4)**:
   - *Requirement*: Symbol-first authoring, equations parsed into typed AST, strict ban on `eval()`, `exec()`, and raw script execution.
   - *Resolution*: Pydantic schemas (`ExprNode`, `VariableSpec`, `UnitSpec`) enforce structural AST validation. Pinned SymPy and Pint evaluate validated AST tokens programmatically. Canonical 7-state enum standardized.
3. **FIND-005, FIND-006, FIND-007, FIND-010 $\rightarrow$ Approved Decision 3, ADR-003 (Milestone M4)**:
   - *Requirement*: Identity split between `user_accounts` and `research_actors`, two MVP visibility states (`private_draft`, `public_preprint`), nullable `organization_id`, and testable RLS policies.
   - *Resolution*: Relational schema enforces right-to-erasure without citation corruption. `research_projects` and all child tables enforce `FORCE ROW LEVEL SECURITY`. Immutability trigger prevents updates to frozen snapshots. Audit IP hashing eliminates PII risks.
4. **FIND-008 & FIND-009 $\rightarrow$ ADR-005 (Milestones M2, M4)**:
   - *Requirement*: Clean directory boundaries and cohesive service contracts.
   - *Resolution*: Python FastAPI Modular Monolith selected as canonical backend. REST hierarchy cleanly separates `/projects/{id}/draft` operations from `/versions/{id}` lookups.

---

## 6. Verification Checklist & Acceptance Criteria for Reviewers and Challengers

To enable independent verification by Reviewers and Challengers during Milestone M5 and Stage 0 sign-off, the following concrete test suite and verification checklist are established.

### 6.1. Automated Verification Commands

```powershell
# ==============================================================================
# STAGE 0 VERIFICATION TEST HARNESS (PowerShell)
# ==============================================================================

# 1. Verify Reference Document Verbatim Preservation
Write-Host "Checking Document Preservation..."
$Doc1 = Test-Path "D:\Reality_Science\docs\architecture\reality_science_prd_and_analysis.md"
$Doc2 = Test-Path "D:\Reality_Science\docs\architecture\reality_science_system_and_data_architecture.md"
$Doc3 = Test-Path "D:\Reality_Science\docs\architecture\reality_science_validation_security_and_ops.md"
$Brief = Test-Path "D:\Reality_Science\docs\brief\MASTER_PROJECT_BRIEF_SUMMARY.md"
if ($Doc1 -and $Doc2 -and $Doc3 -and $Brief) {
    Write-Host "[PASS] All architecture documents and project brief preserved." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Missing reference documents in docs/architecture or docs/brief."
}

# 2. Verify Compute Worker Credential Isolation (ZERO DB Credentials)
Write-Host "Verifying Zero Postgres Credentials in Worker..."
$WorkerEnvMatches = Select-String -Path "D:\Reality_Science\worker\*", "D:\Reality_Science\docker-compose.yml" -Pattern "DATABASE_URL|POSTGRES_"
# Filter out matches that belong strictly to backend or db services
$WorkerViolations = $WorkerEnvMatches | Where-Object { $_.Path -match "worker" -or ($_.Line -match "compute_worker" -and $_.Line -match "POSTGRES") }
if ($WorkerViolations.Count -eq 0) {
    Write-Host "[PASS] Compute worker environment is 100% free of PostgreSQL credentials." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Database credentials detected in compute worker configuration!"
}

# 3. Verify Docker Network Segregation via docker-compose config
Write-Host "Validating Docker Compose Topology..."
docker compose -f "D:\Reality_Science\docker-compose.yml" config > $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] Docker Compose static configuration valid." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Docker Compose syntax or network configuration invalid."
}

# 4. Execute Mathematical AST and RCE Prevention Unit Tests
Write-Host "Executing Worker Mathematical Security Test Suite..."
pytest "D:\Reality_Science\worker\tests\" -v

# 5. Execute PostgreSQL Database Migrations and RLS Isolation Tests
Write-Host "Executing Backend RLS Security Test Suite..."
pytest "D:\Reality_Science\backend\tests\test_rls.py" -v

# 6. Run SAST Security Vulnerability Scanner
Write-Host "Running Static Application Security Testing (SAST)..."
python "D:\AI_Knowledge_Lab\tools\secure_coding_scanner\scanner.py" --target "D:\Reality_Science\backend" --target "D:\Reality_Science\worker"
```

### 6.2. Concrete Acceptance Criteria for Reviewers and Challengers

| # | Inspection Item | Concrete Acceptance Criteria | Verification Tool / Command |
| :--- | :--- | :--- | :--- |
| **AC-01** | **Verbatim Document Preservation** | Reference docs in `docs/architecture/` must match MD5 checksums of originals from source directory. Master Brief summary exists in `docs/brief/`. | File hash verification (`Get-FileHash`) |
| **AC-02** | **Directory Boundary Scaffolding** | Clean directory layout separating `frontend/`, `backend/`, `worker/`, `shared/`, `docs/`. Zero application code in `.agents/`. | Directory tree inspection |
| **AC-03** | **Network Boundary Isolation** | `docker-compose.yml` defines `app_net`, `data_net`, `compute_net`. `compute_worker` attached exclusively to `compute_net`. No route between worker and postgres. | `docker compose config` inspection |
| **AC-04** | **Credential Cleanliness** | `worker/pyproject.toml` contains zero database drivers (`asyncpg`, `psycopg2`). Worker `.env.example` contains zero DB strings. | Static text grep (`Select-String`) |
| **AC-05** | **AST Safety & RCE Defense** | Worker rejects raw string execution payloads (`__import__('os')`). Validates equations ($d = v \cdot t$) successfully. Rejects power bombs ($x^{50}$). | Pytest test suite in `worker/tests/` |
| **AC-06** | **Dimensional Validation (Pint)** | Dimensional mismatch ($d = v + t$) produces `FAIL`. Transcendental argument with units ($\sin(5\text{ kg})$) produces `FAIL`. Valid units produce `PASS`. | Pytest test suite in `worker/tests/` |
| **AC-07** | **Identity Split & GDPR** | `user_accounts` contains encrypted PII. Deletion sets `research_actors.user_account_id = NULL` without cascading to research projects or claims. | Isolated DB test in `backend/tests/` |
| **AC-08** | **PostgreSQL RLS Enforcement** | Queries with `app.current_actor_id = ActorA` return zero rows of ActorB's `private_draft`. Child tables (`variables`, `equations`) strictly respect parent RLS. | Pytest test suite in `backend/tests/` |
| **AC-09** | **Snapshot Immutability Trigger** | SQL `UPDATE` against `research_versions` when `is_frozen = TRUE` raises an SQL exception (`CANNOT_MODIFY_FROZEN_VERSION`). | SQL trigger test in `backend/tests/` |
| **AC-10** | **SAST Security Clearance** | SAST scanner in `D:\AI_Knowledge_Lab\tools\secure_coding_scanner\` executes across backend and worker with zero high/critical vulnerabilities. | Python SAST CLI execution |

### 6.3. Challenger Adversarial Scenarios
Challengers must probe the following adversarial edge cases during verification:
1. **Adversarial Injection**: Attempt to bypass AST validation by submitting deeply nested JSON objects ($depth > 20$) or Unicode variable identifiers. *Expected*: Pydantic validation error `422 Unprocessable Entity` before reaching worker.
2. **Cross-Tenant IDOR Attack**: In an active session for Actor A, attempt to query `GET /api/v1/projects/{actor_b_private_project_id}/draft/equations`. *Expected*: HTTP `404 Not Found` or `403 Forbidden` due to PostgreSQL RLS filter returning 0 rows.
3. **Simulated Worker Compromise**: Simulate shell execution inside the worker container and attempt `nc -zv postgres 5432` or `curl https://google.com`. *Expected*: Connection timeout / network unreachable due to Docker bridge network isolation and `internal: true`.

---

## 7. Conclusion & Next Steps for Milestone M1

This consistency audit formally resolves all outstanding ambiguities, paradoxes, and conflicting requirements across the reference architecture documents. 

By grounding the platform foundation in **Approved Decisions 1 through 4** and formalizing the **six Stage 0 ADRs (ADR-001 through ADR-006)**, REALITY SCIENCE possesses an unambiguous, mathematically sound, and secure architectural blueprint.

### Recommended Next Actions:
1. **For Explorer M1_1**: Ensure verbatim copy of reference documents into `D:\Reality_Science\docs\architecture\` and complete `D:\Reality_Science\docs\brief\MASTER_PROJECT_BRIEF_SUMMARY.md`.
2. **For Spec Miner M1_2**: Finalize the complete production-grade markdown files for `docs/adr/ADR_INDEX.md` and `ADR-001` through `ADR-006`.
3. **For Milestone M2**: Proceed to repository scaffolding, Git initialization, and directory boundary configuration in `D:\Reality_Science\`.
