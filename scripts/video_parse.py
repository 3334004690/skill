#!/usr/bin/env python3
"""Parse short-video share links into direct playable URLs."""

import argparse
import json as json_mod
import sys
from urllib.parse import urlparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

VIDEO_PARSE_ENDPOINT = "https://apis.aimaxhug.cloud/v1/video-parse"
SUPPORTED_PLATFORMS = (
    "抖音", "小红书", "快手", "B站", "微博", "皮皮虾", "知乎", "西瓜视频", "TikTok", "YouTube"
)


def _validate_url(value):
    url = (value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("请提供有效的短视频分享链接（必须以 http:// 或 https:// 开头）")
    return url


def _extract_result(response):
    """Validate the documented envelope and return its parsed data."""
    if not isinstance(response, dict):
        raise AimaxhugError("响应格式无效")
    if response.get("success") is False:
        raise AimaxhugError(response.get("message") or "视频解析失败")
    data = response.get("data")
    if not isinstance(data, dict):
        raise AimaxhugError("响应数据中没有视频解析结果")
    if not data.get("url"):
        raise AimaxhugError("响应数据中没有可播放视频 URL")
    return data


def add_parse_args(parser):
    parser.add_argument("url", nargs="?", help="短视频分享链接")
    parser.add_argument("--url", "-u", dest="url_option", help="短视频分享链接")
    parser.add_argument("--json", action="store_true", help="原样输出 JSON 结果")


def cmd_run(args):
    try:
        share_url = _validate_url(args.url_option or args.url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    try:
        response = client.post(VIDEO_PARSE_ENDPOINT, json={"url": share_url}, timeout=120)
        result = _extract_result(response)
    except AimaxhugError as exc:
        print(f"Error: 视频解析失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json_mod.dumps(response, ensure_ascii=False, indent=2))
        return

    print("✅ 视频解析成功！")
    print(f"🎬 标题: {result.get('title') or '未提供'}")
    print(f"🌐 平台: {result.get('platform') or '未提供'}")
    print(f"📍 视频直链: {result['url']}")
    print(f"🔗 [点击播放]({result['url']})")
    if result.get("request_id"):
        print(f"请求 ID: {result['request_id']}")


def main():
    parser = argparse.ArgumentParser(description="短视频解析（提取视频直链）")
    sub = parser.add_subparsers(dest="subcommand")
    run_parser = sub.add_parser("run", help="解析短视频分享链接（默认）")
    add_parse_args(run_parser)
    args = parser.parse_args()

    if args.subcommand == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
