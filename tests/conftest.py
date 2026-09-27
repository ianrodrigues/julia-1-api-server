"""Replace only the model/download boundary; exercise the real app and executor."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def runtime_predict(state, questions):
    """Answer like the pinned runtime: probabilities 0.7, 0.2, 0.1, ... in criteria order."""
    answers = {}
    for name, question in questions.items():
        kind, criteria = question["type"], question.get("criteria")
        keys = (
            ["false", "true"]
            if kind == "noul"
            else [str(i) for i in range(len(criteria))]
            if kind == "score"
            else list(criteria)
        )
        weights = [2**-i for i in range(len(keys))]
        probabilities = {
            key: weight / sum(weights) for key, weight in zip(keys, weights, strict=True)
        }
        answer = {"type": kind, "probabilities": probabilities}
        if kind == "choice":
            answer["choice"] = keys[0]
        elif kind == "score":
            answer["score"] = sum(i * p for i, p in enumerate(probabilities.values()))
        else:
            answer["noul"] = probabilities["true"]
        if kind != "noul":
            answer["max_probability"] = max(probabilities.values())
        answers[name] = answer
    return {"answers": answers}


@pytest.fixture
def fake_runtime(monkeypatch):
    engine = Mock()
    engine.model.parameters.return_value = [SimpleNamespace(numel=lambda: 144292870)]
    engine.model.marker_only_head = True
    engine.device = "cpu"
    engine.max_length = 8192
    engine.head_length = 512
    engine.strict_encoding = True
    engine.transformer_backend = "torch"
    engine.batch_size = 1
    engine.encoding_info.side_effect = lambda rows: [{"tokens": 100} for _ in rows]
    engine.predict.side_effect = runtime_predict
    download = Mock(return_value="/cache/snapshots/pinned")
    loader = Mock(return_value=engine)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    monkeypatch.setitem(sys.modules, "julia", SimpleNamespace(load_model=loader))
    return SimpleNamespace(engine=engine, download=download, loader=loader, predict=runtime_predict)


@pytest.fixture
def payload():
    return {
        "state": "I was charged twice.",
        "model": "jev-latest",
        "questions": {
            "team": {
                "type": "choice",
                "instructions": "Which team should handle this?",
                "criteria": {"billing": "Billing and payments", "shipping": "Delivery"},
            },
        },
    }


@pytest.fixture
def client(fake_runtime):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        yield client
