"""Async client for the Black Forest Labs FLUX API."""
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

import httpx

from .config import Settings
from .errors import BflProxyError

logger = logging.getLogger("bfl-proxy")


class BflClient:
    """Thin async wrapper around the BFL FLUX API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.request_timeout_seconds),
            )
        return self._client

    def _headers(self) -> Dict[str, str]:
        if not self.settings.bfl_api_key:
            raise BflProxyError(
                "BFL_API_KEY is not configured on the proxy.",
                type="proxy_config_error",
                code="missing_api_key",
                status_code=500,
            )
        return {
            "x-key": self.settings.bfl_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def submit(self, model: str, payload: Dict[str, Any]) -> Tuple[str, str]:
        """POST to BFL to start generation. Returns (task_id, polling_url)."""
        client = await self._get_client()
        url = f"{self.settings.bfl_base_url}/v1/{model}"
        try:
            resp = await client.post(url, json=payload, headers=self._headers())
        except httpx.RequestError as exc:
            raise BflProxyError(
                f"Failed to reach BFL API: {exc}",
                type="bfl_api_error",
                code="upstream_unreachable",
                status_code=502,
            )

        if resp.status_code in (401, 403):
            raise BflProxyError(
                "BFL API rejected the API key (unauthorized).",
                type="bfl_api_error",
                code="upstream_unauthorized",
                status_code=resp.status_code,
            )
        if resp.status_code == 402:
            raise BflProxyError(
                "BFL API returned 402: out of credits.",
                type="bfl_api_error",
                code="out_of_credits",
                status_code=402,
            )
        if resp.status_code == 429:
            raise BflProxyError(
                "BFL API returned 429: rate limit or active task limit reached.",
                type="bfl_api_error",
                code="rate_limited",
                status_code=429,
            )
        if resp.status_code >= 400:
            detail = self._safe_text(resp)
            raise BflProxyError(
                f"BFL API submit failed ({resp.status_code}): {detail}",
                type="bfl_api_error",
                code="upstream_failed",
                status_code=resp.status_code,
            )

        try:
            body = resp.json()
        except Exception:
            raise BflProxyError(
                "Invalid JSON response from BFL API.",
                type="bfl_api_error",
                code="invalid_upstream_response",
                status_code=502,
            )

        task_id = body.get("id")
        polling_url = body.get("polling_url")
        if not task_id or not polling_url:
            raise BflProxyError(
                "BFL API response missing id or polling_url.",
                type="bfl_api_error",
                code="invalid_upstream_response",
                status_code=502,
            )
        return str(task_id), str(polling_url)

    async def poll_until_ready(self, polling_url: str) -> str:
        """Poll the polling_url until status is Ready. Returns the result.sample URL."""
        client = await self._get_client()
        deadline = asyncio.get_event_loop().time() + self.settings.request_timeout_seconds
        last_status: Optional[str] = None
        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise BflProxyError(
                    "Timed out waiting for BFL image generation to complete.",
                    type="bfl_api_error",
                    code="timeout",
                    status_code=504,
                )
            try:
                resp = await client.get(polling_url, headers=self._headers())
            except httpx.RequestError as exc:
                raise BflProxyError(
                    f"Failed to poll BFL API: {exc}",
                    type="bfl_api_error",
                    code="upstream_unreachable",
                    status_code=502,
                )

            if resp.status_code in (401, 403):
                raise BflProxyError(
                    "BFL API rejected the API key while polling (unauthorized).",
                    type="bfl_api_error",
                    code="upstream_unauthorized",
                    status_code=resp.status_code,
                )
            if resp.status_code == 429:
                raise BflProxyError(
                    "BFL API returned 429 while polling: rate limit reached.",
                    type="bfl_api_error",
                    code="rate_limited",
                    status_code=429,
                )
            if resp.status_code >= 400:
                detail = self._safe_text(resp)
                raise BflProxyError(
                    f"BFL API poll failed ({resp.status_code}): {detail}",
                    type="bfl_api_error",
                    code="upstream_failed",
                    status_code=resp.status_code,
                )

            try:
                body = resp.json()
            except Exception:
                raise BflProxyError(
                    "Invalid JSON response from BFL API while polling.",
                    type="bfl_api_error",
                    code="invalid_upstream_response",
                    status_code=502,
                )

            status = str(body.get("status", "")).strip()
            if status != last_status:
                logger.info("bfl task status=%s", status)
                last_status = status

            if status == "Ready":
                result = body.get("result") or {}
                sample = result.get("sample")
                if not sample:
                    raise BflProxyError(
                        "BFL API returned Ready but no result.sample URL.",
                        type="bfl_api_error",
                        code="invalid_upstream_response",
                        status_code=502,
                    )
                return str(sample)

            if status in ("Error", "Failed"):
                detail = body.get("error") or body.get("message") or "unknown error"
                raise BflProxyError(
                    f"BFL image generation failed: {detail}",
                    type="bfl_api_error",
                    code="upstream_failed",
                    status_code=502,
                )

            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def download_image(self, url: str) -> bytes:
        """Download the generated image bytes from a signed URL."""
        client = await self._get_client()
        try:
            resp = await client.get(url)
        except httpx.RequestError as exc:
            raise BflProxyError(
                f"Failed to download generated image: {exc}",
                type="bfl_api_error",
                code="image_download_failed",
                status_code=502,
            )
        if resp.status_code >= 400:
            raise BflProxyError(
                f"Failed to download generated image ({resp.status_code}).",
                type="bfl_api_error",
                code="image_download_failed",
                status_code=502,
            )
        return resp.content

    @staticmethod
    def _safe_text(resp: httpx.Response) -> str:
        try:
            return resp.text[:500]
        except Exception:
            return "<no body>"