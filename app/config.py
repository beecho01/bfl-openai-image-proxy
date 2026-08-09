"""Configuration for bfl-openai-image-proxy."""
import os
from functools import lru_cache
from typing import Optional


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


class Settings:
    """Runtime settings loaded from environment variables."""

    def __init__(self) -> None:
        self.bfl_api_key: Optional[str] = os.environ.get("BFL_API_KEY")
        self.bfl_base_url: str = os.environ.get("BFL_BASE_URL", "https://api.eu.bfl.ai").rstrip("/")
        self.default_model: str = os.environ.get("DEFAULT_MODEL", "flux-2-klein-9b-preview")
        self.proxy_api_key: Optional[str] = os.environ.get("PROXY_API_KEY")
        self.public_base_url: Optional[str] = os.environ.get("PUBLIC_BASE_URL")

        self.poll_interval_seconds: float = _as_float(os.environ.get("POLL_INTERVAL_SECONDS"), 0.5)
        self.request_timeout_seconds: float = _as_float(os.environ.get("REQUEST_TIMEOUT_SECONDS"), 180.0)
        self.image_ttl_seconds: int = _as_int(os.environ.get("IMAGE_TTL_SECONDS"), 3600)
        self.max_concurrent_requests: int = _as_int(os.environ.get("MAX_CONCURRENT_REQUESTS"), 4)

        self.log_level: str = os.environ.get("LOG_LEVEL", "info").lower()
        self.log_prompts: bool = _as_bool(os.environ.get("LOG_PROMPTS"), False)
        self.bfl_pass_through_extra_params: bool = _as_bool(os.environ.get("BFL_PASS_THROUGH_EXTRA_PARAMS"), False)
        self.store_generated_images: bool = _as_bool(os.environ.get("STORE_GENERATED_IMAGES"), False)

        self.generated_dir: str = os.environ.get("GENERATED_DIR", "/tmp/bfl-openai-image-proxy/generated")

        # --- Image editing defaults (env-configurable in case BFL changes model names) ---
        # Default model for general image editing (context-aware: "add wallpaper to my wall")
        self.default_edit_model: str = os.environ.get("DEFAULT_EDIT_MODEL", "flux-2-pro-preview")

        # Model for Kontext-style editing (image + prompt, no mask)
        self.edit_model_kontext: str = os.environ.get("EDIT_MODEL_KONTEXT", "flux-kontext-pro")

        # Model for FLUX.2 multi-image editing (image + prompt, up to 8 reference images)
        self.edit_model_flux2: str = os.environ.get("EDIT_MODEL_FLUX2", "flux-2-pro-preview")

        # Model for inpainting (image + mask + prompt)
        self.edit_model_inpaint: str = os.environ.get("EDIT_MODEL_INPAINT", "flux-pro-1.0-fill")

        # Model for outpainting / expand (image + direction + prompt)
        self.edit_model_outpaint: str = os.environ.get("EDIT_MODEL_OUTPAINT", "flux-tools/outpainting-v1")

        # Model for object erasure (image + mask, no prompt)
        self.edit_model_erase: str = os.environ.get("EDIT_MODEL_ERASE", "flux-tools/erase-v1")

        # Model for deblur (image only, no prompt)
        self.edit_model_deblur: str = os.environ.get("EDIT_MODEL_DEBLUR", "flux-tools/deblur-v1")

        # Model for virtual try-on (person image + garment image + prompt)
        self.edit_model_vto: str = os.environ.get("EDIT_MODEL_VTO", "flux-tools/vto-v2")


@lru_cache
def get_settings() -> Settings:
    return Settings()