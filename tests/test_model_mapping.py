"""Tests for model mapping and aliases."""
import pytest

from app.models import SUPPORTED_MODELS, normalize_model
from app.errors import BflProxyError


def test_default_model():
    assert normalize_model(None, "flux-dev") == "flux-dev"
    assert normalize_model("", "flux-dev") == "flux-dev"


def test_supported_models_pass_through():
    for m in SUPPORTED_MODELS:
        assert normalize_model(m, "flux-dev") == m


def test_case_insensitive():
    assert normalize_model("FLUX-DEV", "flux-dev") == "flux-dev"


def test_aliases():
    assert normalize_model("black-forest-labs/FLUX.2-klein-9B", "flux-dev") == "flux-2-klein-9b"
    assert normalize_model("black-forest-labs/FLUX.2-klein-9B-preview", "flux-dev") == "flux-2-klein-9b-preview"
    assert normalize_model("black-forest-labs/FLUX.2-klein-4B", "flux-dev") == "flux-2-klein-4b"
    assert normalize_model("black-forest-labs/FLUX.2-pro", "flux-dev") == "flux-2-pro"
    assert normalize_model("black-forest-labs/FLUX.2-pro-preview", "flux-dev") == "flux-2-pro-preview"
    assert normalize_model("black-forest-labs/FLUX.2-flex", "flux-dev") == "flux-2-flex"
    assert normalize_model("black-forest-labs/FLUX.2-max", "flux-dev") == "flux-2-max"


def test_unsupported_model():
    with pytest.raises(ValueError):
        normalize_model("not-a-real-model", "flux-dev")