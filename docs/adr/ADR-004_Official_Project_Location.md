# ADR-004: Standard Workspace Root & Pre-Flight Directory Preservation

## Status
**Approved** (Governing Mandate: Approved Decision 4)

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
Development, automated multi-agent workflows, Docker orchestration, and CI pipelines operating on Windows host environments require a fixed, unambiguous filesystem root.

Dynamic path detection or operating across fluctuating drives (`C:` vs `D:`) creates critical operational risks:
1. **Path Drift & Fragmentation**: Different agents or build tools create scattered directories across user profiles (`C:\Users\...`), temp directories, or system roots, resulting in broken absolute path references and fragmented artifacts.
2. **Accidental File Overwrite / Deletion**: Automated build or scaffolding tools run without pre-flight checks can wipe existing experimental data, previous survey work, or uncommitted files.
3. **Container Volume Mount Failures**: Docker Desktop on Windows requires deterministic drive sharing. Moving roots breaks volume mount declarations in `docker-compose.yml`.

### Alternatives Considered
- **Alternative 1: Dynamic Current Working Directory (`.` / `pwd`)**: Rejected. Subagents and nested terminal processes frequently change directories, breaking path consistency across tasks.
- **Alternative 2: User Home Directory (`C:\Users\<user>\...`)**: Rejected. Subject to host-specific username paths, permission restrictions, long path limits, and mixing personal files with project assets.
- **Alternative 3: Canonical Workspace Root at `D:\Reality_Science\` with Pre-Flight Checks**: Chosen.

## Decision
1. **Authoritative Project Workspace Root**:
   - The canonical root directory for all REALITY SCIENCE development, scaffolding, Docker volumes, and documentation is strictly **`D:\Reality_Science\`**.
   - All relative paths in configuration files and scripts resolve relative to this root.
2. **Mandatory Pre-Flight Verification Gate**:
   - Every bootstrap script, agent setup routine, and test runner must execute a pre-flight verification sequence before modifying the filesystem:
     a. Verify that Drive `D:` exists and is writable.
     b. **Halt on Missing Drive**: If Drive `D:` is missing or unwritable, the system must **halt immediately** with an explicit error report (`PREFLIGHT_FAIL_DRIVE_D_UNAVAILABLE`) rather than switching drives or falling back to `C:`.
     c. **Asset Inventory**: Inspect and inventory existing files in `D:\Reality_Science\`.
     d. **Non-Destructive Preservation**: All pre-existing files, architectural notes, and agent logs must be preserved verbatim without silent overwriting or deletion.
3. **Standard Monorepo Directory Boundaries**:
   ```
   D:\Reality_Science\
   ├── .agents/                 # Multi-agent teamwork coordination (read-only to app code)
   ├── apps/
   │   └── web/                 # Next.js 14+ Frontend (Zone 1)
   ├── services/
   │   ├── api/                 # FastAPI Modular Monolith (Zone 2)
   │   └── compute_worker/      # Celery Isolated Compute Worker (Zone 3)
   ├── packages/
   │   └── contracts/           # Shared Pydantic AST schemas & TypeScript types
   ├── docker/                  # Dockerfiles & container configurations
   ├── docs/                    # Architecture, ADRs, and Master Brief documentation
   │   ├── adr/                 # Architecture Decision Records
   │   ├── architecture/        # Preserved baseline architecture documents
   │   └── brief/               # Preserved Master Project Brief summary
   ├── docker-compose.yml       # Multi-zone Docker Compose orchestration
   ├── .env.example             # Zero-secret environment template
   └── README.md                # Developer onboarding & operations guide
   ```

## Consequences

### Positive
- **Guaranteed Path Determinism**: Scripts, Docker mounts, and test assertions operate against a single predictable root across all developer and agent environments.
- **Destruction Prevention**: The pre-flight verification gate stops destructive operations before filesystem modification begins.
- **Reproducible Volume Mounts**: Docker bind mounts remain stable and identical across runs.

### Negative / Trade-Offs
- **Host Drive Requirement**: Host environments must provide Drive `D:` or create a virtual drive mount.

### Risks & Mitigations
- **Risk**: Developer workstation lacks a secondary physical drive `D:`.
  - *Mitigation*: Provide a standard `setup_drive_d.bat` utility using Windows `subst D: <path>` (e.g., `subst D: C:\Reality_Science_Root`) allowing single-drive hosts to satisfy the Drive D: invariant seamlessly.

## Compliance & Verification Rules
1. **Pre-Flight Test Script**: A shell/PowerShell test `tests/preflight_check.ps1` must verify `Test-Path "D:\"` and check write permissions.
2. **Mount Verification**: Docker Compose validation (`docker compose config`) must verify that all bind mount sources begin with `D:\Reality_Science` or relative monorepo paths (`.`).
