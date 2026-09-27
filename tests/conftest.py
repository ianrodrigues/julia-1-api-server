"""Replace only the model/download boundary; exercise the real app and executor."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


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
    engine.predict.return_value = {
        "answers": {
            "team": {
                "type": "choice",
                "choice": "billing",
                "probabilities": {"billing": 0.9, "shipping": 0.1},
                "max_probability": 0.9,
            }
        },
        "upstream_metadata": "preserved",
    }
    download = Mock(return_value="/cache/snapshots/pinned")
    loader = Mock(return_value=engine)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    monkeypatch.setitem(sys.modules, "julia", SimpleNamespace(load_model=loader))
    return SimpleNamespace(engine=engine, download=download, loader=loader)


@pytest.fixture
def payload():
    return {
        "state": "I was charged twice.",
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
