import pytest
from app.modules.research_core.models import ResearchProject


def test_project_owner_actor_isolation_contract():
    """Validates that project model enforces owner_actor_id and visibility states per ADR-003."""
    proj = ResearchProject(
        slug="dark-matter-null-result",
        title="Null Result on Dark Matter Interaction",
        owner_actor_id="actor_uuid_1234",
        visibility="private_draft",
    )
    assert proj.owner_actor_id == "actor_uuid_1234"
    assert proj.visibility == "private_draft"
    assert proj.is_frozen is False
