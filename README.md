# REALITY SCIENCE

> Evidence-Driven Scientific Hypothesis & Mathematical Reality Constraint Verification Engine

## Architecture Overview
REALITY SCIENCE is organized as a security-isolated monorepo adhering to the three-tier network architecture specified in **ADR-002**:
- **Zone 1: `frontend/`** — Next.js 15+ App Router, TypeScript, Tailwind CSS, KaTeX equation viewer.
- **Zone 2: `backend/`** — FastAPI Modular Monolith partitioned into acyclic domain modules (IAM, Research, RCE, Compute Orchestrator, Evidence Lab) backed by PostgreSQL 16.
- **Zone 3: `worker/`** — Isolated Celery compute worker running with **ZERO database credentials** and **ZERO SQL drivers**, evaluating pure symbolic ASTs (SymPy) and physical dimensional consistency (Pint) under least-privilege non-root execution (UID `10001:10001`).
- **Contracts: `shared/`** — Canonical Pydantic v2 schemas (`ExprNode`, `VariableSpec`, `UnitSpec`, `JobBundle`, `FindingResult`).
- **Orchestration: `docker/` & `docker-compose.yml`** — Hardened multi-stage container definitions and multi-zone bridge networks (`app_net`, `data_net`, `compute_net`).

## Quick Start (Local Development)
1. Copy environment templates:
   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp worker/.env.example worker/.env
   cp frontend/.env.example frontend/.env.local
   ```
2. Start services via Docker Compose:
   ```bash
   docker compose up --build
   ```
3. Run verification test harness:
   ```bash
   python .agents/teamwork/explorer_m2_3/verify_m2_boundaries.py
   ```
