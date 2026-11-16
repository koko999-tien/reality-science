import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.compute_orchestrator.errors import ComputeUnavailable
from app.modules.compute_orchestrator.service import compute_job, validate_result
from app.modules.reality_constraint_engine.models import (
    Claim,
    ClaimRelation,
    Equation,
    ValidationFinding,
    ValidationRun,
    Variable,
)
from app.modules.reality_constraint_engine.schemas import (
    EquationCreateRequest,
    EquationVerificationRequest,
    VariableCreateRequest,
)
from app.modules.research_core.models import ResearchVersion
from app.modules.iam_governance.dependencies import get_accessible_version, get_owned_version
from shared.models.enums import DiagnosticCode
from shared.schemas.epistemic_logic import (
    ClaimDependency,
    ClaimGraph,
    ClaimGraphValidationResult,
    ClaimSpec,
    ClaimType,
    DependencyLogic,
    RelationType,
)
from shared.schemas.finding_result import FindingResult, FindingState, TargetEntityType
from shared.schemas.job_bundle import JobBundle
from shared.schemas.math_ast import ExprNode, VariableSpec
from app.modules.reality_constraint_engine.service import verify_claim_graph_backend as verify_claim_graph


router = APIRouter(tags=["reality-constraint-engine", "claims", "validation", "equations", "variables"])


# Request & Response DTOs
class ClaimCreateRequest(BaseModel):
    claim_code: str
    statement: str
    claim_type: str = "HYPOTHESIS"
    target_variable: Optional[str] = None
    expression_ast: Optional[dict] = None
    assumptions: List[str] = Field(default_factory=list)
    dependency_logic: str = "ALL"
    uncertainty_notes: Optional[str] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClaimResponse(BaseModel):
    id: str
    version_id: str
    claim_code: str
    statement: str
    claim_type: str
    target_variable: Optional[str] = None
    canonical_ast_json: Optional[dict] = None
    assumptions_json: List[str] = Field(default_factory=list)
    epistemic_state: str
    uncertainty_notes: Optional[str] = None
    confidence_score: float
    dependency_logic: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ClaimRelationCreateRequest(BaseModel):
    source_claim_id: str
    target_claim_id: str
    relation_type: str = "DEPENDS_ON"
    justification: Optional[str] = None
    weight: float = 1.0


class ClaimRelationResponse(BaseModel):
    id: str
    version_id: str
    source_claim_id: str
    target_claim_id: str
    relation_type: str
    justification: Optional[str] = None
    weight: float
    created_at: str


def _serialize_claim(c: Claim) -> dict:
    return {
        "id": c.id,
        "version_id": c.version_id,
        "claim_code": c.claim_code,
        "statement": c.statement,
        "claim_type": c.claim_type,
        "target_variable": c.target_variable,
        "canonical_ast_json": c.canonical_ast_json,
        "assumptions_json": c.assumptions_json or [],
        "epistemic_state": c.epistemic_state,
        "uncertainty_notes": c.uncertainty_notes,
        "confidence_score": c.confidence_score,
        "dependency_logic": c.dependency_logic,
        "metadata_json": c.metadata_json or {},
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


def _serialize_relation(r: ClaimRelation) -> dict:
    return {
        "id": r.id,
        "version_id": r.version_id,
        "source_claim_id": r.source_claim_id,
        "target_claim_id": r.target_claim_id,
        "relation_type": r.relation_type,
        "justification": r.justification,
        "weight": r.weight,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


def _serialize_equation(eq: Equation) -> dict:
    return {
        "id": eq.id,
        "version_id": eq.version_id,
        "label": eq.label,
        "latex_raw": eq.latex_raw,
        "canonical_ast_json": eq.canonical_ast_json,
        "sympy_expr": eq.sympy_expr,
        "created_at": eq.created_at.isoformat() if eq.created_at else "",
    }


def _serialize_variable(v: Variable) -> dict:
    return {
        "id": v.id,
        "version_id": v.version_id,
        "symbol": v.symbol,
        "name": v.name,
        "unit": v.unit,
        "domain": v.domain,
        "latex_presentation": v.latex_presentation,
        "created_at": v.created_at.isoformat() if v.created_at else "",
    }


def _serialize_finding(f: ValidationFinding) -> dict:
    return {
        "id": f.id,
        "run_id": f.run_id,
        "layer": f.layer,
        "target_entity_type": f.target_entity_type,
        "target_entity_id": f.target_entity_id,
        "job_id": f.job_id,
        "state": f.state,
        "diagnostic_code": f.diagnostic_code,
        "message": f.message,
        "symbolic_simplification": f.symbolic_simplification,
        "dimensions_verified": f.dimensions_verified,
        "diagnostics": f.diagnostics,
        "created_at": f.created_at.isoformat() if f.created_at else "",
    }


def _serialize_run(r: ValidationRun, findings: List[ValidationFinding] = None) -> dict:
    return {
        "id": r.id,
        "version_id": r.version_id,
        "status": r.status,
        "overall_state": r.overall_state,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "findings": [_serialize_finding(f) for f in (findings if findings is not None else getattr(r, "findings", []))],
    }


# =========================================================================
# Validation Endpoints
# =========================================================================

@router.post("/validation/verify", response_model=FindingResult)
async def verify_equation_interactive(payload: EquationVerificationRequest):
    """Interactive equation verification endpoint for frontend UI."""
    job_id = f"verify-{uuid.uuid4()}"
    bundle = JobBundle(
        job_id=job_id,
        version_id=payload.version_id or "interactive",
        target_entity_type=payload.target_entity_type or TargetEntityType.EQUATION,
        target_entity_id=payload.target_entity_id or "interactive",
        expression_ast=payload.expression_ast,
        variables=payload.variables,
        units=payload.units or [],
        system_context=payload.system_context,
        empirical_dataset=payload.empirical_dataset,
        empirical_tolerance_sigma=payload.empirical_tolerance_sigma,
        claim_graph=payload.claim_graph,
    )
    try:
        async with compute_job(bundle) as finding:
            return finding
    except ComputeUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scientific verification is unavailable because the compute worker failed.",
        ) from exc


@router.post("/versions/{version_id}/validate", status_code=status.HTTP_200_OK)
async def validate_version(
    version_id: str,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    """Executes full 6-layer RCE validation pipeline for a research version.
    Loads equations, variables, evidence datasets, and epistemic claims from PostgreSQL.
    Persists ValidationRun and 6 ValidationFinding records in PostgreSQL.
    """
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    # 1. Fetch equations
    stmt_eq = select(Equation).where(Equation.version_id == version_id).order_by(Equation.created_at)
    res_eq = await db.execute(stmt_eq)
    equations_db = list(res_eq.scalars().all())

    # 2. Fetch variables
    stmt_var = select(Variable).where(Variable.version_id == version_id).order_by(Variable.created_at)
    res_var = await db.execute(stmt_var)
    variables_db = list(res_var.scalars().all())

    # 3. Fetch claims & relations
    stmt_claims = select(Claim).where(Claim.version_id == version_id).order_by(Claim.created_at)
    res_claims = await db.execute(stmt_claims)
    claims_db = list(res_claims.scalars().all())

    stmt_rels = select(ClaimRelation).where(ClaimRelation.version_id == version_id).order_by(ClaimRelation.created_at)
    res_rels = await db.execute(stmt_rels)
    relations_db = list(res_rels.scalars().all())

    # Build primary AST if equations exist
    primary_ast = None
    if equations_db and equations_db[0].canonical_ast_json:
        try:
            primary_ast = ExprNode.model_validate(equations_db[0].canonical_ast_json)
        except Exception:
            pass

    variable_specs = [
        VariableSpec(
            symbol=v.symbol,
            name=v.name,
            unit=v.unit,
            domain=v.domain,
            latex_presentation=v.latex_presentation,
        )
        for v in variables_db
    ]

    # Build ClaimGraph if claims exist
    claim_graph = None
    if claims_db:
        claim_specs = []
        for c in claims_db:
            ast_obj = None
            if c.canonical_ast_json:
                try:
                    ast_obj = ExprNode.model_validate(c.canonical_ast_json)
                except Exception:
                    pass
            claim_specs.append(
                ClaimSpec(
                    claim_id=c.id,
                    claim_code=c.claim_code,
                    claim_type=ClaimType(c.claim_type) if c.claim_type in ClaimType.__members__ else ClaimType.HYPOTHESIS,
                    statement=c.statement,
                    target_variable=c.target_variable,
                    expression_ast=ast_obj,
                    assumptions=c.assumptions_json or [],
                    local_state=FindingState(c.epistemic_state) if c.epistemic_state in FindingState.__members__ else FindingState.NOT_YET_TESTED,
                    dependency_logic=DependencyLogic(c.dependency_logic) if getattr(c, "dependency_logic", None) in DependencyLogic.__members__ else DependencyLogic.ALL,
                    confidence_score=float(c.confidence_score) if getattr(c, "confidence_score", None) is not None else 1.0,
                    uncertainty_notes=c.uncertainty_notes,
                    metadata=c.metadata_json or {},
                )
            )
        deps = [
            ClaimDependency(
                source_claim_id=r.source_claim_id,
                target_claim_id=r.target_claim_id,
                relation_type=RelationType(r.relation_type) if r.relation_type in RelationType.__members__ else RelationType.DEPENDS_ON,
                justification=r.justification,
                weight=float(r.weight) if getattr(r, "weight", None) is not None else 1.0,
            )
            for r in relations_db
        ]
        claim_graph = ClaimGraph(
            graph_id=f"graph-{version_id}",
            version_id=version_id,
            claims=claim_specs,
            dependencies=deps,
        )

    # The durable run ID and queue job ID share one server-generated identity.
    job_id = str(uuid.uuid4())
    bundle = JobBundle(
        job_id=job_id,
        version_id=version_id,
        target_entity_type=TargetEntityType.EQUATION if equations_db else (TargetEntityType.CLAIM if claims_db else TargetEntityType.EQUATION),
        target_entity_id=equations_db[0].id if equations_db else (claims_db[0].id if claims_db else version_id),
        expression_ast=primary_ast,
        variables=variable_specs,
        units=[],
        system_context=None,
        empirical_dataset=None,
        claim_graph=claim_graph,
    )

    started_at = datetime.now(timezone.utc)
    try:
        async with compute_job(bundle) as finding_res:
            return await _persist_validation(db, bundle, finding_res, started_at)
    except ComputeUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scientific validation is unavailable because the compute worker failed.",
        ) from exc



async def _persist_validation(db: AsyncSession, bundle: JobBundle,
                               finding_res: FindingResult, started_at: datetime):
    """Only correlated, complete queue results reach this transaction."""
    validate_result(bundle, finding_res)
    version_id, job_id = bundle.version_id, bundle.job_id
    now_utc = datetime.now(timezone.utc)
    run = ValidationRun(
        id=job_id,
        version_id=version_id,
        status="completed",
        overall_state=finding_res.state.value,
        started_at=started_at,
        completed_at=now_utc,
    )
    db.add(run)
    await db.flush()

    persisted_findings: List[ValidationFinding] = []
    for layer_num, l_finding in sorted(finding_res.layer_findings.items()):
        vf = ValidationFinding(
            id=str(uuid.uuid4()),
            run_id=run.id,
            layer=layer_num,
            target_entity_type=bundle.target_entity_type.value,
            target_entity_id=bundle.target_entity_id,
            job_id=job_id,
            state=l_finding.state.value,
            diagnostic_code=l_finding.diagnostic_code,
            message=l_finding.message,
            symbolic_simplification=finding_res.symbolic_simplification if layer_num == 2 else None,
            dimensions_verified=finding_res.dimensions_verified if layer_num == 3 else False,
            diagnostics={"diagnostics": l_finding.diagnostics, "details": l_finding.details or {},
                         "provenance": {"bundle_sha256": finding_res.bundle_sha256,
                                        "job_id": job_id, "version_id": version_id}},
        )
        db.add(vf)
        persisted_findings.append(vf)

    await db.commit()
    return _serialize_run(run, persisted_findings)


@router.get("/versions/{version_id}/validation-runs")
async def list_validation_runs(
    version_id: str,
    _: ResearchVersion = Depends(get_accessible_version),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all historical validation runs with nested layer findings."""
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    stmt_runs = select(ValidationRun).where(ValidationRun.version_id == version_id).order_by(ValidationRun.created_at.desc())
    res_runs = await db.execute(stmt_runs)
    runs = list(res_runs.scalars().all())

    results = []
    for r in runs:
        stmt_f = select(ValidationFinding).where(ValidationFinding.run_id == r.id).order_by(ValidationFinding.layer)
        res_f = await db.execute(stmt_f)
        findings = list(res_f.scalars().all())
        results.append(_serialize_run(r, findings))

    return results


# =========================================================================
# Equations CRUD Endpoints
# =========================================================================

@router.post("/versions/{version_id}/equations", status_code=status.HTTP_201_CREATED)
async def create_equation(
    version_id: str,
    payload: EquationCreateRequest,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new mathematical equation for a research version."""
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")
    if version.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CANNOT_MODIFY_FROZEN_VERSION: Research version {version_id} is frozen and immutable.",
        )

    # Validate AST
    try:
        ExprNode.model_validate(payload.canonical_ast_json)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid canonical_ast_json: {e}")

    eq = Equation(
        id=str(uuid.uuid4()),
        version_id=version_id,
        label=payload.label,
        latex_raw=payload.latex_raw,
        canonical_ast_json=payload.canonical_ast_json,
        sympy_expr=payload.sympy_expr,
    )
    db.add(eq)
    await db.commit()
    await db.refresh(eq)
    return _serialize_equation(eq)


@router.get("/versions/{version_id}/equations")
async def list_equations(
    version_id: str,
    _: ResearchVersion = Depends(get_accessible_version),
    db: AsyncSession = Depends(get_db),
):
    """Lists all equations associated with a research version."""
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    stmt_eq = select(Equation).where(Equation.version_id == version_id).order_by(Equation.created_at)
    res_eq = await db.execute(stmt_eq)
    equations = list(res_eq.scalars().all())
    return [_serialize_equation(eq) for eq in equations]


# =========================================================================
# Variables CRUD Endpoints
# =========================================================================

@router.post("/versions/{version_id}/variables", status_code=status.HTTP_201_CREATED)
async def create_variable(
    version_id: str,
    payload: VariableCreateRequest,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    """Declares a new physical/mathematical variable for a research version."""
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")
    if version.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CANNOT_MODIFY_FROZEN_VERSION: Research version {version_id} is frozen and immutable.",
        )

    var = Variable(
        id=str(uuid.uuid4()),
        version_id=version_id,
        symbol=payload.symbol,
        name=payload.name,
        unit=payload.unit,
        domain=payload.domain,
        latex_presentation=payload.latex_presentation,
    )
    db.add(var)
    await db.commit()
    await db.refresh(var)
    return _serialize_variable(var)


@router.get("/versions/{version_id}/variables")
async def list_variables(
    version_id: str,
    _: ResearchVersion = Depends(get_accessible_version),
    db: AsyncSession = Depends(get_db),
):
    """Lists all declared variables for a research version."""
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    stmt_var = select(Variable).where(Variable.version_id == version_id).order_by(Variable.created_at)
    res_var = await db.execute(stmt_var)
    variables = list(res_var.scalars().all())
    return [_serialize_variable(v) for v in variables]


# =========================================================================
# Epistemic Claims & Relations Endpoints
# =========================================================================

@router.post("/versions/{version_id}/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
    version_id: str,
    payload: ClaimCreateRequest,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")
    if version.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CANNOT_MODIFY_FROZEN_VERSION: Research version {version_id} is frozen and immutable.",
        )

    # Validate AST if present
    if payload.expression_ast:
        try:
            ExprNode.model_validate(payload.expression_ast)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid expression_ast: {e}")

    claim = Claim(
        id=str(uuid.uuid4()),
        version_id=version_id,
        claim_code=payload.claim_code,
        statement=payload.statement,
        claim_type=payload.claim_type,
        target_variable=payload.target_variable,
        canonical_ast_json=payload.expression_ast,
        assumptions_json=payload.assumptions,
        epistemic_state="NOT_YET_TESTED",
        uncertainty_notes=payload.uncertainty_notes,
        confidence_score=payload.confidence_score,
        dependency_logic=payload.dependency_logic,
        metadata_json=payload.metadata,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return _serialize_claim(claim)


@router.get("/versions/{version_id}/claims")
async def list_claims(
    version_id: str,
    _: ResearchVersion = Depends(get_accessible_version),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    stmt_claims = select(Claim).where(Claim.version_id == version_id).order_by(Claim.created_at)
    res_claims = await db.execute(stmt_claims)
    claims = list(res_claims.scalars().all())
    return [_serialize_claim(c) for c in claims]


@router.post("/versions/{version_id}/claims/relations", status_code=status.HTTP_201_CREATED)
async def create_claim_relation(
    version_id: str,
    payload: ClaimRelationCreateRequest,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")
    if version.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CANNOT_MODIFY_FROZEN_VERSION: Research version {version_id} is frozen and immutable.",
        )

    # Check that source and target claims exist in this version
    stmt_src = select(Claim).where(Claim.id == payload.source_claim_id, Claim.version_id == version_id)
    res_src = await db.execute(stmt_src)
    if not res_src.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Source claim not found in version: {payload.source_claim_id}")

    stmt_tgt = select(Claim).where(Claim.id == payload.target_claim_id, Claim.version_id == version_id)
    res_tgt = await db.execute(stmt_tgt)
    if not res_tgt.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target claim not found in version: {payload.target_claim_id}")

    relation = ClaimRelation(
        id=str(uuid.uuid4()),
        version_id=version_id,
        source_claim_id=payload.source_claim_id,
        target_claim_id=payload.target_claim_id,
        relation_type=payload.relation_type,
        justification=payload.justification,
        weight=payload.weight,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return _serialize_relation(relation)


@router.get("/versions/{version_id}/claims/graph")
async def get_claim_graph(
    version_id: str,
    _: ResearchVersion = Depends(get_accessible_version),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    stmt_claims = select(Claim).where(Claim.version_id == version_id).order_by(Claim.created_at)
    res_claims = await db.execute(stmt_claims)
    claims = list(res_claims.scalars().all())

    stmt_rels = select(ClaimRelation).where(ClaimRelation.version_id == version_id).order_by(ClaimRelation.created_at)
    res_rels = await db.execute(stmt_rels)
    relations = list(res_rels.scalars().all())

    return {
        "version_id": version_id,
        "claims": [_serialize_claim(c) for c in claims],
        "relations": [_serialize_relation(r) for r in relations],
    }


@router.post("/versions/{version_id}/claims/verify-epistemic")
async def verify_claims_epistemic(
    version_id: str,
    _: ResearchVersion = Depends(get_owned_version),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResearchVersion).where(ResearchVersion.id == version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version not found: {version_id}")

    # Fetch claims and relations
    stmt_claims = select(Claim).where(Claim.version_id == version_id).order_by(Claim.created_at)
    res_claims = await db.execute(stmt_claims)
    claims_db = list(res_claims.scalars().all())

    stmt_rels = select(ClaimRelation).where(ClaimRelation.version_id == version_id).order_by(ClaimRelation.created_at)
    res_rels = await db.execute(stmt_rels)
    relations_db = list(res_rels.scalars().all())

    # Build Pydantic ClaimGraph
    claim_specs = []
    for c in claims_db:
        ast_obj = None
        if c.canonical_ast_json:
            try:
                ast_obj = ExprNode.model_validate(c.canonical_ast_json)
            except Exception:
                pass
        claim_specs.append(
            ClaimSpec(
                claim_id=c.id,
                claim_code=c.claim_code,
                claim_type=ClaimType(c.claim_type) if c.claim_type in ClaimType.__members__ else ClaimType.HYPOTHESIS,
                statement=c.statement,
                target_variable=c.target_variable,
                expression_ast=ast_obj,
                assumptions=c.assumptions_json or [],
                local_state=FindingState(c.epistemic_state) if c.epistemic_state in FindingState.__members__ else FindingState.NOT_YET_TESTED,
                dependency_logic=DependencyLogic(c.dependency_logic) if getattr(c, "dependency_logic", None) in DependencyLogic.__members__ else DependencyLogic.ALL,
                confidence_score=float(c.confidence_score) if getattr(c, "confidence_score", None) is not None else 1.0,
                uncertainty_notes=c.uncertainty_notes,
                metadata=c.metadata_json or {},
            )
        )

    deps = []
    for r in relations_db:
        rel_type = RelationType(r.relation_type) if r.relation_type in RelationType.__members__ else RelationType.DEPENDS_ON
        deps.append(
            ClaimDependency(
                source_claim_id=r.source_claim_id,
                target_claim_id=r.target_claim_id,
                relation_type=rel_type,
                justification=r.justification,
                weight=float(r.weight) if getattr(r, "weight", None) is not None else 1.0,
            )
        )

    graph_id = f"graph-{version_id}"
    claim_graph = ClaimGraph(
        graph_id=graph_id,
        version_id=version_id,
        claims=claim_specs,
        dependencies=deps,
    )

    # Execute epistemic engine verification
    verification_res = verify_claim_graph(claim_graph)

    # Persist findings and updated claim states if version is not frozen
    now_utc = datetime.now(timezone.utc)
    run = ValidationRun(
        id=str(uuid.uuid4()),
        version_id=version_id,
        status="completed",
        overall_state=verification_res.overall_state.value,
        started_at=now_utc,
        completed_at=now_utc,
    )
    db.add(run)

    for claim_id, finding in verification_res.claim_findings.items():
        vfinding = ValidationFinding(
            id=str(uuid.uuid4()),
            run_id=run.id,
            layer=6,
            target_entity_type="CLAIM",
            target_entity_id=claim_id,
            job_id=graph_id,
            state=finding.state.value,
            diagnostic_code=finding.diagnostic_code,
            message=finding.message,
            dimensions_verified=True,
            diagnostics={
                "diagnostics": finding.diagnostics,
                "contradictions": finding.contradictions,
                "antecedent_failures": finding.antecedent_failures,
            },
        )
        db.add(vfinding)

    # Update claims epistemic_state
    for c in claims_db:
        if c.id in verification_res.claim_findings:
            c.epistemic_state = verification_res.claim_findings[c.id].state.value

    await db.commit()
    return verification_res.model_dump()
