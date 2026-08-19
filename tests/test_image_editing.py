"""Tests for FLUX.2 image editing / multi-reference image input."""
import base64
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import Settings


def _make_settings() -> Settings:
    s = Settings()
    s.bfl_api_key = "test-key"
    s.proxy_api_key = None
    s.store_generated_images = True
    s.generated_dir = "/tmp/bfl-openai-image-proxy-test-generated"
    return s


@pytest.fixture
def client(monkeypatch):
    settings = _make_settings()
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    from app import config as cfg
    cfg.get_settings.cache_clear()
    monkeypatch.setattr(cfg, "Settings", lambda: settings)
    app = create_app()
    return TestClient(app)


def _patch_bfl(monkeypatch, captured: dict):
    fake_image = b"\x89PNG\r\n\x1a\nfake-png-bytes"

    async def fake_submit(self, model, payload):
        captured["model"] = model
        captured["payload"] = payload
        return "task-1", "https://poll.example/1"

    async def fake_poll(self, url):
        return "https://image.example/1.png"

    async def fake_download(self, url):
        return fake_image

    monkeypatch.setattr("app.main.BflClient.submit", fake_submit)
    monkeypatch.setattr("app.main.BflClient.poll_until_ready", fake_poll)
    monkeypatch.setattr("app.main.BflClient.download_image", fake_download)


def test_single_reference_image_forwarded(client, monkeypatch):
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "change the weather to sunny",
            "input_image": "https://example.com/photo.jpg",
        },
    )
    assert r.status_code == 200, r.text
    assert captured["payload"]["input_image"] == "https://example.com/photo.jpg"
    assert "input_image_2" not in captured["payload"]


def test_multi_reference_images_mapped_to_input_image_n(client, monkeypatch):
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "combine materials from references",
            "input_image": "https://example.com/primary.jpg",
            "input_images": [
                "https://example.com/ref2.jpg",
                "https://example.com/ref3.jpg",
                "https://example.com/ref4.jpg",
            ],
        },
    )
    assert r.status_code == 200, r.text
    payload = captured["payload"]
    assert payload["input_image"] == "https://example.com/primary.jpg"
    assert payload["input_image_2"] == "https://example.com/ref2.jpg"
    assert payload["input_image_3"] == "https://example.com/ref3.jpg"
    assert payload["input_image_4"] == "https://example.com/ref4.jpg"
    assert "input_image_5" not in payload


def test_too_many_reference_images_rejected(client, monkeypatch):
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "too many refs",
            "input_image": "https://example.com/primary.jpg",
            "input_images": [f"https://example.com/ref{i}.jpg" for i in range(8)],
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "too_many_reference_images"


def test_invalid_reference_image_url_rejected(client, monkeypatch):
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "bad url",
            "input_image": "not-a-url",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_reference_image"


def test_input_images_only_without_primary(client, monkeypatch):
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "refs only",
            "input_images": ["https://example.com/ref1.jpg"],
        },
    )
    assert r.status_code == 200, r.text
    payload = captured["payload"]
    assert "input_image" not in payload
    assert payload["input_image_2"] == "https://example.com/ref1.jpg"


def test_more_than_seven_extra_images_truncated_to_eight_total(client, monkeypatch):
    """BFL caps at 8 reference images via API; extra entries are dropped, not errored."""
    captured: dict = {}
    _patch_bfl(monkeypatch, captured)

    r = client.post(
        "/v1/images/generations",
        json={
            "model": "flux-2-pro-preview",
            "prompt": "truncated",
            "input_image": "https://example.com/primary.jpg",
            "input_images": [f"https://example.com/ref{i}.jpg" for i in range(7)],
        },
    )
    assert r.status_code == 200, r.text
    payload = captured["payload"]
    # primary + 7 extras = 8 total, all mapped
    assert payload["input_image"] == "https://example.com/primary.jpg"
    for i in range(2, 9):
        assert f"input_image_{i}" in payload
    assert "input_image_9" not in payload