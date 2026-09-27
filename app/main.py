"""FastAPI lifecycle, endpoints, and an environment-aware Uvicorn entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app import __version__
from app.config import Settings
from app.ratelimit import RateLimiter, retry_after_header
from app.schemas import ClassifyRequest, ClassifyResponse, HealthResponse
from app.service import (
    InferenceBusyError,
    InferenceService,
    InvalidInputError,
    ModelUnavailableError,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a separate lifecycle for each process; serve with one Uvicorn worker."""
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        service = InferenceService(settings)
        application.state.service = service
        try:
            await asyncio.to_thread(service.load)
            yield
        finally:
            await service.close()

    application = FastAPI(
        title="Supersonic's Julia-1 Server",
        description=(
            "Turn text into decisions with Julia-1: classify inputs, "
            "score them against a rubric, and evaluate yes/no questions."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    if settings.rate_limit_per_minute:
        limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_burst)

        @application.middleware("http")
        async def rate_limit(request: Request, call_next):
            # Health checks come from the container runtime and must never be throttled.
            if request.url.path == "/health":
                return await call_next(request)
            wait = limiter.acquire(client_key(request, settings.client_ip_header))
            if wait:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests; retry later"},
                    headers={"Retry-After": retry_after_header(wait)},
                )
            return await call_next(request)

    @application.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @application.get(
        "/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}}
    )
    async def health(request: Request):
        service = getattr(request.app.state, "service", None)
        ready = service is not None and service.loaded
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ok" if ready else "unavailable",
                "model_loaded": ready,
                "device": settings.device,
            },
        )

    @application.get("/v1/info")
    async def info(request: Request):
        service = getattr(request.app.state, "service", None)
        if service is None or not service.loaded:
            raise HTTPException(503, "Model is not ready")
        return service.info()

    @application.post(
        "/v1/classify",
        response_model=ClassifyResponse,
        responses={
            422: {"description": "Invalid question or token budget"},
            429: {"description": "Rate limit exceeded"},
            503: {"description": "Model unavailable or queue full"},
            500: {"description": "Inference failed"},
        },
    )
    async def classify(payload: ClassifyRequest, request: Request):
        service = getattr(request.app.state, "service", None)
        if service is None:
            raise HTTPException(503, "Model is not ready")
        try:
            return await service.predict(payload)
        except ModelUnavailableError as error:
            raise HTTPException(503, "Model is not ready") from error
        except InferenceBusyError as error:
            raise HTTPException(
                503, "Inference queue is full; retry later", headers={"Retry-After": "1"}
            ) from error
        except InvalidInputError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            logger.exception("Inference failed")
            raise HTTPException(500, "Inference failed") from error

    return application


def client_key(request: Request, header: str) -> str:
    """Use a proxy-supplied client IP only when configured; otherwise the peer address."""
    if header and (forwarded := request.headers.get(header, "").strip()):
        return forwarded
    return request.client.host if request.client else "unknown"


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = Settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, workers=1)
