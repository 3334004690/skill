"""Reusable HTTP client for the Aimaxhug API with auth."""

import sys
from typing import Optional

import requests

from .config import load_config

BASE_URL = "https://base-api.aimaxhug.com"


class AimaxhugError(Exception):
    """Raised when the Aimaxhug API returns an error."""

    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


class AimaxhugClient:
    """Authenticated HTTP client for Aimaxhug API endpoints.

    Usage::

        client = AimaxhugClient()
        result = client.generate_image(json={...})
        upload_data = client.upload_file(file_path)
    """

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self._api_key = api_key
        else:
            cfg = load_config()
            self._api_key = cfg["api_key"]

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
        }

    def post(self, path: str, json: Optional[dict] = None, **kwargs) -> dict:
        """POST to an API endpoint and return parsed JSON."""
        status_code, data = self.post_with_status(path, json=json, **kwargs)
        if status_code < 200 or status_code >= 300:
            msg = data.get("message", f"HTTP {status_code}")
            raise AimaxhugError(msg, status_code)
        return data

    def post_with_status(self, path: str, json: Optional[dict] = None, **kwargs):
        """POST and return ``(http_status, parsed_json)`` without HTTP raising."""
        url = f"{BASE_URL}{path}" if path.startswith("/") else path
        request_headers = dict(self.headers)
        request_headers.update(kwargs.pop("headers", {}) or {})
        try:
            resp = requests.post(url, headers=request_headers, json=json,
                                 timeout=kwargs.pop("timeout", 900), **kwargs)
        except requests.exceptions.Timeout:
            raise AimaxhugError("请求超时（>900秒）", 0)
        except requests.exceptions.ConnectionError:
            raise AimaxhugError("网络连接失败，请检查网络", 0)

        try:
            data = resp.json()
        except ValueError:
            raise AimaxhugError(f"响应解析失败: {resp.text[:200]}", resp.status_code)

        return resp.status_code, data

    def get(self, path: str, params: Optional[dict] = None, **kwargs) -> dict:
        """GET an authenticated endpoint and return parsed JSON."""
        status_code, data = self.get_with_status(path, params=params, **kwargs)
        if status_code < 200 or status_code >= 300:
            msg = data.get("message", f"HTTP {status_code}")
            raise AimaxhugError(msg, status_code)
        return data

    def get_with_status(self, path: str, params: Optional[dict] = None, **kwargs):
        """GET and return ``(http_status, parsed_json)`` without HTTP raising."""
        url = f"{BASE_URL}{path}" if path.startswith("/") else path
        request_headers = dict(self.headers)
        request_headers.update(kwargs.pop("headers", {}) or {})
        try:
            resp = requests.get(url, headers=request_headers, params=params,
                                timeout=kwargs.pop("timeout", 120), **kwargs)
        except requests.exceptions.Timeout:
            raise AimaxhugError("请求超时（>120秒）", 0)
        except requests.exceptions.ConnectionError:
            raise AimaxhugError("网络连接失败，请检查网络", 0)

        try:
            data = resp.json()
        except ValueError:
            raise AimaxhugError(f"响应解析失败: {resp.text[:200]}", resp.status_code)

        return resp.status_code, data

    def post_file(self, path: str, file_path: str, mime_type: str, **kwargs) -> dict:
        """POST a multipart file upload and return parsed JSON."""
        url = f"{BASE_URL}{path}" if path.startswith("/") else path
        from pathlib import Path
        name = Path(file_path).name
        with open(file_path, "rb") as f:
            try:
                resp = requests.post(
                    url,
                    headers=self.headers,
                    files={"file": (name, f, mime_type)},
                    timeout=kwargs.pop("timeout", 120),
                    **kwargs,
                )
            except requests.exceptions.Timeout:
                raise AimaxhugError("上传超时（>120秒）", 0)
            except requests.exceptions.ConnectionError:
                raise AimaxhugError("网络连接失败，请检查网络", 0)

        try:
            data = resp.json()
        except ValueError:
            raise AimaxhugError(f"响应解析失败: {resp.text[:200]}", resp.status_code)

        if resp.status_code != 200 or data.get("status") != 200:
            msg = data.get("message", f"HTTP {resp.status_code}")
            raise AimaxhugError(msg, resp.status_code)

        return data["data"]
