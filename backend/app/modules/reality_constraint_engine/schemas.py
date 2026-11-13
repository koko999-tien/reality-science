from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ValidationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str


class ValidationFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    job_id: str
    state: str
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool
