"""HTTP contract, validation boundaries, lifecycle and error semantics."""

import json
import math
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
        assert client.post("/v1/systemone", json=payload).status_code == 200
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


def test_responses_match_jev_answer_shapes(client, payload):
    payload["questions"]["urgency"] = {
        "type": "score",
        "instructions": "How urgent?",
        "criteria": ["Low", {"level": "High", "examples": ["outage"]}],
    }
    payload["questions"]["refund"] = {"type": "noul", "instructions": "Is a refund needed?"}
    response = client.post("/v1/systemone", json=payload)
    assert response.status_code == 200
    assert response.headers["Server-Timing"].startswith("inference;dur=")
    body = response.json()
    assert body["model"] == "SupersonicLabs/Julia-1"
    assert body["usage"] == {"input_tokens": 300, "output_tokens": 0}
    third = pytest.approx(1 / 3)
    assert body["answers"] == {
        "team": {
            "type": "choice",
            "choice": "billing",
            "probabilities": {"billing": pytest.approx(2 / 3), "shipping": third},
            "confidence": third,
        },
        "urgency": {
            "type": "score",
            "score": third,
            "legend": {"0": "Low", "1": {"level": "High", "examples": ["outage"]}},
            "probabilities": {"0": pytest.approx(2 / 3), "1": third},
            "confidence": third,
        },
        "refund": {"type": "noul", "noul": third},
    }


def test_confidence_spans_zero_to_one(client, fake_runtime, payload):
    fake_runtime.engine.predict.side_effect = lambda state, questions: {
        "answers": {
            "certain": {"type": "choice", "choice": "a", "probabilities": {"a": 1.0, "b": 0.0}},
            "even": {"type": "choice", "choice": "a", "probabilities": {"a": 0.5, "b": 0.5}},
        }
    }
    question = payload["questions"]["team"]
    payload["questions"] = {"certain": question, "even": question}
    answers = client.post("/v1/systemone", json=payload).json()["answers"]
    assert answers["certain"]["confidence"] == 1
    assert answers["even"]["confidence"] == 0


def test_structured_content_is_rendered_as_json_text(client, fake_runtime):
    state = {"ticket": {"subject": "Payouts failing", "days": 3}}
    instructions = {"question": "Is `vip` affected?", "vip": ["Acme Café"]}
    payload = {
        "state": state,
        "questions": {
            "team": {
                "type": "choice",
                "instructions": instructions,
                "criteria": {"billing": None, "technical": {"covers": ["bugs", "outages"]}},
            },
            "vip": {"type": "noul", "instructions": "VIP?", "criteria": {"true": "A VIP"}},
        },
    }
    assert client.post("/v1/systemone", json=payload).status_code == 200
    kwargs = fake_runtime.engine.predict.call_args.kwargs
    # Structured state goes to the runtime unchanged; it renders state itself.
    assert kwargs["state"] == state
    team, vip = kwargs["questions"]["team"], kwargs["questions"]["vip"]
    assert team["instructions"] == json.dumps(instructions, ensure_ascii=False)
    assert team["criteria"] == {
        "billing": "billing",
        "technical": '{"covers": ["bugs", "outages"]}',
    }
    assert vip["criteria"] == {"false": "false", "true": "A VIP"}
    rows = fake_runtime.engine.encoding_info.call_args.args[0]
    assert rows[0]["options"] == ["billing", '{"covers": ["bugs", "outages"]}']
    assert rows[1]["options"] == ["false", "A VIP"]


def test_model_is_optional_and_unknown_top_level_fields_are_ignored(client, payload):
    del payload["model"]
    payload["future_option"] = True
    assert client.post("/v1/systemone", json=payload).status_code == 200


def test_classify_endpoint_is_gone(client, payload):
    assert client.post("/v1/classify", json=payload).status_code == 404


def test_models_list(client):
    assert client.get("/v1/models").json() == {
        "models": [
            {
                "name": "SupersonicLabs/Julia-1",
                "description": "Supersonic Labs' Julia-1 decision model, served locally.",
                "release_date": "2026-09-23",
            }
        ]
    }


@pytest.mark.parametrize("kind", ["choice", "score"])
@pytest.mark.parametrize("count,expected", [(0, 422), (1, 422), (2, 200), (20, 200), (21, 422)])
def test_criteria_boundaries(client, fake_runtime, payload, kind, count, expected):
    criteria = [f"Option {i}" for i in range(count)]
    if kind == "choice":
        criteria = {str(i): item for i, item in enumerate(criteria)}
    payload["questions"]["team"].update(type=kind, criteria=criteria)
    response = client.post("/v1/systemone", json=payload)
    assert response.status_code == expected
    if expected == 422:
        assert "criteria" in str(response.json()["detail"])
        fake_runtime.engine.predict.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        {"type": "noul", "instructions": "Valid?", "criteria": {"maybe": "Unsure"}},
        {"type": "noul", "instructions": "Valid?", "criteria": ["No", "Yes"]},
        {"type": "noul", "instructions": "Valid?", "criteria": {"false": "", "true": "Yes"}},
        {"type": "score", "instructions": "Rank?", "criteria": {"a": "Low", "b": "High"}},
        {"type": "choice", "instructions": "Team?", "criteria": ["One", "Two"]},
        {"type": "choice", "instructions": "Team?", "criteria": {" ": "One", "b": "Two"}},
        {"type": "choice", "instructions": "Team?", "criteria": {"a": 1, "b": "Two"}},
        {"type": "unknown", "instructions": "Valid?"},
        {"type": "noul", "instructions": " "},
        {"type": "noul", "instructions": {}},
        {"type": "noul"},
        {"type": "noul", "instructions": "Valid?", "unexpected": True},
    ],
)
def test_invalid_questions_never_reach_engine(client, fake_runtime, payload, question):
    payload["questions"] = {"q": question}
    assert client.post("/v1/systemone", json=payload).status_code == 422
    fake_runtime.engine.predict.assert_not_called()


@pytest.mark.parametrize(
    "update",
    [
        {"state": ""},
        {"state": " "},
        {"state": {}},
        {"state": []},
        {"state": 42},
        {"state": "x" * 131073},
        {"questions": {}},
        {"questions": {str(i): {"type": "noul", "instructions": "Yes?"} for i in range(33)}},
    ],
)
def test_invalid_request(client, payload, update):
    payload.update(update)
    assert client.post("/v1/systemone", json=payload).status_code == 422


def test_encoding_errors_are_422_but_model_errors_are_500(client, fake_runtime, payload):
    fake_runtime.engine.encoding_info.side_effect = ValueError(
        "Option exceeds 48-token model contract"
    )
    response = client.post("/v1/systemone", json=payload)
    assert response.status_code == 422
    assert "48-token" in response.json()["detail"]
    fake_runtime.engine.predict.assert_not_called()
    fake_runtime.engine.encoding_info.side_effect = lambda rows: [{"tokens": 1} for _ in rows]
    fake_runtime.engine.predict.side_effect = ValueError("private internal failure")
    response = client.post("/v1/systemone", json=payload)
    assert response.status_code == 500
    assert response.json() == {"detail": "Inference failed"}


def test_not_ready_is_503(payload):
    # Without a lifespan, no model is resident and readiness must not lie.
    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.get("/health").status_code == 503
    assert client.get("/v1/info").status_code == 503
    assert client.post("/v1/systemone", json=payload).status_code == 503


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
        return fake_runtime.predict(**kwargs)

    fake_runtime.engine.predict.side_effect = blocking_predict
    with TestClient(create_app(Settings(_env_file=None, max_pending_requests=1))) as client:
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(client.post, "/v1/systemone", json=payload)
            try:
                assert started.wait(5)
                assert client.get("/health").status_code == 200
                response = client.post("/v1/systemone", json=payload)
                # Jev's overloaded status, which its SDKs retry with backoff.
                assert response.status_code == 529
                assert response.headers["Retry-After"] == "1"
            finally:
                release.set()
            assert first.result(timeout=5).status_code == 200


def keyed_client(fake_runtime):
    return TestClient(create_app(Settings(_env_file=None, api_keys="first-key, second-key")))


@pytest.mark.parametrize(
    "authorization", [None, "Bearer wrong", "first-key", "Basic first-key", "Bearer "]
)
def test_api_keys_reject_bad_credentials(fake_runtime, payload, authorization):
    headers = {"Authorization": authorization} if authorization else {}
    with keyed_client(fake_runtime) as client:
        for request in (
            lambda: client.post("/v1/systemone", json=payload, headers=headers),
            lambda: client.get("/v1/models", headers=headers),
            lambda: client.get("/v1/info", headers=headers),
        ):
            response = request()
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"
        fake_runtime.engine.predict.assert_not_called()


def test_api_keys_accept_any_configured_key_and_leave_health_open(fake_runtime, payload):
    with keyed_client(fake_runtime) as client:
        for key in ("first-key", "second-key"):
            headers = {"Authorization": f"Bearer {key}"}
            assert client.post("/v1/systemone", json=payload, headers=headers).status_code == 200
        assert client.get("/health").status_code == 200


def test_probabilities_sum_to_one(client, payload):
    payload["questions"]["levels"] = {
        "type": "score",
        "instructions": "Level?",
        "criteria": ["A", "B", "C"],
    }
    for answer in client.post("/v1/systemone", json=payload).json()["answers"].values():
        assert math.isclose(sum(answer["probabilities"].values()), 1)
