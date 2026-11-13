# ADR-003: Dual-Table Identity Split, Scientific Provenance, and Two-State Row-Level Security

## Status
**Approved** (Governing Mandate: Approved Decision 3)

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
Scientific verification systems must resolve an inherent tension between privacy regulations and scientific permanence:
1. **Privacy Law Mandate (GDPR / PDPD Right to Erasure)**: Users have a legal right to request complete deletion of their account and Personally Identifiable Information (PII).
2. **Scientific Epistemic Permanence**: Scientific papers, mathematical proofs, derivations, citations, and peer reviews must remain immutable and permanently verifiable. Cascading deletion of a user's account would break the academic citation graph, orphan claims, and destroy historical provenance.
3. **Workspace Access Complexity**: While research publications eventually pass through complex multi-stage lifecycles (submitted, preprint, peer-reviewed, retracted), evaluating multi-state lifecycle workflows in database Row-Level Security (RLS) policies causes severe query performance degradation, logic bugs, and authorization bypass vulnerabilities.
4. **Multi-Tenancy Growth**: The system must support independent solo researchers at MVP without forcing artificial organization creation, while cleanly providing for institutional multi-tenancy (universities, laboratories) in future phases.

### Alternatives Considered
- **Alternative 1: Single `users` Table with Cascading Delete**: Rejected. Legally compliant but scientifically catastrophic; destroys scientific literature and references upon user deletion.
- **Alternative 2: Single `users` Table with Soft Deletes (`deleted_at`)**: Rejected. Retaining PII in soft-deleted rows violates GDPR data minimization; overwriting user rows with nulls corrupts historical actor differentiation.
- **Alternative 3: Complex Multi-State RLS Policies**: Rejected. Evaluating 8 publication states and 7 validation states in every SQL row policy creates unmaintainable SQL expressions and slow table scans.
- **Alternative 4: Dual-Table Identity Split with Inherited RLS and Nullable Organization ID**: Chosen. Separation of authentication from scholarly persona, paired with a minimal two-state project visibility model.

## Decision
1. **Dual-Table Identity Split Architecture**:
   - `user_accounts`: Contains authentication credentials and PII (`id`, `email_hash` SHA-256, `encrypted_email` AES-256-GCM, `password_hash` Argon2id, `mfa_secret_enc`, `status`). Never referenced by academic citation foreign keys.
   - `research_actors`: Holds public scholarly identity (`actor_id`, `user_account_id` NULLABLE, `display_handle`, `actor_type`, `is_anonymized`). Referenced by all projects, versions, claims, equations, and reviews.
   - **Right to Erasure Handling**: Upon account deletion, the `user_accounts` row is erased. In `research_actors`, `user_account_id` is set to `NULL`, `display_handle` becomes `Contributor-Ghost-[ShortHash]`, and `is_anonymized` is set to `TRUE`. All scholarly records, citations, and version hashes remain 100% intact with unbroken relational integrity.
2. **Minimal Two-State MVP Visibility Model**:
   - `research_projects.visibility` is strictly constrained to two states in Stage 0/MVP:
     - `private_draft`: Accessible strictly by the project owner actor (`owner_actor_id`) and designated collaborators.
     - `public_preprint`: Publicly readable to all authenticated and anonymous actors; open for peer review and challenge.
   - Detailed publication lifecycles (`under_review`, `peer_reviewed`, `withdrawn`, `retracted`) are tracked in `research_versions.publication_status` and do not complicate the core authorization boundary.
3. **Nullable Organization ID for Multi-Tenancy**:
   - `research_projects.organization_id UUID NULL REFERENCES organizations(id) ON DELETE SET NULL`.
   - Supports solo researchers immediately (`organization_id = NULL`), while seamlessly enabling institutional workspaces (`organization_id = <uuid>`) in Stage 2+ with zero schema refactoring.
4. **PostgreSQL Row-Level Security (RLS) Enforcement**:
   - RLS is enabled and forced across all project-bound tables: `research_projects`, `research_versions`, `variables`, `equations`, `claims`, and `validation_runs`.
   - Application connections set transaction-scoped session variables:
     ```sql
     SET LOCAL app.current_actor_id = :actor_id;
     SET LOCAL app.current_org_id = :org_id;
     ```
   - Child tables enforce inherited RLS via project ownership or public preprint visibility.

### Relational Schema Blueprint
```sql
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_hash VARCHAR(64) UNIQUE NOT NULL,
    encrypted_email BYTEA NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_secret_enc BYTEA NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE research_actors (
    actor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID NULL REFERENCES user_accounts(id) ON DELETE SET NULL,
    display_handle VARCHAR(64) UNIQUE NOT NULL,
    actor_type VARCHAR(32) NOT NULL DEFAULT 'INDIVIDUAL' CHECK (actor_type IN ('INDIVIDUAL', 'ORGANIZATION', 'AI_AGENT', 'SYSTEM_BOT')),
    is_anonymized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE research_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(128) UNIQUE NOT NULL,
    owner_actor_id UUID NOT NULL REFERENCES research_actors(actor_id),
    organization_id UUID NULL REFERENCES organizations(id) ON DELETE SET NULL,
    visibility VARCHAR(32) NOT NULL DEFAULT 'private_draft' CHECK (visibility IN ('private_draft', 'public_preprint')),
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_projects FORCE ROW LEVEL SECURITY;

CREATE POLICY project_access_policy ON research_projects
    FOR ALL
    USING (
        visibility = 'public_preprint'
        OR owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID
        OR (organization_id IS NOT NULL AND organization_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID)
    )
    WITH CHECK (
        owner_actor_id = NULLIF(current_setting('app.current_actor_id', true), '')::UUID
    );
```

## Consequences

### Positive
- **Guaranteed GDPR Compliance**: User PII is completely expunged on demand without breaking academic attribution or corrupting cryptographic version hashes.
- **Elimination of IDOR Vulnerabilities**: RLS enforces access at the PostgreSQL engine level; application-level bugs cannot leak draft equations or private claims across actors.
- **Future-Proof Multi-Tenancy**: Individual researchers and institutional labs share a unified schema from day one.

### Negative / Trade-Offs
- **Session Management Overhead**: Backend database drivers must set session variables (`SET LOCAL`) on every transaction.
- **Non-Superuser Requirement**: The application connection pool must use a dedicated unprivileged user (`rs_app_user`) because PostgreSQL superusers bypass RLS by default.

### Risks & Mitigations
- **Risk**: Connection pooling (e.g. PgBouncer in transaction mode) leaking session variables across requests.
  - *Mitigation*: Session variables are strictly declared with `SET LOCAL`, ensuring automatic expiration at `COMMIT` or `ROLLBACK`. Furthermore, connection checkout executes `RESET ALL` or `DISCARD ALL` upon recycling.

## Compliance & Verification Rules
1. **Right-to-Erasure Test**: Test deleting a `user_account` record and verify that corresponding `research_actors` has `user_account_id = NULL`, `is_anonymized = TRUE`, and all child project records remain intact.
2. **RLS Cross-Tenant Isolation Test**: Execute queries under Actor A context attempting to read or write Actor B's `private_draft` project and assert that 0 rows are returned / operation is forbidden.
3. **Child Table RLS Test**: Directly query `equations` table with Actor A context for an equation belonging to Actor B's private project; assert zero rows returned.
