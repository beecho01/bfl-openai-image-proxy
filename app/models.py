"""Pydantic models for OpenAI-compatible request/response and model mapping."""
from typing import List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Model mapping
# ---------------------------------------------------------------------------

SUPPORTED_MODELS: List[str] = [
    "flux-2-max",
    "flux-2-pro-preview",
    "flux-2-pro",
    "flux-2-flex",
    "flux-2-klein-4b",
    "flux-2-klein-9b-preview",
    "flux-2-klein-9b",
    "flux-kontext-max",
    "flux-kontext-pro",
    "flux-pro-1.1-ultra",
    "flux-pro-1.1",
    "flux-pro",
    "flux-dev",
]

MODEL_ALIASES = {
    "black-forest-labs/FLUX.2-klein-9B": "flux-2-klein-9b",
    "black-forest-labs/FLUX.2-klein-9B-preview": "flux-2-klein-9b-preview",
    "black-forest-labs/FLUX.2-klein-4B": "flux-2-klein-4b",
    "black-forest-labs/FLUX.2-pro": "flux-2-pro",
    "black-forest-labs/FLUX.2-pro-preview": "flux-2-pro-preview",
    "black-forest-labs/FLUX.2-flex": "flux-2-flex",
    "black-forest-labs/FLUX.2-max": "flux-2-max",
}


def normalize_model(model: Optional[str], default: str) -> str:
    """Normalize a model name, applying aliases and defaults. Raises ValueError if unsupported."""
    if not model:
        return default
    name = model.strip()
    if name in MODEL_ALIASES:
        name = MODEL_ALIASES[name]
    # case-insensitive match against supported list
    lower_map = {m.lower(): m for m in SUPPORTED_MODELS}
    if name in lower_map:
        return lower_map[name]
    if name.lower() in lower_map:
        return lower_map[name.lower()]
    raise ValueError(f"Unsupported model: {model}")


# ---------------------------------------------------------------------------
# OpenAI-compatible request/response
# ---------------------------------------------------------------------------


class ImageGenerationRequest(BaseModel):
    model: Optional[str] = None
    prompt: Optional[str] = None
    n: int = 1
    size: str = "1024x1024"
    response_format: str = "b64_json"
    user: Optional[str] = None
    quality: Optional[str] = None
    style: Optional[str] = None
    seed: Optional[int] = None
    guidance: Optional[float] = None
    safety_tolerance: Optional[int] = None
    output_format: Optional[str] = None
    web_search: Optional[bool] = None

    model_config = {"extra": "allow"}


class ImageData(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None

    model_config = {"exclude_none": True}


class ImageGenerationResponse(BaseModel):
    created: int
    data: List[ImageData]


class ErrorBody(BaseModel):
    message: str
    type: str = "bfl_api_error"
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "black-forest-labs"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]