"""FastAPI application: OpenAI-compatible image generation proxy for BFL FLUX."""
import asyncio
import base64
import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .bfl_client import BflClient
from .config import get_settings
from .errors import BflProxyError, bfl_proxy_exception_handler, error_response
from .models import (
    SUPPORTED_MODELS,
    ImageData,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ModelInfo,
    ModelListResponse,
    normalize_model,
)
from .storage import ImageStorage

logger = logging.getLogger("bfl-proxy")

# ---------------------------------------------------------------------------
# Size parsing
# ---------------------------------------------------------------------------


def parse_size(size: str) -> Tuple[int, int]:
    """Parse an OpenAI-style size string into (width, height). Raises BflProxyError on invalid."""
    if not size:
        return 1024, 1024
    s = size.strip().lower().replace("*", "x")
    if "x" not in s:
        raise BflProxyError(
            f"Invalid size format: {size}. Expected e.g. '1024x1024'.",
            type="invalid_request_error",
            code="invalid_size",
            status_code=400,
        )
    parts = s.split("x")
    if len(parts) != 2:
        raise BflProxyError(
            f"Invalid size format: {size}. Expected e.g. '1024x1024'.",
            type="invalid_request_error",
            code="invalid_size",
            status_code=400,
        )
    try:
        w = int(parts[0])
        h = int(parts[1])
    except ValueError:
        raise BflProxyError(
            f"Invalid size dimensions: {size}. Width and height must be integers.",
            type="invalid_request_error",
            code="invalid_size",
            status_code=400,
        )
    if w <= 0 or h <= 0:
        raise BflProxyError(
            f"Invalid size dimensions: {size}. Width and height must be positive.",
            type="invalid_request_error",
            code="invalid_size",
            status_code=400,
        )
    return w, h


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = FastAPI(
        title="bfl-openai-image-proxy",
        version="1.0.0",
        description="OpenAI-compatible image generation proxy for Black Forest Labs FLUX.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bfl = BflClient(settings)
    storage = ImageStorage(settings)
    semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    # Startup warnings
    if not settings.bfl_api_key:
        logger.warning("BFL_API_KEY is not set; image generation will fail until it is provided.")
    if not settings.proxy_api_key:
        logger.warning("PROXY_API_KEY is not set; proxy will allow unauthenticated access.")

    # ------------------------------------------------------------------
    # Auth dependency
    # ------------------------------------------------------------------

    async def require_auth(authorization: Optional[str] = Header(default=None)) -> None:
        if not settings.proxy_api_key:
            return
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": "Missing Authorization header.", "type": "auth_error", "code": "missing_auth"}},
            )
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != settings.proxy_api_key:
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": "Invalid API key.", "type": "auth_error", "code": "invalid_api_key"}},
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def infer_public_base_url(request: Request) -> str:
        if settings.public_base_url:
            return settings.public_base_url.rstrip("/")
        host = request.headers.get("host")
        if host:
            scheme = request.headers.get("x-forwarded-proto", "http")
            return f"{scheme}://{host}"
        return "http://localhost:8000"

    def build_bfl_payload(
        req: ImageGenerationRequest,
        model: str,
        width: int,
        height: int,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "prompt": req.prompt,
            "width": width,
            "height": height,
        }
        # Known-safe optional fields
        if req.seed is not None:
            payload["seed"] = req.seed
        if req.guidance is not None:
            payload["guidance"] = req.guidance
        if req.safety_tolerance is not None:
            payload["safety_tolerance"] = req.safety_tolerance
        if req.output_format is not None:
            payload["output_format"] = req.output_format
        if req.web_search is not None:
            payload["web_search"] = req.web_search

        # Extra fields pass-through
        if settings.bfl_pass_through_extra_params:
            known = {
                "model", "prompt", "n", "size", "response_format", "user",
                "quality", "style", "seed", "guidance", "safety_tolerance",
                "output_format", "web_search",
            }
            extras = req.model_dump().get("__pydantic_extra__", {}) or {}
            for k, v in extras.items():
                if k not in known and v is not None:
                    payload[k] = v
        return payload

    async def generate_one(
        req: ImageGenerationRequest,
        model: str,
        width: int,
        height: int,
        request: Request,
    ) -> ImageData:
        payload = build_bfl_payload(req, model, width, height)
        task_id, polling_url = await bfl.submit(model, payload)
        logger.info("submitted bfl task id=%s model=%s", task_id, model)
        sample_url = await bfl.poll_until_ready(polling_url)
        image_bytes = await bfl.download_image(sample_url)

        if req.response_format == "url":
            ext = "png"
            if req.output_format:
                ext = req.output_format.lower()
            filename = storage.save_image(image_bytes, ext=ext)
            base = infer_public_base_url(request)
            return ImageData(url=f"{base}/generated/{filename}")
        # default b64_json
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return ImageData(b64_json=b64)

    # ------------------------------------------------------------------
    # Exception handler
    # ------------------------------------------------------------------

    app.add_exception_handler(BflProxyError, bfl_proxy_exception_handler)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "bfl_api_key_configured": bool(settings.bfl_api_key)}

    @app.get("/v1/models")
    async def list_models(_auth: None = None) -> ModelListResponse:
        created = int(time.time())
        return ModelListResponse(
            data=[ModelInfo(id=m, created=created) for m in SUPPORTED_MODELS]
        )

    @app.post("/v1/images/generations", response_model=ImageGenerationResponse, response_model_exclude_none=True)
    async def images_generations(
        request: Request,
        req: ImageGenerationRequest,
        authorization: Optional[str] = Header(default=None),
    ) -> ImageGenerationResponse:
        await require_auth(authorization)

        if not req.prompt or not req.prompt.strip():
            raise BflProxyError(
                "Missing required field: prompt.",
                type="invalid_request_error",
                code="missing_prompt",
                status_code=400,
            )
        if not settings.bfl_api_key:
            raise BflProxyError(
                "BFL_API_KEY is not configured on the proxy.",
                type="proxy_config_error",
                code="missing_api_key",
                status_code=500,
            )

        try:
            model = normalize_model(req.model, settings.default_model)
        except ValueError as exc:
            raise BflProxyError(
                str(exc),
                type="invalid_request_error",
                code="unsupported_model",
                status_code=400,
            )

        width, height = parse_size(req.size)

        n = max(1, min(req.n, 4))  # cap to 4 to limit abuse

        if settings.log_prompts:
            logger.info("image request model=%s size=%sx%s n=%d prompt=%r", model, width, height, n, req.prompt)
        else:
            logger.info("image request model=%s size=%sx%s n=%d", model, width, height, n)

        async with semaphore:
            start = time.time()
            try:
                tasks = [
                    generate_one(req, model, width, height, request) for _ in range(n)
                ]
                images = await asyncio.gather(*tasks)
            except BflProxyError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("unexpected error during generation: %s", exc)
                raise BflProxyError(
                    f"Unexpected error: {exc}",
                    type="internal_error",
                    code="internal_error",
                    status_code=500,
                )
            duration = time.time() - start
            logger.info("image request complete model=%s n=%d duration=%.2fs", model, n, duration)

        return ImageGenerationResponse(created=int(time.time()), data=list(images))

    @app.get("/generated/{filename}")
    async def serve_generated(filename: str) -> FileResponse:
        # prevent path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(status_code=404)
        if not storage.exists(filename):
            raise HTTPException(status_code=404)
        return FileResponse(storage.full_path(filename))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @app.on_event("startup")
    async def _startup() -> None:
        storage.ensure_dir()
        storage.start_cleanup_task()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await storage.stop_cleanup_task()
        await bfl.aclose()

    return app


app = create_app()