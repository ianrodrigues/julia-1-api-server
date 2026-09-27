# syntax=docker/dockerfile:1
# The playground is static files, so build it once on the native platform.
FROM --platform=$BUILDPLATFORM oven/bun:1.4.2 AS playground
WORKDIR /playground
COPY playground/package.json playground/bun.lock ./
RUN bun install --frozen-lockfile
COPY playground ./
RUN bun run typecheck && bun run build

FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY requirements.txt .
# CPU wheels keep NVIDIA libraries out of the default image. Override for CUDA.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install torch==2.14.0 --index-url "${TORCH_INDEX_URL}" \
    && pip install -r requirements.txt
# Runtime installation only needs the pinned revision, so API edits reuse this layer.
COPY app/__init__.py app/config.py ./app/
COPY scripts ./scripts
RUN python -m scripts.install_runtime && pip check

FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/root/.cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HOST=0.0.0.0 \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY app ./app
COPY --from=playground /playground/dist ./playground/dist
COPY LICENSE THIRD_PARTY_NOTICES.md /usr/share/doc/julia-1-api-server/
COPY licenses /usr/share/doc/julia-1-api-server/licenses
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10m --retries=3 \
    CMD curl --fail --silent --show-error "http://127.0.0.1:${PORT}/health" || exit 1
CMD ["python", "-m", "app.main"]
