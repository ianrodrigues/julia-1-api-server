"""Opt-in test against pinned runtime code and actual checkpoint weights."""

import math

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.mark.integration
def test_real_model_all_question_types_and_token_rejection():
    application = create_app(Settings(_env_file=None))
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/info").json()["parameters"] > 140_000_000
        payload = {
            "state": "I was charged twice for the same order.",
            "questions": {
                "team": {
                    "type": "choice",
                    "instructions": "Which team should handle this?",
                    "criteria": {"billing": "Billing and payments", "shipping": "Delivery"},
                },
                "urgency": {
                    "type": "score",
                    "instructions": "How urgent is this?",
                    "criteria": ["Low", "Medium", "High"],
                },
                "refund": {"type": "noul", "instructions": "Is a refund needed?"},
                "payment": {
                    "type": "noul",
                    "instructions": "Is payment involved?",
                    "criteria": {"true": "Payment is involved", "false": "No payment involved"},
                },
            },
        }
        response = client.post("/v1/classify", json=payload)
        assert response.status_code == 200, response.text
        answers = response.json()["answers"]
        assert set(answers) == set(payload["questions"])
        assert answers["team"]["choice"] in {"billing", "shipping"}
        assert 0 <= answers["urgency"]["score"] <= 2
        for name in ("refund", "payment"):
            assert 0 <= answers[name]["noul"] <= 1
            assert set(answers[name]["probabilities"]) == {"false", "true"}
        for answer in answers.values():
            assert math.isclose(sum(answer["probabilities"].values()), 1, abs_tol=1e-6)
        assert response.json()["execution_time_ms"] > 0
        payload["questions"]["team"]["criteria"]["billing"] = "billing " * 100
        response = client.post("/v1/classify", json=payload)
        assert response.status_code == 422
        assert "48-token" in response.json()["detail"]
