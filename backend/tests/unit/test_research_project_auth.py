from __future__ import annotations

import re
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash, jwt_signing_is_configured
from app.core.config import settings
from app.db.session import get_db
from app.main import app, lifespan
from app.modules.iam_governance.models import ResearchActor, UserAccount
from app.modules.research_core.models import ResearchProject, ResearchVersion


class MockResult:
    def __init__(self, items: list[Any]):
        self.items = items

    def scalar_one_or_none(self) -> Any | None:
        return self.items[0] if self.items else None

    def scalar_one(self) -> Any:
        assert len(self.items) == 1
        return self.items[0]

    def scalars(self) -> MockResult:
        return self

    def all(self) -> list[Any]:
        return list(self.items)


class MockDb:
    def __init__(self, entities: list[Any]):
        self.entities = entities
        self.info: dict[str, Any] = {}

    async def execute(self, statement: Any, _params: dict[str, Any] | None = None) -> MockResult:
        if not hasattr(statement, "column_descriptions"):
            return MockResult([])

        model = statement.column_descriptions[0]["type"]
        params = statement.compile().params
        candidates = [item for item in self.entities if isinstance(item, model)]
        for name, value in params.items():
            attr = re.sub(r"_\d+$", "", name)
            if any(hasattr(item, attr) for item in candidates):
                candidates = [item for item in candidates if not hasattr(item, attr) or getattr(item, attr) == value]
        return MockResult(candidates)

    def add(self, entity: Any) -> None:
        if isinstance(entity, ResearchProject):
            entity.id = getattr(entity, "id", None) or str(uuid.uuid4())
            entity.created_at = entity.created_at or datetime.now(UTC)
            entity.versions = []
        self.entities.append(entity)

    async def commit(self) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def refresh(self, _entity: Any) -> None:
        return None


@pytest.fixture
def research_records() -> tuple[MockDb, ResearchActor, ResearchProject]:
    actor = ResearchActor(id="actor-owner", display_name="Project Owner")
    user = UserAccount(
        id="user-owner",
        email="owner@example.com",
        hashed_password=get_password_hash("correct-test-password"),
        is_active=True,
    )
    user.actor = actor
    project = ResearchProject(
        id="project-private",
        slug="private-study",
        title="Private Study",
        owner_actor_id=actor.id,
        visibility="private_draft",
        created_at=datetime.now(UTC),
    )
    version = ResearchVersion(
        id="version-private",
        project_id=project.id,
        version_number=1,
        title="Draft",
        publication_status="draft",
        is_frozen=False,
        created_at=datetime.now(UTC),
    )
    project.versions = [version]
    return MockDb([actor, user, project, version]), actor, project


@pytest.fixture
def api_client(research_records: tuple[MockDb, ResearchActor, ResearchProject]):
    db, _, _ = research_records

    async def override_db() -> AsyncGenerator[MockDb, None]:
        yield db

    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_db
    original_jwt_secret = settings.jwt_secret_key
    settings.jwt_secret_key = "test-only-jwt-signing-key-at-least-32-bytes"

    async def make_client() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield make_client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    settings.jwt_secret_key = original_jwt_secret


@pytest.mark.asyncio
async def test_private_project_hides_from_anonymous_and_actor_header_but_allows_owner(
    api_client, research_records
):
    _, actor, _ = research_records
    async with await api_client() as client:
        anonymous = await client.get("/api/v1/projects/private-study")
        spoofed = await client.get(
            "/api/v1/projects/private-study",
            headers={"X-Actor-Id": actor.id},
        )
        owner_token = create_access_token("user-owner")
        owner = await client.get(
            "/api/v1/projects/private-study",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert anonymous.status_code == 404
    assert spoofed.status_code == 404
    assert owner.status_code == 200
    assert owner.json()["owner_actor_id"] == actor.id


@pytest.mark.asyncio
async def test_non_owner_cannot_read_private_project(api_client, research_records):
    db, _, _ = research_records
    other_actor = ResearchActor(id="actor-other", display_name="Other User")
    other_user = UserAccount(
        id="user-other",
        email="other@example.test",
        hashed_password=get_password_hash("another-test-password"),
        is_active=True,
    )
    other_user.actor = other_actor
    db.entities.extend([other_actor, other_user])
    token = create_access_token("user-other")
    async with await api_client() as client:
        response = await client.get(
            "/api/v1/projects/private-study",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_project_is_readable_without_authentication(api_client, research_records):
    db, actor, _ = research_records
    public_version = ResearchVersion(
        id="version-public",
        project_id="project-public",
        version_number=1,
        title="Public Version",
        publication_status="published",
        is_frozen=True,
        created_at=datetime.now(UTC),
    )
    db.entities.append(
        ResearchProject(
            id="project-public",
            slug="public-study",
            title="Public Study",
            owner_actor_id=actor.id,
            visibility="public_preprint",
            created_at=datetime.now(UTC),
        )
    )
    db.entities.append(public_version)
    async with await api_client() as client:
        response = await client.get("/api/v1/projects/public-study")
        public_version_response = await client.get("/api/v1/versions/version-public/equations")

    assert response.status_code == 200
    assert response.json()["slug"] == "public-study"
    assert public_version_response.status_code == 200
    assert public_version_response.json() == []


@pytest.mark.asyncio
async def test_private_version_equation_read_is_owner_only(api_client):
    owner_token = create_access_token("user-owner")
    async with await api_client() as client:
        anonymous = await client.get("/api/v1/versions/version-private/equations")
        owner = await client.get(
            "/api/v1/versions/version-private/equations",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert anonymous.status_code == 404
    assert owner.status_code == 200
    assert owner.json() == []


@pytest.mark.asyncio
async def test_private_version_equation_write_requires_owner(api_client, research_records):
    db, _, _ = research_records
    other_actor = ResearchActor(id="actor-other", display_name="Other User")
    other_user = UserAccount(
        id="user-other",
        email="other@example.test",
        hashed_password=get_password_hash("another-test-password"),
        is_active=True,
    )
    other_user.actor = other_actor
    db.entities.extend([other_actor, other_user])
    other_token = create_access_token("user-other")
    owner_token = create_access_token("user-owner")
    payload = {
        "label": "Energy",
        "latex_raw": "E = m c^2",
        "canonical_ast_json": {"node_type": "variable", "value": "E"},
    }
    async with await api_client() as client:
        non_owner = await client.post(
            "/api/v1/versions/version-private/equations",
            headers={"Authorization": f"Bearer {other_token}"},
            json=payload,
        )
        owner = await client.post(
            "/api/v1/versions/version-private/equations",
            headers={"Authorization": f"Bearer {owner_token}"},
            json=payload,
        )

    assert non_owner.status_code == 404
    assert owner.status_code == 201


@pytest.mark.asyncio
async def test_invalid_bearer_token_does_not_read_private_project(api_client):
    async with await api_client() as client:
        response = await client.get(
            "/api/v1/projects/private-study",
            headers={"Authorization": "Bearer invalid-token"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_project_creation_requires_authenticated_principal(api_client, research_records):
    _, actor, _ = research_records
    async with await api_client() as client:
        response = await client.post(
            "/api/v1/projects",
            headers={"X-Actor-Id": actor.id},
            json={"slug": "spoofed-project", "title": "Spoofed"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_project_creation_uses_authenticated_actor_not_request_identity(api_client, research_records):
    _, actor, _ = research_records
    token = create_access_token("user-owner")
    async with await api_client() as client:
        response = await client.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}", "X-Actor-Id": "attacker"},
            json={"slug": "owner-project", "title": "Owner project"},
        )

    assert response.status_code == 201
    assert response.json()["owner_actor_id"] == actor.id


@pytest.mark.asyncio
async def test_login_returns_bearer_token_and_rejects_wrong_password(api_client):
    async with await api_client() as client:
        success = await client.post(
            "/api/v1/iam/login",
            json={"email": "owner@example.com", "password": "correct-test-password"},
        )
        failure = await client.post(
            "/api/v1/iam/login",
            json={"email": "owner@example.com", "password": "wrong-password"},
        )

    assert success.status_code == 200
    assert success.json()["token_type"] == "bearer"
    assert success.json()["access_token"]
    assert failure.status_code == 401


def test_known_development_jwt_key_is_not_accepted(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "dev_jwt_secret_change_in_production_min_32_bytes_long")

    assert not jwt_signing_is_configured()
    with pytest.raises(RuntimeError, match="signing key"):
        create_access_token("user-owner")


def test_repeated_jwt_signing_key_is_not_accepted(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "a" * 64)

    assert not jwt_signing_is_configured()
    with pytest.raises(RuntimeError, match="signing key"):
        create_access_token("user-owner")


@pytest.mark.parametrize("algorithm", ["none", "RS256", "HS1024"])
def test_unsupported_jwt_algorithm_is_not_accepted(monkeypatch, algorithm):
    monkeypatch.setattr(settings, "jwt_algorithm", algorithm)

    assert not jwt_signing_is_configured()
    with pytest.raises(RuntimeError, match="signing key"):
        create_access_token("user-owner")


@pytest.mark.asyncio
async def test_production_lifespan_rejects_missing_jwt_key(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret_key", "")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        async with lifespan(app):
            pytest.fail("production startup accepted a missing JWT key")
