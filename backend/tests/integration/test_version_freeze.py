from app.modules.research_core.models import ResearchProject


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
