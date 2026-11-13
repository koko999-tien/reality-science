# Architecture Decision Register (ADR) Index

## REALITY SCIENCE — Evidence-Driven Scientific Verification Platform

This register records the key architectural and design decisions made for REALITY SCIENCE. Each record documents the context, decision, consequences, and verification rules for a fundamental architectural choice.

### Architectural Decision Records

| ADR ID | Title | Status | Date | Deciders | Category |
| :--- | :--- | :---: | :---: | :--- | :--- |
| [ADR-001](ADR-001_Structured_Mathematical_Input.md) | Structured Mathematical AST Input & Elimination of Arbitrary Code Execution | **Approved** | 2026-11-13 | Technical Steering Committee / Master Brief | Security / Scientific Engine |
| [ADR-002](ADR-002_Private_Scientific_Compute_Infrastructure.md) | Three-Tier Network Isolation & Credential-Free Compute Workers | **Approved** | 2026-11-13 | Technical Steering Committee / Master Brief | Infrastructure / Security |
| [ADR-003](ADR-003_Workspace_and_Access_Model.md) | Dual-Table Identity Split, Scientific Provenance, and Two-State Row-Level Security | **Approved** | 2026-11-13 | Technical Steering Committee / Master Brief | Data Architecture / Privacy |
| [ADR-004](ADR-004_Official_Project_Location.md) | Standard Workspace Root & Pre-Flight Directory Preservation | **Approved** | 2026-11-13 | Technical Steering Committee / Master Brief | Operations / Tooling |
| [ADR-005](ADR-005_Python_FastAPI_Modular_Monolith.md) | Modular Monolith Backend Architecture in Python FastAPI | **Approved** | 2026-11-13 | Technical Steering Committee / Architecture Survey | Backend Architecture |
| [ADR-006](ADR-006_Isolated_Worker_Queue_and_Staging_Architecture.md) | Staged Payload Broker Pattern for Asynchronous Compute Jobs | **Approved** | 2026-11-13 | Technical Steering Committee / Architecture Survey | Compute Architecture |

---

### Decision Dependency & Relationship Matrix

```
   [ADR-004: Workspace Root D:\]
                │
                ▼
   [ADR-005: FastAPI Modular Monolith] ◄──────────────┐
         │                       │                    │
         ▼                       ▼                    │
   [ADR-003: Identity & RLS]   [ADR-001: Math AST]    │
         │                       │                    │
         │                       ▼                    │
         └─────────────► [ADR-006: Staged Broker] ────┤
                                 │                    │
                                 ▼                    │
                         [ADR-002: Network Isolation] ┘
```

1. **ADR-004** anchors the file tree that hosts the Monolith (**ADR-005**), Worker packages, and documentation.
2. **ADR-005** coordinates domain models, housing the Identity/RLS engine (**ADR-003**) and packaging mathematical expressions (**ADR-001**) into job bundles.
3. **ADR-001** defines the typed JSON AST payload that allows **ADR-006** to transmit tasks through Redis without requiring direct database access.
4. **ADR-006** establishes the broker communication pattern that satisfies the extreme network isolation mandated in **ADR-002**.
5. **ADR-002** enforces multi-zone network boundaries (`app_net`, `data_net`, `compute_net`) so that **ADR-005** and compute workers operate within their appropriate security trust zones.

---

### Change Management Protocol

1. **Immutability of Approved ADRs**: Once an ADR is marked `Approved` and merged, its text is immutable. If architectural requirements change, a new ADR must be authored (e.g. `ADR-007`) that explicitly supersedes the earlier ADR via a `Supersedes: ADR-xxx` metadata header.
2. **Verification Gate**: Any pull request or milestone that alters system boundaries, database access patterns, or execution security must reference the corresponding ADR and pass all automated compliance checks defined therein.
