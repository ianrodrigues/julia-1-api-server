# Supersonic's Julia-1 Server

A self-hosted HTTP API for [Julia-1](https://huggingface.co/SupersonicLabs/Julia-1). Send text and questions. Get classifications, scores, and yes/no probabilities.

Built with Python 3.11+, FastAPI, and Uvicorn. The server loads the model once, runs inference in a worker thread, and keeps model files in a persistent cache.

## Quick run

With Docker installed, pull and start the latest release from GitHub Container Registry:

```bash
docker run -d --name julia --pull=always \
  -p 127.0.0.1:8000:8000 \
  -v hf-cache:/root/.cache/huggingface \
  ghcr.io/ianrodrigues/supersonic-julia-server:latest
```

No repository clone, Python installation, or `.env` file is needed. The first start downloads the model weights and tokenizer. The `hf-cache` volume keeps them for future runs.

Follow startup with `docker logs -f julia`. Once the model is loaded, open [http://localhost:8000/docs](http://localhost:8000/docs) to try a sample request.

If port 8000 is busy, use `-p 127.0.0.1:18000:8000` and open `http://localhost:18000/docs` instead. Stop the container with `docker stop julia` and start it again with `docker start julia`.

## Run with Docker Compose

Install Docker with Compose, then run:

```bash
git clone https://github.com/ianrodrigues/supersonic-julia-server.git
cd supersonic-julia-server
cp .env.example .env
docker compose up -d
docker compose logs -f julia
```

The first start downloads about 550.5 MiB of model weights, plus tokenizer files. The server starts accepting requests after the model has loaded.

Open [http://localhost:8000/docs](http://localhost:8000/docs) to try the API. The root URL also redirects there. Check the server with:

```bash
curl --fail http://localhost:8000/health
```

If port 8000 is busy, change `PORT` in `.env`. Use that port in the URLs below.

To stop the server:

```bash
docker compose down
```

Model files stay in the `hf-cache` volume. `docker compose down -v` deletes that cache. After changing the source code, rebuild with `docker compose up -d --build`.

## Send a request

```bash
curl --fail-with-body http://localhost:8000/v1/classify \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "state": "I was charged twice for the same order. Please refund the duplicate charge.",
  "questions": {
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this request?",
      "criteria": {
        "billing": "Billing and payment disputes",
        "shipping": "Shipping and delivery",
        "access": "Account access and login"
      }
    },
    "urgency": {
      "type": "score",
      "instructions": "How urgently should this request be handled?",
      "criteria": ["Routine", "Soon", "Immediate"]
    },
    "refund_needed": {
      "type": "noul",
      "instructions": "Does the customer request a refund?"
    }
  }
}
JSON
```

The response contains Julia's answers and `execution_time_ms`. This example shows the shape of one answer; the numbers are illustrative:

```json
{
  "answers": {
    "team": {
      "type": "choice",
      "choice": "billing",
      "probabilities": {"billing": 0.9, "shipping": 0.06, "access": 0.04},
      "max_probability": 0.9
    }
  },
  "execution_time_ms": 12.4
}
```

Each question has its own answer. Execution time includes input encoding and inference. It does not include queue time or HTTP processing. Latency depends on the input and hardware.

### Question types

| Type | Criteria | Result |
| --- | --- | --- |
| `choice` | An object with 2–20 IDs and descriptions | `choice`: the selected ID |
| `score` | An ordered list of 2–20 descriptions | `score`: the expected zero-based index; it can be fractional |
| `noul` | Optional descriptions for `false` and `true` | `noul`: the probability of true, from 0 to 1 |

All answers include `type` and `probabilities`. Choice and score answers also include `max_probability`. The server preserves your IDs and criterion descriptions.

For `noul`, omitted or `null` criteria use the literal labels `false` and `true`. To supply descriptions, use both keys:

```json
"criteria": {
  "false": "No payment is involved",
  "true": "A payment is involved"
}
```

A `noul` result is a probability, not a JSON boolean. Your application can apply a threshold if it needs a boolean.

## API reference

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Redirect to `/docs` |
| `POST /v1/classify` | Run inference |
| `GET /health` | Report whether the model is loaded |
| `GET /v1/info` | Show model parameters, versions, device, and runtime settings |
| `GET /docs` | Open the interactive API docs, including a sample request |
| `GET /openapi.json` | Get the OpenAPI schema |

A healthy server returns HTTP 200 with:

```json
{"status": "ok", "model_loaded": true, "device": "cpu"}
```

### Input limits

- 1–32 questions per request.
- 2–20 criteria for each choice or score question.
- At most 131,072 characters for state text, 128 for IDs, 8,192 for instructions, and 4,096 for each criterion description.
- Text must not be blank. Unknown fields are rejected.
- The full encoded input must fit `MAX_LENGTH`. Questions and criteria must also fit `HEAD_LENGTH`.
- Each criterion description must fit the model's 48-token limit.

Character limits and token limits are separate. The server rejects text that would need truncation or contains reserved model markers.

### Errors

| Status | Meaning |
| --- | --- |
| `422` | Invalid input or exceeded token limit; see `detail` in the response |
| `503` | Model unavailable or inference queue full; full queues include `Retry-After: 1` |
| `500` | Inference failed; check the server logs |

If the model cannot load, startup fails. The server does not accept requests until loading succeeds.

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
| `make docker-build` | Build the Docker image |
| `make docker-up` | Start the Compose service |
| `make docker-down` | Stop the Compose service |

For API-only work, install just `requirements-dev.txt`. CI runs the fast tests on Python 3.11–3.13 and builds the CPU image. The integration test requires the full dependencies, runtime, and model files.

## Published images and releases

GitHub releases publish CPU images to `ghcr.io/ianrodrigues/supersonic-julia-server` for `linux/amd64` and `linux/arm64`.

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

The API has no built-in authentication. Use a trusted private network or a reverse proxy with TLS, authentication, request-size limits, and rate limits. Compose binds to localhost and gives the model ten minutes to start before health checks count failures. Increase that period if the first download is slow.

The container runs as root to use `/root/.cache/huggingface`. Compose drops Linux capabilities and blocks privilege escalation. A non-root setup needs a writable cache directory and volume.

### NVIDIA GPUs

Build with a CUDA PyTorch wheel that supports your driver:

```bash
docker build -f docker/Dockerfile \
  --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 \
  -t supersonic-julia-server:cuda .
docker run --rm --gpus all -p 127.0.0.1:8000:8000 \
  -e DEVICE=cuda \
  -v julia_gpu_cache:/root/.cache/huggingface \
  supersonic-julia-server:cuda
```

This requires NVIDIA Container Toolkit and a BF16-capable GPU. Setting `DEVICE=cuda` in the CPU image is not enough. GPU inference is not tested in CI.

## Credits and license

[Supersonic Labs](https://huggingface.co/SupersonicLabs/Julia-1) created Julia-1 and its Python runtime. [Hugging Face](https://huggingface.co) hosts the model and provides the Hub and Transformers libraries.

Copyright © 2026 Ian Rodrigues. This wrapper is [MIT licensed](LICENSE). Julia and other dependencies keep their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details. The Docker image includes these notices and the Apache-2.0 license text at `/usr/share/doc/supersonic-julia-server`.

This project is independent and is not affiliated with Supersonic Labs or Hugging Face.

## Contributing

Keep changes focused. Add tests when behavior changes and update the docs when the API changes. Run `make test lint` before opening a pull request. Run `make test-integration` for model runtime or dependency changes.

Do not commit model weights, credentials, or `.env` files.
