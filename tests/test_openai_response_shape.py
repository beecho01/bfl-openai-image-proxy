"""Tests for OpenAI-compatible response shape."""
import base64
import time
from unittest.mock import AsyncMock, MagicMock, patch

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
    # patch the settings used by create_app via the lru_cache
    from app import config as cfg
    cfg.get_settings.cache_clear()
    monkeypatch.setattr(cfg, "Settings", lambda: settings)
    app = create_app()
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_models_list(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    ids = [m["id"] for m in body["data"]]
    assert "flux-dev" in ids
    assert "flux-2-klein-9b-preview" in ids


def test_missing_prompt(client):
    r = client.post("/v1/images/generations", json={"model": "flux-dev"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "missing_prompt"


def test_unsupported_model(client):
    r = client.post(
        "/v1/images/generations",
        json={"model": "nope", "prompt": "hi"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_model"


def test_invalid_size(client):
    r = client.post(
        "/v1/images/generations",
        json={"model": "flux-dev", "prompt": "hi", "size": "big"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_size"


def test_b64_json_response_shape(client, monkeypatch):
    fake_image = b"\x89PNG\r\n\x1a\nfake-png-bytes"
    expected_b64 = base64.b64encode(fake_image).decode("ascii")

    async def fake_submit(self, model, payload):
        return "task-1", "https://poll.example/1"

    async def fake_poll(self, url):
        return "https://image.example/1.png"

    async def fake_download(self, url):
        return fake_image

    monkeypatch.setattr("app.main.BflClient.submit", fake_submit)
    monkeypatch.setattr("app.main.BflClient.poll_until_ready", fake_poll)
    monkeypatch.setattr("app.main.BflClient.download_image", fake_download)

    r = client.post(
        "/v1/images/generations",
        json={"model": "flux-dev", "prompt": "a lighthouse", "response_format": "b64_json"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "created" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0]["b64_json"] == expected_b64
    assert "url" not in body["data"][0]


def test_url_response_shape(client, monkeypatch):
    fake_image = b"\x89PNG\r\n\x1a\nfake-png-bytes"

    async def fake_submit(self, model, payload):
        return "task-1", "https://poll.example/1"

    async def fake_poll(self, url):
        return "https://image.example/1.png"

    async def fake_download(self, url):
        return fake_image

    monkeypatch.setattr("app.main.BflClient.submit", fake_submit)
    monkeypatch.setattr("app.main.BflClient.poll_until_ready", fake_poll)
    monkeypatch.setattr("app.main.BflClient.download_image", fake_download)

    r = client.post(
        "/v1/images/generations",
        json={"model": "flux-dev", "prompt": "a lighthouse", "response_format": "url"},
        headers={"host": "localhost:8000"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["data"]) == 1
    url = body["data"][0]["url"]
    assert url.startswith("http://localhost:8000/generated/")
    assert url.endswith(".png")
    assert "b64_json" not in body["data"][0]


def test_error_response_shape(client, monkeypatch):
    from app.errors import BflProxyError

    async def fake_submit(self, model, payload):
        raise BflProxyError("boom", code="upstream_failed", status_code=502)

    monkeypatch.setattr("app.main.BflClient.submit", fake_submit)

    r = client.post(
        "/v1/images/generations",
        json={"model": "flux-dev", "prompt": "a lighthouse"},
    )
    assert r.status_code == 502
    body = r.json()
    assert body["error"]["message"] == "boom"
    assert body["error"]["type"] == "bfl_api_error"
    assert body["error"]["code"] == "upstream_failed"