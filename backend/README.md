# REALITY SCIENCE — Backend API (`backend/`)

## Architecture
The backend is structured as a **FastAPI Modular Monolith** operating in **Zone 2 (Private Core)**:
- **Acyclic Domain Modules**: Cleanly separated into `iam_governance`, `research_core`, `reality_constraint_engine`, `compute_orchestrator`, and `evidence_lab`.
- **Database Boundary**: Direct asynchronous access to PostgreSQL via SQLAlchemy 2.0 and `asyncpg`. Connects to `data_net` internal bridge.
- **Compute Dispatcher**: Packages validated mathematical ASTs into `JobBundle` payloads and publishes them to Redis `compute_tasks` queue. Consumes `FindingResult` responses from Redis and persists findings to PostgreSQL.
- **Security & Authorization**: Row-Level Security (RLS) enforcement via session-scoped `app.current_actor_id`, Argon2id password hashing, and JWT tokens.
