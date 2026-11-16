
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: str | None = None
    visibility: str = "private_draft"


class ResearchVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    version_number: int
    title: str
    content_hash: str | None = None
    publication_status: str
    is_frozen: bool
    created_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    title: str
    description: str | None = None
    owner_actor_id: str
    visibility: str
    is_frozen: bool
    created_at: datetime
    versions: list[ResearchVersionResponse] = Field(default_factory=list)
