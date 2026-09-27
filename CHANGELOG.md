# Changelog

## 0.1.0 — 2026-09-27

Initial release of Supersonic's Julia-1 Server.

- FastAPI inference API with named `choice`, `score`, and `noul` questions.
- Validated criteria and strict context limits, with raw model answers and timing.
- Model preloading, persistent Hugging Face cache, and a pinned Julia-1 runtime.
- Bounded threaded inference with responsive health checks and graceful shutdown.
- Model/runtime information at `/v1/info`, interactive examples at `/docs`, and a root redirect.
- CPU Docker image, Compose configuration, and optional CUDA build instructions.
- API, concurrency, configuration, and real-model integration tests.
- GitHub CI and release-triggered amd64/arm64 container publishing to GHCR.
- MIT-licensed wrapper with separate upstream licensing and attribution.
