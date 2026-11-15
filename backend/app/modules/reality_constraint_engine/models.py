import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Equation(Base):
    __tablename__ = "equations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    latex_raw: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_ast_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sympy_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Variable(Base):
    __tablename__ = "variables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(30), default="real", nullable=False)
    latex_presentation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    overall_state: Mapped[str] = mapped_column(String(30), default="NOT_YET_TESTED", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    findings: Mapped[list["ValidationFinding"]] = relationship("ValidationFinding", back_populates="run", cascade="all, delete-orphan")


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    layer: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(50), default="EQUATION", nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    diagnostic_code: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    symbolic_simplification: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    diagnostics: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    run: Mapped[ValidationRun] = relationship("ValidationRun", back_populates="findings")
