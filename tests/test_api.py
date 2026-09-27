"""HTTP contract, validation boundaries, lifecycle and error semantics."""

import os
import threading

import pytest
from fastapi.testclient import TestClient

from app.config import JULIA_REVISION, Settings
from app.main import create_app


def test_health_info_and_load_once(client, fake_runtime, payload):
    assert client.get("/health").json() == {
        "status": "ok",
        "model_loaded": True,
        "device": "cpu",
    }
    info = client.get("/v1/info").json()
    assert info["parameters"] == 144292870
    assert info["max_length"] == 8192
    assert info["head_length"] == 512
    assert info["strict_encoding"] is True
    assert info["model_revision"] == JULIA_REVISION
    for _ in range(2):
        assert client.post("/v1/classify", json=payload).status_code == 200
    fake_runtime.loader.assert_called_once_with(
        "/cache/snapshots/pinned",
        device="cpu",
        max_length=8192,
        head_length=512,
        strict_encoding=True,
        backend="torch",
        batch_size=1,
    )
    assert "local_dir" not in fake_runtime.download.call_args.kwargs
    assert "cache_dir" not in fake_runtime.download.call_args.kwargs
    assert os.environ["JULIA_CPU_THREADS"] == "4"


def test_payload_and_raw_results_preserved(client, fake_runtime, payload):
    payload["questions"]["score"] = {
        "type": "score",
        "instructions": "How urgent?",
        "criteria": ["Low", "High"],
    }
    payload["questions"]["boolean"] = {"type": "noul", "instructions": "Is it billing?"}
    payload["questions"]["custom"] = {
        "type": "noul",
        "instructions": "Is payment involved?",
        "criteria": {"true": "Payment is involved", "false": "No payment involved"},
    }
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["answers"] == fake_runtime.engine.predict.return_value["answers"]
    assert result["upstream_metadata"] == "preserved"
    assert result["execution_time_ms"] >= 0
    fake_runtime.engine.predict.assert_called_once_with(**payload)
    rows = fake_runtime.engine.encoding_info.call_args.args[0]
    assert rows[2]["options"] == ["false", "true"]
    assert rows[3]["options"] == ["No payment involved", "Payment is involved"]


@pytest.mark.parametrize("kind", ["choice", "score"])
@pytest.mark.parametrize("count,expected", [(0, 422), (1, 422), (2, 200), (20, 200), (21, 422)])
def test_criteria_boundaries(client, fake_runtime, payload, kind, count, expected):
    criteria = [f"Option {i}" for i in range(count)]
    if kind == "choice":
        criteria = {str(i): item for i, item in enumerate(criteria)}
    payload["questions"]["team"].update(type=kind, criteria=criteria)
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == expected
    if expected == 422:
        assert "criteria" in str(response.json()["detail"])
        fake_runtime.engine.predict.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        {"type": "noul", "instructions": "Valid?", "criteria": {}},
        {"type": "noul", "instructions": "Valid?", "criteria": {"true": "Yes"}},
        {"type": "noul", "instructions": "Valid?", "criteria": ["No", "Yes"]},
        {"type": "noul", "instructions": "Valid?", "criteria": {"false": "", "true": "Yes"}},
        {"type": "score", "instructions": "Rank?", "criteria": {"a": "Low", "b": "High"}},
        {"type": "choice", "instructions": "Team?", "criteria": ["One", "Two"]},
        {"type": "choice", "instructions": "Team?", "criteria": {" ": "One", "b": "Two"}},
        {"type": "choice", "instructions": "Team?", "criteria": {"a": 1, "b": "Two"}},
        {"type": "unknown", "instructions": "Valid?"},
        {"type": "noul", "instructions": " "},
        {"type": "noul"},
        {"type": "noul", "instructions": "Valid?", "unexpected": True},
    ],
)
def test_invalid_questions_never_reach_engine(client, fake_runtime, payload, question):
    payload["questions"] = {"q": question}
    assert client.post("/v1/classify", json=payload).status_code == 422
    fake_runtime.engine.predict.assert_not_called()


@pytest.mark.parametrize(
    "update",
    [
        {"state": ""},
        {"state": " "},
        {"state": {}},
        {"state": "x" * 131073},
        {"questions": {}},
        {"unknown": "field"},
        {"questions": {str(i): {"type": "noul", "instructions": "Yes?"} for i in range(33)}},
    ],
)
def test_invalid_request(client, payload, update):
    payload.update(update)
    assert client.post("/v1/classify", json=payload).status_code == 422


def test_encoding_errors_are_422_but_model_errors_are_500(client, fake_runtime, payload):
    fake_runtime.engine.encoding_info.side_effect = ValueError(
        "Option exceeds 48-token model contract"
    )
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == 422
    assert "48-token" in response.json()["detail"]
    fake_runtime.engine.predict.assert_not_called()
    fake_runtime.engine.encoding_info.side_effect = None
    fake_runtime.engine.predict.side_effect = ValueError("private internal failure")
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == 500
    assert response.json() == {"detail": "Inference failed"}


def test_not_ready_is_503(payload):
    # Without a lifespan, no model is resident and readiness must not lie.
    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.get("/health").status_code == 503
    assert client.get("/v1/info").status_code == 503
    assert client.post("/v1/classify", json=payload).status_code == 503


def test_startup_failure_aborts_and_shutdown_releases_model(fake_runtime):
    fake_runtime.loader.side_effect = RuntimeError("cannot load checkpoint")
    application = create_app(Settings(_env_file=None))
    with pytest.raises(RuntimeError, match="cannot load"):
        with TestClient(application):
            pass
    assert not application.state.service.loaded
    fake_runtime.loader.side_effect = None
    with TestClient(application):
        assert application.state.service.loaded
    assert not application.state.service.loaded


def test_health_and_overload_remain_responsive_during_inference(fake_runtime, payload):
    from concurrent.futures import ThreadPoolExecutor

    started, release = threading.Event(), threading.Event()

    def blocking_predict(**kwargs):
        started.set()
        assert release.wait(5)
        return {"answers": {}}

    fake_runtime.engine.predict.side_effect = blocking_predict
    with TestClient(create_app(Settings(_env_file=None, max_pending_requests=1))) as client:
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(client.post, "/v1/classify", json=payload)
            try:
                assert started.wait(5)
                assert client.get("/health").status_code == 200
                response = client.post("/v1/classify", json=payload)
                assert response.status_code == 503
                assert response.headers["Retry-After"] == "1"
            finally:
                release.set()
            assert first.result(timeout=5).status_code == 200
