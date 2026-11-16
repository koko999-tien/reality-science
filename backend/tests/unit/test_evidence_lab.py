"""Unit tests for Evidence Lab Ingestion, Validation, and Mock Datasets API (Feature 25)."""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.evidence_lab.service import (
    parse_and_validate_dataset_json,
    register_empirical_dataset,
)
from shared.fixtures.empirical.loader import load_cern_z_resonance


@pytest.mark.asyncio
async def test_list_mock_datasets():
    """Verify GET /api/v1/evidence/mocks returns list of standard benchmarks."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/evidence/mocks")

    assert response.status_code == 200
    data = response.json()
    assert "mocks" in data
    mock_names = [m["name"] for m in data["mocks"]]
    assert "cern_z_resonance" in mock_names
    assert "cern_higgs_resonance" in mock_names
    assert "nasa_hubble_supernovae" in mock_names
    assert "nist_codata_2022" in mock_names


@pytest.mark.asyncio
async def test_fetch_mock_dataset_by_name():
    """Verify GET /api/v1/evidence/mocks/{mock_name} returns full EmpiricalDatasetSpec."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/evidence/mocks/cern_z_resonance")

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "cern-lhc-z-resonance-peak"
    assert data["dataset_type"] == "cern_particle_collision"
    assert len(data["points"]) == 13
    assert data["tolerance_sigma"] == 3.0


@pytest.mark.asyncio
async def test_fetch_mock_dataset_not_found():
    """Verify GET /api/v1/evidence/mocks/{mock_name} returns 404 for unknown benchmark."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/evidence/mocks/nonexistent_dataset")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_dataset_json():
    """Verify POST /api/v1/evidence/upload ingests valid JSON dataset."""
    sample_dataset = {
        "dataset_id": "test-json-upload-1",
        "dataset_name": "Test JSON Ingestion",
        "dataset_type": "custom",
        "independent_variable_symbol": "x",
        "dependent_variable_symbol": "y",
        "points": [
            {"independent_variable": 1.0, "observed_value": 10.0, "uncertainty": 0.5, "label": "p1"},
            {"independent_variable": 2.0, "observed_value": 20.0, "uncertainty": 0.5, "label": "p2"},
            {"independent_variable": 3.0, "observed_value": 30.0, "uncertainty": 0.5, "label": "p3"},
        ],
    }
    json_bytes = json.dumps(sample_dataset).encode("utf-8")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("dataset.json", json_bytes, "application/json")},
            data={"dataset_name": "Test JSON Ingestion", "tolerance_sigma": "2.5"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["dataset_id"] != "test-json-upload-1"
    assert data["point_count"] == 3
    assert "sha256_hash" in data
    assert len(data["sha256_hash"]) == 64

    # Verify retrieval
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_res = await ac.get(f"/api/v1/evidence/datasets/{data['dataset_id']}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["dataset_name"] == "Test JSON Ingestion"
    assert len(retrieved["points"]) == 3


@pytest.mark.asyncio
async def test_upload_cannot_overwrite_dataset_with_client_chosen_id():
    first = {
        "dataset_id": "shared-client-id",
        "dataset_name": "First Upload",
        "dataset_type": "custom",
        "points": [
            {"independent_variable": 1, "observed_value": 2},
            {"independent_variable": 2, "observed_value": 4},
        ],
    }
    second = {**first, "dataset_name": "Second Upload", "points": [
        {"independent_variable": 10, "observed_value": 20},
        {"independent_variable": 20, "observed_value": 40},
    ]}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first_response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("first.json", json.dumps(first).encode(), "application/json")},
        )
        second_response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("second.json", json.dumps(second).encode(), "application/json")},
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        first_id = first_response.json()["dataset_id"]
        second_id = second_response.json()["dataset_id"]
        assert first_id != "shared-client-id"
        assert second_id != "shared-client-id"
        assert first_id != second_id

        stored_first = await ac.get(f"/api/v1/evidence/datasets/{first_id}")
        stored_second = await ac.get(f"/api/v1/evidence/datasets/{second_id}")
        assert stored_first.json()["dataset_name"] == "First Upload"
        assert stored_second.json()["dataset_name"] == "Second Upload"


def test_dataset_registry_rejects_duplicate_server_id():
    dataset, digest = parse_and_validate_dataset_json(json.dumps({
        "dataset_name": "Duplicate Guard",
        "dataset_type": "custom",
        "points": [
            {"independent_variable": 1, "observed_value": 2},
            {"independent_variable": 2, "observed_value": 4},
        ],
    }).encode())
    register_empirical_dataset(dataset, digest)
    with pytest.raises(ValueError, match="already exists"):
        register_empirical_dataset(dataset, digest)


@pytest.mark.asyncio
async def test_upload_rejects_request_over_limit():
    from app.modules.evidence_lab.router import MAX_DATASET_REQUEST_BYTES

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/upload",
            content=b"x" * (MAX_DATASET_REQUEST_BYTES + 1),
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_dataset_csv():
    """Verify POST /api/v1/evidence/upload ingests valid CSV dataset."""
    csv_content = (
        "independent_variable,observed_value,uncertainty,label\n"
        "10.0,100.0,2.5,point_A\n"
        "20.0,200.0,3.0,point_B\n"
        "30.0,300.0,4.0,point_C\n"
    ).encode("utf-8")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("observations.csv", csv_content, "text/csv")},
            data={
                "dataset_name": "CSV Upload Test",
                "dataset_type": "custom",
                "independent_variable_symbol": "energy",
                "dependent_variable_symbol": "cross_section",
                "tolerance_sigma": "3.0",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["dataset_name"] == "CSV Upload Test"
    assert data["point_count"] == 3
    assert "sha256_hash" in data


@pytest.mark.asyncio
async def test_upload_empty_file_rejected():
    """Verify POST /api/v1/evidence/upload rejects empty payload with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("empty.json", b"", "application/json")},
        )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_malformed_json_rejected():
    """Verify POST /api/v1/evidence/upload rejects syntax-invalid JSON with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/upload",
            files={"file": ("corrupt.json", b"{invalid json content:", "application/json")},
        )

    assert response.status_code == 400
    assert "validation failure" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_dataset_dry_run():
    """Verify POST /api/v1/evidence/validate dry-run returns validation report."""
    dataset = load_cern_z_resonance()
    json_bytes = json.dumps(dataset.model_dump()).encode("utf-8")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/evidence/validate",
            files={"file": ("cern_z.json", json_bytes, "application/json")},
        )

    assert response.status_code == 200
    report = response.json()
    assert report["is_valid"] is True
    assert report["point_count"] == 13
    assert report["dataset_type"] == "cern_particle_collision"
    assert report["x_range"] is not None
    assert report["x_range"][0] == 86.0
    assert report["x_range"][1] == 96.0
    assert len(report["errors"]) == 0


@pytest.mark.asyncio
async def test_get_dataset_not_found():
    """Verify GET /api/v1/evidence/datasets/{id} returns 404 for unknown dataset."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/evidence/datasets/unknown-id-12345")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
