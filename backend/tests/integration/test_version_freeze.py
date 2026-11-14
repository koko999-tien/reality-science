from app.modules.research_core.models import ResearchProject, ResearchVersion


def test_project_version_freeze_flag():
    proj = ResearchProject(
        slug="verified-cosmology",
        title="Cosmological Constant Bounds",
        owner_actor_id="actor_uuid_9999",
        visibility="public_preprint",
        is_frozen=True,
    )
    assert proj.is_frozen is True
    assert proj.visibility == "public_preprint"


def test_research_version_freeze_contract():
    ver_draft = ResearchVersion(
        project_id="proj_123",
        version_number=1,
        title="Initial Draft",
    )
    assert ver_draft.is_frozen is False
    assert ver_draft.publication_status == "draft"

    ver_frozen = ResearchVersion(
        project_id="proj_123",
        version_number=2,
        title="Published Preprint v2",
        publication_status="published",
        is_frozen=True,
    )
    assert ver_frozen.is_frozen is True
    assert ver_frozen.publication_status == "published"

