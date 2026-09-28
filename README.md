# SupersonicLabs Julia-1 API Server

A self-hosted, **Jev-compatible** HTTP API for [Julia-1](https://huggingface.co/SupersonicLabs/Julia-1). Send text or JSON and typed questions. Get classifications, scores, and yes/no probabilities.

The server implements TypeSafe's [Jev API](https://docs.typesafe.ai/api) (`POST /v1/systemone` and `GET /v1/models`). Code written for Jev, including TypeSafe's SDKs, can switch to this server by changing only the base URL and API key. See [Switching from Jev](#switching-from-jev) for the differences to expect.

Built with Python 3.11+, FastAPI, and Uvicorn. The server loads the model once, runs inference in a worker thread, and keeps model files in a persistent cache.

## Quick run

With Docker installed, pull and start the latest release from GitHub Container Registry:

```bash
docker run -d --name julia --pull=always \
  -p 127.0.0.1:8000:8000 \
  -v hf-cache:/root/.cache/huggingface \
  ghcr.io/ianrodrigues/julia-1-api-server:latest
```

No repository clone, Python installation, or `.env` file is needed. The first start downloads the model weights and tokenizer. The `hf-cache` volume keeps them for future runs.

Follow startup with `docker logs -f julia`. Once the model is loaded, open [http://localhost:8000/playground](http://localhost:8000/playground) to try Julia-1 in your browser, or [http://localhost:8000/docs](http://localhost:8000/docs) for the API reference.

If port 8000 is busy, use `-p 127.0.0.1:18000:8000` and open `http://localhost:18000/docs` instead. Stop the container with `docker stop julia` and start it again with `docker start julia`.

## Run with Docker Compose

Install Docker with Compose, then run:

```bash
git clone https://github.com/ianrodrigues/julia-1-api-server.git
cd julia-1-api-server
cp .env.example .env
docker compose up -d
docker compose logs -f julia
```

The first start downloads about 550.5 MiB of model weights, plus tokenizer files. The server starts accepting requests after the model has loaded.

Open [http://localhost:8000/playground](http://localhost:8000/playground) to try Julia-1, or [http://localhost:8000/docs](http://localhost:8000/docs) to try the API. The root URL redirects to the playground. Check the server with:

```bash
curl --fail http://localhost:8000/health
```

If port 8000 is busy, change `PORT` in `.env`. Use that port in the URLs below.

To stop the server:

```bash
docker compose down
```

Model files stay in the `hf-cache` volume. `docker compose down -v` deletes that cache. After changing the source code, rebuild with `docker compose up -d --build`.

## Playground

The server includes a web playground at `/playground` for people who want to try Julia-1 without writing code. Pick a sample scenario, such as a support ticket, a product to categorize, or a scam message, or write your own text and questions. Julia-1's answers show the chosen option, where the text lands on a scale, or the chance of yes, with bars for every probability and a plain-language certainty label. **Show the API request** gives the matching `curl` command.

The playground calls the same `/v1/systemone` endpoint as any other client, so it uses the same rate limit and API keys. When `API_KEYS` is set, it asks visitors for a key and remembers it in their browser.

The Docker image builds the playground. To add [Umami](https://umami.is) analytics, set the `UMAMI_WEBSITE_ID` build argument, or put it in `.env` for Compose, and rebuild:

```bash
UMAMI_WEBSITE_ID=<website-id> docker compose build
```

The ID is baked into the page at build time. Without it, the playground loads no analytics. Published images are built without one.

To work on it locally, install [Bun](https://bun.sh) and run:

```bash
make playground-dev
```

This serves the playground with hot reload at `http://localhost:3000/playground` and forwards API calls to `https://julia-1.rdgs.net`. Set `JULIA_API_URL=http://localhost:8000` to use a local server instead. `make playground` builds the static files into `playground/dist`, which `make run-dev` then serves.

## Send a request

The request and response formats are the same as Jev's:

```bash
curl --fail-with-body http://localhost:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "state": "Help! My payouts have been failing for 3 days.",
  "model": "jev-latest",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payments, invoicing, refunds",
        "technical": "Bugs, outages, integrations",
        "sales": "Pricing, upgrades, new accounts"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": ["Calm", "Frustrated", "Very angry"]
    },
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this convey urgency?"
    }
  }
}
JSON
```

If you set `API_KEYS`, add `-H 'Authorization: Bearer <key>'`. The response has one answer per question, under the same names. The numbers below are illustrative:

```json
{
  "model": "SupersonicLabs/Julia-1",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "technical",
      "probabilities": {"billing": 0.03, "technical": 0.96, "sales": 0.01},
      "confidence": 0.94
    },
    "frustration": {
      "type": "score",
      "score": 1.05,
      "legend": {"0": "Calm", "1": "Frustrated", "2": "Very angry"},
      "probabilities": {"0": 0.0, "1": 0.95, "2": 0.05},
      "confidence": 0.92
    },
    "is_urgent": {"type": "noul", "noul": 0.95}
  },
  "usage": {"input_tokens": 296, "output_tokens": 0}
}
```

`state` can be a string, a JSON object, or an array. Instructions and criteria can also be objects or arrays, and the model sees them as JSON text. The `model` field is optional. Any value is accepted, and the response always reports this server's model. Inference time, excluding queue time, is in the `Server-Timing` response header.

### With the TypeSafe SDK

Point TypeSafe's SDK at this server:

```python
from typesafe_sdk import Choice, TypeSafeClient

client = TypeSafeClient(api_key="<key>", base_url="http://localhost:8000")
response = client.system_one(
    state="Help! My payouts have been failing for 3 days.",
    questions={
        "department": Choice(
            instructions="Which team should handle this?",
            criteria={"billing": "Payments", "technical": "Bugs and outages"},
        )
    },
)
print(response.answers["department"].choice)
```

The SDK requires an API key even when the server has no `API_KEYS`. Any value works in that case.

### Question types

| Type | Criteria | Answer |
| --- | --- | --- |
| `choice` | An object mapping 2–20 option IDs to descriptions; `null` uses the ID as the description | `choice`, `probabilities`, `confidence` |
| `score` | An ordered list of 2–20 level descriptions | `score` (the expected level, can be fractional), `legend`, `probabilities`, `confidence` |
| `noul` | Optional `true` and `false` descriptions | `noul`: the probability of yes, from 0 to 1 |

`confidence` goes from 0 (probability spread evenly) to 1 (all probability on one option). It is calculated as `(n × highest probability − 1) / (n − 1)` for `n` options, the formula Jev's documentation uses to explain its confidence. Jev may compute it differently.

### Switching from Jev

Requests and responses have the same shape, but this server runs a different model on your own hardware:

- **Different answers.** Julia-1 is not Jev. Its probabilities and confidence differ, so re-check any thresholds you tuned on Jev.
- **Smaller limits.** Choice questions allow 20 options, not 255. Requests allow at most 32 questions. The whole input must fit `MAX_LENGTH`, at most 8,192 tokens, where Jev allows 64k. Each description must fit 48 tokens. Requests over these limits get HTTP 422.
- **Token usage.** `input_tokens` counts the tokens the model processed. Each question encodes the state separately, so the count grows with the number of questions. `output_tokens` is always 0.
- **Model name.** `model` in responses and `GET /v1/models` is `MODEL_ID`, such as `SupersonicLabs/Julia-1`, not a Jev version.

## API reference

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/systemone` | Answer typed questions about a state |
| `GET /v1/models` | List the served model |
| `GET /health` | Report whether the model is loaded |
| `GET /v1/info` | Show model parameters, versions, device, and runtime settings |
| `GET /docs` | Open the interactive API docs, including a sample request |
| `GET /openapi.json` | Get the OpenAPI schema |
| `GET /playground` | Open the web playground |
| `GET /` | Redirect to `/playground`, or to `/docs` when the playground isn't built |

When `API_KEYS` is set, the `/v1` endpoints require `Authorization: Bearer <key>`. `/health` and the docs stay open.

A healthy server returns HTTP 200 with:

```json
{"status": "ok", "model_loaded": true, "device": "cpu"}
```

### Input limits

- 1–32 questions per request.
- 2–20 criteria for each choice or score question.
- At most 131,072 characters for string state, 128 for IDs, and 8,192 for each instruction or description string.
- Text must not be blank, and objects and arrays must not be empty. Unknown fields inside questions are rejected; unknown top-level fields are ignored.
- The full encoded input must fit `MAX_LENGTH`. Questions and criteria must also fit `HEAD_LENGTH`.
- Each criterion description must fit the model's 48-token limit.

Character limits and token limits are separate. The server rejects text that would need truncation or contains reserved model markers.

### Errors

Status codes match Jev's, so its SDKs handle them the same way:

| Status | Meaning |
| --- | --- |
| `401` | Missing or invalid API key |
| `422` | Invalid input or exceeded token limit; see `detail` in the response |
| `429` | Rate limit exceeded; includes `Retry-After` in seconds |
| `529` | Inference queue full; includes `Retry-After: 1` |
| `503` | Model not loaded yet |
| `500` | Inference failed; check the server logs |

TypeSafe's SDKs retry `429` and `529` with backoff by default. If the model cannot load, startup fails. The server does not accept requests until loading succeeds.

## Configuration

Edit `.env` before starting the server. Environment variables take priority over `.env` when running Python directly.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODEL_ID` | `SupersonicLabs/Julia-1` | Hugging Face model repository |
| `MODEL_REVISION` | `a85b127321d580d65176c89ced8273f305745d85` | Checkpoint version |
| `DEVICE` | `cpu` | `cpu`, `cuda`, or `cuda:N` |
| `MAX_LENGTH` | `8192` | Maximum combined input length in tokens |
| `HEAD_LENGTH` | `512` | Token budget for questions and criteria |
| `CPU_THREADS` | `4` | Sets `JULIA_CPU_THREADS` before loading Julia |
| `HOST` | `0.0.0.0` | Bind address; keep this value inside Docker |
| `PORT` | `8000` | HTTP port |
| `MAX_PENDING_REQUESTS` | `16` | Maximum running and queued requests combined |
| `RATE_LIMIT_PER_MINUTE` | `60` | Requests per minute for each client; `0` disables rate limiting |
| `RATE_LIMIT_BURST` | `10` | Requests a client can send at once before the per-minute rate applies |
| `CLIENT_IP_HEADER` | empty | Header with the real client IP when behind a proxy, such as `CF-Connecting-IP` |
| `API_KEYS` | empty | Comma-separated bearer tokens for the `/v1` endpoints; empty leaves them open |

`HEAD_LENGTH + 4` must be smaller than `MAX_LENGTH`. Invalid settings stop startup.

Compose stores model files at `/root/.cache/huggingface`. Local Python uses `~/.cache/huggingface` by default. Standard Hugging Face settings such as `HF_HOME`, `HF_TOKEN`, and `HF_HUB_OFFLINE=1` are supported. Offline mode requires an existing cache.

A different `MODEL_ID` must have a compatible Julia checkpoint and a valid `MODEL_REVISION`. To update the runtime, change `JULIA_REVISION` in `app/config.py`, update the model revision in `.env.example` and `.env`, rebuild, and run the integration test. The runtime is installed during the build; it is not imported from downloaded checkpoint files.

## Local development

Create a Python 3.11+ virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m scripts.install_runtime
cp .env.example .env
make run-dev
```

On macOS, install `torch==2.14.0` from the default PyPI index instead. Use `DEVICE=cpu`.

The installer gets Julia's Python runtime from the pinned model repository. Do not install the unrelated PyPI package named `julia`.

`make run-dev` uses the host and port from your settings. Restart it after editing the source.

| Command | Purpose |
| --- | --- |
| `make test` | Run API and service tests without model downloads |
| `make lint` | Check Python style and formatting |
| `make test-integration` | Load the real model and test inference |
| `make playground` | Build the web playground (requires Bun) |
| `make playground-dev` | Run the playground with hot reload |
| `make docker-build` | Build the Docker image |
| `make docker-up` | Start the Compose service |
| `make docker-down` | Stop the Compose service |

For API-only work, install just `requirements-dev.txt`. CI runs the fast tests on Python 3.11–3.13 and builds the CPU image. The integration test requires the full dependencies, runtime, and model files.

## Published images and releases

GitHub releases publish CPU images to `ghcr.io/ianrodrigues/julia-1-api-server` for `linux/amd64` and `linux/arm64`.

The [quick run](#quick-run) command uses `latest`. To use a specific release, replace `:latest` with its version tag, such as `:0.1.0`.

Release `v0.1.0` publishes tags `0.1.0`, `0.1`, and `latest`. Prereleases publish only the full version tag. Each image includes source and version labels, build provenance, and a software bill of materials (SBOM).

To release a new version:

1. Update `app/__init__.py` and [CHANGELOG.md](CHANGELOG.md).
2. Commit the changes and create a matching tag, such as `v0.1.0`.
3. Push the commit and tag, then publish a GitHub release for that tag.
4. Wait for the **Release container** workflow to finish.

The workflow checks the version, runs CI, and publishes only if those checks pass. A tag push alone does not publish an image. It uses the built-in `GITHUB_TOKEN`; no Docker Hub credentials are needed.

After the first publish, set the GHCR package to public to allow anonymous pulls. The workflow summary lists the image tags and digest. Deploy by digest if you need an immutable image reference.

Actions are pinned to commit hashes. Dependabot checks for updates each month.

## Deployment

Use one Uvicorn worker per container. Each process loads its own model. The model has about 144.3 million parameters. Allow extra memory for Python, tokenization, caches, and inference; long inputs need more memory.

The server runs one inference request at a time on a separate thread. Each question uses a batch size of one. Extra requests wait in the bounded queue. A cancelled HTTP request keeps its slot until inference finishes. On shutdown, the server stops accepting work and waits for accepted requests to finish.

Set `API_KEYS` before exposing the server beyond your machine. Generate a key with `openssl rand -hex 32`, and list several keys, separated by commas, to give each client its own. Keys travel in a header, so serve the API over TLS; a Cloudflare Tunnel provides it. Use a reverse proxy for request-size limits.

### Rate limiting

Each client gets `RATE_LIMIT_BURST` requests at once, then refills at `RATE_LIMIT_PER_MINUTE`. Requests over the limit get HTTP 429 before reaching the model or checking the API key. Only `/v1` endpoints count; `/health`, the playground's files, and the docs are exempt. Limits are kept in memory per process and reset on restart.

By default, clients are identified by their connection address. Behind a proxy, every request comes from the proxy, so all clients share one limit. Set `CLIENT_IP_HEADER` to the header your proxy uses for the real client IP. For a Cloudflare Tunnel, use:

```bash
CLIENT_IP_HEADER=CF-Connecting-IP
```

Set this only when every request passes through that proxy. Clients that can reach the server directly can send any value in the header and bypass the limit. Compose binds to localhost, so with a tunnel only `cloudflared` and local processes can connect.

For stronger protection, also add a rate-limiting rule in Cloudflare. It blocks floods before they reach your machine. Compose binds to localhost and gives the model ten minutes to start before health checks count failures. Increase that period if the first download is slow.

The container runs as root to use `/root/.cache/huggingface`. Compose drops Linux capabilities and blocks privilege escalation. A non-root setup needs a writable cache directory and volume.

### NVIDIA GPUs

Build with a CUDA PyTorch wheel that supports your driver:

```bash
docker build -f docker/Dockerfile \
  --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 \
  -t julia-1-api-server:cuda .
docker run --rm --gpus all -p 127.0.0.1:8000:8000 \
  -e DEVICE=cuda \
  -v julia_gpu_cache:/root/.cache/huggingface \
  julia-1-api-server:cuda
```

This requires NVIDIA Container Toolkit and a BF16-capable GPU. Setting `DEVICE=cuda` in the CPU image is not enough. GPU inference is not tested in CI.

## Credits and license

[Supersonic Labs](https://huggingface.co/SupersonicLabs/Julia-1) created Julia-1 and its Python runtime. [Hugging Face](https://huggingface.co) hosts the model and provides the Hub and Transformers libraries.

Copyright © 2026 Ian Rodrigues. This wrapper is [MIT licensed](LICENSE). Julia and other dependencies keep their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details. The Docker image includes these notices and the Apache-2.0 license text at `/usr/share/doc/julia-1-api-server`.

This project is independent and is not affiliated with Supersonic Labs or Hugging Face.

## Contributing

Keep changes focused. Add tests when behavior changes and update the docs when the API changes. Run `make test lint` before opening a pull request. Run `make test-integration` for model runtime or dependency changes.

Do not commit model weights, credentials, or `.env` files.
