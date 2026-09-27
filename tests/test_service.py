"""Cancellation must not release capacity while native model work is still running."""

import asyncio
import threading

import pytest

from app.config import Settings
from app.schemas import SystemOneRequest
from app.service import InferenceBusyError, InferenceService


def test_cancelled_request_keeps_capacity_until_worker_finishes(fake_runtime, payload):
    started, release = threading.Event(), threading.Event()

    def blocking_predict(**kwargs):
        started.set()
        assert release.wait(5)
        return fake_runtime.predict(**kwargs)

    fake_runtime.engine.predict.side_effect = blocking_predict

    async def scenario():
        service = InferenceService(Settings(_env_file=None, max_pending_requests=1))
        service.load()
        request = SystemOneRequest.model_validate(payload)
        try:
            task = asyncio.create_task(service.predict(request))
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(InferenceBusyError):
                await service.predict(request)
            release.set()
            async with asyncio.timeout(5):
                while service._pending:
                    await asyncio.sleep(0.01)
            assert (await service.predict(request))["answers"]["team"]["choice"] == "billing"
        finally:
            release.set()
            await service.close()

    asyncio.run(scenario())
