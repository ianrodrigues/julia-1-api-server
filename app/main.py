"""FastAPI lifecycle, endpoints, and an environment-aware Uvicorn entrypoint."""

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import JULIA_RELEASE_DATE, Settings
from app.ratelimit import RateLimiter, retry_after_header
from app.schemas import HealthResponse, ListModelsResponse, SystemOneRequest, SystemOneResponse
from app.service import (
    InferenceBusyError,
    InferenceService,
    InvalidInputError,
    ModelUnavailableError,
)

logger = logging.getLogger(__name__)

# Built by `make playground`; the API still serves without it.
PLAYGROUND_DIR = Path(__file__).resolve().parent.parent / "playground" / "dist"

# Jev's status for a temporarily overloaded service; its SDKs retry it with backoff.
OVERLOADED = 529


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a separate lifecycle for each process; serve with one Uvicorn worker."""
    settings = settings or Settings()
    api_keys = [key.encode() for key in settings.api_key_list]

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
        title="SupersonicLabs Julia-1 API Server",
        description=(
            "A Jev-compatible System One API for Julia-1: classify inputs, "
            "score them against a rubric, and evaluate yes/no questions."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    if settings.rate_limit_per_minute:
        limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_burst)

        @application.middleware("http")
        async def rate_limit(request: Request, call_next):
            # Only API calls reach the model; pages, assets, and health checks stay unthrottled.
            if not request.url.path.startswith("/v1/"):
                return await call_next(request)
            wait = limiter.acquire(client_key(request, settings.client_ip_header))
            if wait:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests; retry later"},
                    headers={"Retry-After": retry_after_header(wait)},
                )
            return await call_next(request)

    def authenticate(request: Request) -> None:
        if not api_keys:
            return
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        # Compare against every key so timing does not reveal which one nearly matched.
        matches = [hmac.compare_digest(token.strip().encode(), key) for key in api_keys]
        if scheme.lower() != "bearer" or not any(matches):
            raise HTTPException(
                401, "Missing or invalid API key", headers={"WWW-Authenticate": "Bearer"}
            )

    playground = PLAYGROUND_DIR.is_dir()
    if playground:
        application.mount(
            "/playground", StaticFiles(directory=PLAYGROUND_DIR, html=True), name="playground"
        )

    @application.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/playground/" if playground else "/docs")

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

    @application.get("/v1/info", dependencies=[Depends(authenticate)])
    async def info(request: Request):
        service = getattr(request.app.state, "service", None)
        if service is None or not service.loaded:
            raise HTTPException(503, "Model is not ready")
        return service.info()

    @application.get(
        "/v1/models", response_model=ListModelsResponse, dependencies=[Depends(authenticate)]
    )
    async def models():
        return {
            "models": [
                {
                    "name": settings.model_id,
                    "description": "Supersonic Labs' Julia-1 decision model, served locally.",
                    "release_date": JULIA_RELEASE_DATE,
                }
            ]
        }

    @application.post(
        "/v1/systemone",
        response_model=SystemOneResponse,
        dependencies=[Depends(authenticate)],
        responses={
            401: {"description": "Missing or invalid API key"},
            422: {"description": "Invalid question or token budget"},
            429: {"description": "Rate limit exceeded"},
            OVERLOADED: {"description": "Inference queue is full"},
            503: {"description": "Model unavailable"},
            500: {"description": "Inference failed"},
        },
    )
    async def system_one(payload: SystemOneRequest, request: Request):
        service = getattr(request.app.state, "service", None)
        if service is None:
            raise HTTPException(503, "Model is not ready")
        try:
            result = await service.predict(payload)
        except ModelUnavailableError as error:
            raise HTTPException(503, "Model is not ready") from error
        except InferenceBusyError as error:
            raise HTTPException(
                OVERLOADED, "Inference queue is full; retry later", headers={"Retry-After": "1"}
            ) from error
        except InvalidInputError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            logger.exception("Inference failed")
            raise HTTPException(500, "Inference failed") from error
        elapsed = result.pop("execution_time_ms")
        return JSONResponse(
            content=SystemOneResponse.model_validate(result).model_dump(mode="json"),
            headers={"Server-Timing": f"inference;dur={elapsed}"},
        )

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
