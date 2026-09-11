#!/usr/bin/env python3
"""Convert a local .html file to a directly displayable image."""

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.config import load_config

CONVERT_ENDPOINT = "https://apis.aimaxhug.cloud/api/convert/file"


def convert_file(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"文件不存在: {file_path}")
    if path.suffix.lower() != ".html":
        raise ValueError("仅支持 .html 文件")

    with path.open("rb") as handle:
        try:
            response = requests.post(
                CONVERT_ENDPOINT,
                headers={"Authorization": f"Bearer {load_config()['api_key']}"},
                files={"file": (path.name, handle, "text/html")},
                timeout=180,
            )
        except requests.exceptions.Timeout as exc:
            raise ValueError("转换请求超时") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ValueError("网络连接失败，请检查网络") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise ValueError(f"响应解析失败: {response.text[:200]}") from exc

    if response.status_code < 200 or response.status_code >= 300 or result.get("code") != 0:
        raise ValueError(result.get("msg", f"HTTP {response.status_code}"))

    url = result.get("data", {}).get("url")
    if not url:
        raise ValueError("返回数据中没有图片链接")
    return url


def main():
    parser = argparse.ArgumentParser(description="将 HTML 文件转换为图片")
    parser.add_argument("file", help="本地 .html 文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    try:
        url = convert_file(args.file)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"success": True, "url": url}, ensure_ascii=False, indent=2))
    else:
        print(f"📍 {url}")
        print(f"🖼️  ![]({url})")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
