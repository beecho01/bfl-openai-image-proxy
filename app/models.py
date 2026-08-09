"""Pydantic models for OpenAI-compatible request/response and model mapping."""
from typing import List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Model mapping
# ---------------------------------------------------------------------------

SUPPORTED_MODELS: List[str] = [
    # FLUX.2 generation models
    "flux-2-max",
    "flux-2-pro-preview",
    "flux-2-pro",
    "flux-2-flex",
    "flux-2-klein-4b",
    "flux-2-klein-9b-preview",
    "flux-2-klein-9b",
    # FLUX.2 editing models (same endpoints, accept input_image)
    # (these are the same model names — editing is triggered by passing input_image)
    # FLUX.1 Kontext models (editing)
    "flux-kontext-max",
    "flux-kontext-pro",
    # FLUX.1 generation models (legacy)
    "flux-pro-1.1-ultra",
    "flux-pro-1.1",
    "flux-pro",
    "flux-dev",
    # FLUX Tools (editing-specific endpoints)
    "flux-pro-1.0-fill",
    "flux-pro-1.0-fill-finetuned",
    "flux-pro-1.0-expand",
    "flux-tools/outpainting-v1",
    "flux-tools/erase-v1",
    "flux-tools/deblur-v1",
    "flux-tools/vto-v1",
    "flux-tools/vto-v2",
    # FLUX 3 Video (different modality but listed for completeness)
    "flux-3-video",
]

MODEL_ALIASES = {
    "black-forest-labs/FLUX.2-klein-9B": "flux-2-klein-9b",
    "black-forest-labs/FLUX.2-klein-9B-preview": "flux-2-klein-9b-preview",
    "black-forest-labs/FLUX.2-klein-4B": "flux-2-klein-4b",
    "black-forest-labs/FLUX.2-pro": "flux-2-pro",
    "black-forest-labs/FLUX.2-pro-preview": "flux-2-pro-preview",
    "black-forest-labs/FLUX.2-flex": "flux-2-flex",
    "black-forest-labs/FLUX.2-max": "flux-2-max",
    "black-forest-labs/FLUX.1-kontext-pro": "flux-kontext-pro",
    "black-forest-labs/FLUX.1-kontext-max": "flux-kontext-max",
}

# Models that support image editing via input_image parameter
# (same endpoint, just add input_image to the payload)
EDITING_CAPABLE_MODELS = {
    "flux-2-max",
    "flux-2-pro-preview",
    "flux-2-pro",
    "flux-2-flex",
    "flux-kontext-max",
    "flux-kontext-pro",
}

# Models that use a mask (inpainting / erase)
MASK_REQUIRED_MODELS = {
    "flux-pro-1.0-fill",
    "flux-pro-1.0-fill-finetuned",
    "flux-tools/erase-v1",
}

# Models that require an image but no prompt
NO_PROMPT_MODELS = {
    "flux-tools/deblur-v1",
}

# Models that use person + garment images (VTO)
VTO_MODELS = {
    "flux-tools/vto-v1",
    "flux-tools/vto-v2",
}

# Models that use input_image (Kontext style) vs image (FLUX Tools style)
INPUT_IMAGE_FIELD_MODELS = {
    "flux-kontext-max",
    "flux-kontext-pro",
    "flux-tools/outpainting-v1",
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


class ImageEditRequest(BaseModel):
    """OpenAI-compatible image edit request.

    Open WebUI sends:
    - image: base64-encoded image (the source image to edit)
    - prompt: text describing the edit
    - model: model name (optional, falls back to default_edit_model)
    - n: number of images (default 1)
    - size: output size (default 1024x1024)
    - response_format: "b64_json" or "url"
    - mask: base64-encoded mask (optional, for inpainting)
    """
    model: Optional[str] = None
    prompt: Optional[str] = None
    image: Optional[str] = None  # base64-encoded source image
    mask: Optional[str] = None   # base64-encoded mask (optional)
    n: int = 1
    size: str = "1024x1024"
    response_format: str = "b64_json"
    user: Optional[str] = None
    seed: Optional[int] = None
    guidance: Optional[float] = None
    safety_tolerance: Optional[int] = None
    output_format: Optional[str] = None

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