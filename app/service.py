"""Resident model ownership and bounded, cancellation-safe threaded inference."""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

from app.config import JULIA_REVISION, Settings
from app.schemas import (
    ChoiceQuestion,
    NoulQuestion,
    Question,
    ScoreQuestion,
    SystemOneRequest,
    render,
)

logger = logging.getLogger(__name__)


class ModelUnavailableError(Exception):
    """The model has not loaded, or shutdown has started."""


class InferenceBusyError(Exception):
    """The bounded inference queue is full."""


class InvalidInputError(Exception):
    """A structurally valid request violates the model's token contract."""


class InferenceService:
    """Own one engine per process and serialize access on a dedicated worker.

    Admission happens on the event loop. A disconnected/cancelled request keeps
    its queue slot until the worker actually finishes; Python cannot interrupt
    an in-flight PyTorch computation safely.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._engine: Any = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="julia")
        self._pending = 0
        self._closing = False
        self._info: dict[str, Any] = {}

    @property
    def loaded(self) -> bool:
        return self._engine is not None and not self._closing

    def load(self) -> None:
        """Download into the standard HF cache and load exactly once at startup.

        Julia accepts a local directory, not a Hub model ID. Runtime Python code
        is installed at build time from a pinned upstream commit; downloaded
        checkpoint code is never imported from the snapshot.
        """
        if self._engine is not None:
            return
        os.environ["JULIA_CPU_THREADS"] = str(self.settings.cpu_threads)

        # Lazy imports keep PyTorch initialization after the CPU thread setting
        # and let API-only tests run without downloading the ML stack or weights.
        from huggingface_hub import snapshot_download
        from julia import load_model

        logger.info(
            "Loading model %s at %s on %s",
            self.settings.model_id,
            self.settings.model_revision,
            self.settings.device,
        )
        checkpoint = snapshot_download(
            repo_id=self.settings.model_id,
            revision=self.settings.model_revision,
            allow_patterns=["*.json", "*.safetensors", "encoder/*", "tokenizer/*"],
        )
        engine = load_model(
            checkpoint,
            device=self.settings.device,
            max_length=self.settings.max_length,
            head_length=self.settings.head_length,
            strict_encoding=True,
            backend="torch",
            batch_size=1,
        )
        self._info = {
            "model_id": self.settings.model_id,
            "model_revision": self.settings.model_revision,
            "parameters": sum(parameter.numel() for parameter in engine.model.parameters()),
            "device": str(engine.device),
            "max_length": engine.max_length,
            "head_length": engine.head_length,
            "cpu_threads": self.settings.cpu_threads,
            "strict_encoding": engine.strict_encoding,
            "backend": engine.transformer_backend,
            "batch_size": engine.batch_size,
            "marker_only_head": engine.model.marker_only_head,
            "memory_map": True,
            "max_pending_requests": self.settings.max_pending_requests,
            "max_questions": 32,
            "criteria_limits": {"min": 2, "max": 20, "max_option_tokens": 48},
            "runtime_revision": JULIA_REVISION,
        }
        self._engine = engine
        logger.info("Model ready: %s parameters", self._info["parameters"])

    def info(self) -> dict[str, Any]:
        """Return observed model settings, without exposing cache paths or secrets."""
        return {**self._info, "model_loaded": self.loaded}

    async def predict(self, request: SystemOneRequest) -> dict[str, Any]:
        """Admit a request without blocking the event loop or growing an unbounded queue."""
        if not self.loaded:
            raise ModelUnavailableError
        if self._pending >= self.settings.max_pending_requests:
            raise InferenceBusyError
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._executor, self._predict, request)
        self._pending += 1
        future.add_done_callback(self._finished)
        return await asyncio.shield(future)

    def _finished(self, future: asyncio.Future) -> None:
        self._pending -= 1
        # Retrieve errors even when the HTTP caller has gone away.
        if not future.cancelled():
            future.exception()

    def _predict(self, request: SystemOneRequest) -> dict[str, Any]:
        started = perf_counter()
        questions = {
            name: runtime_question(question) for name, question in request.questions.items()
        }
        rows = [
            {
                "state": request.state,
                "question": question["instructions"],
                "type": question["type"],
                "options": options(question),
            }
            for question in questions.values()
        ]
        # Audit encoding separately: only input errors become HTTP 422. A later
        # model/scoring ValueError is a server failure, never blamed on the client.
        try:
            encoded = self._engine.encoding_info(rows)
        except ValueError as error:
            raise InvalidInputError(str(error)) from error
        payload = self._engine.predict(state=request.state, questions=questions)
        answers = {
            name: jev_answer(question, payload["answers"][name])
            for name, question in request.questions.items()
        }
        return {
            "model": self.settings.model_id,
            "answers": answers,
            # Julia scores every question in one pass and generates no tokens.
            "usage": {"input_tokens": sum(row["tokens"] for row in encoded), "output_tokens": 0},
            "execution_time_ms": round((perf_counter() - started) * 1000, 3),
        }

    async def close(self) -> None:
        """Stop admissions and drain work before releasing the resident engine."""
        self._closing = True
        await asyncio.to_thread(self._executor.shutdown, wait=True, cancel_futures=False)
        self._engine = None


def runtime_question(question: Question) -> dict[str, Any]:
    """Render Jev's structured and optional descriptions into the runtime's text-only form."""
    runtime = {"type": question.type, "instructions": render(question.instructions)}
    if isinstance(question, ChoiceQuestion):
        runtime["criteria"] = {
            key: key if value is None else render(value) for key, value in question.criteria.items()
        }
    elif isinstance(question, ScoreQuestion):
        runtime["criteria"] = [render(level) for level in question.criteria]
    elif isinstance(question, NoulQuestion) and question.criteria is not None:
        criteria = question.criteria
        runtime["criteria"] = {
            "false": "false" if criteria.false is None else render(criteria.false),
            "true": "true" if criteria.true is None else render(criteria.true),
        }
    return runtime


def options(question: dict[str, Any]) -> list[str]:
    criteria = question.get("criteria")
    if question["type"] == "noul":
        criteria = criteria or {"false": "false", "true": "true"}
        return [criteria["false"], criteria["true"]]
    return list(criteria.values()) if isinstance(criteria, dict) else criteria


def confidence(probabilities: dict[str, float]) -> float:
    """1 when all mass is on one option, 0 when it is spread evenly, as Jev documents."""
    count = len(probabilities)
    return max(0.0, min(1.0, (count * max(probabilities.values()) - 1) / (count - 1)))


def jev_answer(question: Question, raw: dict[str, Any]) -> dict[str, Any]:
    """Reshape a runtime answer into Jev's answer fields for the same question type."""
    if question.type == "noul":
        return {"type": "noul", "noul": raw["noul"]}
    probabilities = raw["probabilities"]
    if question.type == "choice":
        return {
            "type": "choice",
            "choice": raw["choice"],
            "probabilities": probabilities,
            "confidence": confidence(probabilities),
        }
    return {
        "type": "score",
        "score": raw["score"],
        "legend": {str(level): value for level, value in enumerate(question.criteria)},
        "probabilities": probabilities,
        "confidence": confidence(probabilities),
    }
