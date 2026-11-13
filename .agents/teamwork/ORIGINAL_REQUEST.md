# Original User Request

## Initial Request — 2026-11-13T03:56:11Z

Audit the three existing architecture documents against each other and against the complete Master Project Brief, incorporate Approved Decisions 1–4, and execute Stage 0 of REALITY SCIENCE to establish a production-grade, secure, and maintainable project foundation.

Working directory: D:\Reality_Science\
Integrity mode: demo
The team must NOT:
- Execute untrusted external scripts without inspecting their contents and purpose.
- Execute unrestricted shell commands or grant agents unrestricted operating-system access.
- Use administrative privileges unless explicitly authorized.
- Execute destructive operations or modify files outside the authorized project workspace without permission.
- Expose credentials, private datasets, or sensitive project information to unauthorized external services.
- Blindly copy entire repositories or unverified implementations into the project.

## Reference Material
- Master Project Brief v1.0 (Evidence-Driven Scientific Platform)
- Architecture Document 1: `reality_science_prd_and_analysis.md` (source: `C:\Users\TIEN PC\.gemini\antigravity\brain\6990c588-45cf-40b9-ba46-23671efa18a9\reality_science_prd_and_analysis.md`)
- Architecture Document 2: `reality_science_system_and_data_architecture.md` (source: `C:\Users\TIEN PC\.gemini\antigravity\brain\6990c588-45cf-40b9-ba46-23671efa18a9\reality_science_system_and_data_architecture.md`)
- Architecture Document 3: `reality_science_validation_security_and_ops.md` (source: `C:\Users\TIEN PC\.gemini\antigravity\brain\6990c588-45cf-40b9-ba46-23671efa18a9\reality_science_validation_security_and_ops.md`)
- AI Knowledge Lab catalog (`D:\AI_Knowledge_Lab\`), including SQLite catalog `data\web_repos.db` (5,992 curated Web repos; CLI: `python -m tools.web_repo_catalog.cli --json search "<query>"`), knowledge base `tools\knowledge_engine\`, and SAST security scanner `tools\secure_coding_scanner\`
- Harvested Telegram GitHub Corpus (`D:\AI_Telegram_Downloads\2026-11-12\full_skill_harvest\by_chat\*.json` and `web_curated\web_github_repos.json` containing 78,221 indexed repositories)

## Requirements

### R1. Architectural Consistency Audit and Architecture Decision Register (ADR)
Audit the three existing architecture documents against each other and against the complete REALITY SCIENCE Master Project Brief. Identify contradictory requirements, missing system boundaries, database design risks, security weaknesses, scientific validation limitations, missing data governance requirements, unresolved architectural decisions, unnecessary complexity, and long-term scalability risks. Produce an Architecture Decision Register (ADR) documenting approved Decisions 1 through 4 (Structured Mathematical Input, Private Scientific Compute Infrastructure with Strict Network Isolation, Workspace and Access Model, Official Project Location) and all additional decisions required for Stage 0. Explain and document the purpose and necessity of every major architectural technology choice in the ADR before adding it. Preserve the three architecture documents verbatim in `D:\Reality_Science\docs\architecture\` and save a baseline copy of the Master Project Brief summary in `D:\Reality_Science\docs\brief\`.

### R2. Workspace Pre-Flight Checks, Repository Scaffolding, and Boundary Isolation
Perform pre-flight workspace checks: verify drive `D:` exists and is writable, inspect whether `D:\Reality_Science\` exists and inventory its existing contents, preserve all existing files without deletion or replacement, and halt immediately with an explicit report if drive `D:` is unavailable or access is denied rather than switching directories. Establish clean directory boundaries separating frontend (Next.js + TypeScript), backend (Python + FastAPI), and isolated compute workers (Celery + Redis). Enforce strict network and data isolation so compute workers operate in a separate security zone, receive zero direct PostgreSQL credentials (`DATABASE_URL`, `POSTGRES_*`), run under least-privilege non-root execution with CPU/memory/PIDs/timeout limits, and communicate with the system exclusively through authorized queues, storage abstractions, and staged input/output artifacts.

### R3. Environment Configuration, Dependency Management, and Orchestration
Create environment variable templates (`.env.example`) for all services containing zero committed secrets. Establish dependency management with pinned versions and reproducible lockfiles across frontend, backend, and compute workers. Provide Docker Compose orchestration defining distinct network security zones (`app_net`, `data_net`, `compute_net`) and isolated container service definitions. If Docker daemon is unavailable in the execution environment, validate container definitions via `docker compose config` and Dockerfile static checks while maintaining local development runnability.

### R4. Automated Testing, Code Quality, SAST Security, and Service Contracts
Establish automated testing frameworks and code quality configs (linting, formatting, type checking) across all services. Integrate SAST security checks on backend and worker code using the tools in `D:\AI_Knowledge_Lab\tools\secure_coding_scanner\`. Implement basic application health checks, database connectivity checks, and Docker health check configurations. Define and test initial service contracts and mathematical boundaries for Decisions 1 and 3:
- Decision 1 contract: define typed mathematical AST contracts (`ExprNode`, `VariableSpec`, `UnitSpec`), separate LaTeX presentation from executable logic, explicitly reject arbitrary code execution, and verify symbolic and dimensional validation boundaries using pinned SymPy and Pint in worker unit tests.
- Decision 3 contract: define initial PostgreSQL migration schemas and isolated DB tests supporting `owner_actor_id`, MVP visibility states (`private_draft`, `public_preprint`), nullable `organization_id` prepared for future organizational expansion, PII separation for research actors, role decoupling, and testable PostgreSQL Row-Level Security (RLS) policies.

### R5. Documentation, Honest Verification, and Stage 0 Completion Report
Document local development, testing, and deployment procedures in the repository. Inspect existing repository resources before recreating, and research reputable architecture patterns in the harvested repository corpus (`D:\AI_Telegram_Downloads\2026-11-12\`) and web repo catalog (`D:\AI_Knowledge_Lab\`) while strictly checking license compatibility and attribution. Execute all automated tests and verifications using isolated test databases (never production data), honestly reporting all passing, failing, or skipped tests without fabrication. Produce a complete 10-point Stage 0 completion report covering:
1. Actual directory created and used
2. Final project folder structure
3. Architecture decisions implemented
4. Documents created or updated
5. Dependencies and technologies configured
6. Tests executed and their actual results
7. Security boundaries established
8. Known limitations and unresolved issues
9. Actions requiring user authorization
10. Recommended next stage
Do not proceed to Stage 1.
