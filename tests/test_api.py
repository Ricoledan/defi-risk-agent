"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.graph.workflow import DeFiRiskWorkflow


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    # Initialize the workflow before testing
    import src.api.main as api_module
    api_module.workflow = DeFiRiskWorkflow()

    with TestClient(app) as client:
        yield client

    api_module.workflow = None


def test_health_check(client: TestClient):
    """Test health endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_list_protocols(client: TestClient):
    """Test listing protocols."""
    response = client.get("/protocols?limit=10")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10

    # Check structure
    if data:
        first = data[0]
        assert "name" in first
        assert "slug" in first
        assert "tvl" in first


def test_analyze_protocol(client: TestClient):
    """Test analyzing a protocol."""
    response = client.post("/analyze/aave")

    assert response.status_code == 200
    data = response.json()

    assert "protocol" in data
    assert "assessment" in data
    assert "executive_summary" in data
    assert "detailed_analysis" in data

    assert "aave" in data["protocol"]["name"].lower()
    assert data["assessment"]["score"]["overall"] >= 0


def test_analyze_protocol_not_found(client: TestClient):
    """Test analyzing non-existent protocol."""
    response = client.post("/analyze/nonexistent_xyz123")

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "not found" in detail or "could not identify" in detail


def test_compare_protocols(client: TestClient):
    """Test comparing protocols."""
    response = client.post("/compare", json={"protocols": ["aave", "compound"]})

    assert response.status_code == 200
    data = response.json()

    assert "protocols" in data
    assert "assessments" in data
    assert "comparison_summary" in data
    assert "recommendation" in data

    assert len(data["protocols"]) == 2
    assert len(data["assessments"]) == 2


def test_compare_protocols_too_few(client: TestClient):
    """Test comparing with too few protocols."""
    response = client.post("/compare", json={"protocols": ["aave"]})

    # Pydantic validation returns 422 for invalid input
    assert response.status_code == 422


def test_compare_protocols_too_many(client: TestClient):
    """Test comparing with too many protocols."""
    response = client.post(
        "/compare",
        json={"protocols": ["aave", "compound", "uniswap", "curve", "lido", "maker"]},
    )

    # Pydantic validation returns 422 for invalid input
    assert response.status_code == 422
