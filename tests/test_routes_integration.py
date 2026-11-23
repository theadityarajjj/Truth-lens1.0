import pytest

from app import create_app
from app.services import history
from app import routes


class TestConfig:

    TESTING = True
    MAX_INPUT_CHARS = 5000
    GEMINI_API_KEY = "test-key"
    DATABASE_PATH = ":memory:"


@pytest.fixture
def client(monkeypatch):

    # Prevent real database initialization during tests.
    monkeypatch.setattr(
        history,
        "initialize_database",
        lambda *args, **kwargs: None
    )

    app = create_app(TestConfig)

    return app.test_client()


def test_analyze_success(client, monkeypatch):

    monkeypatch.setattr(
        routes,
        "extract_claims",
        lambda text: ["The Earth revolves around the Sun."]
    )

    monkeypatch.setattr(
        routes,
        "search_all_sources",
        lambda claim: []
    )

    monkeypatch.setattr(
        routes,
        "verify_claim",
        lambda claim, evidence: {
            "verdict": "SUPPORTED",
            "explanation": "Test verification.",
            "evidence_assessment": [],
            "limitations": "Test limitations.",
            "error": False
        }
    )

    monkeypatch.setattr(
        routes,
        "save_analysis",
        lambda text, claims, results: 123
    )

    response = client.post(
        "/analyze",
        json={
            "text": "The Earth revolves around the Sun."
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["total_claims"] == 1
    assert data["claims"][0]["verdict"] == "SUPPORTED"
    assert data["analysis_id"] == 123


def test_analyze_empty_input(client):

    response = client.post(
        "/analyze",
        json={"text": ""}
    )

    assert response.status_code == 400


def test_analyze_invalid_input(client):

    response = client.post(
        "/analyze",
        json={"text": 123}
    )

    assert response.status_code == 400


def test_analyze_bias_and_fallacy(client, monkeypatch):

    monkeypatch.setattr(
        routes,
        "extract_claims",
        lambda text: []
    )

    monkeypatch.setattr(
        routes,
        "save_analysis",
        lambda text, claims, results: 124
    )

    response = client.post(
        "/analyze",
        json={
            "text": (
                "Everyone knows this politician is corrupt. "
                "Either you support us or you hate the country."
            )
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["bias_analysis"]["potential_bias_detected"] is True

    assert (
        data["fallacy_analysis"]["potential_fallacies_detected"]
        is True
    )


def test_analyze_gemini_failure(client, monkeypatch):

    monkeypatch.setattr(
        routes,
        "extract_claims",
        lambda text: ["The Earth revolves around the Sun."]
    )

    monkeypatch.setattr(
        routes,
        "search_all_sources",
        lambda claim: []
    )

    def mock_verifier(claim, evidence):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(
        routes,
        "verify_claim",
        mock_verifier
    )

    monkeypatch.setattr(
        routes,
        "save_analysis",
        lambda text, claims, results: 125
    )

    response = client.post(
        "/analyze",
        json={
            "text": "The Earth revolves around the Sun."
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        data["claims"][0]["verdict"]
        == "VERIFICATION UNAVAILABLE"
    )

    assert data["claims"][0]["verification_error"] is True

    assert data["analysis_id"] == 125