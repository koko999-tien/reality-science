import pytest
from app.modules.research_core.models import ResearchProject, ResearchVersion


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
    assert proj.organization_id is None
    assert proj.is_frozen is False

    # Also verify institutional project support
    org_proj = ResearchProject(
        slug="institutional-collaboration",
        title="Institutional Study",
        owner_actor_id="actor_uuid_1234",
        organization_id="org_cern_001",
        visibility="public_preprint",
    )
    assert org_proj.organization_id == "org_cern_001"
    assert org_proj.visibility == "public_preprint"

