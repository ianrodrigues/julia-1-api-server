# Changelog

## Unreleased

- **Breaking:** the API is now Jev-compatible. `POST /v1/systemone` replaces `POST /v1/classify` and uses TypeSafe's Jev request and response format, so Jev clients and SDKs work by changing the base URL.
- Answers use Jev's fields: `confidence` replaces `max_probability`, score answers include `legend`, noul answers carry only `noul`, and responses include `model` and `usage`. Inference time moved to the `Server-Timing` header.
- `state`, instructions, and criteria accept JSON objects and arrays; `null` choice descriptions and partial noul criteria are accepted.
- `GET /v1/models` lists the served model.
- Optional bearer-token authentication with `API_KEYS`.
- A full inference queue returns `529`, as Jev does, instead of `503`.
- Per-client rate limiting with HTTP 429 and `Retry-After`, configured by `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_BURST`.
- `CLIENT_IP_HEADER` identifies clients behind a proxy, such as `CF-Connecting-IP` for Cloudflare Tunnel.

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
