# Changelog

## 0.1.0 — 2026-09-27

Initial release of SupersonicLabs Julia-1 API Server.

- Jev-compatible API: `POST /v1/systemone` and `GET /v1/models` follow TypeSafe's Jev request and response format, so Jev clients and SDKs work by changing the base URL.
- Named `choice`, `score`, and `noul` questions over string, object, or array state, with Jev's `confidence`, score `legend`, and `usage` fields.
- Validated criteria and strict context limits, with inference time in the `Server-Timing` header.
- Optional bearer-token authentication with `API_KEYS`.
- Per-client rate limiting with HTTP 429 and `Retry-After`, configured by `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_BURST`; `CLIENT_IP_HEADER` identifies clients behind a proxy such as Cloudflare Tunnel.
- Model preloading, persistent Hugging Face cache, and a pinned Julia-1 runtime.
- Bounded threaded inference with responsive health checks and graceful shutdown; a full queue returns `529`, as Jev does.
- Model/runtime information at `/v1/info`, interactive examples at `/docs`, and a root redirect.
- CPU Docker image, Compose configuration, and optional CUDA build instructions.
- API, concurrency, configuration, and real-model integration tests.
- GitHub CI and release-triggered amd64/arm64 container publishing to `ghcr.io/ianrodrigues/julia-1-api-server`.
- MIT-licensed wrapper with separate upstream licensing and attribution.
