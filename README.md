<!-- PROJECT LOGO -->
<br />
<div align="center">
  <!-- <a href="https://github.com/beecho01/bfl-openai-image-proxy">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a> -->

<h3 align="center">Black Forest Labs FLUX to OpenAI Image Generation & Editing API Proxy</h3>

  <p align="center">
    An OpenAI-compatible image generation and editing proxy for Open WebUI. It exposes OpenAI-style endpoints, translates requests into Black Forest Labs FLUX API calls, polls BFL until generation is complete, then returns an OpenAI-compatible image response.
    <br />
    <a href="https://github.com/beecho01/bfl-openai-image-proxy"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/beecho01/bfl-openai-image-proxy/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/beecho01/bfl-openai-image-proxy/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- BADGES -->
<p align="center">
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/actions/workflows/ci.yml">
    <img src="https://github.com/beecho01/bfl-openai-image-proxy/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/actions/workflows/publish.yml">
    <img src="https://github.com/beecho01/bfl-openai-image-proxy/actions/workflows/publish.yml/badge.svg" alt="Publish Docker image">
  </a>
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/pkgs/container/bfl-openai-image-proxy">
    <img src="https://img.shields.io/badge/ghcr.io-latest-blue?logo=docker&logoColor=white" alt="Docker Image">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white" alt="Python versions">
  </a>
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/stargazers">
    <img src="https://img.shields.io/github/stars/beecho01/bfl-openai-image-proxy?style=social" alt="Stars">
  </a>
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/network/members">
    <img src="https://img.shields.io/github/forks/beecho01/bfl-openai-image-proxy?style=social" alt="Forks">
  </a>
  <a href="https://github.com/beecho01/bfl-openai-image-proxy/issues">
    <img src="https://img.shields.io/github/issues/beecho01/bfl-openai-image-proxy" alt="Issues">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/beecho01/bfl-openai-image-proxy" alt="License">
  </a>
</p>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#scope">Scope</a></li>
        <li><a href="#what-the-proxy-does">What the Proxy Does</a></li>
        <li><a href="#how-the-proxy-handles-bfls-10-minute-signed-url-expiry">How the Proxy Handles BFL's 10-Minute Signed URL Expiry</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#image-sizes">Image Sizes</a></li>
    <li><a href="#configure-open-webui">Configure Open WebUI</a></li>
    <li><a href="#supported-models">Supported Models</a></li>
    <li><a href="#configuration-reference">Configuration Reference</a></li>
    <li><a href="#privacy">Privacy</a></li>
    <li><a href="#running-tests">Running Tests</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

An OpenAI-compatible image generation and editing proxy for [Open WebUI](https://github.com/open-webui/open-webui). It exposes OpenAI-style endpoints, translates requests into [Black Forest Labs FLUX](https://docs.bfl.ai/) API calls, polls BFL until generation is complete, then returns an OpenAI-compatible image response.

The proxy supports both **text-to-image generation** (`POST /v1/images/generations`) and **image editing** (`POST /v1/images/edits`), covering the full range of FLUX.2, FLUX.1, and FLUX Tools models available through the BFL API.

<p align="right">(<a href="#top">back to top</a>)</p>

### Scope

This proxy supports:

- **Text-to-image generation** via `POST /v1/images/generations` — all FLUX generation endpoints
- **Image editing** via `POST /v1/images/edits` — context-aware editing, inpainting, outpainting, object erasure, deblur, and virtual try-on
- The async poll/retrieve flow used by all BFL endpoints

It does **not** support BFL's fine-tune management endpoints, FLUX 3 video generation (different API shape), or the FLUX 3 Action model. These may be added in future versions.

<p align="right">(<a href="#top">back to top</a>)</p>

### What the Proxy Does

#### Image Generation (`POST /v1/images/generations`)

- Translates OpenAI-style `size` (e.g. `1024x1024`) into BFL `width`/`height`.
- Submits to BFL `POST {BFL_BASE_URL}/v1/{model}`, polls the returned `polling_url` until `status == "Ready"`, then downloads `result.sample`.
- Returns either `b64_json` (default) or `url` response format.

#### Image Editing (`POST /v1/images/edits`)

- Accepts a base64-encoded source image, a text prompt, and optionally a base64-encoded mask.
- Automatically adapts the BFL API payload shape based on the target model:
  - **FLUX.2 models** (`flux-2-max`, `flux-2-pro`, `flux-2-flex`, `flux-2-pro-preview`): sends `input_image` + `prompt` + `width` + `height`
  - **FLUX Kontext models** (`flux-kontext-pro`, `flux-kontext-max`): sends `input_image` + `prompt` (uses aspect ratio, not explicit dimensions)
  - **FLUX Tools erase**: sends `image` + `mask` (no prompt)
  - **FLUX Tools deblur**: sends `image` only (no prompt, no mask)
  - **FLUX Tools outpainting**: sends `input_image` + `width` + `height` + optional `prompt`
  - **FLUX Tools VTO** (virtual try-on): sends `person` + `garment` + `prompt`
  - **FLUX.1 Fill** (inpainting): sends `image` + `mask` + `prompt`
  - **FLUX.1 Expand**: sends `image` + `prompt`
- Strips `data:` URI prefixes from base64 image data (Open WebUI sends these).
- All editing model defaults are configurable via environment variables.

#### General

- Exposes `GET /v1/models` listing all supported FLUX models.
- Exposes `GET /health` for health checks.
- Downloads the generated image **immediately** when ready — BFL's signed `result.sample` URLs expire after 10 minutes, so the proxy fetches the bytes straight away and never exposes the short-lived URL to the client.
- Supports friendly model aliases (e.g. `black-forest-labs/FLUX.2-klein-9B`).
- Optional bearer auth for the proxy.
- Privacy-first: no prompts, images, or API keys are logged by default.
- Temporary generated files are cleaned up automatically after a configurable TTL.

<p align="right">(<a href="#top">back to top</a>)</p>

### How the Proxy Handles BFL's 10-Minute Signed URL Expiry

BFL's `result.sample` is a signed URL that is **only valid for 10 minutes** after generation completes (see the [FLUX.2 text-to-image docs](https://docs.bfl.ai/)). The proxy is designed around this constraint:

- When polling reports `status == "Ready"`, the proxy **downloads the image bytes immediately** from `result.sample` using the same `x-key` header.
- For `response_format=b64_json` (the default), the bytes are base64-encoded and returned inline in the OpenAI response — no URL is exposed to the client, so the 10-minute expiry is irrelevant.
- For `response_format=url`, the downloaded bytes are saved to the proxy's local `/generated` directory and served from `GET /generated/{filename}` via `PUBLIC_BASE_URL`. The URL returned to the client points at the proxy, not at BFL's expiring signed URL, so the client can fetch it for as long as the proxy keeps the file (controlled by `IMAGE_TTL_SECONDS`, default 1 hour).

This means Open WebUI never sees a BFL signed URL and never has to race the 10-minute window.

<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

This project is built with the following major frameworks and libraries:

- [FastAPI](https://fastapi.tiangolo.com/) — async web framework
- [httpx](https://www.python-httpx.org/) — async HTTP client for BFL API calls
- [Pydantic](https://docs.pydantic.dev/) — request/response validation
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [Docker](https://www.docker.com/) — containerised deployment

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

- A [Black Forest Labs API key](https://docs.bfl.ai/)
- Docker and Docker Compose (recommended), or Python 3.11+ if running directly

### Installation

#### Option A: Use the prebuilt image from ghcr.io

A multi-arch image (amd64 + arm64) is published to the GitHub Container Registry on every push to `main` and on every version tag:

```bash
docker pull ghcr.io/beecho01/bfl-openai-image-proxy:latest
```

Tags available:

| Tag | When |
|-----|------|
| `latest` | Latest push to `main` |
| `YYYYMMDD.Iteration` (e.g. `20260628.1`) | Every push to `main` (date + GitHub run number) |
| `main` | Latest push to `main` (branch alias) |
| `1.0.0`, `1.0` | From git tag `v1.0.0` |
| `sha-<short>` | Every push (by commit SHA) |

Use it in your compose file by replacing `build: .` with `image: ghcr.io/beecho01/bfl-openai-image-proxy:latest`.

#### Option B: Build from source

1. Get a BFL API key at [https://docs.bfl.ai/](https://docs.bfl.ai/)
2. Clone the repo

   ```bash
   git clone https://github.com/beecho01/bfl-openai-image-proxy.git
   cd bfl-openai-image-proxy
   ```

3. Copy the example env file and fill in your BFL API key

   ```bash
   cp .env.example .env
   # edit .env and set BFL_API_KEY
   ```

4. Build and run with Docker Compose

   ```bash
   export BFL_API_KEY="your-bfl-api-key"
   export PROXY_API_KEY="choose-a-proxy-secret"

   docker compose -f docker-compose.example.yml up --build
   ```

The service listens on `http://localhost:8000`.

The Dockerfile uses `python:3.12-slim` with a non-root user and a healthcheck. If you prefer the [Chainguard](https://hub.docker.com/r/chainguard/python) hardened image, swap the `FROM` line for `chainguard/python:latest` (ships Python 3.14) and drop the `groupadd`/`useradd` block — but verify dependency compatibility first.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

### Test with curl

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

Edit an image (context-aware editing with FLUX.2):

```bash
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Authorization: Bearer ${PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-2-pro-preview",
    "prompt": "add floral wallpaper to this wall",
    "image": "<base64-encoded-image>",
    "size": "1024x1024",
    "response_format": "b64_json"
  }'
```

Edit an image with FLUX Kontext:

```bash
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Authorization: Bearer ${PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-kontext-pro",
    "prompt": "remove the person in the background",
    "image": "<base64-encoded-image>",
    "response_format": "b64_json"
  }'
```

Inpaint with a mask (FLUX.1 Fill):

```bash
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Authorization: Bearer ${PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro-1.0-fill",
    "prompt": "replace the scratched area with clear paint",
    "image": "<base64-encoded-image>",
    "mask": "<base64-encoded-mask>",
    "response_format": "b64_json"
  }'
```

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- IMAGE SIZES -->
## Image Sizes

Unlike OpenAI's DALL-E (which only accepts `1024x1024`, `1024x1792`, `1792x1024`), BFL accepts **arbitrary integer dimensions** with a minimum of 64px per side. The proxy parses the OpenAI-style `size` string (e.g. `1024x1024`, `1440x2048`, `800x600`) into `width` and `height` integers and forwards them directly to BFL.

- The `1024x1024` default is just a safe fallback when the client doesn't send a `size`.
- Both `x` and `*` separators are accepted (e.g. `1024*1024`).
- The FLUX.2 family supports outputs up to ~4 megapixels (e.g. `2048x2048`). Older FLUX.1 models have different limits. BFL returns a `422` validation error if you exceed a model's maximum, which the proxy surfaces as an OpenAI-style error.
- In Open WebUI, set `IMAGE_SIZE` to any valid dimensions (e.g. `IMAGE_SIZE=1440x2048`).
- For FLUX Kontext models, explicit width/height are not used — the model uses aspect ratio instead.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- CONFIGURE OPEN WEBUI -->
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

To enable image editing in Open WebUI:

```
ENABLE_IMAGE_EDIT=true
IMAGE_EDIT_ENGINE=openai
IMAGES_EDIT_OPENAI_API_BASE_URL=http://bfl-openai-image-proxy:8000/v1
IMAGES_EDIT_OPENAI_API_KEY=<PROXY_API_KEY>
```

If Open WebUI runs in the same Docker network as the proxy, use the container name `bfl-openai-image-proxy` as the host. Otherwise, use the host/port where the proxy is reachable.

### Run alongside Open WebUI in a single Docker Compose stack

Drop the following into a `docker-compose.yml` alongside your Open WebUI deployment so both services share a network and Open WebUI can reach the proxy by container name:

```yaml
services:
  bfl-openai-image-proxy:
    image: ghcr.io/beecho01/bfl-openai-image-proxy:latest
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
      # Image editing model defaults
      DEFAULT_EDIT_MODEL: "flux-2-pro-preview"
      EDIT_MODEL_KONTEXT: "flux-kontext-pro"
      EDIT_MODEL_FLUX2: "flux-2-pro-preview"
      EDIT_MODEL_INPAINT: "flux-pro-1.0-fill"
      EDIT_MODEL_OUTPAINT: "flux-tools/outpainting-v1"
      EDIT_MODEL_ERASE: "flux-tools/erase-v1"
      EDIT_MODEL_DEBLUR: "flux-tools/deblur-v1"
      EDIT_MODEL_VTO: "flux-tools/vto-v2"
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

Open WebUI will be available at `http://localhost:3000` and will use the proxy for image generation and editing. The proxy is only reachable from within the Docker network (Open WebUI reaches it at `http://bfl-openai-image-proxy:8000`); uncomment the `ports` block on the proxy if you also want to test it directly from the host.

> **Note on `PUBLIC_BASE_URL`:** when `response_format=url` is used, the proxy returns image URLs that Open WebUI's browser must be able to fetch. If Open WebUI and the proxy are in the same Docker network but the user's browser is outside it, set `PUBLIC_BASE_URL` to a URL the browser can reach (e.g. `http://localhost:8000` if you expose the proxy port, or your reverse-proxy host). For `response_format=b64_json` (the default), this is not a concern because the image data is embedded in the response.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- SUPPORTED MODELS -->
## Supported Models

### Text-to-Image Generation (`POST /v1/images/generations`)

All models below accept a text `prompt` and `size` parameter.

#### FLUX.2 (latest generation)

| Model | BFL Endpoint | Description |
|-------|-------------|-------------|
| `flux-2-max` | `/v1/flux-2-max` | Top-tier quality, most capable FLUX.2 variant |
| `flux-2-pro-preview` | `/v1/flux-2-pro-preview` | Latest FLUX.2 [pro] — preview endpoint (recommended starting point) |
| `flux-2-pro` | `/v1/flux-2-pro` | Fixed snapshot of FLUX.2 [pro] for reproducibility |
| `flux-2-flex` | `/v1/flux-2-flex` | Flexible FLUX.2 variant with configurable steps/guidance |
| `flux-2-klein-4b` | `/v1/flux-2-klein-4b` | Fast, lightweight FLUX.2 [klein] 4B |
| `flux-2-klein-9b-preview` | `/v1/flux-2-klein-9b-preview` | Latest FLUX.2 [klein] 9B with KV caching (preview) |
| `flux-2-klein-9b` | `/v1/flux-2-klein-9b` | Fixed snapshot of FLUX.2 [klein] 9B for reproducibility |

#### FLUX.1 Kontext (image editing)

| Model | BFL Endpoint | Description |
|-------|-------------|-------------|
| `flux-kontext-max` | `/v1/flux-kontext-max` | Higher quality Kontext editing |
| `flux-kontext-pro` | `/v1/flux-kontext-pro` | Standard Kontext editing |

#### FLUX.1 (legacy generation)

| Model | BFL Endpoint | Description |
|-------|-------------|-------------|
| `flux-pro-1.1-ultra` | `/v1/flux-pro-1.1-ultra` | Ultra high-resolution (4MP) generation |
| `flux-pro-1.1` | `/v1/flux-pro-1.1` | Fast, high-quality generation |
| `flux-pro` | `/v1/flux-pro` | Original FLUX.1 [pro] |
| `flux-dev` | `/v1/flux-dev` | Open-weight development model |

### Image Editing (`POST /v1/images/edits`)

The following models accept a base64-encoded source `image` and a text `prompt`. Some require additional fields:

| Model | BFL Endpoint | Requires | Description |
|-------|-------------|----------|-------------|
| `flux-2-max` | `/v1/flux-2-max` | image + prompt | FLUX.2 [max] context-aware editing (recommended) |
| `flux-2-pro-preview` | `/v1/flux-2-pro-preview` | image + prompt | FLUX.2 [pro] context-aware editing (recommended default) |
| `flux-2-pro` | `/v1/flux-2-pro` | image + prompt | FLUX.2 [pro] fixed snapshot editing |
| `flux-2-flex` | `/v1/flux-2-flex` | image + prompt | FLUX.2 [flex] editing with configurable steps/guidance |
| `flux-kontext-pro` | `/v1/flux-kontext-pro` | image + prompt | FLUX.1 Kontext [pro] — natural language image editing |
| `flux-kontext-max` | `/v1/flux-kontext-max` | image + prompt | FLUX.1 Kontext [max] — higher quality editing |
| `flux-pro-1.0-fill` | `/v1/flux-pro-1.0-fill` | image + mask + prompt | Inpainting — modify masked region |
| `flux-pro-1.0-fill-finetuned` | `/v1/flux-pro-1.0-fill-finetuned` | image + mask + prompt | Inpainting with a finetuned LoRA |
| `flux-pro-1.0-expand` | `/v1/flux-pro-1.0-expand` | image + prompt | Outpainting — expand image borders |
| `flux-tools/outpainting-v1` | `/v1/flux-tools/outpainting-v1` | image + size | FLUX Tools outpainting |
| `flux-tools/erase-v1` | `/v1/flux-tools/erase-v1` | image + mask | Object removal (no prompt needed) |
| `flux-tools/deblur-v1` | `/v1/flux-tools/deblur-v1` | image only | Sharpen blurry images (no prompt needed) |
| `flux-tools/vto-v1` | `/v1/flux-tools/vto-v1` | person + garment + prompt | Virtual try-on v1 |
| `flux-tools/vto-v2` | `/v1/flux-tools/vto-v2` | person + garment + prompt | Virtual try-on v2 (up to 4MP) |

### FLUX 3 (listed for completeness)

| Model | BFL Endpoint | Description |
|-------|-------------|-------------|
| `flux-3-video` | `/v1/flux-3-video` | FLUX 3 multimodal — video with audio (different API shape, not yet integrated for image generation) |

> **Note:** FLUX 3 Image is announced but not yet available via the BFL API. Only FLUX 3 Video is live.

### Friendly Aliases

Friendly aliases are also accepted, e.g. `black-forest-labs/FLUX.2-klein-9B` → `flux-2-klein-9b`.

See the [BFL API documentation](https://docs.bfl.ai/) for the full list of available models and their parameters.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- CONFIGURATION REFERENCE -->
## Configuration Reference

All settings are env-driven. Copy `.env.example` to `.env` and adjust as needed.

Required:

| Variable | Description |
|----------|-------------|
| `BFL_API_KEY` | Your Black Forest Labs API key. |

Optional — Generation:

| Variable | Default | Description |
|----------|---------|-------------|
| `BFL_BASE_URL` | `https://api.eu.bfl.ai` | BFL API base URL. Other options: `https://api.bfl.ai` (global), `https://api.us.bfl.ai`. |
| `DEFAULT_MODEL` | `flux-2-klein-9b-preview` | Model used when the client doesn't specify one for generation. |
| `PROXY_API_KEY` | _(unset)_ | If set, clients must send `Authorization: Bearer <PROXY_API_KEY>`. If unset, unauthenticated access is allowed (a warning is logged at start-up). |
| `PUBLIC_BASE_URL` | _(inferred)_ | Base URL used for returned image URLs when `response_format=url`. If unset, inferred from request headers. |
| `POLL_INTERVAL_SECONDS` | `0.5` | Seconds between BFL polling requests. |
| `REQUEST_TIMEOUT_SECONDS` | `180` | Overall timeout for a generation request (submit + poll + download). |
| `IMAGE_TTL_SECONDS` | `3600` | How long generated files are kept before cleanup (1 hour). |
| `MAX_CONCURRENT_REQUESTS` | `4` | Concurrency semaphore limiting in-flight generations. |
| `LOG_LEVEL` | `info` | Logging level. |
| `LOG_PROMPTS` | `false` | Set to `true` to log prompts. |
| `BFL_PASS_THROUGH_EXTRA_PARAMS` | `false` | Forward unknown request fields to BFL. |
| `STORE_GENERATED_IMAGES` | `false` | Persist generated images beyond TTL cleanup. |
| `GENERATED_DIR` | `/tmp/bfl-openai-image-proxy/generated` | Directory for generated image files. |

Optional — Image Editing:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_EDIT_MODEL` | `flux-2-pro-preview` | Default model for `/v1/images/edits` when the client doesn't specify one. |
| `EDIT_MODEL_KONTEXT` | `flux-kontext-pro` | Default for Kontext-style editing (image + prompt, no mask). |
| `EDIT_MODEL_FLUX2` | `flux-2-pro-preview` | Default for FLUX.2 multi-image editing. |
| `EDIT_MODEL_INPAINT` | `flux-pro-1.0-fill` | Default for inpainting (image + mask + prompt). |
| `EDIT_MODEL_OUTPAINT` | `flux-tools/outpainting-v1` | Default for outpainting / image expansion. |
| `EDIT_MODEL_ERASE` | `flux-tools/erase-v1` | Default for object erasure (image + mask, no prompt). |
| `EDIT_MODEL_DEBLUR` | `flux-tools/deblur-v1` | Default for deblur (image only, no prompt). |
| `EDIT_MODEL_VTO` | `flux-tools/vto-v2` | Default for virtual try-on (person + garment images). |

All editing model variables are configurable so you can update model names without code changes if BFL releases new models or renames existing ones.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- PRIVACY -->
## Privacy

- Prompts are not logged unless `LOG_PROMPTS=true`.
- Base64 image data is never logged.
- API keys are never logged.
- Temporary generated files are deleted after `IMAGE_TTL_SECONDS` (default 1 hour).

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- RUNNING TESTS -->
## Running Tests

```bash
pip install -r requirements.txt
pytest -q
```

CI runs the test suite across Python 3.11, 3.12, and 3.13, plus a Docker build smoke test that verifies the `/health` endpoint responds.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [ ] Add support for FLUX 3 Image when available via BFL API
- [ ] Add support for FLUX 3 Video generation (different API shape)
- [ ] Add request/response examples to OpenAPI docs
- [ ] Add optional Prometheus metrics endpoint
- [ ] Multi-language Support
    - [ ] Chinese
    - [ ] Spanish

See the [open issues](https://github.com/beecho01/bfl-openai-image-proxy/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure `python -m pytest -q` passes before submitting. Keep the proxy's OpenAI-compatible contract and privacy guarantees intact.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Project Link: [https://github.com/beecho01/bfl-openai-image-proxy](https://github.com/beecho01/bfl-openai-image-proxy)

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

- [Black Forest Labs FLUX](https://docs.bfl.ai/) — the underlying image generation and editing API
- [Open WebUI](https://github.com/open-webui/open-webui) — the OpenAI-compatible UI this proxy serves
- [FastAPI](https://fastapi.tiangolo.com/) — the async web framework
- [httpx](https://www.python-httpx.org/) — the async HTTP client
- [Best-README-Template](https://github.com/othneildrew/Best-README-Template) — the README structure this file follows
- [Img Shields](https://shields.io/) — for the badges

<p align="right">(<a href="#top">back to top</a>)</p>