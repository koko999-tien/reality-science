from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: Optional[str] = None
    visibility: str = "private_draft"


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    title: str
    description: Optional[str] = None
    owner_actor_id: str
    visibility: str
    is_frozen: bool
