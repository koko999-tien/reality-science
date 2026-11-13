# REALITY SCIENCE — Shared Contracts (`shared/`)

## Overview
This package contains canonical Pydantic v2 schemas and data contracts shared across Zone 2 (FastAPI backend) and Zone 3 (isolated Celery compute worker).

## Modules
- `shared.schemas.math_ast`: Structured mathematical AST models (`ExprNode`, `VariableSpec`, `UnitSpec`, `NodeType`, `OperatorType`, `AllowedFunction`).
- `shared.schemas.job_bundle`: Typed compute payload contract (`JobBundle`, `TargetEntityType`).
- `shared.schemas.finding_result`: Canonical validation output contract (`FindingResult`, `FindingState`).
- `shared.models.enums`: Shared domain enumerations and diagnostic codes.

## Design Invariants
- Strict Pydantic v2 models with `extra="forbid"` to prevent contract drift and silent attribute leakage.
- Self-contained, immutable schemas ensuring safe cross-zone serialization over Redis.
- Zero database or ORM dependencies.
