import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.iam_governance.models import ResearchActor
from app.modules.reality_constraint_engine.models import (
    Claim,
    ClaimRelation,
    Equation,
    ValidationFinding,
    ValidationRun,
    Variable,
)



class ResearchProject(Base):
    __tablename__ = "research_projects"
    __table_args__ = (
        CheckConstraint("visibility IN ('private_draft', 'public_preprint')", name="ck_project_visibility"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_actors.id"), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(30), default="private_draft", nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    versions: Mapped[list["ResearchVersion"]] = relationship(
        "ResearchVersion",
        back_populates="project",
        order_by=lambda: ResearchVersion.version_number.desc(),
    )
    owner: Mapped[ResearchActor] = relationship("ResearchActor", foreign_keys=[owner_actor_id], lazy="selectin")

    def __init__(self, **kwargs):
        kwargs.setdefault("is_frozen", False)
        kwargs.setdefault("visibility", "private_draft")
        super().__init__(**kwargs)


class ResearchVersion(Base):
    __tablename__ = "research_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    project: Mapped[ResearchProject] = relationship("ResearchProject", back_populates="versions")
    equations: Mapped[list[Equation]] = relationship("Equation", foreign_keys="[Equation.version_id]", cascade="all, delete-orphan", lazy="selectin")
    variables: Mapped[list[Variable]] = relationship("Variable", foreign_keys="[Variable.version_id]", cascade="all, delete-orphan", lazy="selectin")
    validation_runs: Mapped[list[ValidationRun]] = relationship("ValidationRun", foreign_keys="[ValidationRun.version_id]", cascade="all, delete-orphan", lazy="selectin")
    claims: Mapped[list[Claim]] = relationship("Claim", foreign_keys="[Claim.version_id]", cascade="all, delete-orphan", lazy="selectin")
    claim_relations: Mapped[list[ClaimRelation]] = relationship("ClaimRelation", foreign_keys="[ClaimRelation.version_id]", cascade="all, delete-orphan", lazy="selectin")


    def __init__(self, **kwargs):
        kwargs.setdefault("is_frozen", False)
        kwargs.setdefault("version_number", 1)
        kwargs.setdefault("publication_status", "draft")
        super().__init__(**kwargs)


__all__ = [
    "Claim",
    "ClaimRelation",
    "Equation",
    "ResearchActor",
    "ResearchProject",
    "ResearchVersion",
    "ValidationFinding",
    "ValidationRun",
    "Variable",
]


