# bfl-openai-image-proxy

A small OpenAI-compatible image generation proxy for [Open WebUI](https://github.com/open-webui/open-webui). It exposes an OpenAI-style image generation endpoint, translates requests into [Black Forest Labs FLUX](https://docs.bfl.ml/) API calls, polls BFL until generation is complete, then returns an OpenAI-compatible image response.

## Scope

This proxy is **text-to-image generation only**. It supports the FLUX generation endpoints (`POST /v1/{model}` with a prompt) and the async poll/retrieve flow.

It does **not** support BFL's editing, out-painting, in-painting, erasure, de-blur, virtual try-on, fine-tune management, or FLUX Tools endpoints. Open WebUI's OpenAI image generation engine only performs generation, so this matches its use case exactly.

## What the proxy does

- Exposes `POST /v1/images/generations` (OpenAI-compatible).
- Exposes `GET /v1/models` listing supported FLUX models.
- Exposes `GET /health` for health checks.
- Translates OpenAI-style `size` (e.g. `1024x1024`) into BFL `width`/`height`.
- Submits to BFL `POST {BFL_BASE_URL}/v1/{model}`, polls the returned `polling_url` until `status == "Ready"`, then downloads `result.sample`.
- Downloads the generated image **immediately** when ready — BFL's signed `result.sample` URLs expire after 10 minutes, so the proxy fetches the bytes straight away and never exposes the short-lived URL to the client.
- Returns either `b64_json` (default) or `url` response format.
- Supports friendly model aliases (e.g. `black-forest-labs/FLUX.2-klein-9B`).
- Optional bearer auth for the proxy.
- Privacy-first: no prompts, images, or API keys are logged by default.
- Temporary generated files are cleaned up automatically after a configurable TTL.

## How the proxy handles BFL's 10-minute signed URL expiry

BFL's `result.sample` is a signed URL that is **only valid for 10 minutes** after generation completes (see the [FLUX.2 text-to-image docs](https://docs.bfl.ml/flux_2/flux2_text_to_image)). The proxy is designed around this constraint:

- When polling reports `status == "Ready"`, the proxy **downloads the image bytes immediately** from `result.sample` using the same `x-key` header.
- For `response_format=b64_json` (the default), the bytes are base64-encoded and returned inline in the OpenAI response — no URL is exposed to the client, so the 10-minute expiry is irrelevant.
- For `response_format=url`, the downloaded bytes are saved to the proxy's local `/generated` directory and served from `GET /generated/{filename}` via `PUBLIC_BASE_URL`. The URL returned to the client points at the proxy, not at BFL's expiring signed URL, so the client can fetch it for as long as the proxy keeps the file (controlled by `IMAGE_TTL_SECONDS`, default 1 hour).

This means Open WebUI never sees a BFL signed URL and never has to race the 10-minute window.

## Image sizes

Unlike OpenAI's DALL-E (which only accepts `1024x1024`, `1024x1792`, `1792x1024`), BFL accepts **arbitrary integer dimensions** with a minimum of 64px per side. The proxy parses the OpenAI-style `size` string (e.g. `1024x1024`, `1440x2048`, `800x600`) into `width` and `height` integers and forwards them directly to BFL.

- The `1024x1024` default is just a safe fallback when the client doesn't send a `size`.
- Both `x` and `*` separators are accepted (e.g. `1024*1024`).
- The FLUX.2 family supports outputs up to ~4 megapixels (e.g. `2048x2048`). Older FLUX.1 models have different limits. BFL returns a `422` validation error if you exceed a model's maximum, which the proxy surfaces as an OpenAI-style error.
- In Open WebUI, set `IMAGE_SIZE` to any valid dimensions (e.g. `IMAGE_SIZE=1440x2048`).

## Configure `.env`

Copy the example and fill in your BFL API key:

```bash
cp .env.example .env
# edit .env and set BFL_API_KEY
```

Required:

- `BFL_API_KEY` — your Black Forest Labs API key.

Optional (see `.env.example` for full list and defaults):

- `BFL_BASE_URL` — default `https://api.eu.bfl.ai`. Other options: `https://api.bfl.ai` (global), `https://api.us.bfl.ai`.
- `DEFAULT_MODEL` — default `flux-2-klein-9b-preview`.
- `PROXY_API_KEY` — if set, clients must send `Authorization: Bearer <PROXY_API_KEY>`. If unset, unauthenticated access is allowed (a warning is logged at start-up).
- `PUBLIC_BASE_URL` — base URL used for returned image URLs when `response_format=url`. If unset, inferred from request headers.
- `LOG_PROMPTS` — default `false`. Set to `true` to log prompts.
- `STORE_GENERATED_IMAGES` — default `false`.
- `IMAGE_TTL_SECONDS` — default `3600` (1 hour).
- `MAX_CONCURRENT_REQUESTS` — default `4`.

## Build and run with Docker Compose

The Dockerfile uses the [Chainguard](https://hub.docker.com/r/chainguard/python) hardened `python:3.12` base image — minimal, non-root by default, and patched quickly for CVEs. If you prefer the standard Debian-based image, swap the `FROM` line for `python:3.12-slim` and restore the `groupadd`/`useradd` block.

### Option A: Use the prebuilt image from ghcr.io

A multi-arch image (amd64 + arm64) is published to the GitHub Container Registry on every push to `main` and on every version tag:

```bash
docker pull ghcr.io/beecho01/bfl-openai-image-proxy:latest
```

Tags available:

| Tag | When |
|-----|------|
| `latest` | Latest push to `main` |
| `main` | Latest push to `main` (branch alias) |
| `1.0.0`, `1.0`, `1` | From git tag `v1.0.0` |
| `sha-<short>` | Every push (by commit SHA) |

Use it in your compose file by replacing `build: .` with `image: ghcr.io/beecho01/bfl-openai-image-proxy:latest`.

### Option B: Build from source

```bash
export BFL_API_KEY="your-bfl-api-key"
export PROXY_API_KEY="choose-a-proxy-secret"

docker compose -f docker-compose.example.yml up --build
```

The service listens on `http://localhost:8000`.

## Test with curl

Health check:

```bash
curl http://localhost:8000/health
```

List models:

```bash
curl http://localhost:8000/v1/models
```

Generate an image (b64_json):

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Authorization: Bearer ${PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-2-klein-9b-preview",
    "prompt": "a cinematic photo of a lighthouse on a stormy British coastline",
    "size": "1024x1024",
    "response_format": "b64_json"
  }'
```

Generate an image (URL):

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Authorization: Bearer ${PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-2-klein-9b-preview",
    "prompt": "a cinematic photo of a lighthouse on a stormy British coastline",
    "size": "1024x1024",
    "response_format": "url"
  }'
```

## Configure Open WebUI

Open WebUI talks to this proxy using its OpenAI image generation engine. You can either configure it via the admin settings UI, or via environment variables:

```
ENABLE_IMAGE_GENERATION=true
IMAGE_GENERATION_ENGINE=openai
IMAGES_OPENAI_API_BASE_URL=http://bfl-openai-image-proxy:8000/v1
IMAGES_OPENAI_API_KEY=<PROXY_API_KEY>
IMAGE_GENERATION_MODEL=flux-2-klein-9b-preview
IMAGE_SIZE=1024x1024
```

If Open WebUI runs in the same Docker network as the proxy, use the container name `bfl-openai-image-proxy` as the host. Otherwise, use the host/port where the proxy is reachable.

### Run alongside Open WebUI in a single Docker Compose stack

Drop the following into a `docker-compose.yml` alongside your Open WebUI deployment so both services share a network and Open WebUI can reach the proxy by container name:

```yaml
services:
  bfl-openai-image-proxy:
    build: ./bfl-openai-image-proxy
    # or use a prebuilt image:
    # image: ghcr.io/your-org/bfl-openai-image-proxy:latest
    container_name: bfl-openai-image-proxy
    restart: unless-stopped
    environment:
      BFL_API_KEY: "${BFL_API_KEY}"
      BFL_BASE_URL: "https://api.eu.bfl.ai"
      DEFAULT_MODEL: "flux-2-klein-9b-preview"
      PROXY_API_KEY: "${PROXY_API_KEY}"
      PUBLIC_BASE_URL: "http://bfl-openai-image-proxy:8000"
      REQUEST_TIMEOUT_SECONDS: "180"
      IMAGE_TTL_SECONDS: "3600"
      LOG_PROMPTS: "false"
    # No port mapping needed if only Open WebUI needs to reach it.
    # Expose to the host only if you also want to test from outside the stack:
    # ports:
    #   - "8000:8000"

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: unless-stopped
    ports:
      - "3000:8080"
    environment:
      ENABLE_IMAGE_GENERATION: "true"
      IMAGE_GENERATION_ENGINE: "openai"
      IMAGES_OPENAI_API_BASE_URL: "http://bfl-openai-image-proxy:8000/v1"
      IMAGES_OPENAI_API_KEY: "${PROXY_API_KEY}"
      IMAGE_GENERATION_MODEL: "flux-2-klein-9b-preview"
      IMAGE_SIZE: "1024x1024"
    volumes:
      - open-webui-data:/app/backend/data
    depends_on:
      - bfl-openai-image-proxy

volumes:
  open-webui-data:
```

Create a `.env` in the same directory as the compose file:

```env
BFL_API_KEY=your-bfl-api-key
PROXY_API_KEY=choose-a-proxy-secret
```

Then bring up the whole stack:

```bash
docker compose up -d --build
```

Open WebUI will be available at `http://localhost:3000` and will use the proxy for image generation. The proxy is only reachable from within the Docker network (Open WebUI reaches it at `http://bfl-openai-image-proxy:8000`); uncomment the `ports` block on the proxy if you also want to test it directly from the host.

> **Note on `PUBLIC_BASE_URL`:** when `response_format=url` is used, the proxy returns image URLs that Open WebUI's browser must be able to fetch. If Open WebUI and the proxy are in the same Docker network but the user's browser is outside it, set `PUBLIC_BASE_URL` to a URL the browser can reach (e.g. `http://localhost:8000` if you expose the proxy port, or your reverse-proxy host). For `response_format=b64_json` (the default), this is not a concern because the image data is embedded in the response.

## Supported models

- `flux-2-max`
- `flux-2-pro-preview`
- `flux-2-pro`
- `flux-2-flex`
- `flux-2-klein-4b`
- `flux-2-klein-9b-preview`
- `flux-2-klein-9b`
- `flux-kontext-max`
- `flux-kontext-pro`
- `flux-pro-1.1-ultra`
- `flux-pro-1.1`
- `flux-pro`
- `flux-dev`

Friendly aliases are also accepted, e.g. `black-forest-labs/FLUX.2-klein-9B` → `flux-2-klein-9b`.

## Privacy

- Prompts are not logged unless `LOG_PROMPTS=true`.
- Base64 image data is never logged.
- API keys are never logged.
- Temporary generated files are deleted after `IMAGE_TTL_SECONDS` (default 1 hour).

## Running tests

```bash
pip install -r requirements.txt
pytest -q
```