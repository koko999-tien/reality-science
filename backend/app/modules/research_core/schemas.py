
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: str | None = None
    visibility: str = "private_draft"


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    title: str
    description: str | None = None
    owner_actor_id: str
    visibility: str
    is_frozen: bool
